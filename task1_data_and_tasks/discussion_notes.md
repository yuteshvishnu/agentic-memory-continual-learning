# Oral discussion prep (Person 1)

**My question:** *How did the agent handle an exception or conflict with an earlier memory?*
Evidence tasks: **T5, T6, T8, T9**. Target: 3–5 bullets, each backed by a trace or memory
snapshot.

> Status: the framework below is ready; the bracketed evidence must be filled in **after
> Person 3's runs** exist (`outputs/traces/`, `outputs/memory_snapshots/`,
> `outputs/results/`). Each exception task is where an earlier lesson actively conflicts
> with the current task, so these are exactly the moments to inspect.

## Where the conflicts live
- **T5 (Wingra mean temp, Jul 4):** conflicts with **C2**. By T5 the agent has learned
  "shift the day to 08:00" from T2–T4. Wingra (v2) must *not* be shifted (E1). Good
  handling = recognize the station/firmware is different and suppress the rule.
- **T6 (Mendota max wind, July):** conflicts with **C1**. The agent learned to exclude
  flagged readings; the naive form is to drop the whole row. The true max wind sits in a
  row whose temperature is flagged, so whole-row dropping (E2 violation) loses it. Good
  handling = filter per sensor.
- **T8 (Wingra − Mendota, Jul 22):** conflicts within a single task — Mendota needs the
  08:00 day (C2) while Wingra needs the calendar day (E1). Good handling = apply the rule
  to one station and the exception to the other simultaneously.
- **T9 (Wingra max wind, Jul 18):** both exceptions at once (E1 day + E2 per-sensor).

## Draft bullets (fill brackets from the runs)
1. **Did the exception get caught at all?** Compare first-attempt success on T5/T8/T9
   across conditions. Expect: no-memory is unaffected by the conflict (it never learned the
   rule), structured memory does best *if* it stored scope. `[first-try success per
   condition on T5, T8, T9 — from results]`.
2. **Retrieved-but-misapplied:** find a trajectory where the agent *retrieved* the C2/C1
   rule and still over-applied it to Wingra / dropped whole rows. `[trace id + the
   retrieved memory text + the wrong answer, e.g. T5 shifted_wingra = 21.88 vs correct
   22.46]`.
3. **How memory changed after the correction:** show the structured-memory snapshot
   before vs after T5/T6 — did it *edit* the rule to add scope ("v1 only" / "per sensor")
   or just append a contradictory note? `[snapshot diff around T5 and T6]`.
4. **Episodic vs structured on the exception:** did a retrieved past episode make episodic
   memory *more* likely to over-apply the rule than structured? `[T6 episodic vs
   structured first-try + the misleading retrieved episode]`.
5. **Combining under conflict (T8/T9):** did any condition handle rule + exception in the
   same task, or did fixing one break the other? `[T8/T9 trajectory]`.

## One-line takeaway to land
`[After runs: state whether the agent treated exceptions as scoped overrides or as flat
contradictions, and which memory design handled the conflict best.]`
