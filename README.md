# CS 839 HW1: Continual Learning Through Agent Memory

An LLM agent answers 10 numeric questions about lake sensor CSV data, one after another. We run the same task sequence under three memory conditions (no memory, episodic memory, structured memory) and compare the results to see whether memory helps the agent improve across tasks.

## Who owns what

| Task folder | Person | Responsibility |
|---|---|---|
| `task1_data_and_tasks/` | Person 1 (`<name>`) | Sensor CSVs and the 10 tasks with answers |
| `task2_checker_and_report/` | Person 2 (`<name>`) | Answer checker with reviewer feedback, hypotheses, report and submission |
| `task3_agent_and_runner/` | Person 3 (`<name>`) | Agent loop, experiment runner, cost logging, results plot |
| `task4_episodic_memory/` | Person 4 (`<name>`) | No-memory baseline and episodic memory |
| `task5_structured_memory/` | Person 5 (`<name>`) | Structured memory with rules, exceptions and forgetting |

`shared/` holds the common interface. `outputs/` holds results, traces and memory snapshots from experiment runs.

## Shared signatures

Change these only by team agreement.

```python
# shared/interfaces.py
class Memory:
    def retrieve(self, task: dict) -> str: ...
    def update(self, task: dict, trace: dict, success: bool) -> None: ...
    def snapshot(self) -> str: ...

# task2_checker_and_report/checker.py
def check(task: dict, answer: str) -> tuple[bool, str]: ...  # (correct, feedback)

# task3_agent_and_runner/agent.py
def run_task(task: dict, memory_text: str, max_attempts: int = 3) -> dict: ...
```

## Key dates

| When | What |
|---|---|
| Sun Oct 11, 11pm | All modules pushed |
| Mon Oct 12, 10am | Integration |
| Mon Oct 12, 3pm | Experiment runs done |
| Tue Oct 13 | Submit |

## Workflow

- Only edit your own task folder.
- One branch per person: `task1` through `task5`.
- Small PRs into `main`.
- Never commit `.env`. Copy `.env.example` to `.env` locally and fill it in.
- Run code from the repo root (e.g. `python -m task3_agent_and_runner.run_experiment`) so `shared` imports resolve.

Detailed instructions are in the team plan doc and the per-person PDFs.


