# Task 4: No-Memory and Episodic Memory

- **Owner:** Person 4 (Shubhangi)
- **Delivers:**
  - The no-memory baseline ([`no_memory.py`](no_memory.py))
  - Episodic memory ([`episodic.py`](episodic.py))
  - Verification unit tests ([`test_memory.py`](test_memory.py))
  - Discussion prep notes ([`discussion_notes.md`](discussion_notes.md))
  - Report section draft ([`report_section_episodic_memory.tex`](report_section_episodic_memory.tex))
- **Report & Oral Question:** Episodic memory design + trajectory where memory **misled** (see [../PLAN.md](../PLAN.md) §13).

See [../PLAN.md](../PLAN.md) §7 for how the conditions differ.

---

## 1. No Memory (`no_memory.py`)

The cold baseline.
- `retrieve(task)`: returns `""` (no memory context injected into prompt).
- `update(task, trace, success)`: no-op; retains nothing across tasks.
- `snapshot()`: returns `""`.

Each task starts cold, forcing the agent to rediscover hidden conventions C1 and C2 on every task.

---

## 2. Episodic Memory (`episodic.py`)

Stores raw execution episodes and injects top-k relevant past experiences into subsequent task prompts.

- `update(task, trace, success)`: parses and stores an episode record containing the prompt, files, reviewer feedback messages from incorrect attempts, executed Python code, and final answer. Handles multiple trace structures (attempt lists, flat dicts, strings).
- `retrieve(task)`: calculates a domain-aware relevance score across all stored episodes based on:
  - Exact date overlap (e.g., matching July 4 between T2 and T5)
  - Referenced CSV files / station targets (Mendota, Monona, Wingra)
  - Domain keywords (temperatures, dissolved oxygen, wind speed, aggregations)
  - Recency weighting
  Returns the top-$k$ formatted episodes with reviewer feedback and trimmed code blocks.
- `snapshot()`: dumps the complete episode store as structured JSON (`outputs/memory_snapshots/`).

### Why Episodic Memory Drives Hypothesis H2
Because episodic memory performs unstructured recall rather than distilling scoped rules:
1. **On T5 (Wingra, Jul 4):** It retrieves T2 (Monona, Jul 4) where the reviewer enforced the 08:00 observation day shift. The agent blindly reapplies the 08:00 shift to Wingra (firmware v2), triggering the planted trap (`21.88` instead of `22.46`).
2. **On T6 (Mendota, July max wind):** It retrieves T1 (Mendota, July mean temp) where non-zero flags were dropped. The agent copies whole-row dropping code, discarding the row with peak wind speed due to a flagged temperature sensor.

---

## 3. Running Unit Tests

Run from the repository root:
```bash
python3 -m task4_episodic_memory.test_memory
```
