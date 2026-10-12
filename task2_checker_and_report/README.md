# Task 2: Checker and Report

- **Owner:** Person 2 (`<name>`)
- **Delivers:** `checker.py` (grades answers with reviewer feedback), committed hypotheses, the
  report in `report/`; leads submission.
- **Deadline:** checker by Sun 11pm; hypotheses committed by Sun 6pm (before any runs).

See [../PLAN.md](../PLAN.md) §6 (hypotheses) and §13 (report ownership).

## The checker

Plays a senior lab member grading the new assistant. Two jobs: decide right/wrong (within
`tol`), and when wrong return a short reviewer message that **names the broken convention** so the
agent can learn it.

```python
def check(task: dict, answer: float) -> tuple[bool, str]:
    # (correct?, feedback message when wrong)
```

- Compare `answer` to `task["answer"]` within `task["tol"]`.
- When wrong, match against `task["wrong_variants"]` (known-mistake value → feedback) to return the
  specific convention-naming message; fall back to a generic "try again" otherwise.
- Deterministic — not an LLM judge.

> Note: this signature uses `float` (the Python tool returns a number). Update the skeleton stub
> accordingly.

## Hypotheses (commit before any runs)

- **H1 (memory helps):** on T2–T4, T7, T10, structured memory ≥ 80% first-attempt success and
  fewer attempts; no memory ≤ 30%.
- **H2 (memory hurts/does nothing):** on T5 both memory conditions do worse than no memory (they
  over-apply the 08:00 shift to Wingra); episodic worse than structured on T6; all equal on T1.

## Report (`report/`)

3–4 page LaTeX (Overleaf export). Must include: one table/plot across the sequence; two trajectory
deep-dives (one where memory helped, one where it misled); and the final structured memory.
Person 2 does final merge/editing and leads the Tuesday submission (code + traces + snapshots).
