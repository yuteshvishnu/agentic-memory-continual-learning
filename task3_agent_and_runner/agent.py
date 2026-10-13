"""Person 3: the agent loop that answers one task by writing and running Python.

One attempt = one answer submitted to the checker. Within an attempt the model may run
Python as many times as it needs (up to MAX_STEPS_PER_ATTEMPT model calls). A wrong answer
gets the checker's reviewer feedback and the agent tries again, up to `max_attempts`.

The prompt template, model, and tool are identical across all memory conditions; only
`memory_text` changes. Nothing here may hint at a lab convention (PLAN.md §11).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

from task2_checker_and_report.checker import check
from task3_agent_and_runner.llm import REPO_ROOT, call_llm, set_context

MAX_STEPS_PER_ATTEMPT = 8   # model calls per attempt; the last one must answer
CODE_TIMEOUT_S = 60
MAX_OUTPUT_CHARS = 4000

SYSTEM_PROMPT = """You are a new research assistant at a lab that monitors Madison's lakes.
Answer each question by writing Python and running it with the run_python tool. File paths
are relative to the working directory, and pandas is installed. Print whatever you need to see.

When you know the answer, reply with exactly one line:
FINAL ANSWER: <number>"""

USER_TEMPLATE = """Your notes from earlier tasks:
{memory}

Question: {prompt}"""

RUN_PYTHON_TOOL = {
    "type": "function",
    "function": {
        "name": "run_python",
        "description": "Run a Python script and return what it prints (stdout and stderr).",
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "The full Python script to run."}},
            "required": ["code"],
        },
    },
}

ANSWER_RE = re.compile(r"FINAL ANSWER\W*?([-+]?\d*\.?\d+)", re.IGNORECASE)


def run_task(task: dict, memory_text: str, max_attempts: int = 3) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(memory=(memory_text or "").strip() or "(none)",
                                                         prompt=task["prompt"])},
    ]
    attempts = []
    n_calls = in_tokens = out_tokens = 0
    answer, success = None, False

    for attempt in range(1, max_attempts + 1):
        set_context(attempt=attempt)
        runs = []
        answer = None
        for step in range(MAX_STEPS_PER_ATTEMPT):
            last_step = step == MAX_STEPS_PER_ATTEMPT - 1
            message, n_in, n_out = call_llm(messages, tools=[RUN_PYTHON_TOOL],
                                            tool_choice="none" if last_step else "auto")
            n_calls += 1
            in_tokens += n_in
            out_tokens += n_out
            messages.append(_assistant_entry(message))

            if message.tool_calls:
                for call in message.tool_calls:
                    code = _code_from(call.function.arguments)
                    output = run_python(code) if code else "Error: no code was given."
                    runs.append({"code": code, "output": output})
                    messages.append({"role": "tool", "tool_call_id": call.id, "content": output})
                continue

            answer = parse_answer(message.content)
            if answer is not None:
                break
            messages.append({"role": "user", "content": "Reply with exactly one line: FINAL ANSWER: <number>"})

        if answer is None:
            success, feedback = False, "No numeric answer was given."
        else:
            success, feedback = grade(task, answer)

        attempts.append({
            "attempt": attempt,
            "code": runs[-1]["code"] if runs else "",
            "stdout": runs[-1]["output"] if runs else "",
            "answer": answer,
            "feedback": "" if success else feedback,
            "runs": runs,
        })
        if success:
            break
        messages.append({"role": "user",
                         "content": f"That answer was marked wrong. Reviewer feedback: {feedback}\nPlease try again."})

    # `trace["attempts"]` is the list shape episodic memory reads (task4 branch).
    trace = {
        "task_id": task["id"],
        "answer": answer,
        "success": success,
        "memory_text": memory_text,
        "attempts": attempts,
        "messages": messages,
    }
    return {
        "answer": answer,
        "success": success,
        "first_try": success and len(attempts) == 1,
        "attempts": len(attempts),
        "n_calls": n_calls,
        "in_tokens": in_tokens,
        "out_tokens": out_tokens,
        "trace": trace,
    }


# --- the one tool ---

def run_python(code: str) -> str:
    """Run the agent's script in a fresh process from the repo root."""
    try:
        proc = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT,
                              capture_output=True, text=True, timeout=CODE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return f"Error: the script ran longer than {CODE_TIMEOUT_S}s and was stopped."
    output = proc.stdout
    if proc.stderr:
        output += f"\n[stderr]\n{proc.stderr}"
    output = output.strip() or "(no output)"
    if len(output) > MAX_OUTPUT_CHARS:
        half = MAX_OUTPUT_CHARS // 2
        output = output[:half] + "\n... (output truncated) ...\n" + output[-half:]
    return output


# --- grading ---

def grade(task: dict, answer: float) -> tuple[bool, str]:
    """Person 2's checker, or a stand-in until theirs is on main."""
    try:
        return check(task, answer)
    except NotImplementedError:
        return _stand_in_check(task, answer)


def _stand_in_check(task: dict, answer: float) -> tuple[bool, str]:
    """Same grading idea as PLAN.md §8: match the answer, else a planted wrong variant."""
    if abs(answer - task["answer"]) <= task["tol"]:
        return True, "Correct."
    for value, message in task["wrong_variants"].values():
        if abs(answer - value) <= task["tol"]:
            return False, message
    return False, "That doesn't match the lab's number. Check your work and try again."


# --- helpers ---

def parse_answer(text: str | None) -> float | None:
    matches = ANSWER_RE.findall(text or "")
    return float(matches[-1]) if matches else None


def _code_from(arguments: str) -> str:
    try:
        return json.loads(arguments).get("code", "")
    except (json.JSONDecodeError, AttributeError):
        return ""


def _assistant_entry(message) -> dict:
    """The model's reply as a plain dict, so it can be sent back and saved in the trace."""
    entry = {"role": "assistant", "content": message.content or ""}
    if message.tool_calls:
        entry["tool_calls"] = [
            {"id": c.id, "type": "function",
             "function": {"name": c.function.name, "arguments": c.function.arguments}}
            for c in message.tool_calls
        ]
    return entry
