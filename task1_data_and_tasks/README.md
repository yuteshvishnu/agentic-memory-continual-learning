# Task 1: Data and Tasks

- **Owner:** Person 1 (Akshat)
- **Delivers:** the three station CSVs in `data/` and the 10 numeric tasks with answers in
  `tasks.json`.
- **Deadline:** T1 by Sun 6pm, all by Sun 11pm. (On the critical path — everyone else mocks
  against your outputs until integration.)

See [../PLAN.md](../PLAN.md) §3–§5 for the full data and sequence design.

## The CSVs (`data/`)

Three stations, hourly readings for **July 2026**. Each reading carries its own quality flag:

```
timestamp,water_temp_C,water_temp_qc,dissolved_oxygen,do_qc,wind_speed,wind_qc
2026-07-04 03:00,22.1,0,7.8,0,3.2,0
2026-07-04 05:00,24.9,2,7.5,0,5.0,0        # temp "suspect" but looks valid
2026-07-04 06:00,-9999,3,7.6,0,4.4,0       # temp sensor offline
```

- Stations: `mendota.csv`, `monona.csv` (firmware **v1**), `wingra.csv` (firmware **v2**).
- Flags: `0` good, `1` estimated, `2` suspect, `3` offline. `-9999` appears **only** with flag `3`.
- Flags `1`/`2` must carry **plausible, in-range values** — bad readings can't be spotted by value.

### Data-design requirements (so the traps actually fire)

- Each **day-scoped** task's answer must **differ** between the midnight window and the 08:00
  observation-day window (put relevant readings in the 00:00–08:00 boundary hours).
- For **T6/T9**, the true **max wind** must sit in a row whose `water_temp_qc != 0`, so whole-row
  dropping loses it.
- The C2 observation-day boundary applies **only to single-day tasks**; whole-month ("July") tasks
  use the plain calendar month.

## The tasks (`tasks.json`)

Ten tasks, each answer a single number. Prompts must **never state the conventions**. Entry shape:

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

The sequence (T1–T10), lessons needed, and role are in [../PLAN.md](../PLAN.md) §5.
