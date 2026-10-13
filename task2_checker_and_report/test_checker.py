"""Quick check. Run from the repo root:  python3 -m task2_checker_and_report.test_checker"""
import json

from task2_checker_and_report.checker import check

# A fake task, as in the PDF.
fake = {"answer": 21.37, "tol": 0.05,
        "wrong_variants": {"shifted_wingra": [20.81, "Wingra uses a normal calendar day."]}}

assert check(fake, 21.37) == (True, "Correct.")
assert check(fake, 21.42)[0] is True                       # edge of tolerance
assert check(fake, 20.81) == (False, "Wingra uses a normal calendar day.")
assert check(fake, 5.0) == (False, "Incorrect. Re-check how the data was processed.")
assert check(fake, "about 21") == (False, "Could not read a single numeric answer.")

# Every real task: its own answer passes, and each wrong variant gets its own message.
for t in json.load(open("task1_data_and_tasks/tasks.json")):
    assert check(t, t["answer"])[0], t["id"]
    for value, message in t.get("wrong_variants", {}).values():
        assert check(t, value) == (False, message), t["id"]

print("All checks passed.")