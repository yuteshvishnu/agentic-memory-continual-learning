"""Person 3: the single place that calls the LLM.

Every call is logged to outputs/results/calls.csv with its tokens and cost, and calls stop
once the logged total reaches the $5 budget (PLAN.md §2, §10). Memory code that calls the
model (e.g. structured memory) should use `call_llm(..., purpose="memory")` so its cost is
counted too.

Needs `.env` in the repo root with LLM_API_KEY and MODEL_NAME, and the two prices below.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parent.parent
CALLS_CSV = REPO_ROOT / "outputs" / "results" / "calls.csv"
BUDGET_USD = 5.0

# USD per 1M tokens for MODEL_NAME (gpt-5.6-luna, standard tier). Update both if the model changes.
PRICE_IN_PER_1M: float | None = 0.20
PRICE_OUT_PER_1M: float | None = 1.20

# gpt-5.6-luna rejects tools + reasoning on /v1/chat/completions, so reasoning is off for every
# call (same setting in all conditions). Older models like gpt-5-nano don't accept "none".
REASONING_EFFORT = "none"

CALL_FIELDS = ["time", "purpose", "condition", "repeat", "task_id", "attempt",
               "model", "in_tokens", "out_tokens", "cost_usd"]
CONTEXT_FIELDS = ["condition", "repeat", "task_id", "attempt"]

_client: OpenAI | None = None
_spent: float | None = None
_context: dict = {}


class BudgetExceeded(RuntimeError):
    pass


def set_context(**fields) -> None:
    """Tag the following calls in calls.csv (condition, repeat, task_id, attempt)."""
    _context.update(fields)


def cost(in_tokens: int, out_tokens: int) -> float:
    return (in_tokens * PRICE_IN_PER_1M + out_tokens * PRICE_OUT_PER_1M) / 1_000_000


def spent() -> float:
    """Total cost of every call in calls.csv, across all runs on this machine."""
    global _spent
    if _spent is None:
        _spent = 0.0
        if CALLS_CSV.exists():
            with CALLS_CSV.open() as f:
                _spent = sum(float(row["cost_usd"]) for row in csv.DictReader(f))
    return _spent


def call_llm(messages: list[dict], tools: list[dict] | None = None,
             tool_choice: str | None = None, purpose: str = "agent"):
    """One model call, logged. Returns (message, in_tokens, out_tokens)."""
    global _client, _spent
    if spent() >= BUDGET_USD:
        raise BudgetExceeded(f"${spent():.2f} already spent; the budget is ${BUDGET_USD:.2f}.")
    if _client is None:
        if PRICE_IN_PER_1M is None or PRICE_OUT_PER_1M is None:
            raise RuntimeError("Set PRICE_IN_PER_1M and PRICE_OUT_PER_1M in task3_agent_and_runner/llm.py.")
        load_dotenv(REPO_ROOT / ".env")
        _client = OpenAI(api_key=os.environ["LLM_API_KEY"])

    model = os.environ["MODEL_NAME"]
    kwargs = {"model": model, "messages": messages, "reasoning_effort": REASONING_EFFORT}
    if tools:
        kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice
    response = _client.chat.completions.create(**kwargs)

    in_tokens = response.usage.prompt_tokens
    out_tokens = response.usage.completion_tokens
    call_cost = cost(in_tokens, out_tokens)
    _spent = spent() + call_cost
    _log({
        "time": datetime.now().isoformat(timespec="seconds"),
        "purpose": purpose,
        **{k: _context.get(k, "") for k in CONTEXT_FIELDS},
        "model": model,
        "in_tokens": in_tokens,
        "out_tokens": out_tokens,
        "cost_usd": round(call_cost, 6),
    })
    return response.choices[0].message, in_tokens, out_tokens


def _log(row: dict) -> None:
    new_file = not CALLS_CSV.exists()
    CALLS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with CALLS_CSV.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CALL_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)
