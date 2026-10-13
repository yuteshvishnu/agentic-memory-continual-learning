"""Unit tests for Task 4: NoMemory baseline and EpisodicMemory."""

import json
from shared.interfaces import Memory
from task4_episodic_memory.no_memory import NoMemory
from task4_episodic_memory.episodic import EpisodicMemory


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


if __name__ == "__main__":
    test_no_memory_interface()
    test_episodic_memory_cold_start()
    test_episodic_memory_update_and_snapshot()
    test_episodic_retrieval_relevance_and_misleading()
    test_episodic_robust_trace_handling()
    print("All Task 4 tests passed successfully!")
