# Discussion prep — Person 5

## "What information was most useful to remember?"

- **The day rule (C2), with its scope, is what separated structured memory from no memory
  on T7 and T10 — robustly, across all three repeats.** In run `20261013-200839`, structured
  solved T7 on the first attempt in all three repeats (1 attempt each). The `none` baseline
  never did (3, 2, and 2 attempts across repeats 0/1/2); its repeat-0 trace shows the exact
  failure memory prevents — attempt 1 generic-wrong, attempt 2 drew the reviewer message
  *"Lab days run 08:00 to 08:00 local for the v1 stations, not midnight to midnight,"* attempt
  3 finally correct. T10 shows the same pattern even more starkly: structured was first-try in
  all three repeats, while `none` failed to answer T10 correctly within three attempts at all
  in two of the three repeats (`success=False`). The memory text structured received for T7
  (repeat 0) included: *"2. Lab days run 08:00 to 08:00 local for the v1 stations, not midnight
  to midnight. Scope: learned at monona/water\_temp/single\_day (T2); retrieved, solved first
  try at monona/dissolved\_oxygen/single\_day (T4); retrieved, solved first try at
  wingra/water\_temp/single\_day (T5)."*

- **The flag-trust rule (C1) was the most consistently reused across stations and variables.**
  Once learned, C1 is relevant to every task regardless of station or variable (unlike C2,
  which is withheld for whole-month tasks) and shows up in evidence for nearly every later task.
  In repeat 1 of `20261013-200839`, by T10 the final snapshot's C1 scope reads *"learned at
  monona/water\_temp/single\_day (T2); retrieved, solved first try at
  monona/dissolved\_oxygen/single\_day (T4); ... wingra/wind\_speed/single\_day (T9);
  ... monona/dissolved\_oxygen/single\_day (T10)"* — seven scope entries across T2, T4, T6, T7,
  T8, T9, and T10 (six distinct station/variable combinations; T4 and T10 are both
  monona/dissolved\_oxygen) confirming the same one rule.

- **Storing the Wingra exception as an edit to C2 (not a new rule) was what let the memory
  recover immediately instead of contradicting itself.** In repeat 1 of `20261013-200839`, T5
  failed once (answer 21.88, feedback *"Wingra's v2 logger already records on the standard
  calendar day; don't apply the 08:00 observation-day shift,"*) then succeeded. The resulting
  snapshot shows the exception attached to the live `[C2]` entry (*"Exception (station=wingra):
  ... [seen at: T5]"*) with the pre-exception version frozen separately as `[C2@T5]`, not as a
  second contradictory C2-like rule. The same editing behavior fired independently in two other
  repeats (0 and 2 of the same run), just later — at T8 instead of T5 — confirming the
  write/edit logic, not just this one instance of it.

- **Scope mattered concretely at T8: it is what let the agent apply the exception correctly on
  the one repeat where it had already been learned.** In repeat 1 of `20261013-200839`, T8
  (Wingra − Mendota) succeeded on the first attempt with the Wingra exception already in
  memory from T5. In repeats 0 and 2 of the same run, T5 happened to succeed on the first
  attempt without ever revealing the exception, so T8 became the task where it was learned
  instead (first attempt answer $-0.48$, the same Wingra reviewer message, before correcting to
  $0.08$ in both repeats). Without storing *where* the exception applies (the station), a
  structured memory could not have made this distinction at all — it would have had to choose
  between always shifting Wingra's day or never shifting any station's day.

- **Limits — read the above with these caveats.** All numbers above come from the one full
  three-repeat, three-condition run (`20261013-200839`) — three structured observations, not a
  large sample. (Two earlier single-pass structured-only runs, `20261013-182822` and
  `20261013-193556`, also exist but ran against an earlier version of the task data, so they
  are not counted here.) The per-variable exception (E2, planted for T6/T9) never fired in any
  of the three repeats — T6 was solved on the first attempt every time, so the row-drop mistake
  it is meant to catch never happened, and the *same* edit/retire logic that worked for E1
  remains unverified by real data for C1. *Which* task reveals the Wingra exception also varies
  even within this one run (T5 once, T8 twice) — "the final memory" is not identical repeat to
  repeat, only the same *kind* of memory.

## Bonus: retrieved-but-not-applied evidence (for Person 4's question — "did it retrieve a
useful memory and still fail to apply it?")

- **Yes, directly: T3 in repeat 1 of `20261013-200839`.** The memory text handed to the agent
  at the start of T3 already contained the C2 rule, learned two tasks earlier at T2: *"2. Lab
  days run 08:00 to 08:00 local for the v1 stations, not midnight to midnight. Scope: learned
  at monona/water\_temp/single\_day (T2)."* The agent's first attempt still answered 4.0 and
  drew the identical reviewer message back, before correcting to 1.0 on its second attempt. The
  final snapshot records this explicitly: both the active `[C2]` entry and its retired
  predecessor `[C2@T5]` carry the line *"Retrieved but not applied: 1 time(s) (T3)."* This is
  `structured.py`'s dedicated signal for exactly this failure mode — the rule was in context and
  named in the feedback again, not merely similar to it.
