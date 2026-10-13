# Task 3: Agent and Runner

- **Owner:** Person 3 (Yutesh)
- **Delivers:** the agent loop (`agent.py`), the experiment runner with cost logging
  (`run_experiment.py`), and the results plot.
- **Deadline:** integration Mon 10am (one full no-memory run end to end), all 90 runs by Mon 3pm.

See [../PLAN.md](../PLAN.md) §7 (conditions) and §10 (measurement protocol).

## The agent (`agent.py`)

```python
def run_task(task: dict, memory_text: str, max_attempts: int = 3) -> dict:
    # returns: answer, success, first_try, attempts, n_calls, in_tokens, out_tokens, trace
```

- One tool: **Python execution**. The agent writes Python over the task's CSV(s); we run it and
  feed stdout/errors back; parse the final single number.
- Up to `max_attempts` (3). On a wrong answer the checker returns feedback; the agent retries.
- `memory_text` (from `Memory.retrieve`) is injected into the prompt. The **prompt template, model,
  and tool are identical across all three conditions** and must not hint at any convention.

## The runner (`run_experiment.py`)

- `run_condition(condition, memory, tasks)` runs T1–T10 in order, calling `retrieve` → `run_task`
  → `check` → `update`, and **snapshots memory after every task**.
- Runs **3 full repeats** per condition (90 task-runs); more only for close comparisons.
- Metrics per task per condition: first-attempt success, final success, attempts, model calls,
  input/output tokens, cost. **Every model call logged to `outputs/results/calls.csv`** (memory-
  writing calls count toward cost too). Enforce the shared **$5** hard limit.
- `plot_results(results_dir, out_path)` produces the one table/plot across the sequence.

Outputs go to `outputs/{results,traces,memory_snapshots}/`.

## How to run

1. `cp .env.example .env` in the repo root, then fill in `LLM_API_KEY` and `MODEL_NAME`.
2. Set `PRICE_IN_PER_1M` and `PRICE_OUT_PER_1M` in `llm.py` (USD per 1M tokens for that model).
3. From the repo root:

```bash
python -m task3_agent_and_runner.run_experiment --conditions none --repeats 1 --tasks T1   # one cheap task first
python -m task3_agent_and_runner.run_experiment                                            # full: 3 conditions x 3 repeats
python -m task3_agent_and_runner.run_experiment --plot-only                                # redraw the plot
```

Writes `results/results.csv` (one row per task-run), `results/calls.csv` (one row per model
call), `results/summary_by_task.csv`, `results/performance_by_task.png`, plus one trace and one
memory snapshot per task-run. Until Person 2's `check` is on `main`, `agent.py` grades with a
stand-in built from `tasks.json`.

**Memory code that calls the model** (e.g. structured memory) must go through
`task3_agent_and_runner.llm.call_llm(messages, purpose="memory")` so its cost is logged and
counted against the $5 budget.
