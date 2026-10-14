"""Person 1: generate the three lake-sensor CSVs (refined conventions).

Deterministic (fixed seed). Base signals are deliberately "safe" (temperature
never exceeds 25 C, dissolved oxygen never below 5 mg/L, wind below 8 m/s) so that
every task-relevant extreme, count, and boundary value is *planted* explicitly and
the correct/wrong answers are guaranteed to be distinguishable.

Hidden conventions the data encodes (never stated in prompts):
  C1  trust a reading only if its own quality flag (*_qc) == 0
  C2  the lab "day" runs 08:00 -> 08:00 for v1 stations (Mendota, Monona)
  E1  exception to C2: Wingra (v2) uses the normal calendar-midnight day
  E2  exception to C1: filter flags per variable, never drop a whole row

Run from the repo root:  python -m task1_data_and_tasks.generate_data
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 839
START = "2026-07-01 00:00"
HOURS = 744  # hourly, July 1 00:00 .. July 31 23:00

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"

# station -> (firmware, per-station seed offset)
STATIONS = {
    "mendota": ("v1", 1),
    "monona": ("v1", 2),
    "wingra": ("v2", 3),
}

QC_OF = {
    "water_temp_C": "water_temp_qc",
    "dissolved_oxygen": "do_qc",
    "wind_speed": "wind_qc",
}


def base_frame(seed_offset: int) -> tuple[pd.DataFrame, np.random.Generator]:
    """Boring, in-range base signals; all quality flags 0."""
    rng = np.random.default_rng(SEED + seed_offset)
    ts = pd.date_range(START, periods=HOURS, freq="h")
    h = ts.hour.to_numpy()
    temp = 22.0 + 1.5 * np.sin(2 * np.pi * (h - 15) / 24) + rng.normal(0, 0.2, HOURS)
    do = 7.5 - 0.3 * (temp - 22.0) + rng.normal(0, 0.15, HOURS)
    wind = np.clip(np.abs(rng.normal(0, 2.5, HOURS)), 0, 8.0)
    df = pd.DataFrame(
        {
            "timestamp": ts,
            "water_temp_C": np.round(temp, 2),
            "water_temp_qc": 0,
            "dissolved_oxygen": np.round(do, 2),
            "do_qc": 0,
            "wind_speed": np.round(wind, 2),
            "wind_qc": 0,
        }
    )
    return df, rng


def add_background_flags(df: pd.DataFrame, rng: np.random.Generator) -> None:
    """~2.5% of temp and DO readings get a nonzero flag, independently per column.

    flag 1 = estimated (value kept), 2 = suspect (value kept, plausible),
    3 = offline (value set to -9999). This is background realism; the task traps
    are planted separately and overwrite these where they overlap.
    """
    n = len(df)
    for var in ("water_temp_C", "dissolved_oxygen"):
        qc_col = QC_OF[var]
        idx = rng.choice(n, size=int(0.025 * n), replace=False)
        for i in idx:
            flag = int(rng.choice([1, 2, 3], p=[0.4, 0.3, 0.3]))
            df.at[i, qc_col] = flag
            if flag == 3:
                df.at[i, var] = -9999.0


def apply_plants(df: pd.DataFrame, plants: list[tuple]) -> None:
    """Each plant is (timestamp, column, value, qc). Overwrites base + background."""
    for ts, col, value, qc in plants:
        rows = df.index[df["timestamp"] == pd.Timestamp(ts)]
        if len(rows) == 0:
            raise ValueError(f"plant timestamp not in range: {ts}")
        i = rows[0]
        df.at[i, col] = float(value)
        df.at[i, QC_OF[col]] = int(qc)


# --- Planted traps, per station (see reference.py for how each is read back) ---

MENDOTA_PLANTS = [
    # T1 (whole-July mean): guarantee an offline temp so "kept everything" differs hard
    ("2026-07-02 02:00", "water_temp_C", -9999.0, 3),
    # T3 (hours > 25 C on July 10): C2 boundary. observation day = 07-10 08:00..07-11 08:00
    ("2026-07-10 02:00", "water_temp_C", 26.0, 0),  # calendar-only (before 08:00)
    ("2026-07-10 03:00", "water_temp_C", 26.0, 0),
    ("2026-07-10 04:00", "water_temp_C", 26.0, 0),
    ("2026-07-10 05:00", "water_temp_C", 26.0, 0),
    ("2026-07-11 02:00", "water_temp_C", 26.0, 0),  # observation-only (after midnight)
    ("2026-07-10 15:00", "water_temp_C", 27.0, 2),  # suspect high, in both windows -> C1
    # T6 (max wind, whole July): E2 -> true max sits in a row whose temp is flagged
    ("2026-07-12 14:00", "wind_speed", 11.0, 0),
    ("2026-07-12 14:00", "water_temp_C", -9999.0, 3),
    ("2026-07-13 14:00", "wind_speed", 9.0, 0),  # second-highest, fully clean row
    # T7 (Mendota - Monona daily mean temp, July 20): asymmetric boundary vs Monona
    ("2026-07-20 02:00", "water_temp_C", 20.0, 0),  # calendar-only, low
    ("2026-07-20 03:00", "water_temp_C", 20.0, 0),
    ("2026-07-21 02:00", "water_temp_C", 26.0, 0),  # observation-only, high
    ("2026-07-21 03:00", "water_temp_C", 26.0, 0),
    ("2026-07-20 12:00", "water_temp_C", -9999.0, 3),  # offline in-window -> C1
    # T8 (Wingra - Mendota, July 22): Mendota is the v1 (observation-day) side
    ("2026-07-22 02:00", "water_temp_C", 20.0, 0),  # calendar-only, low
    ("2026-07-22 03:00", "water_temp_C", 20.0, 0),
    ("2026-07-23 02:00", "water_temp_C", 25.0, 0),  # observation-only, high
    ("2026-07-23 03:00", "water_temp_C", 25.0, 0),
]

MONONA_PLANTS = [
    # T2 (max water temp on July 4): C2 boundary + C1 suspect
    ("2026-07-05 03:00", "water_temp_C", 28.0, 0),  # observation-only -> true max
    ("2026-07-04 16:00", "water_temp_C", 31.0, 2),  # suspect high, in-window -> C1
    # T4 (mean DO on July 15): C2 boundary + C1 offline
    ("2026-07-15 02:00", "dissolved_oxygen", 9.0, 0),  # calendar-only, high
    ("2026-07-15 03:00", "dissolved_oxygen", 9.0, 0),
    ("2026-07-16 02:00", "dissolved_oxygen", 6.0, 0),  # observation-only, low
    ("2026-07-16 03:00", "dissolved_oxygen", 6.0, 0),
    ("2026-07-15 12:00", "dissolved_oxygen", -9999.0, 3),  # offline in-window -> C1
    # T7 (Mendota - Monona, July 20): mirror of Mendota's asymmetry
    ("2026-07-20 02:00", "water_temp_C", 26.0, 0),  # calendar-only, high
    ("2026-07-20 03:00", "water_temp_C", 26.0, 0),
    ("2026-07-21 02:00", "water_temp_C", 20.0, 0),  # observation-only, low
    ("2026-07-21 03:00", "water_temp_C", 20.0, 0),
    # T10 (hours with DO < 5 on July 25): C2 boundary + C1 offline
    ("2026-07-25 10:00", "dissolved_oxygen", 4.0, 0),  # in both windows
    ("2026-07-25 11:00", "dissolved_oxygen", 4.0, 0),
    ("2026-07-25 12:00", "dissolved_oxygen", 4.0, 0),
    ("2026-07-25 02:00", "dissolved_oxygen", 4.0, 0),  # calendar-only
    ("2026-07-25 03:00", "dissolved_oxygen", 4.0, 0),
    ("2026-07-25 04:00", "dissolved_oxygen", 4.0, 0),
    ("2026-07-25 05:00", "dissolved_oxygen", 4.0, 0),  # (keeps calendar_day != kept_flagged)
    ("2026-07-26 02:00", "dissolved_oxygen", 4.0, 0),  # observation-only
    ("2026-07-25 14:00", "dissolved_oxygen", -9999.0, 3),  # offline (< 5) in-window -> C1
]

WINGRA_PLANTS = [
    # Wingra is v2: the CORRECT day is calendar midnight. Applying the 08:00 shift (E1) is wrong.
    # T5 (mean water temp on July 4):
    ("2026-07-04 02:00", "water_temp_C", 26.0, 0),  # in correct (midnight) day, high
    ("2026-07-04 03:00", "water_temp_C", 26.0, 0),
    ("2026-07-05 02:00", "water_temp_C", 20.0, 0),  # only a wrong 08:00-shift would include
    ("2026-07-05 03:00", "water_temp_C", 20.0, 0),
    ("2026-07-04 12:00", "water_temp_C", -9999.0, 3),  # offline in-window -> C1
    # T8 (Wingra - Mendota, July 22): Wingra side (correct = midnight day)
    ("2026-07-22 02:00", "water_temp_C", 26.0, 0),
    ("2026-07-22 03:00", "water_temp_C", 26.0, 0),
    ("2026-07-23 02:00", "water_temp_C", 20.0, 0),
    ("2026-07-23 03:00", "water_temp_C", 20.0, 0),
    ("2026-07-22 12:00", "water_temp_C", -9999.0, 3),
    # T9 (max wind on July 18): E1 (midnight day) + E2 (max in a flagged-temp row)
    ("2026-07-18 03:00", "wind_speed", 10.0, 0),  # true max, in correct midnight day
    ("2026-07-18 03:00", "water_temp_C", -9999.0, 3),  # same row: temp offline -> E2
    ("2026-07-19 02:00", "wind_speed", 9.0, 0),  # only a wrong 08:00-shift would include
]

# Suspect (flag-2) readings that *bias* a statistic. Without these, the suspect values
# sit so close to the clean mean that "drop only -9999 but keep flags 1/2" stays within
# tolerance and is graded correct -- so C1 would be testable only on T2/T3. A stuck-high
# temperature sensor over a few afternoons (T1), and short low-DO excursions (T4, T10),
# make the flag rule change the answer by more than the tolerance on the mean/count tasks.
MENDOTA_PLANTS += [
    (f"2026-07-{d:02d} {h:02d}:00", "water_temp_C", 28.0, 2)  # T1 whole-month mean
    for d in (5, 6, 7, 8)
    for h in (12, 13, 14, 15)
]
MENDOTA_PLANTS += [
    ("2026-07-20 13:00", "water_temp_C", 28.0, 2),  # T7 (Mendota side of the July 20 diff)
    ("2026-07-20 14:00", "water_temp_C", 28.0, 2),
    ("2026-07-22 13:00", "water_temp_C", 28.0, 2),  # T8 (Mendota side of the July 22 diff)
    ("2026-07-22 14:00", "water_temp_C", 28.0, 2),
]
MONONA_PLANTS += [
    ("2026-07-15 13:00", "dissolved_oxygen", 2.0, 2),  # T4 mean DO
    ("2026-07-15 14:00", "dissolved_oxygen", 2.0, 2),
    ("2026-07-25 13:00", "dissolved_oxygen", 4.0, 2),  # T10 count DO < 5
]

PLANTS = {"mendota": MENDOTA_PLANTS, "monona": MONONA_PLANTS, "wingra": WINGRA_PLANTS}


def write_station(name: str, firmware: str, seed_offset: int) -> pd.DataFrame:
    df, rng = base_frame(seed_offset)
    add_background_flags(df, rng)
    apply_plants(df, PLANTS[name])
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / f"{name}.csv"
    header = f"# station={name.capitalize()} firmware={firmware}\n"
    body = df.to_csv(index=False)
    out.write_text(header + body)
    return df


def main() -> None:
    for name, (firmware, seed_offset) in STATIONS.items():
        df = write_station(name, firmware, seed_offset)
        print(f"wrote data/{name}.csv  ({firmware}, {len(df)} rows)")


if __name__ == "__main__":
    main()
