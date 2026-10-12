# Task 5: Structured Memory

- **Owner:** Person 5 (`<name>`)
- **Delivers:** structured memory (`structured.py`) with rules, exceptions and forgetting,
  implementing `shared/interfaces.py`.
- **Deadline:** Sun 11pm.
- **Report:** structured memory design + the final memory dump + the trajectory where memory
  **helped** (see [../PLAN.md](../PLAN.md) §13).

See [../PLAN.md](../PLAN.md) §7 for how the conditions differ.

## Structured memory (`structured.py`)

Maintains a **compact memory of reusable facts, procedures, warnings, and failure conditions** —
you design the write / retrieve / update / forget rules. This is the condition the experiment is
really about.

- `retrieve`: return the compact rule set as prompt text.
- `update`: distill the task trace into rules. **The grading signal is in the update/forget
  logic** — when a task reveals an exception (e.g. Wingra), the memory should be **edited**
  ("08:00 day — v1 stations only; Wingra uses midnight day") rather than blindly appended. Store
  rules **with their scope** so T5/T6/T8/T9 don't over-apply them.
- `snapshot`: dump the current structured memory (saved after every task; the final one goes in the
  report).

Expected behavior that drives **H1**: a well-scoped memory turns earlier corrections into first-try
successes on T2–T4, T7, T10. A good "memory helped" trajectory is a late task (T7–T10) reusing C1/C2
correctly on the first attempt.
