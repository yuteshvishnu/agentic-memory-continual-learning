# Oral Discussion Prep (Person 4 - Shubhangi)

**My assigned question:** *Did it retrieve a useful memory and still fail to apply it?*
Target: 3–5 bullets, each backed by a trace or memory snapshot.

> Status: The framework below is ready; bracketed evidence fields `[...]` are to be filled in
> as soon as Person 3's experiment runs are executed (`outputs/traces/`, `outputs/memory_snapshots/`, `outputs/results/`).

---

## 1. What does "Retrieved but Failed to Apply" mean?

This failure mode occurs when:
1. `EpisodicMemory.retrieve(task)` successfully surfaced a past episode containing the relevant convention (C1 quality flag filtering or C2 observation day definition).
2. The retrieved episode text was injected into the prompt and visible to the LLM agent.
3. Yet, the agent's generated Python code either:
   - Completely ignored the retrieved feedback/code, OR
   - Misinterpreted the retrieved feedback, OR
   - Over-applied/misapplied it without appropriate scoping (e.g., negative transfer).

---

## 2. Key Evidence Tasks to Inspect

- **T5 (Wingra mean temp, Jul 4 — E1 exception):**
  - *Retrieved Memory:* Episode T2 (Monona max temp, Jul 4) containing the feedback:
    `"Lab days run 08:00 to 08:00 local for the v1 stations, not midnight to midnight."`
  - *Failure to apply scope:* The memory was informative about July 4 and the observation day, but because episodic memory is unstructured, the agent failed to isolate the scope (`"for the v1 stations"` vs Wingra v2). It applied the 08:00 day shift to Wingra anyway, generating the wrong answer `21.88` instead of `22.46`.
  - `[Evidence: Trace ID + prompt injection showing T2 episode + generated attempt 1 code applying 08:00 shift to Wingra]`.

- **T6 (Mendota max wind, July — E2 exception):**
  - *Retrieved Memory:* Episode T1 (Mendota mean temp, July) containing C1 filtering (`*_qc == 0`).
  - *Failure to apply scope:* Naive code in T1 dropped whole rows where quality flags were non-zero (or `df.dropna()` / `df[df.filter(like='qc') == 0]`). In T6, the true max wind reading occurred in a row where `water_temp_qc != 0`. The agent retrieved T1's code and dropped the entire row, producing a lower/wrong max wind speed.
  - `[Evidence: Trace ID + prompt injection showing T1 episode + code dropping whole rows]`.

- **T7 or T10 (Return to rule reuse: C1 + C2):**
  - *Retrieved Memory:* T2, T3, or T4 showing 08:00 shift and qc == 0.
  - *Did it still fail on attempt 1?* Inspect whether in any run the model retrieved the exact C2 rule but hallucinated a different timezone/time calculation (e.g. offsetting by UTC hours or doing string filtering incorrectly).
  - `[Evidence: Trace ID + attempt 1 error despite memory injection]`.

---

## 3. Draft Discussion Bullets (to finalize after runs)

1. **Information Was Present But Not Attended To:**
   - On `[Task ID]`, the episodic memory prompt clearly included `[feedback snippet from prior episode]`, but the agent wrote code that did not implement the filter on attempt 1.
   - `[Insert trace citation: run repeat X, Task Y, Attempt 1 code vs retrieved memory snippet]`.

2. **Negative Transfer / Over-Generalization (Memory Misled):**
   - On T5, episodic memory retrieved the July 4 episode (T2). Rather than failing cold, the agent actively used the retrieved episode to apply an 08:00 day shift to Wingra, falling into the planted trap (`21.88`). Memory actively hurt first-attempt performance compared to a cold model that naturally defaulted to midnight-to-midnight.
   - `[Insert trace citation: T5 prompt memory injection -> attempt 1 answer 21.88]`.

3. **Code Pattern Copying vs Principle Extraction:**
   - In episodic memory, the agent receives raw past code snippets rather than distilled declarative rules. On `[Task T6 / T8]`, the agent copied the pandas filtering pattern verbatim from `[prior task]`, which included `[per-row dropping]`, causing failure when the problem required per-variable filtering.
   - `[Insert trace citation: comparison of retrieved code snippet and newly generated code]`.

4. **Clutter and Context Competition:**
   - As tasks progressed (T7–T10), the episodic memory injected multiple past episodes. In `[run X]`, having multiple code blocks in context led the model to confuse column names / stations between episodes.
   - `[Insert trace citation: model using wrong column or station name from past episode]`.

---

## 4. One-Line Takeaway for the Professor

> *"Unstructured episodic memory provides precedent rather than abstraction: the agent frequently retrieves the correct historical episode but fails either by copying specific implementation artifacts (verbatim code patterns) or by applying the precedent without checking conditional boundaries (station firmware and variable scope)."*
