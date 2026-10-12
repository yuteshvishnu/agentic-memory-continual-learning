# CS 839 HW1: Continual Learning Through Agent Memory

An LLM agent answers 10 numeric questions about Madison lake sensor CSV data, one after
another, by writing and running Python. We run the same task sequence under three memory
conditions (no memory, episodic memory, structured memory) and compare the results to see
whether memory lets the agent **improve across tasks**. The underlying model never changes —
any improvement comes only from what the agent stores, retrieves, updates, or forgets.

**[PLAN.md](PLAN.md) is the single source of truth** for the full design: domain, data schema,
the four hidden conventions, the task sequence, hypotheses, measurement protocol, and timeline.
This README is the quick reference.

## The four hidden conventions (never stated in prompts)

The agent learns these only from checker feedback, then must remember them.

| ID | Convention |
|---|---|
| **C1** | Trust a reading only if its own quality flag `*_qc == 0` (flags 1/2/3 are bad, even when the value looks normal). |
| **C2** | The lab "day" runs **08:00 → 08:00** for v1 stations (Mendota, Monona); applies to single-day-scoped tasks. |
| **E1** | Exception to C2: Wingra (v2) uses a normal **calendar-midnight** day — don't shift it. |
| **E2** | Exception to C1: filter flags **per variable**, never drop a whole row because one variable is flagged. |

## Who owns what

| Task folder | Person | Responsibility |
|---|---|---|
| `task1_data_and_tasks/` | Person 1 (`<name>`) | Station CSVs (with `*_qc` columns) and the 10 tasks with answers |
| `task2_checker_and_report/` | Person 2 (`<name>`) | Answer checker with reviewer feedback, hypotheses, report and submission |
| `task3_agent_and_runner/` | Person 3 (`<name>`) | Agent loop, experiment runner, cost logging, results plot |
| `task4_episodic_memory/` | Person 4 (`<name>`) | No-memory baseline and episodic memory |
| `task5_structured_memory/` | Person 5 (`<name>`) | Structured memory with rules, exceptions and forgetting |

`shared/` holds the common interface. `outputs/` holds results, traces and memory snapshots.

## Shared signatures

Change these only by team agreement.

```python
# shared/interfaces.py
class Memory:
    def retrieve(self, task: dict) -> str: ...          # text injected into the prompt
    def update(self, task: dict, trace: dict, success: bool) -> None: ...
    def snapshot(self) -> str: ...                       # saved after every task

# task2_checker_and_report/checker.py
def check(task: dict, answer: float) -> tuple[bool, str]: ...   # (correct, feedback)

# task3_agent_and_runner/agent.py
def run_task(task: dict, memory_text: str, max_attempts: int = 3) -> dict: ...
# returns: answer, success, first_try, attempts, n_calls, in_tokens, out_tokens, trace
```

## Key dates

| When | What |
|---|---|
| Sun Oct 11, 6pm | T1 data + task pushed; hypotheses committed |
| Sun Oct 11, 11pm | All modules pushed, tested against mocks |
| Mon Oct 12, 10am | Integration (one full no-memory run end to end) |
| Mon Oct 12, 3pm | All 90 runs done |
| Tue Oct 13 | Submit |

## Workflow

- Only edit your own task folder.
- One branch per person: `task1` through `task5`.
- Small PRs into `main` (protected).
- Never commit `.env`. Copy `.env.example` to `.env` locally and fill it in.
- Run code from the repo root (e.g. `python -m task3_agent_and_runner.run_experiment`) so
  `shared` imports resolve.

See [PLAN.md](PLAN.md) for the full detail.
