# Models and coding tools used — for the report's required disclosure

Person 2: please merge each person's line into one combined statement for the report.

## Agent model (the model under test)

- `MODEL_NAME` in `.env` (read directly, key not included here): **`gpt-5.6-luna`**.
- `task3_agent_and_runner/llm.py` prices are commented as set "for MODEL_NAME (gpt-5.6-luna,
  standard tier)" — **this matches `.env`'s `MODEL_NAME`, no disagreement to flag.**
- Confirmed from `outputs/results/calls.csv` on this machine: every logged call used model
  `gpt-5.6-luna`, purpose `agent` — consistent with the above.

## Structured memory's own cost (Person 5's part)

- `StructuredMemory` (`task5_structured_memory/structured.py`) makes **zero LLM calls** — it is
  pure Python (string classification + in-memory bookkeeping). It adds no API cost beyond the
  agent's own calls; no `purpose="memory"` rows appear in `calls.csv` from this module.

## API cost observed

- From `outputs/results/calls.csv` **on this machine**: 89 logged calls, totaling **$0.0317**.
  This covers only the runs executed on this machine (two single-pass structured-only runs,
  `20261013-182822` and `20261013-193556`) — it does **not** include the full three-repeat,
  three-condition run (`20261013-200839`) that landed on `origin/main` from another machine, or
  any other teammate's runs. Person 2/Person 3 should sum `calls.csv` from wherever the
  authoritative/merged run outputs live for the report's total.

## Coding tools

- **Person 5 (this section, `task5_structured_memory/`): Claude Code.**
- Person 1: _<placeholder — fill in your own tool(s)>_
- Person 2: _<placeholder — fill in your own tool(s)>_
- Person 3: _<placeholder — fill in your own tool(s)>_
- Person 4: _<placeholder — fill in your own tool(s)>_

(Not filled in above because I only know what I used for my own part — don't want to guess
at anyone else's.)
