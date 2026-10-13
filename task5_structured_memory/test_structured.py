"""Simulates T1-T10 against StructuredMemory using the real wrong_variants feedback
from task1_data_and_tasks/tasks.json. No LLM/API calls -- fake traces are built by
hand so update()/retrieve()/snapshot() can be tested in isolation.

Run from the repo root:
    /opt/anaconda3/bin/python -m pytest task5_structured_memory/test_structured.py -v -s
"""

import json
from pathlib import Path

import pytest

from task5_structured_memory.structured import StructuredMemory

TASKS_JSON = Path(__file__).resolve().parent.parent / "task1_data_and_tasks" / "tasks.json"
TASKS = {t["id"]: t for t in json.loads(TASKS_JSON.read_text())}

KNOWN_FEEDBACK = {
    feedback
    for task in TASKS.values()
    for _, feedback in task.get("wrong_variants", {}).values()
}


def feedback_for(task_id: str, mistake_key: str) -> str:
    return TASKS[task_id]["wrong_variants"][mistake_key][1]


def make_trace(task_id: str, wrong_feedbacks: list[str], final_success: bool = True) -> dict:
    """One failed attempt per entry in wrong_feedbacks, then (if final_success) one
    more attempt with empty feedback. Mirrors the shape agent.run_task produces."""
    attempts = [
        {"attempt": i, "code": "", "stdout": "", "answer": None, "feedback": fb, "runs": []}
        for i, fb in enumerate(wrong_feedbacks, start=1)
    ]
    if final_success:
        attempts.append({"attempt": len(attempts) + 1, "code": "", "stdout": "",
                          "answer": TASKS[task_id]["answer"], "feedback": "", "runs": []})
    return {
        "task_id": task_id, "answer": TASKS[task_id]["answer"], "success": final_success,
        "memory_text": "", "attempts": attempts, "messages": [],
    }


def learn_c1_c2(memory: StructuredMemory) -> None:
    memory.update(TASKS["T1"], make_trace("T1", [feedback_for("T1", "kept_flagged")]), True)
    memory.update(TASKS["T2"], make_trace("T2", [feedback_for("T2", "calendar_day"),
                                                  feedback_for("T2", "kept_flagged")]), True)


def learn_everything(memory: StructuredMemory) -> None:
    learn_c1_c2(memory)
    memory.update(TASKS["T5"], make_trace("T5", [feedback_for("T5", "shifted_wingra"),
                                                  feedback_for("T5", "kept_flagged")]), True)
    memory.update(TASKS["T6"], make_trace("T6", [feedback_for("T6", "row_drop")]), True)


@pytest.fixture
def memory() -> StructuredMemory:
    return StructuredMemory()


def test_memory_starts_empty(memory):
    assert memory.rules == {}
    assert memory.retrieve(TASKS["T1"]) == ""


def test_c1_appears_after_t1(memory):
    assert memory.retrieve(TASKS["T1"]) == ""
    memory.update(TASKS["T1"], make_trace("T1", [feedback_for("T1", "kept_flagged")]), True)
    assert "C1" in memory.rules
    assert memory.rules["C1"]["status"] == "active"
    assert memory.rules["C1"]["evidence"][0]["task_id"] == "T1"
    assert memory.rules["C1"]["evidence"][0]["action"] == "learned"
    assert "C2" not in memory.rules


def test_c2_appears_after_t2(memory):
    memory.update(TASKS["T1"], make_trace("T1", [feedback_for("T1", "kept_flagged")]), True)
    assert "C2" not in memory.rules
    memory.update(TASKS["T2"], make_trace("T2", [feedback_for("T2", "calendar_day"),
                                                  feedback_for("T2", "kept_flagged")]), True)
    assert "C2" in memory.rules
    assert memory.rules["C2"]["status"] == "active"


def test_no_prewritten_text_anywhere_in_memory(memory):
    """Every rule's text must be one of the checker's exact reviewer messages --
    never an invented/paraphrased convention like "v1 = Mendota, Monona"."""
    learn_everything(memory)
    memory.update(TASKS["T3"], make_trace("T3", [feedback_for("T3", "calendar_day"),
                                                  feedback_for("T3", "kept_flagged")]), True)
    for rule in memory.rules.values():
        assert rule["text"] in KNOWN_FEEDBACK
        for exc in rule["exceptions"]:
            assert exc["text"] in KNOWN_FEEDBACK
    # The scope/snapshot machinery must not contain hand-written convention summaries.
    full_text = memory.snapshot() + "".join(memory.retrieve(TASKS[t]) for t in TASKS)
    for banned in ("v1 stations (mendota, monona)", "single-day only", "normal calendar day rule"):
        assert banned not in full_text.lower()


