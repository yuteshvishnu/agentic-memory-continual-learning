# CS 839 HW1 — Refined Plan & Assignment Roadmap

**Continual Learning Through Agent Memory** · Due **Tue Oct 13, 2026** · API budget: **< $5 total**

This document is the single source of truth for the design. It supersedes the earlier
timezone-based convention design in the team plan. It captures the refined rules, the
task sequence, hypotheses, interfaces, repo layout, measurement protocol, and timeline.

---

## 1. Goal in one sentence

Test whether a **fixed LLM agent** gets better over a sequence of 10 tasks **purely through
external memory** — comparing *no memory*, *episodic memory*, and *structured memory* — and
show, with evidence, **when memory helps and when it misleads**.

The underlying model never changes. Any improvement across tasks must come only from what the
agent stores, retrieves, updates, or forgets between tasks. That is the "learning."

---

## 2. Deliverables & hard constraints

- A **3–4 page LaTeX report** (`task2_checker_and_report/report/`).
- **Code** (all task folders).
- **Agent traces** for every run (`outputs/traces/`).
- **Memory snapshots** after every task, plus the final structured memory (`outputs/memory_snapshots/`).
- A statement of **which models and coding tools** we used.
- **Approximate API cost**, with a **hard limit of $5 for the whole team**.
- The six **discussion questions** are answered **orally** with the professor after the due
  date — so every teammate must understand the whole system, not just their own part.

---

## 3. The domain: Madison lake sensor data

The agent plays a **new research assistant** at a lab that monitors Madison's lakes. It answers
**numeric questions** (every answer is a single number) by **writing and running Python** over
sensor CSV files. The lab has **unwritten rules** about the data. A **checker** plays a senior
lab member who grades answers and, when wrong, returns a reviewer message naming the broken
rule. **Memory is what lets the agent stop repeating those mistakes.**

### Stations & firmware

Three stations, each one CSV of **hourly** readings for **July 2026**:

| Station | Firmware | Day convention it follows |
|---|---|---|
| Mendota | v1 | observation day (see C2) |
| Monona  | v1 | observation day (see C2) |
| Wingra  | v2 | normal calendar-midnight day (the exception, see E1) |

The **v1 vs v2 firmware split is the structural hook**: the shared rules apply to the v1
stations, and Wingra (v2) is the exception that tests whether memory stores rules *with their
scope*.

### CSV schema

Each reading carries its own **quality flag** (`*_qc`), as in real limnology / USGS datasets:

```
timestamp,water_temp_C,water_temp_qc,dissolved_oxygen,do_qc,wind_speed,wind_qc
2026-07-04 03:00,22.1,0,7.8,0,3.2,0
2026-07-04 04:00,23.4,0,7.6,0,4.1,0
2026-07-04 05:00,24.9,2,7.5,0,5.0,0        # temp "suspect" but looks valid
2026-07-04 06:00,-9999,3,7.6,0,4.4,0       # temp sensor offline
```

Quality-flag values: `0` = good, `1` = estimated, `2` = suspect, `3` = offline.
`-9999` appears **only** when a flag is `3` (offline). Flags `1` and `2` carry **plausible,
in-range values**, so bad readings cannot be spotted by their value alone.

---

## 4. The four hidden conventions (never stated in prompts)

The agent can only learn these from checker feedback, then must remember them.

| ID | Convention | What the agent does wrong cold |
|---|---|---|
| **C1** | A reading is trustworthy only if its **own quality flag `== 0`**. Exclude flags 1/2/3 for that variable. | Uses all readings, including suspect (flag 2) values that look perfectly normal, biasing the result. |
| **C2** | The lab's **"day" runs 08:00 → 08:00** (an observation day), **for v1 stations** (Mendota, Monona). Applies only to single-day-scoped tasks. | Treats "July 4" as midnight→23:59, grabbing the wrong early-morning hours and missing the right ones. |
| **E1** | **Exception to C2:** Wingra (v2) auto-logs on a **normal calendar-midnight day** — do **not** apply the 08:00 shift to Wingra. | Applies the 08:00 observation-day shift to Wingra, selecting the wrong rows. |
| **E2** | **Exception to C1:** filter flags **per variable, not per row** — never drop a whole row because one variable is flagged. | Drops entire rows whenever any flag is nonzero, losing good readings of other variables (e.g. the true max wind in a row whose temp is flagged). |

