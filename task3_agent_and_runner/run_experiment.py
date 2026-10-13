"""Person 3: run the task sequence under each memory condition, log results and cost, plot them.

For each task: memory.retrieve -> run_task -> memory.update, then the trace and a memory
snapshot are saved. Every repeat starts with a fresh, empty memory. Results are appended to
outputs/results/results.csv as they finish, so nothing paid for is lost if a run stops.

Run from the repo root:
    python -m task3_agent_and_runner.run_experiment                          # all 3 conditions x 3 repeats
    python -m task3_agent_and_runner.run_experiment --conditions none --repeats 1 --tasks T1
    python -m task3_agent_and_runner.run_experiment --plot-only
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from shared.interfaces import Memory
from task3_agent_and_runner.agent import run_task
from task3_agent_and_runner.llm import REPO_ROOT, BudgetExceeded, cost, set_context, spent

TASKS_JSON = REPO_ROOT / "task1_data_and_tasks" / "tasks.json"
OUTPUTS = REPO_ROOT / "outputs"
RESULTS_DIR = OUTPUTS / "results"
RESULTS_CSV = RESULTS_DIR / "results.csv"
PLOT_PATH = RESULTS_DIR / "performance_by_task.png"

CONDITIONS = ["none", "episodic", "structured"]
RESULT_FIELDS = ["run_id", "condition", "repeat", "position", "task_id", "answer", "expected",
                 "success", "first_try", "attempts", "n_calls", "in_tokens", "out_tokens", "cost_usd"]


class _NoMemoryStandIn(Memory):
    """Used for "none" until Person 4's NoMemory is on main."""

    def retrieve(self, task: dict) -> str:
        return ""

    def update(self, task: dict, trace: dict, success: bool) -> None:
        pass

    def snapshot(self) -> str:
        return ""


def make_memory(condition: str):
    """A fresh memory for one repeat. Imported here so one unfinished module doesn't block the others."""
    if condition == "none":
        from task4_episodic_memory.no_memory import NoMemory
        memory = NoMemory()
        try:
            memory.snapshot()
        except NotImplementedError:
            memory = _NoMemoryStandIn()
        return memory
    if condition == "episodic":
        from task4_episodic_memory.episodic import EpisodicMemory
        return EpisodicMemory()
    if condition == "structured":
        from task5_structured_memory.structured import StructuredMemory
        return StructuredMemory()
    raise ValueError(f"unknown condition: {condition}")


def run_condition(condition: str, memory, tasks: list[dict], repeat: int = 0, run_id: str = "") -> list[dict]:
    rows = []
    for position, task in enumerate(tasks, start=1):
        set_context(condition=condition, repeat=repeat, task_id=task["id"], attempt="")
        memory_text = memory.retrieve(task)
        result = run_task(task, memory_text)
        set_context(attempt="")  # memory-writing calls aren't part of an attempt
        memory.update(task, result["trace"], result["success"])

        name = f"{run_id}_{condition}_r{repeat}_{task['id']}"
        _write(OUTPUTS / "traces" / f"{name}.json", json.dumps(result["trace"], indent=2, default=str))
        _write(OUTPUTS / "memory_snapshots" / f"{name}.txt", memory.snapshot())

        row = {
            "run_id": run_id,
            "condition": condition,
            "repeat": repeat,
            "position": position,
            "task_id": task["id"],
            "answer": result["answer"],
            "expected": task["answer"],
            "success": result["success"],
            "first_try": result["first_try"],
            "attempts": result["attempts"],
            "n_calls": result["n_calls"],
            "in_tokens": result["in_tokens"],
            "out_tokens": result["out_tokens"],
            "cost_usd": round(cost(result["in_tokens"], result["out_tokens"]), 6),
        }
        _append_result(row)
        rows.append(row)
        verdict = "correct" if result["success"] else "wrong"
        print(f"[{condition} r{repeat}] {task['id']}: {verdict} after {result['attempts']} attempt(s), "
              f"answer={result['answer']}  (spent ${spent():.2f})")
    return rows


# --- results plot + table ---

# Categorical slots 1-3 of the validated default palette, fixed per condition.
COLORS = {"none": "#2a78d6", "episodic": "#eb6834", "structured": "#1baf7a"}
MARKERS = {"none": "o", "episodic": "s", "structured": "^"}
LABELS = {"none": "No memory", "episodic": "Episodic", "structured": "Structured"}
TEXT, TEXT_MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3de"


