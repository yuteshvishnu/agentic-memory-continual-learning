"""Person 5: structured memory -- scoped rules, exceptions, and forgetting.

Zero LLM calls. Memory starts empty; nothing is pre-written. A rule's text is
never invented or paraphrased -- it is the exact checker reviewer message that
first produced it (classified by substring match into one of four hidden
conventions):

    C1  flag-trust        ("quality flag is 0")
    C2  observation-day   ("08:00 to 08:00" / "midnight")
    E1  Wingra exception to C2  ("Wingra" / "standard calendar day")
    E2  per-variable exception to C1  ("per sensor" / "other readings in that row")

A rule's scope is not written by us either -- it is assembled from evidence:
the station(s)/variable(s)/day-scope of the task that first taught it, plus
any later task where it was active and the agent solved the task on the first
try (labeled "retrieved, solved first try" -- weak evidence, since a first-try
success doesn't prove the agent actually used the memory). A task that only
re-triggers a known exception, or re-violates an already-learned rule, adds
no scope evidence to the parent rule at all -- the former is recorded only
under that exception's own evidence, and the latter is already captured by
retrieved_but_not_applied below. An exception stores the verbatim exception
message plus the
concrete station/variable situation that produced it (derived from the task,
never hardcoded), and retrieve() marks whether that situation matches the
current task.

Forgetting: whenever an exception is attached to a rule for the first time,
the pre-edit version of that rule (as it stood just before learning the
exception) is frozen into a separate retired entry -- it shows up in
snapshot() but is never returned by retrieve(). Separately, if a rule (or an
already-known exception on it) was handed to the agent via retrieve() and the
task still failed on feedback naming that same rule, that is logged as
retrieved_but_not_applied on the rule -- evidence for cases where a useful
memory was retrieved and still not applied.
"""

from __future__ import annotations

import re

from shared.interfaces import Memory

STATIONS = ("mendota", "monona", "wingra")

VARIABLE_KEYWORDS = {
    "water_temp": ("temperature", "°c", "deg c"),
    "dissolved_oxygen": ("oxygen",),
    "wind_speed": ("wind",),
}

EXCEPTION_PARENT = {"E1": "C2", "E2": "C1"}


def _stations_from_files(files: list[str]) -> list[str]:
    text = " ".join(files).lower()
    return [s for s in STATIONS if s in text]


def _variables_from_prompt(prompt: str) -> list[str]:
    lower = prompt.lower()
    return [var for var, keywords in VARIABLE_KEYWORDS.items() if any(kw in lower for kw in keywords)]


def _scope_from_prompt(prompt: str) -> str:
    lower = prompt.lower()
    if re.search(r"\bon july \d", lower):
        return "single_day"
    if "during july" in lower:
        return "whole_month"
    return "unknown"


def classify_feedback(message: str) -> list[str]:
    """Map a checker reviewer message to every convention it names.

    A single message can name more than one rule (e.g. a combined "you broke
    both C1 and C2" reviewer message), so this checks all four patterns --
    no early return -- and returns every kind that matched, in the order
    checked: E1, E2, C2, C1.
    """
    if not message:
        return []
    lower = message.lower()
    kinds = []
    if "wingra" in lower or "standard calendar day" in lower:
        kinds.append("E1")
    if "per sensor" in lower or "other readings in that row" in lower:
        kinds.append("E2")
    if "08:00 to 08:00" in lower or "midnight" in lower or "how the day is defined" in lower:
        kinds.append("C2")
    if "flag is 0" in lower:   # matches both "quality flag is 0" and "own flag is 0"
        kinds.append("C1")
    return kinds