def test_wingra_exception_edits_c2_and_retires_pre_edit_copy(memory):
    learn_c1_c2(memory)
    memory.update(TASKS["T5"], make_trace("T5", [feedback_for("T5", "shifted_wingra"),
                                                  feedback_for("T5", "kept_flagged")]), True)

    active_ids = [rid for rid, r in memory.rules.items() if r["status"] == "active"]
    retired_ids = [rid for rid, r in memory.rules.items() if r["status"] == "retired"]
    assert sorted(active_ids) == ["C1", "C2"]
    assert len(retired_ids) == 1

    retired = memory.rules[retired_ids[0]]
    assert retired["superseded_by"] == "C2"
    assert retired["retired_at"] == "T5"
    assert retired["exceptions"] == []        # pre-edit copy had no exception yet

    c2 = memory.rules["C2"]
    assert len(c2["exceptions"]) == 1
    assert c2["exceptions"][0]["situation"] == "station=wingra"
    assert c2["exceptions"][0]["text"] == feedback_for("T5", "shifted_wingra")


def test_per_variable_exception_edits_c1_and_retires_pre_edit_copy(memory):
    learn_c1_c2(memory)
    memory.update(TASKS["T6"], make_trace("T6", [feedback_for("T6", "row_drop")]), True)

    retired_ids = [rid for rid, r in memory.rules.items() if r["status"] == "retired"]
    assert len(retired_ids) == 1
    retired = memory.rules[retired_ids[0]]
    assert retired["superseded_by"] == "C1"
    assert retired["retired_at"] == "T6"

    c1 = memory.rules["C1"]
    assert len(c1["exceptions"]) == 1
    assert c1["exceptions"][0]["situation"] == "variable=wind_speed"
    assert c1["exceptions"][0]["text"] == feedback_for("T6", "row_drop")


def test_retired_rule_never_appears_in_retrieve(memory):
    learn_c1_c2(memory)
    memory.update(TASKS["T5"], make_trace("T5", [feedback_for("T5", "shifted_wingra"),
                                                  feedback_for("T5", "kept_flagged")]), True)
    retired_ids = [rid for rid, r in memory.rules.items() if r["status"] == "retired"]
    assert retired_ids   # sanity: a retired copy really was created
    for task in TASKS.values():
        day_scope = memory._task_context(task)["day_scope"]
        ids_returned = memory._relevant_rule_ids(day_scope)
        assert set(ids_returned) <= {"C1", "C2"}              # never a retired/composite id
        for rid in ids_returned:
            assert memory.rules[rid]["status"] == "active"
        note = memory.retrieve(task)
        for retired_id in retired_ids:
            assert retired_id not in note


def test_retrieve_wingra_task_shows_wingra_exception(memory):
    learn_everything(memory)
    note = memory.retrieve(TASKS["T9"])   # Wingra, single-day (July 18)
    assert "station=wingra" in note
    assert "applies to this task" in note
    assert feedback_for("T5", "shifted_wingra") in note


def test_retrieve_mendota_task_shows_exception_as_not_applying(memory):
    learn_everything(memory)
    note = memory.retrieve(TASKS["T3"])   # Mendota, single-day -- not Wingra
    assert "station=wingra" in note
    assert "does not apply to this task" in note


def test_retrieve_shows_variable_exception_neutrally_not_applies_tagged(memory):
    learn_everything(memory)
    for task_id in ("T3", "T5", "T9"):      # any task where C1 (and its exception) surfaces
        note = memory.retrieve(TASKS[task_id])
        assert "learned on wind_speed, T6" in note
        assert feedback_for("T6", "row_drop") in note
        # The variable-based exception line itself must carry no applies/does-not-apply claim.
        exception_line = next(line for line in note.splitlines() if feedback_for("T6", "row_drop") in line)
        assert "applies to this task" not in exception_line
        assert "does not apply to this task" not in exception_line


def test_retrieve_whole_month_task_omits_day_rule(memory):
    learn_everything(memory)
    note = memory.retrieve(TASKS["T1"])   # Mendota, whole month -> C2 withheld
    assert feedback_for("T1", "kept_flagged") in note
    assert "08:00" not in note


