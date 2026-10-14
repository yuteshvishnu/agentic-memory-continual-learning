# Oral discussion prep (Person 3)

**My question:** *Did either memory system improve over time? What evidence suggests real learning?*

All evidence is from the final run `20261013-200839` (3 conditions × 3 repeats × T1–T10):
`outputs/results/results.csv`, `outputs/traces/`, `outputs/memory_snapshots/`.

## Bullets

- **Both memories improved, consistently.** First-attempt success: no memory 26.7%, episodic
  66.7%, structured 63.3%. The gap held in every repeat (no memory 20/30/30%, episodic
  70/70/60%, structured 60/70/60%). Attempts per task fell from 2.13 to 1.33 (episodic) and
  1.40 (structured). Final success: 28/30 vs 30/30 and 30/30.
- **The gains appear only after a lesson has been taught.** On T4, T7 and T10, which reuse
  the rules taught at T1–T2: structured 9/9 first-try, episodic 8/9, no memory 0/9. T2,
  where the 08:00 day rule is first taught, is 0/3 in every condition, as expected before
  the lesson exists.
- **Clearest sign of real learning: structured memory at T8.** The agent solved T8 on the
  first try only in the repeat (r1) where memory had already stored the Wingra exception at
  T5. In r0 and r2 the exception wasn't there yet and the agent applied the 08:00 shift to
  Wingra (answer −0.48, the planted `shifted_wingra` mistake). Memory then edited the day
  rule and retired the old version (`C2@T8` in the snapshot).
- **Memory can also mislead.** Episodic memory scored 0/3 on T5 versus 2/3 for no memory, and
  all three failures were the planted "08:00 shift on Wingra" mistake (21.88): it recalled
  the rule without its scope.
- **Retrieved is not the same as applied.** On T3 structured memory gave the agent the 08:00
  day rule in all three repeats, yet it used the calendar day every time (0/3, answer 4);
  the snapshot logs this as "retrieved but not applied". Episodic memory, which showed T2's
  actual code, scored 3/3. A concrete worked example transferred better than a stated rule.
  Possible reason (not verified): the rule says "v1 stations", but the agent never sees
  which stations are v1, because that label is in a CSV comment line its code skips.
