"""Person 1: reference answers + planted wrong variants for every task.

For each task this computes the CORRECT answer (all conventions applied) and the
value an agent gets if it ignores exactly one convention:

  kept_flagged   C1 ignored  -- no quality-flag filtering at all
  calendar_day   C2 ignored  -- used midnight->midnight for a v1 station
  shifted_wingra E1 ignored  -- applied the 08:00 observation-day shift to Wingra
  row_drop       E2 ignored  -- dropped whole rows whenever any flag was nonzero

`build_tasks(data_dir)` returns the full tasks.json content (answers computed from
the CSVs, so it stays in sync with generate_data.py).

Run from the repo root:  python -m task1_data_and_tasks.reference   (writes tasks.json)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
TASKS_JSON = HERE / "tasks.json"
TOL = 0.05

# Reviewer messages: name the broken convention, never give code.
C1_MSG = "Readings aren't trustworthy unless their own quality flag is 0; drop estimated, suspect, and offline values."
C2_MSG = "Lab days run 08:00 to 08:00 local for the v1 stations, not midnight to midnight."
E1_MSG = "Wingra's v2 logger already records on the standard calendar day; don't apply the 08:00 observation-day shift."
E2_MSG = "Quality flags are per sensor; a flag on one reading doesn't invalidate the other readings in that row."
# Compound mistake (more than one rule broken at once). Names the quality-flag rule
# first; once the agent fixes it the answer lands on the calendar_day corner, whose
# message then names the day rule -- so the two hints arrive one per attempt.
BOTH_MSG = "More than one convention is off here. Start with data quality: use only readings whose own flag is 0, then reconsider how the day is defined."


def load_station(name: str) -> tuple[pd.DataFrame, str]:
    path = DATA_DIR / f"{name}.csv"
    with open(path) as f:
        header = f.readline()
    firmware = "v2" if "firmware=v2" in header else "v1"
    df = pd.read_csv(path, comment="#", parse_dates=["timestamp"])
    return df, firmware


# --- window + filter helpers ---

def valid(df: pd.DataFrame, var: str) -> pd.DataFrame:
    """Keep rows whose own flag for `var` is 0 (C1 / E2 done correctly)."""
    qc = {"water_temp_C": "water_temp_qc", "dissolved_oxygen": "do_qc", "wind_speed": "wind_qc"}[var]
    return df[df[qc] == 0]


def obs_day(df: pd.DataFrame, date: str) -> pd.DataFrame:
    start = pd.Timestamp(date) + pd.Timedelta(hours=8)
    return df[(df["timestamp"] >= start) & (df["timestamp"] < start + pd.Timedelta(hours=24))]


def cal_day(df: pd.DataFrame, date: str) -> pd.DataFrame:
    start = pd.Timestamp(date)
    return df[(df["timestamp"] >= start) & (df["timestamp"] < start + pd.Timedelta(hours=24))]


def lab_day(df: pd.DataFrame, firmware: str, date: str) -> pd.DataFrame:
    """Correct lab day for the station: observation (08:00) for v1, calendar for v2."""
    return cal_day(df, date) if firmware == "v2" else obs_day(df, date)


def all_clean(df: pd.DataFrame) -> pd.DataFrame:
    """The E2 mistake: drop a whole row if ANY variable is flagged."""
    return df[(df["water_temp_qc"] == 0) & (df["do_qc"] == 0) & (df["wind_qc"] == 0)]


def cold_compounds() -> dict[str, tuple[float, bool]]:
    """Cold-agent compound mistake per multi-rule task: calendar/midnight day AND no
    flag filtering (C1 and C2 broken together). Returns {task_id: (value, is_count)}.

    A no-memory agent on its first attempt knows neither rule, so it lands exactly here
    -- the corner the single-rule wrong_variants don't cover. `_tasks` plants a
    `both_rules` variant for each of these whose value is distinct from the answer and
    the other variants, so the checker can still name a rule instead of going generic.
    """
    mendota, _ = load_station("mendota")
    monona, _ = load_station("monona")
    wingra, _ = load_station("wingra")
    r2 = lambda x: round(float(x), 2)  # noqa: E731
    return {
        "T2": (r2(cal_day(monona, "2026-07-04")["water_temp_C"].max()), False),
        "T3": (int((cal_day(mendota, "2026-07-10")["water_temp_C"] > 25).sum()), True),
        "T4": (r2(cal_day(monona, "2026-07-15")["dissolved_oxygen"].mean()), False),
        "T7": (r2(cal_day(mendota, "2026-07-20")["water_temp_C"].mean()
                  - cal_day(monona, "2026-07-20")["water_temp_C"].mean()), False),
        "T8": (r2(cal_day(wingra, "2026-07-22")["water_temp_C"].mean()
                  - cal_day(mendota, "2026-07-22")["water_temp_C"].mean()), False),
        "T10": (int((cal_day(monona, "2026-07-25")["dissolved_oxygen"] < 5).sum()), True),
    }


def suspect_values() -> dict[str, tuple[float, bool]]:
    """Half-learned-C1 mistake per mean/count task: drop the -9999 offline readings
    (flag 3) but KEEP the suspect/estimated ones (flags 1 and 2). Returns
    {task_id: (value, is_count)}.

    This is the mistake an agent makes once it has figured out "-9999 is junk" but not
    the full rule "trust only flag 0". The data is planted so this value is outside
    tolerance (otherwise it would be graded correct, and C1 would go untested here);
    `_tasks` plants a `kept_suspect` variant carrying the flag-rule message.
    """
    mendota, _ = load_station("mendota")
    monona, _ = load_station("monona")
    wingra, _ = load_station("wingra")
    r2 = lambda x: round(float(x), 2)  # noqa: E731

    def keep12(df: pd.DataFrame, var: str) -> pd.Series:
        qc = {"water_temp_C": "water_temp_qc", "dissolved_oxygen": "do_qc"}[var]
        return df[df[qc] != 3][var]  # drop offline (flag 3) only; keep flags 1 and 2

    return {
        "T1": (r2(keep12(mendota, "water_temp_C").mean()), False),
        "T4": (r2(keep12(obs_day(monona, "2026-07-15"), "dissolved_oxygen").mean()), False),
        "T7": (r2(keep12(obs_day(mendota, "2026-07-20"), "water_temp_C").mean()
                  - keep12(obs_day(monona, "2026-07-20"), "water_temp_C").mean()), False),
        "T8": (r2(keep12(cal_day(wingra, "2026-07-22"), "water_temp_C").mean()
                  - keep12(obs_day(mendota, "2026-07-22"), "water_temp_C").mean()), False),
        "T10": (int((keep12(obs_day(monona, "2026-07-25"), "dissolved_oxygen") < 5).sum()), True),
    }


def _distinct(value, answer, existing: list, is_count: bool) -> bool:
    """A new variant value is worth planting only if it's cleanly separated from the
    answer (> 0.1 / >= 1) and from every existing variant (> tol / >= 1)."""
    if is_count:
        return abs(value - answer) >= 1 and all(abs(value - v) >= 1 for v in existing)
    return abs(value - answer) > 0.1 and all(abs(value - v) > TOL for v in existing)


# --- per-task computation: returns (answer, {variant_name: [value, message]}) ---

def _tasks():
    mendota, _ = load_station("mendota")
    monona, _ = load_station("monona")
    wingra, _ = load_station("wingra")

    def r2(x):
        return round(float(x), 2)

    specs = []

    # T1 -- Mendota mean water temp, July (C1)
    specs.append((
        "T1",
        "Using task1_data_and_tasks/data/mendota.csv, what was the mean water temperature (deg C) "
        "at Lake Mendota during July 2026? Reply with one number to 2 decimals.",
        ["task1_data_and_tasks/data/mendota.csv"],
        r2(valid(mendota, "water_temp_C")["water_temp_C"].mean()),
        {"kept_flagged": [r2(mendota["water_temp_C"].mean()), C1_MSG]},
    ))

    # T2 -- Monona max water temp on July 4 (C1, C2)
    obs = obs_day(monona, "2026-07-04")
    cal = cal_day(monona, "2026-07-04")
    specs.append((
        "T2",
        "Using task1_data_and_tasks/data/monona.csv, what was the maximum water temperature (deg C) "
        "at Lake Monona on July 4, 2026? Reply with one number to 2 decimals.",
        ["task1_data_and_tasks/data/monona.csv"],
        r2(valid(obs, "water_temp_C")["water_temp_C"].max()),
        {
            "calendar_day": [r2(valid(cal, "water_temp_C")["water_temp_C"].max()), C2_MSG],
            "kept_flagged": [r2(obs["water_temp_C"].max()), C1_MSG],
        },
    ))

    # T3 -- Mendota hours above 25 C on July 10 (C1, C2)
    obs = obs_day(mendota, "2026-07-10")
    cal = cal_day(mendota, "2026-07-10")
    specs.append((
        "T3",
        "Using task1_data_and_tasks/data/mendota.csv, how many hourly readings exceeded 25 deg C "
        "at Lake Mendota on July 10, 2026? Reply with one integer.",
        ["task1_data_and_tasks/data/mendota.csv"],
        int((valid(obs, "water_temp_C")["water_temp_C"] > 25).sum()),
        {
            "calendar_day": [int((valid(cal, "water_temp_C")["water_temp_C"] > 25).sum()), C2_MSG],
            "kept_flagged": [int((obs["water_temp_C"] > 25).sum()), C1_MSG],
        },
    ))

    # T4 -- Monona mean dissolved oxygen on July 15 (C1, C2)
    obs = obs_day(monona, "2026-07-15")
    cal = cal_day(monona, "2026-07-15")
    specs.append((
        "T4",
        "Using task1_data_and_tasks/data/monona.csv, what was the mean dissolved oxygen (mg/L) "
        "at Lake Monona on July 15, 2026? Reply with one number to 2 decimals.",
        ["task1_data_and_tasks/data/monona.csv"],
        r2(valid(obs, "dissolved_oxygen")["dissolved_oxygen"].mean()),
        {
            "calendar_day": [r2(valid(cal, "dissolved_oxygen")["dissolved_oxygen"].mean()), C2_MSG],
            "kept_flagged": [r2(obs["dissolved_oxygen"].mean()), C1_MSG],
        },
    ))

    # T5 -- Wingra mean water temp on July 4 (C1, E1)
    correct = cal_day(wingra, "2026-07-04")
    shifted = obs_day(wingra, "2026-07-04")
    specs.append((
        "T5",
        "Using task1_data_and_tasks/data/wingra.csv, what was the mean water temperature (deg C) "
        "at Lake Wingra on July 4, 2026? Reply with one number to 2 decimals.",
        ["task1_data_and_tasks/data/wingra.csv"],
        r2(valid(correct, "water_temp_C")["water_temp_C"].mean()),
        {
            "shifted_wingra": [r2(valid(shifted, "water_temp_C")["water_temp_C"].mean()), E1_MSG],
            "kept_flagged": [r2(correct["water_temp_C"].mean()), C1_MSG],
        },
    ))

    # T6 -- Mendota max wind speed, July (C1-flavored E2)
    specs.append((
        "T6",
        "Using task1_data_and_tasks/data/mendota.csv, what was the maximum wind speed (m/s) "
        "at Lake Mendota during July 2026? Reply with one number to 2 decimals.",
        ["task1_data_and_tasks/data/mendota.csv"],
        r2(valid(mendota, "wind_speed")["wind_speed"].max()),
        {"row_drop": [r2(all_clean(mendota)["wind_speed"].max()), E2_MSG]},
    ))

    # T7 -- Mendota minus Monona daily mean temp, July 20 (C1, C2)
    m_obs = valid(obs_day(mendota, "2026-07-20"), "water_temp_C")["water_temp_C"].mean()
    n_obs = valid(obs_day(monona, "2026-07-20"), "water_temp_C")["water_temp_C"].mean()
    m_cal = valid(cal_day(mendota, "2026-07-20"), "water_temp_C")["water_temp_C"].mean()
    n_cal = valid(cal_day(monona, "2026-07-20"), "water_temp_C")["water_temp_C"].mean()
    m_obs_raw = obs_day(mendota, "2026-07-20")["water_temp_C"].mean()
    n_obs_raw = obs_day(monona, "2026-07-20")["water_temp_C"].mean()
    specs.append((
        "T7",
        "Using task1_data_and_tasks/data/mendota.csv and task1_data_and_tasks/data/monona.csv, "
        "what was Lake Mendota's mean water temperature (deg C) minus Lake Monona's mean water "
        "temperature on July 20, 2026 (Mendota minus Monona)? Reply with one number to 2 decimals.",
        ["task1_data_and_tasks/data/mendota.csv", "task1_data_and_tasks/data/monona.csv"],
        r2(m_obs - n_obs),
        {
            "calendar_day": [r2(m_cal - n_cal), C2_MSG],
            "kept_flagged": [r2(m_obs_raw - n_obs_raw), C1_MSG],
        },
    ))

    # T8 -- Wingra minus Mendota daily mean temp, July 22 (C2 + E1)
    w_cal = valid(cal_day(wingra, "2026-07-22"), "water_temp_C")["water_temp_C"].mean()
    w_obs = valid(obs_day(wingra, "2026-07-22"), "water_temp_C")["water_temp_C"].mean()
    m_obs2 = valid(obs_day(mendota, "2026-07-22"), "water_temp_C")["water_temp_C"].mean()
    m_cal2 = valid(cal_day(mendota, "2026-07-22"), "water_temp_C")["water_temp_C"].mean()
    w_cal_raw = cal_day(wingra, "2026-07-22")["water_temp_C"].mean()
    m_obs2_raw = obs_day(mendota, "2026-07-22")["water_temp_C"].mean()
    specs.append((
        "T8",
        "Using task1_data_and_tasks/data/wingra.csv and task1_data_and_tasks/data/mendota.csv, "
        "what was Lake Wingra's mean water temperature (deg C) minus Lake Mendota's mean water "
        "temperature on July 22, 2026 (Wingra minus Mendota)? Reply with one number to 2 decimals.",
        ["task1_data_and_tasks/data/wingra.csv", "task1_data_and_tasks/data/mendota.csv"],
        r2(w_cal - m_obs2),
        {
            "shifted_wingra": [r2(w_obs - m_obs2), E1_MSG],
            "calendar_day": [r2(w_cal - m_cal2), C2_MSG],
            "kept_flagged": [r2(w_cal_raw - m_obs2_raw), C1_MSG],
        },
    ))

    # T9 -- Wingra max wind speed on July 18 (E1, E2)
    correct = cal_day(wingra, "2026-07-18")
    shifted = obs_day(wingra, "2026-07-18")
    specs.append((
        "T9",
        "Using task1_data_and_tasks/data/wingra.csv, what was the maximum wind speed (m/s) "
        "at Lake Wingra on July 18, 2026? Reply with one number to 2 decimals.",
        ["task1_data_and_tasks/data/wingra.csv"],
        r2(valid(correct, "wind_speed")["wind_speed"].max()),
        {
            "shifted_wingra": [r2(valid(shifted, "wind_speed")["wind_speed"].max()), E1_MSG],
            "row_drop": [r2(all_clean(correct)["wind_speed"].max()), E2_MSG],
        },
    ))

    # T10 -- Monona hours with dissolved oxygen below 5 mg/L on July 25 (C1, C2)
    obs = obs_day(monona, "2026-07-25")
    cal = cal_day(monona, "2026-07-25")
    specs.append((
        "T10",
        "Using task1_data_and_tasks/data/monona.csv, how many hourly readings had dissolved oxygen "
        "below 5 mg/L at Lake Monona on July 25, 2026? Reply with one integer.",
        ["task1_data_and_tasks/data/monona.csv"],
        int((valid(obs, "dissolved_oxygen")["dissolved_oxygen"] < 5).sum()),
        {
            "calendar_day": [int((valid(cal, "dissolved_oxygen")["dissolved_oxygen"] < 5).sum()), C2_MSG],
            "kept_flagged": [int((obs["dissolved_oxygen"] < 5).sum()), C1_MSG],
        },
    ))

    # Plant the compound ("both rules broken") variant for each multi-rule task, but
    # only where it's distinct from the answer and the single-rule variants (e.g. T2's
    # compound coincides with kept_flagged, so it's already covered and skipped).
    compounds = cold_compounds()
    for _id, _prompt, _files, answer, variants in specs:
        if _id in compounds:
            value, is_count = compounds[_id]
            existing = [v[0] for v in variants.values()]
            if _distinct(value, answer, existing, is_count):
                variants["both_rules"] = [value, BOTH_MSG]

    # Plant the "dropped only -9999, kept the suspect readings" mistake where it's
    # distinct, so the checker can name the flag rule instead of grading it correct.
    suspects = suspect_values()
    for _id, _prompt, _files, answer, variants in specs:
        if _id in suspects:
            value, is_count = suspects[_id]
            existing = [v[0] for v in variants.values()]
            if _distinct(value, answer, existing, is_count):
                variants["kept_suspect"] = [value, C1_MSG]

    return specs


def build_tasks(_data_dir: str | None = None) -> list[dict]:
    tasks = []
    for task_id, prompt, files, answer, variants in _tasks():
        tasks.append(
            {
                "id": task_id,
                "prompt": prompt,
                "files": files,
                "answer": answer,
                "tol": TOL,
                "wrong_variants": variants,
            }
        )
    return tasks


def main() -> None:
    import json

    tasks = build_tasks()
    TASKS_JSON.write_text(json.dumps(tasks, indent=2) + "\n")
    print(f"wrote {TASKS_JSON.relative_to(HERE.parent)}  ({len(tasks)} tasks)")


if __name__ == "__main__":
    main()
