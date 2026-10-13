"""Unit tests for Task 4: NoMemory baseline and EpisodicMemory."""

import json
import sys
from pathlib import Path

# Ensure repo root is on sys.path whether executed directly or via python -m
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.interfaces import Memory
from task4_episodic_memory.episodic import EpisodicMemory, _extract_date_keywords
from task4_episodic_memory.no_memory import NoMemory


def test_no_memory_interface():
    """Verify NoMemory satisfies the shared Memory interface and stays empty."""
    mem = NoMemory()
    assert isinstance(mem, Memory)

    task = {
        "id": "T1",
        "prompt": "What was the mean water temp?",
        "files": ["task1_data_and_tasks/data/mendota.csv"],
    }
    trace = {"answer": 22.04, "attempts": []}

    # Cold retrieval
    assert mem.retrieve(task) == ""

    # Update should be a no-op
    mem.update(task, trace, success=True)
    assert mem.retrieve(task) == ""
    assert mem.snapshot() == ""


def test_episodic_memory_cold_start():
    """Verify EpisodicMemory returns empty string when no tasks have been run."""
    mem = EpisodicMemory()
    assert isinstance(mem, Memory)
    assert len(mem) == 0

    task = {"id": "T1", "prompt": "Mendota mean water temp, July"}
    assert mem.retrieve(task) == ""

    snap = json.loads(mem.snapshot())
    assert snap["condition"] == "episodic"
    assert snap["total_episodes"] == 0
    assert snap["episodes"] == []


def test_episodic_memory_update_and_snapshot():
    """Verify episode ingestion from execution trace and JSON snapshotting."""
    mem = EpisodicMemory()

    task1 = {
        "id": "T1",
        "prompt": "Using task1_data_and_tasks/data/mendota.csv, what was the mean water temperature (deg C) at Lake Mendota during July 2026?",
        "files": ["task1_data_and_tasks/data/mendota.csv"],
    }
    trace1 = {
        "answer": 22.04,
        "attempts": [
            {
                "attempt": 1,
                "code": "import pandas as pd\ndf = pd.read_csv('.../mendota.csv')\nprint(df['water_temp_C'].mean())",
                "answer": -112.65,
                "feedback": "Readings aren't trustworthy unless their own quality flag is 0; drop estimated, suspect, and offline values.",
            },
            {
                "attempt": 2,
                "code": "import pandas as pd\ndf = pd.read_csv('.../mendota.csv')\nprint(df[df['water_temp_qc'] == 0]['water_temp_C'].mean())",
                "answer": 22.04,
                "feedback": "",
            },
        ],
    }

    mem.update(task1, trace1, success=True)
    assert len(mem) == 1

    snap_str = mem.snapshot()
    snap = json.loads(snap_str)
    assert snap["total_episodes"] == 1
    assert snap["episodes"][0]["task_id"] == "T1"
    assert snap["episodes"][0]["success"] is True
    assert len(snap["episodes"][0]["feedbacks"]) == 1
    assert "quality flag is 0" in snap["episodes"][0]["feedbacks"][0]


