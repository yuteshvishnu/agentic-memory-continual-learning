# Task 4: No-Memory and Episodic Memory

- **Owner:** Person 4 (`<name>`)
- **Delivers:** the no-memory baseline (`no_memory.py`) and episodic memory (`episodic.py`), both
  implementing `shared/interfaces.py`.
- **Deadline:** Sun 11pm.
- **Report:** episodic memory design + the trajectory where memory **misled** (see
  [../PLAN.md](../PLAN.md) §13).

See [../PLAN.md](../PLAN.md) §7 for how the conditions differ.

## No memory (`no_memory.py`)

The baseline. `retrieve` returns `""`, `update` is a no-op, `snapshot` returns empty. Each task
starts cold, so the agent must rediscover C1/C2 every time — expected ≤ 30% first-attempt success.

## Episodic memory (`episodic.py`)

Retains **past task traces or short summaries** and injects relevant episodes into the prompt.

- `update`: store a summary/trace of the task just finished (what was asked, the mistake, the
  correction).
- `retrieve`: surface the episodes most relevant to the current task.
- `snapshot`: dump the current episode store (saved after every task).

Expected behavior that drives **H2**: unstructured recall clutters over time and can **mislead** —
e.g. on T6 a retrieved trace showing whole rows being dropped reinforces the wrong (per-row) flag
handling. That T6 (or T5) case is the "memory misled" trajectory for the report.