def plot_results(results_dir: str, out_path: str) -> None:
    """Per-task summary table (summary_by_task.csv) and one figure across the sequence."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    df = pd.read_csv(Path(results_dir) / "results.csv")
    summary = (
        df.groupby(["condition", "task_id"])
        .agg(runs=("success", "size"), first_try_rate=("first_try", "mean"),
             final_success_rate=("success", "mean"), mean_attempts=("attempts", "mean"),
             in_tokens=("in_tokens", "sum"), out_tokens=("out_tokens", "sum"), cost_usd=("cost_usd", "sum"))
        .reset_index()
    )
    summary.to_csv(Path(results_dir) / "summary_by_task.csv", index=False)

    order = [t["id"] for t in json.loads(TASKS_JSON.read_text()) if t["id"] in set(df["task_id"])]
    conditions = [c for c in CONDITIONS if c in set(df["condition"])]
    x = {task_id: i for i, task_id in enumerate(order)}
    dodge = {c: (i - (len(conditions) - 1) / 2) * 0.08 for i, c in enumerate(conditions)}

    fig, (ax_first, ax_attempts) = plt.subplots(1, 2, figsize=(11, 4.2), sharex=True)
    panels = [(ax_first, "first_try_rate", 100, "First-attempt success (%)"),
              (ax_attempts, "mean_attempts", 1, "Attempts used (mean)")]
    for ax, column, scale, title in panels:
        for c in conditions:
            rows = summary[summary["condition"] == c].set_index("task_id").reindex(order)
            xs = [x[t] + dodge[c] for t in order]
            ax.plot(xs, rows[column] * scale, color=COLORS[c], marker=MARKERS[c], lw=1.5, ms=6,
                    mec="white", mew=1, label=LABELS[c])
        ax.set_title(title, loc="left", fontsize=11, color=TEXT)
        ax.set_xticks(range(len(order)), order)
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(GRID)
        ax.tick_params(colors=TEXT_MUTED, labelsize=9)

    ax_first.set_ylim(-5, 105)
    ax_first.set_yticks([0, 25, 50, 75, 100])
    ax_attempts.set_ylim(0.8, 3.2)
    ax_attempts.set_yticks([1, 2, 3])
    ax_first.set_xlim(-0.5, len(order) + 1)  # room for the line-end labels (x is shared)
    _label_line_ends(ax_first, summary, conditions, order, len(order) - 1)

    n_repeats = df.groupby("condition")["repeat"].nunique().max()
    fig.suptitle(f"Performance across the task sequence (mean of {n_repeats} repeat(s) per condition)",
                 x=0.01, ha="left", fontsize=12, color=TEXT)
    fig.legend(*ax_first.get_legend_handles_labels(), loc="upper right", ncol=len(conditions),
               frameon=False, fontsize=9, labelcolor=TEXT_MUTED)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out_path, dpi=200, facecolor="white")
    plt.close(fig)
    print(f"wrote {out_path} and summary_by_task.csv")


def _label_line_ends(ax, summary, conditions, order, last_x) -> None:
    """Name each line at its right end, nudged apart so equal values don't overlap."""
    ends = []
    for c in conditions:
        rows = summary[(summary["condition"] == c) & (summary["task_id"] == order[-1])]
        if len(rows):
            ends.append([rows["first_try_rate"].iloc[0] * 100, c])
    ends.sort()
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 9)
    for y, c in ends:
        ax.annotate(LABELS[c], (last_x + 0.25, y), fontsize=9, color=TEXT_MUTED,
                    va="center", annotation_clip=False)


# --- output helpers ---

def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _append_result(row: dict) -> None:
    new_file = not RESULTS_CSV.exists()
    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_CSV.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the task sequence under each memory condition.")
    parser.add_argument("--conditions", nargs="+", choices=CONDITIONS, default=CONDITIONS)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--tasks", nargs="+", help="only these task ids, e.g. T1 T2 (default: all 10)")
    parser.add_argument("--plot-only", action="store_true", help="skip running; redraw from results.csv")
    args = parser.parse_args()

    if not args.plot_only:
        tasks = json.loads(TASKS_JSON.read_text())
        if args.tasks:
            tasks = [t for t in tasks if t["id"] in args.tasks]
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            # Repeats on the outside, so if the budget runs out every condition has the same count.
            for repeat in range(args.repeats):
                for condition in args.conditions:
                    run_condition(condition, make_memory(condition), tasks, repeat, run_id)
        except BudgetExceeded as e:
            print(f"Stopped: {e}")
        print(f"Total spent (all runs logged in calls.csv): ${spent():.2f}")

    if RESULTS_CSV.exists():
        plot_results(RESULTS_DIR, PLOT_PATH)


if __name__ == "__main__":
    main()