### Worked examples

**C1** — mean of four temperatures `22.1 (qc0), 23.4 (qc0), 24.9 (qc2), -9999 (qc3)`:
- keep the `-9999` → garbage (≈ −2482)
- drop only `-9999` but keep the suspect `24.9` → `(22.1+23.4+24.9)/3 = 23.47` (**still wrong**)
- correct (only qc 0) → `(22.1+23.4)/2 = 22.75`

The suspect value is the real test: it is in-range, so only the learned rule "trust only flag 0"
catches it.

**C2** — "mean temp on July 4" at a v1 station:
- naive window = `07-04 00:00` … `07-04 23:59`
- correct window = `07-04 08:00` … `07-05 08:00`

The two windows differ by 8 boundary hours, so the mean/max/count all change.

### Why these are "good difficulty"

- **C1 is moderate, not trivial** — the old `-9999`-only sentinel was a famous missing-data code
  the model excludes automatically, leaving nothing to learn. Suspect-but-plausible flagged values
  force the agent to learn the lab's trust rule.
- **C2 drops all timezone math** — the old UTC→local-day rule was non-obvious but made our own
  answer key error-prone (DST, offsets). An 08:00 observation-day boundary keeps the "a day isn't
  what you think" twist with trivial, reliable ground truth, and still applies to **any variable**.

---

## 5. Task sequence (T1–T10)

Meets the rubric: **4 tasks share the rules (T1–T4), 2 are exceptions (T5–T6), 4 return to or
combine earlier lessons (T7–T10).** Every answer is one number. Exact prompt wording is finalized
by Person 1; prompts must **never state the conventions**.

| Task | Question (answer is one number) | Lessons needed | Role |
|---|---|---|---|
| T1  | Mendota mean water temp, July (whole month) | C1 | Introduce C1 |
| T2  | Monona max water temp on July 4 | C1, C2 | Introduce C2 |
| T3  | Mendota hours above 25 °C on July 10 | C1, C2 | Reinforce |
| T4  | Monona mean dissolved oxygen on July 15 | C1, C2 | Reinforce (C2 on a non-temp variable) |
| T5  | Wingra mean water temp on July 4 | C1, **E1** | **Exception** — do not shift Wingra's day |
| T6  | Mendota max wind speed, July (whole month) | C1, **E2** | **Exception** — per-variable flag filtering |
| T7  | Mendota − Monona daily mean temp, July 20 | C1, C2 | Return to pattern |
| T8  | Wingra − Mendota daily mean temp, July 22 | C2 **+ E1** | Combine (08:00 day for Mendota, midnight day for Wingra, same task) |
| T9  | Wingra max wind speed on **July 18** | **E1, E2** | Combine exceptions (midnight day **and** per-variable flags) |
| T10 | Monona hours with dissolved oxygen below 5 mg/L, July 25 | C1, C2 | Return to pattern |

**Scoping rule for the answer key:** the C2 observation-day boundary applies **only to
single-day-scoped tasks**. Whole-month ("July") tasks use the plain calendar month
(`07-01 00:00` … `07-31 23:59`) to keep those answers unambiguous.

**Data-design requirements Person 1 must engineer so the traps actually fire:**
- Each day-scoped task's answer must **differ** between the midnight window and the 08:00 window
  (put relevant readings in the 00:00–08:00 boundary hours).
- For T6/T9, the true **max wind** must sit in a row whose **water_temp_qc ≠ 0**, so whole-row
  dropping loses it.
- Suspect (flag 1/2) values must be **in-range and plausible** so they can't be caught by value.

### What could transfer