def test_no_duplicate_rules_or_exceptions_on_repeat(memory):
    learn_everything(memory)
    n_rules_before = len(memory.rules)
    n_c2_exceptions_before = len(memory.rules["C2"]["exceptions"])

    memory.update(TASKS["T8"], make_trace("T8", [feedback_for("T8", "shifted_wingra")]), True)

    assert len(memory.rules) == n_rules_before                      # no new rule entries
    assert len(memory.rules["C2"]["exceptions"]) == n_c2_exceptions_before   # edited, not duplicated
    assert memory.rules["C2"]["exceptions"][0]["evidence"].count("T8") == 1


def test_retrieved_but_not_applied_recorded_on_repeated_failure(memory):
    # T1 creates C1 (not a "retrieved but not applied" case -- nothing existed yet).
    # T2 creates C2, but by then C1 already exists and is retrieved for T2 -- and T2's
    # trace still fails on a C1 violation before correcting, so that IS a real hit.
    learn_c1_c2(memory)
    assert memory.rules["C1"]["retrieved_but_not_applied"]["count"] == 1
    assert memory.rules["C1"]["retrieved_but_not_applied"]["task_ids"] == ["T2"]
    assert memory.rules["C2"]["retrieved_but_not_applied"]["count"] == 0   # C2 didn't exist before T2

    # T3: Mendota single-day. Both C1 and C2 now exist and are retrieved -- but the
    # agent still gets both wrong before correcting, i.e. it had the memory and
    # didn't apply it.
    memory.update(TASKS["T3"], make_trace("T3", [feedback_for("T3", "calendar_day"),
                                                  feedback_for("T3", "kept_flagged")]), True)
    assert memory.rules["C1"]["retrieved_but_not_applied"]["count"] == 2
    assert memory.rules["C1"]["retrieved_but_not_applied"]["task_ids"] == ["T2", "T3"]
    assert memory.rules["C2"]["retrieved_but_not_applied"]["count"] == 1
    assert memory.rules["C2"]["retrieved_but_not_applied"]["task_ids"] == ["T3"]


def test_retrieved_but_not_applied_not_counted_on_the_learning_task(memory):
    # T1 is the task that CREATES C1 -- it must not count as "retrieved but not applied".
    memory.update(TASKS["T1"], make_trace("T1", [feedback_for("T1", "kept_flagged")]), True)
    assert memory.rules["C1"]["retrieved_but_not_applied"]["count"] == 0


def test_retrieved_but_not_applied_for_a_known_exception_ignored_again(memory):
    learn_everything(memory)
    # T9 combines E1+E2 on Wingra; simulate the agent ignoring the already-known
    # Wingra exception again before correcting.
    memory.update(TASKS["T9"], make_trace("T9", [feedback_for("T9", "shifted_wingra")]), True)
    assert memory.rules["C2"]["retrieved_but_not_applied"]["count"] == 1
    assert "T9" in memory.rules["C2"]["retrieved_but_not_applied"]["task_ids"]


def test_full_sequence_t1_through_t10_and_print_final_snapshot(memory):
    learn_everything(memory)
    memory.update(TASKS["T3"], make_trace("T3", [feedback_for("T3", "calendar_day"),
                                                  feedback_for("T3", "kept_flagged")]), True)
    memory.update(TASKS["T4"], make_trace("T4", [feedback_for("T4", "calendar_day"),
                                                  feedback_for("T4", "kept_flagged")]), True)
    for task_id in ("T7", "T8", "T9", "T10"):
        memory.update(TASKS[task_id], make_trace(task_id, []), True)   # memory applies cleanly now

    active = {rid for rid, r in memory.rules.items() if r["status"] == "active"}
    retired = {rid for rid, r in memory.rules.items() if r["status"] == "retired"}
    assert active == {"C1", "C2"}
    assert len(retired) == 2   # one pre-edit copy retired for each of C1 and C2

    final_snapshot = memory.snapshot()
    assert "retired" in final_snapshot
    assert "superseded_by" in final_snapshot
    assert "Retrieved but not applied" in final_snapshot
    print("\n----- FINAL STRUCTURED MEMORY SNAPSHOT (after T1-T10) -----")
    print(final_snapshot)
    print("-------------------------------------------------------------")
