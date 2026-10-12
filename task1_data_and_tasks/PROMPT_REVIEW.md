# Prompt hint review (Person 1 DoD item)

Checks that none of the 10 task prompts leak a hidden convention (C1 quality flags,
C2 observation-day, E1 Wingra exception, E2 per-sensor flags). A prompt "hints" if it
mentions quality/validity/missing data, time zones, day boundaries or hours, firmware,
or which station is special.

Reviewed against `tasks.json` (prompts are authored in `reference.py`).

| Task | Prompt (verbatim) | Verdict |
|---|---|---|
| T1 | mean water temperature at Lake Mendota during July 2026 | clean |
| T2 | maximum water temperature at Lake Monona on July 4, 2026 | clean |
| T3 | how many hourly readings exceeded 25 °C at Lake Mendota on July 10, 2026 | clean |
| T4 | mean dissolved oxygen at Lake Monona on July 15, 2026 | clean |
| T5 | mean water temperature at Lake Wingra on July 4, 2026 | clean |
| T6 | maximum wind speed at Lake Mendota during July 2026 | clean |
| T7 | Lake Mendota minus Lake Monona mean water temperature on July 20, 2026 | clean |
| T8 | Lake Wingra minus Lake Mendota mean water temperature on July 22, 2026 | clean |
| T9 | maximum wind speed at Lake Wingra on July 18, 2026 | clean |
| T10 | how many hourly readings had dissolved oxygen below 5 mg/L at Lake Monona on July 25, 2026 | clean |

**Findings:** no accidental hints. The prompts ask only for a quantity, a station, and a
date, and never mention data quality, time zones, day boundaries, firmware, or that any
station is special. "Hourly readings" (T3, T10) is a neutral description of the data
granularity, not a hint. The parentheticals in T7/T8 only fix the subtraction order.

**By design (not a leak):** each CSV's header comment carries
`# station=<name> firmware=v1|v2`, and the file names carry the station. This is the
observable the agent must learn to attach the conventions to (v1 => observation day,
Wingra/v2 => calendar day). The prompts themselves stay silent, so a cold agent cannot
know what the firmware label implies until the checker's feedback teaches it.

**Status:** this is a self-review by the author. The DoD still asks for a glance by a
different teammate; nothing here needs changing, so that review should be quick.