class StructuredMemory(Memory):
    def __init__(self):
        self.rules: dict[str, dict] = {}

    # ---------- task context (never keys off task["id"]) ----------

    def _task_context(self, task: dict) -> dict:
        stations = _stations_from_files(task.get("files", []))
        variables = _variables_from_prompt(task.get("prompt", ""))
        day_scope = _scope_from_prompt(task.get("prompt", ""))
        return {
            "stations": stations,
            "variables": variables,
            "day_scope": day_scope,
            "station_str": "+".join(stations) or "unknown",
            "variable_str": "+".join(variables) or "unknown",
        }

    # ---------- retrieve ----------

    def retrieve(self, task: dict) -> str:
        ctx = self._task_context(task)
        ids = self._relevant_rule_ids(ctx["day_scope"])
        if not ids:
            return ""
        lines = []
        for i, rid in enumerate(ids, start=1):
            rule = self.rules[rid]
            lines.append(f"{i}. {rule['text']}")
            lines.append(f"   Scope: {self._render_scope(rule['evidence'])}")
            for exc in rule["exceptions"]:
                key, _, value = exc["situation"].partition("=")
                if key == "station":
                    # Station exceptions (e.g. Wingra) are specific claims about one
                    # station, so it's meaningful to say whether this task hits it.
                    applies = self._situation_matches(exc["situation"], ctx)
                    tag = "applies to this task" if applies else "does not apply to this task"
                    lines.append(f"   Exception ({exc['situation']}, {tag}): {exc['text']}")
                else:
                    # Variable-based exceptions (e.g. per-variable flag filtering) come
                    # from a reviewer message that is worded generally -- it doesn't
                    # name a station or variable scope to check the task against, so
                    # show it neutrally instead of claiming it does/doesn't apply.
                    task_ids = ", ".join(exc["evidence"])
                    lines.append(f"   Exception (learned on {value}, {task_ids}): {exc['text']}")
        return "\n".join(lines)

    def _relevant_rule_ids(self, day_scope: str) -> list[str]:
        ids = []
        c1 = self.rules.get("C1")
        if c1 and c1["status"] == "active":
            ids.append("C1")
        c2 = self.rules.get("C2")
        if c2 and c2["status"] == "active" and day_scope == "single_day":
            # Retrieval heuristic, not a learned fact: the observation-day rule only
            # matters for single-day questions (whole-month tasks use the plain
            # calendar month), so it's withheld there to avoid noise.
            ids.append("C2")
        return ids

    def _situation_matches(self, situation: str, ctx: dict) -> bool:
        key, _, value = situation.partition("=")
        if key == "station":
            return value in ctx["stations"]
        if key == "variable":
            return value in ctx["variables"]
        return False

    def _render_scope(self, evidence: list[dict]) -> str:
        return "; ".join(
            f"{e['action']} at {e['station']}/{e['variable']}/{e['day_scope']} ({e['task_id']})"
            for e in evidence
        )

    # ---------- update ----------

    def update(self, task: dict, trace: dict, success: bool) -> None:
        task_id = task["id"]
        ctx = self._task_context(task)
        attempts = trace.get("attempts", [])

        # Snapshot "what was in play before this task" so retrieved_but_not_applied
        # only fires on memory the agent actually had, not on lessons this task itself
        # just taught for the first time.
        retrieved_ids = set(self._relevant_rule_ids(ctx["day_scope"]))
        pre_exception_situations = {
            rid: {e["situation"] for e in self.rules[rid]["exceptions"]} for rid in retrieved_ids
        }

        feedback_by_kind: dict[str, str] = {}
        for attempt in attempts:
            feedback = attempt.get("feedback", "")
            for kind in classify_feedback(feedback):
                # A combined message (e.g. "you broke both rules") names more than one
                # kind for the same attempt -- handle every one of them, not just the first.
                feedback_by_kind[kind] = feedback
                if kind in ("C1", "C2"):
                    self._write_or_reinforce(kind, feedback, task_id, ctx)
                else:
                    self._apply_exception(kind, feedback, task_id, ctx)

        for rule_id in retrieved_ids:
            hit = rule_id in feedback_by_kind
            if not hit:
                exc_kind = "E1" if rule_id == "C2" else "E2"
                if exc_kind in feedback_by_kind:
                    situation = self._situation_for(exc_kind, ctx, feedback_by_kind[exc_kind])
                    hit = situation in pre_exception_situations.get(rule_id, set())
            if hit:
                self._mark_retrieved_but_not_applied(rule_id, task_id)

        first_try_success = success and len(attempts) == 1 and attempts[0].get("feedback", "") == ""
        if first_try_success:
            for rule_id in self._relevant_rule_ids(ctx["day_scope"]):
                self._confirm(rule_id, task_id, ctx)

    def _new_rule(self, rule_id: str, kind: str) -> dict:
        rule = {
            "id": rule_id,
            "kind": kind,
            "text": None,
            "evidence": [],
            "exceptions": [],
            "retrieved_but_not_applied": {"count": 0, "task_ids": []},
            "status": "active",
        }
        self.rules[rule_id] = rule
        return rule

    def _evidence_entry(self, task_id: str, action: str, ctx: dict) -> dict:
        return {"task_id": task_id, "action": action, "station": ctx["station_str"],
                "variable": ctx["variable_str"], "day_scope": ctx["day_scope"]}

    def _write_or_reinforce(self, rule_id: str, feedback: str, task_id: str, ctx: dict) -> None:
        kind = "flag_trust" if rule_id == "C1" else "observation_day"
        rule = self.rules.get(rule_id)
        if rule is None:
            # Only the task that FIRST creates the rule gets a scope-evidence entry here.
            # A later task that violates the same rule again isn't positive scope evidence
            # (it didn't confirm anything) -- that failure is already captured honestly by
            # retrieved_but_not_applied, in update().
            rule = self._new_rule(rule_id, kind)
            rule["text"] = feedback
            rule["evidence"].append(self._evidence_entry(task_id, "learned", ctx))

    def _situation_for(self, exc_kind: str, ctx: dict, feedback: str = "") -> str:
        # A diff-task (e.g. "Wingra minus Mendota") can reference two stations, but the
        # exception is only ABOUT whichever one the reviewer message actually names --
        # so match the message text first, and only fall back to the full station/
        # variable context when the message itself doesn't name one (as with E2, whose
        # wording is generic). This keeps the same situation key across task shapes.
        lower = feedback.lower()
        if exc_kind == "E1":
            matched = [s for s in ctx["stations"] if s in lower]
            return f"station={'+'.join(matched) or ctx['station_str']}"
        matched = [v for v in ctx["variables"] if v.replace("_", " ") in lower]
        return f"variable={'+'.join(matched) or ctx['variable_str']}"

    def _apply_exception(self, exc_kind: str, feedback: str, task_id: str, ctx: dict) -> None:
        parent_id = EXCEPTION_PARENT[exc_kind]
        kind = "flag_trust" if parent_id == "C1" else "observation_day"
        rule = self.rules.get(parent_id)
        just_created = rule is None
        if just_created:
            rule = self._new_rule(parent_id, kind)
            rule["text"] = feedback   # edge case: the parent is learned via its own exception

        situation = self._situation_for(exc_kind, ctx, feedback)
        existing = next((e for e in rule["exceptions"] if e["situation"] == situation), None)
        if existing is None:
            if not just_created:
                self._retire_copy(rule, task_id,
                                   reason=f"narrowed by exception learned at {task_id}: {feedback}")
            rule["exceptions"].append({"situation": situation, "text": feedback, "evidence": [task_id]})
        elif task_id not in existing["evidence"]:
            existing["evidence"].append(task_id)
        # A task that teaches or re-triggers an exception is evidence about the EXCEPTION,
        # not the general rule -- it belongs only in rule["exceptions"][...]["evidence"]
        # above, never in the parent rule's own evidence/scope list (even when this task
        # happened to be the one that created the parent rule).

    def _retire_copy(self, rule: dict, task_id: str, reason: str) -> None:
        retired_id = f"{rule['id']}@{task_id}"
        self.rules[retired_id] = {
            "id": retired_id,
            "kind": rule["kind"],
            "text": rule["text"],
            "evidence": [dict(e) for e in rule["evidence"]],
            "exceptions": [dict(e, evidence=list(e["evidence"])) for e in rule["exceptions"]],
            "retrieved_but_not_applied": dict(rule["retrieved_but_not_applied"],
                                               task_ids=list(rule["retrieved_but_not_applied"]["task_ids"])),
            "status": "retired",
            "superseded_by": rule["id"],
            "retired_at": task_id,
            "reason": reason,
        }

    def _mark_retrieved_but_not_applied(self, rule_id: str, task_id: str) -> None:
        rbna = self.rules[rule_id]["retrieved_but_not_applied"]
        if task_id not in rbna["task_ids"]:
            rbna["count"] += 1
            rbna["task_ids"].append(task_id)

    def _confirm(self, rule_id: str, task_id: str, ctx: dict) -> None:
        # A first-try success is weak evidence at best -- we can't tell whether the agent
        # actually used the rule or would have gotten it right anyway, so this is labeled
        # accordingly rather than as a firm "confirmed".
        rule = self.rules.get(rule_id)
        if rule is None or rule["status"] != "active":
            return
        if self._has_matching_station_exception(rule, ctx):
            # The rule's general form doesn't cover this station -- its exception does.
            # Crediting the parent rule here would claim scope it doesn't have.
            return
        if any(e["task_id"] == task_id for e in rule["evidence"]):
            return
        rule["evidence"].append(self._evidence_entry(task_id, "retrieved, solved first try", ctx))

    def _has_matching_station_exception(self, rule: dict, ctx: dict) -> bool:
        return any(exc["situation"].startswith("station=") and self._situation_matches(exc["situation"], ctx)
                   for exc in rule["exceptions"])

    # ---------- snapshot ----------

    def snapshot(self) -> str:
        if not self.rules:
            return "Structured memory: empty (no lessons learned yet)."
        lines = ["Structured memory snapshot", "=" * 27]
        for rule in self.rules.values():
            header = f"\n[{rule['id']}] status={rule['status']}"
            if rule["status"] == "retired":
                header += f" superseded_by={rule['superseded_by']} retired_at={rule['retired_at']}"
            lines.append(header)
            if rule["status"] == "retired":
                lines.append(f"  Reason: {rule['reason']}")
            lines.append(f"  Rule (verbatim feedback): {rule['text']}")
            lines.append(f"  Scope: {self._render_scope(rule['evidence'])}")
            for exc in rule["exceptions"]:
                lines.append(f"  Exception ({exc['situation']}): {exc['text']} "
                             f"[seen at: {', '.join(exc['evidence'])}]")
            rbna = rule["retrieved_but_not_applied"]
            if rbna["count"]:
                lines.append(f"  Retrieved but not applied: {rbna['count']} time(s) "
                             f"({', '.join(rbna['task_ids'])})")
        return "\n".join(lines)