def test_episodic_retrieval_relevance_and_misleading():
    """Verify retrieval surfaces relevant past episodes.

    Crucially tests:
    - T5 (Wingra, July 4) should retrieve T2 (Monona, July 4) which had C2 day-shift feedback.
    - T6 (Mendota, July wind speed) should retrieve T1 (Mendota, July water temp).
    """
    mem = EpisodicMemory(max_retrieved=2)

    # Seed T1 (Mendota July whole month)
    task1 = {
        "id": "T1",
        "prompt": "Using task1_data_and_tasks/data/mendota.csv, what was the mean water temperature (deg C) at Lake Mendota during July 2026?",
        "files": ["task1_data_and_tasks/data/mendota.csv"],
    }
    trace1 = {
        "answer": 22.04,
        "attempts": [
            {
                "attempt": 1,
                "code": "import pandas as pd\n# Dropping bad qc flags\n",
                "answer": 22.04,
                "feedback": "Readings aren't trustworthy unless their own quality flag is 0.",
            }
        ],
    }
    mem.update(task1, trace1, success=True)

    # Seed T2 (Monona July 4)
    task2 = {
        "id": "T2",
        "prompt": "Using task1_data_and_tasks/data/monona.csv, what was the maximum water temperature (deg C) at Lake Monona on July 4, 2026?",
        "files": ["task1_data_and_tasks/data/monona.csv"],
    }
    trace2 = {
        "answer": 28.0,
        "attempts": [
            {
                "attempt": 1,
                "code": "# attempt 1 calendar day\n",
                "answer": 23.64,
                "feedback": "Lab days run 08:00 to 08:00 local for the v1 stations, not midnight to midnight.",
            },
            {
                "attempt": 2,
                "code": "# shifted 08:00 to 08:00\n",
                "answer": 28.0,
                "feedback": "",
            },
        ],
    }
    mem.update(task2, trace2, success=True)

    # Test T5 retrieval: Wingra on July 4
    task5 = {
        "id": "T5",
        "prompt": "Using task1_data_and_tasks/data/wingra.csv, what was the mean water temperature (deg C) at Lake Wingra on July 4, 2026? Reply with one number to 2 decimals.",
        "files": ["task1_data_and_tasks/data/wingra.csv"],
    }
    retrieved_t5 = mem.retrieve(task5)
    # T5 should retrieve T2 because both share July 4 and water temperature!
    assert "T2" in retrieved_t5
    # The feedback from T2 containing the 08:00 day shift should be visible to agent
    assert "Lab days run 08:00 to 08:00" in retrieved_t5

    # Test T6 retrieval: Mendota July whole month
    task6 = {
        "id": "T6",
        "prompt": "Using task1_data_and_tasks/data/mendota.csv, what was the maximum wind speed (m/s) at Lake Mendota during July 2026?",
        "files": ["task1_data_and_tasks/data/mendota.csv"],
    }
    retrieved_t6 = mem.retrieve(task6)
    # T6 should rank T1 at top because both share Mendota and July whole month
    assert "T1" in retrieved_t6
    assert "quality flag is 0" in retrieved_t6


def test_episodic_robust_trace_handling():
    """Verify EpisodicMemory gracefully handles varied trace structures."""
    mem = EpisodicMemory()

    # Flat dict trace
    task_a = {"id": "TA", "prompt": "Question A", "files": []}
    mem.update(task_a, {"final_code": "print(1)", "feedback": "Try again", "answer": 1.0}, success=False)
    assert len(mem) == 1
    assert mem.episodes[0]["feedbacks"] == ["Try again"]

    # Raw string trace
    task_b = {"id": "TB", "prompt": "Question B", "files": []}
    mem.update(task_b, "print(2)", success=True)
    assert len(mem) == 2
    assert mem.episodes[1]["final_code"] == "print(2)"

    # List of attempts trace
    task_c = {"id": "TC", "prompt": "Question C", "files": []}
    mem.update(task_c, [{"code": "print(3)", "feedback": "Err"}], success=True)
    assert len(mem) == 3


def test_date_extraction_year_vs_day():
    """Verify 'July 2026' is not parsed as 'July 20', avoiding false date matches for T7."""
    assert _extract_date_keywords("mean water temperature during July 2026") == set()
    assert _extract_date_keywords("maximum water temperature on July 20, 2026") == {"july 20"}
    assert _extract_date_keywords("maximum water temperature on July 4, 2026") == {"july 4"}
    assert _extract_date_keywords("hours above 25 deg C on July 10, 2026") == {"july 10"}

    # Verify T7 does not get a false date overlap score with T1
    mem = EpisodicMemory()
    task1 = {
        "id": "T1",
        "prompt": "Using task1_data_and_tasks/data/mendota.csv, what was the mean water temperature (deg C) at Lake Mendota during July 2026?",
        "files": ["task1_data_and_tasks/data/mendota.csv"],
    }
    mem.update(task1, {"answer": 22.04}, success=True)

    task7 = {
        "id": "T7",
        "prompt": "Using task1_data_and_tasks/data/mendota.csv and task1_data_and_tasks/data/monona.csv, what was Lake Mendota's mean water temperature (deg C) minus Lake Monona's mean water temperature on July 20, 2026?",
        "files": ["task1_data_and_tasks/data/mendota.csv", "task1_data_and_tasks/data/monona.csv"],
    }
    # Date overlap between T7 and T1 should be empty
    t7_dates = _extract_date_keywords(task7["prompt"])
    t1_dates = _extract_date_keywords(task1["prompt"])
    assert t7_dates == {"july 20"}
    assert t1_dates == set()
    assert len(t7_dates.intersection(t1_dates)) == 0


if __name__ == "__main__":
    test_no_memory_interface()
    test_episodic_memory_cold_start()
    test_episodic_memory_update_and_snapshot()
    test_episodic_retrieval_relevance_and_misleading()
    test_episodic_robust_trace_handling()
    test_date_extraction_year_vs_day()
    print("All Task 4 tests passed successfully!")
