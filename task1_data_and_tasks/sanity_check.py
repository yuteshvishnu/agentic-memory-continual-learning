"""Person 1: definition-of-done sanity check.

For every task, prints the correct answer and each planted wrong variant, and
asserts each variant is distinguishable from the answer: numeric answers must
differ by > 0.1 (tol is 0.05), integer-count answers by >= 1.

Run from the repo root:
    python -m task1_data_and_tasks.generate_data
    python -m task1_data_and_tasks.reference
    python -m task1_data_and_tasks.sanity_check
"""

from task1_data_and_tasks.reference import build_tasks

MIN_NUMERIC_GAP = 0.1


def main() -> None:
    tasks = build_tasks()
    failures = []
    for task in tasks:
        ans = task["answer"]
        is_int = isinstance(ans, int)
        print(f"\n{task['id']}: answer = {ans}" + ("  (count)" if is_int else ""))
        for name, (value, _msg) in task["wrong_variants"].items():
            gap = abs(value - ans)
            ok = (abs(value - ans) >= 1) if is_int else (gap > MIN_NUMERIC_GAP)
            flag = "ok" if ok else "FAIL"
            print(f"    {name:<16} = {value:<10} gap={gap:.3f}  [{flag}]")
            if not ok:
                failures.append(f"{task['id']}/{name} (gap={gap:.3f})")

    print("\n" + "=" * 48)
    if failures:
        print("SANITY FAILED - variants too close to the answer:")
        for f in failures:
            print("   ", f)
        raise SystemExit(1)
    print(f"SANITY OK - all {len(tasks)} tasks have distinguishable variants.")


if __name__ == "__main__":
    main()