The flag-trust rule (C1), the observation-day definition (C2), and the two **scoped** exceptions
(Wingra's day, per-variable flag filtering). **A memory that stores rules without their scope will
fail T5, T6, T8, and T9** — that is the whole point.

---

## 6. Hypotheses (commit to git **before** any runs)

**H1 — memory helps.** On the rule-reuse tasks (T2–T4, T7, T10), **structured memory** reaches
**≥ 80% first-attempt success** and uses fewer attempts on average, while **no memory stays ≤ 30%**,
because no memory must rediscover C1 and C2 on every task.

**H2 — memory hurts or does nothing.** On **T5**, both memory conditions have **lower
first-attempt success than no memory**, because they over-apply the 08:00 observation-day shift to
Wingra. On **T6**, **episodic** memory does worse than structured if a retrieved trace shows whole
rows being dropped. On **T1**, all three conditions perform the same, since nothing has been
learned yet.

Both hypotheses are **falsifiable from the first-attempt-success numbers** per task per condition.

---

## 7. The three memory conditions

Same model, same prompt template, same single tool (Python execution) across all three. Only the
memory differs. The actual memory available to the agent is **snapshotted after every task**.

| Condition | Carries between tasks | What it tests |
|---|---|---|
| **No memory** | Nothing — each task starts cold. | Baseline: the model's raw ability. Must rediscover every rule. |
| **Episodic** | Prior task traces / short summaries; relevant past episodes injected. | Does *unstructured* recall help? Expected to clutter and to mislead at the exceptions. |
| **Structured** | A compact memory of reusable facts, procedures, warnings, and failure conditions, with our own **write / retrieve / update / forget** rules. | Can a *distilled* memory encode "rule + scope + exception" and apply it correctly? |

**The grading signal lives in structured memory's update/forget logic:** when a task reveals an
exception (e.g. Wingra), does the memory get **edited** ("08:00 day — v1 stations only; Wingra uses
midnight") rather than blindly appended? That edit is the learning.

---

## 8. Shared interfaces & data contracts

Change these only by team agreement. Everyone codes against them from the start, using mocks until
the real pieces land.

```python
# shared/interfaces.py  (whole team)
class Memory:
    def retrieve(self, task: dict) -> str: ...          # text injected into the prompt
    def update(self, task: dict, trace: dict, success: bool) -> None: ...
    def snapshot(self) -> str: ...                        # saved after every task

# task2_checker_and_report/checker.py  (Person 2)
def check(task: dict, answer: float) -> tuple[bool, str]: ...   # (correct?, reviewer feedback)

# task3_agent_and_runner/agent.py  (Person 3)
def run_task(task: dict, memory_text: str, max_attempts: int = 3) -> dict: ...
# returns: answer, success, first_try, attempts, n_calls, in_tokens, out_tokens, trace
```

**`tasks.json` entry shape** (Person 1):

```json
{
  "id": "T5",
  "prompt": "...",
  "files": ["task1_data_and_tasks/data/wingra.csv"],
  "answer": 21.37,
  "tol": 0.05,
  "wrong_variants": {
    "applied_observation_day_shift": [20.81, "Reviewer: Wingra (v2) logs on a normal midnight day — don't apply the 08:00 observation-day shift."],
    "kept_flagged_readings": [22.90, "Reviewer: use only quality-flag-0 readings."]
  }
}
```

**Note:** the skeleton's `check(task, answer: str)` stub must be updated to `answer: float` to
match this contract (the Python tool returns a number).

---

## 9. Repo layout & ownership

We **keep the skeleton's per-person folder layout** (good for the 5-branch workflow). The team
plan's flat `memory/` layout maps onto it as follows:

| Folder / file | Owner | Delivers |
|---|---|---|
| `task1_data_and_tasks/` — `generate_data.py`, `tasks.json`, `data/` | Person 1 | The three station CSVs (with `*_qc` columns) and the 10 tasks with answers, tolerances, and `wrong_variants`. |
| `task2_checker_and_report/` — `checker.py`, `report/` | Person 2 | The checker (grade + reviewer feedback), committed hypotheses, final report; leads submission. |
| `task3_agent_and_runner/` — `agent.py`, `run_experiment.py` | Person 3 | The agent loop (writes & runs Python, retries on feedback), the experiment runner, cost logging, the results plot. |
| `task4_episodic_memory/` — `no_memory.py`, `episodic.py` | Person 4 | No-memory baseline and episodic memory. |
| `task5_structured_memory/` — `structured.py` | Person 5 | Structured memory with write/retrieve/update/forget rules. |
| `shared/interfaces.py` | Whole team | The `Memory` base class. |
| `outputs/{results,traces,memory_snapshots}/` | Written by the runner | `results/` (per-task metrics, `calls.csv`), `traces/`, `memory_snapshots/`. |

**Workflow:** one branch per person (`task1`–`task5`), small PRs into `main` (protected), edit only
your own folder. Run everything from the repo root (`python -m task3_agent_and_runner.run_experiment`)
so `shared` imports resolve. Never commit `.env`; copy `.env.example` and fill it in locally.

---

## 10. Measurement protocol

**Metrics per task per condition:** first-attempt success, final success, attempts used, model
calls, input tokens, output tokens, cost.

**Rules for all conditions:**
- One model, one prompt template, one tool (Python execution) across all three conditions.
- Memory-writing LLM calls use the **same model**, and their tokens **count toward cost**.
- One shared API key with a hard spend limit; **every call is logged to `outputs/results/calls.csv`**.
- Run **3 full repeats** of the 10-task sequence per condition = **90 task-runs**; repeat more only
  for close or surprising comparisons (to check stability).
- Record every model and coding tool each person used, for the report.

**Report must include:** one table or plot of performance across the sequence; two trajectory
deep-dives — **one where memory helped** (ideally a T7–T10 reuse) and **one where memory misled**
(ideally T5 over-applying the day shift to Wingra); and the **final structured memory**.

---

## 11. Validity risks to watch during integration

- **Is C1 actually non-trivial for the chosen model?** Verify on the Monday no-memory run that
  first-attempt success on C1 tasks is genuinely low. If the model trusts only flag-0 readings
  unprompted, strengthen the trap (more suspect-but-plausible values; don't hint at `*_qc` in the
  system prompt).
- **C2 carries most of H1's signal** (it's the least guessable rule). Keep an eye on whether
  no-memory ever stumbles into the 08:00 convention by luck.
- **Single-run noise.** Any claim near the H1/H2 thresholds must be backed by the 3 repeats (or
  more) — report variance, not just a point estimate.
- **Prompt leakage.** The system prompt and tool description must be identical across conditions and
  must not hint at any convention.

---

## 12. Roadmap & timeline

Critical path: **Person 1's T1 data** (needed ~Sun 6pm) → **Monday 10am integration**. Everyone else
builds against mocks until then.

| When | Milestone | Owner |
|---|---|---|
| Sun 5:00–5:30pm | Kickoff: confirm this plan, pick the model, set up the shared API key | All |
| Sun ~6pm | T1 data + task pushed; hypotheses committed to git | P1, P2 |
| Sun 11pm | All modules pushed and tested against mocks | All |
| Mon 10am | Integration: one full no-memory run of T1–T10 works end to end | P3 |
| Mon 10am–3pm | All 90 runs, plus repeats on close comparisons | P3 (P4, P5 watch memory) |
| Mon 3–9pm | Table/plot, two trajectories, full report draft | All |
| Tue | Polish to 3–4 pages; bundle code, traces, snapshots; submit | P2 |

---

## 13. Report & discussion-question ownership

**Report sections**

| Section | Owner |
|---|---|
| Task sequence and what transfers | Person 1 |
| Hypotheses; final merge and editing | Person 2 |
| Methods (agent, metrics), results table/plot, cost | Person 3 |
| Episodic memory design; trajectory where memory misled | Person 4 |
| Structured memory design; final memory dump; trajectory where memory helped | Person 5 |

**Oral discussion questions** (3–5 evidence bullets each, by Tuesday)

| Question | Owner |
|---|---|
| Did either memory system improve over time? What shows real learning? | Person 3 |
| What information was most useful to remember? | Person 5 |
| How did the agent handle an exception or conflict? | Person 1 |
| Did it retrieve a useful memory and still fail to apply it? | Person 4 |
| What should have been updated or forgotten? What would we change? | Person 2 |
