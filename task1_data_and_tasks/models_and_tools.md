# Models and coding tools used — Person 1 (Akshat)

For Person 2 to fold into the report's required "which models and tools we used" disclosure.

- **Coding assistant:** Claude Code (Anthropic's CLI agent), model **Claude Opus 4.8 (1M
  context)** — used to design and write `generate_data.py`, `reference.py`, `sanity_check.py`,
  the task sequence, and the report section, and to analyze the run traces for the discussion
  notes.
- **Language / libraries:** **Python 3.9.6** with **pandas 2.3.3** and **numpy 2.0.2** (local
  virtualenv) to generate the three station CSVs and compute/verify the answers.
- **Version control:** git and the GitHub CLI (`gh`) for branches and pull requests.

**Important distinction for the report:** Person 1's data pipeline makes **no LLM calls at
runtime** — it is deterministic pandas/numpy. The model above was a development/coding aid only.
The experiment's fixed model *under test* (`gpt-5.6-luna`, reasoning off) is Person 3's and is
separate from this.
