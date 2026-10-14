# Oral discussion prep (Person 1 — Akshat)

**My question:** *How did the agent handle an exception or conflict with an earlier memory?*
Evidence tasks: **T5, T6, T8, T9.**

Evidence is from run **`20261013-200839`** (3 conditions × 3 repeats; model `gpt-5.6-luna`,
reasoning off). Files under `outputs/results/`, `outputs/traces/`, `outputs/memory_snapshots/`.

## First-attempt success on the exception tasks (out of 3 repeats)

| Task | What it tests | no-memory | episodic | structured |
|---|---|---|---|---|
| T5 | don't shift Wingra's day (E1) | 2/3 | **0/3** | 2/3 |
| T6 | per-sensor flags, not whole-row (E2) | 3/3 | 3/3 | 3/3 |
| T8 | combine v1 shift **+** Wingra exception | 0/3 | **3/3** | 1/3 |
| T9 | combine both exceptions (E1+E2) | 3/3 | 3/3 | 3/3 |

All conditions reached final success within 3 attempts, so the signal is in first-try and
attempts (T5 mean attempts: episodic 2.0 vs no-memory/structured 1.33; T8: no-memory 2.67,
structured 1.67, episodic 1.0). Source: `outputs/results/summary_by_task.csv`.

## T5 — the clean "memory misled" case
By T5 the agent has learned "shift the day to 08:00" from T2–T4. Wingra (v2) is the exception.
- **Episodic failed the first try in all 3 repeats.** Its memory was raw past episodes (T2/T4),
  all of which said *"lab days run 08:00…"* with no Wingra exception yet. It applied the shift to
  Wingra: `episodic_r0_T5` attempt 1 answer **21.88** (the shift-applied-to-Wingra value) →
  feedback *"Wingra's v2 logger already records on the standard calendar day; don't apply the
  08:00 shift"* → attempt 2 **22.46**. (`outputs/traces/20261013-200839_episodic_r0_T5.json`)
- **Structured solved it first try (2/3).** Its C2 rule was stored *with scope* —
  *"Lab days run 08:00 to 08:00 local **for the v1 stations**"* — so Wingra (v2) fell outside the
  rule and was not shifted. (`outputs/memory_snapshots/20261013-200839_structured_r0_T4.txt`)

## T8 — the flip: episodic beats structured
T8 needs the v1 shift (Mendota) **and** the Wingra exception in one task.
- **Episodic solved it first try in all 3 repeats.** By now it still had the concrete T5 episode
  ("Wingra: don't shift") in recent memory and reused it → **0.08** first try.
- **Structured failed first try in 2/3 repeats.** `structured_r0_T8` attempt 1 = **−0.48** (shift
  wrongly applied to Wingra) → same Wingra feedback → attempt 2 **0.08**. Its memory going into T8
  (snapshot after T7) held C1 and C2 but **never crystallized a standalone Wingra/E1 rule** — the
  exception lived only inside C2's "v1 stations" phrase, which the agent didn't honor on the harder
  two-station task. (`outputs/traces/20261013-200839_structured_r0_T8.json`,
  `outputs/memory_snapshots/20261013-200839_structured_r0_T7.txt`)

So the two conditions failed in opposite places: episodic on the *first* Wingra encounter (T5,
no exception episode yet), structured on the *later combination* (T8, no explicit exception rule).

## T6, T9 — exceptions nobody stumbled on
All three conditions solved T6 and T9 on the first try (`episodic_r0_T6` attempt 1 = **11.0**).
The cold default already matches: the max-wind reading is a valid value even though its row's
temperature is flagged, so **no condition over-applied whole-row dropping** — the E2 failure mode
we worried about never appeared. T9 (both exceptions) behaved the same way.

## 3–5 bullets with evidence
1. **Memory both helped and hurt on exceptions, depending on position.** Episodic was *worst* on
   T5 (0/3 first-try vs 2/3 no-memory) and *best* on T8 (3/3 vs 0/3). `summary_by_task.csv`.
2. **The misleading mechanism is unscoped recall.** On T5, episodic retrieved "lab days run 08:00"
   episodes and applied the shift to Wingra (answer 21.88) before any Wingra exception existed.
   `traces/..._episodic_r0_T5.json`.
3. **Scope travels with a well-written rule.** Structured solved T5 first try because its C2 rule
   literally said *"for the v1 stations"*; Wingra (v2) fell outside it.
   `memory_snapshots/..._structured_r0_T4.txt`.
4. **Retrieved-but-misapplied really happened — to structured, on T8.** It over-applied the 08:00
   shift to Wingra (−0.48) even though its memory contained the v1 scope; it never formed a
   standalone Wingra exception. `traces/..._structured_r0_T8.json`.
5. **Not every exception is hard.** T6 and T9 were first-try for all conditions because the default
   computation already matched the exception — the agent "handled" them by never forming the wrong
   habit in the first place.

## One-line takeaway
Exceptions were handled well only when the *conflicting scope was explicit*: a scoped structured
rule caught the first Wingra case, raw episodic recall caught the later one, and each condition
failed exactly where its memory lacked the exception — so memory helped or hurt depending on
whether the exception was encoded, not on the memory type alone.
