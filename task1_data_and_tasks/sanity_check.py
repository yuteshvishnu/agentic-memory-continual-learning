"""Person 1: definition-of-done sanity check.

Three gates, for every task:
  1. Separability     -- each wrong variant differs from the correct answer
                         (> 0.1 for numeric tasks, >= 1 for counts).
  2. No collisions    -- the answer and all variant values are mutually
                         distinguishable (> tol / >= 1), so the checker can map an
                         answer to exactly one message.
  3. Compound coverage -- for every multi-rule task, the cold-agent compound mistake
                         (both rules broken) matches the answer or some variant, so the
                         checker never has to fall back to a hint-less generic message.
  4. Flag rule tested -- on the mean/count tasks, "drop only -9999 but keep the suspect
                         flag-1/2 readings" is outside tolerance (> 0.1 / >= 1), so an
                         agent can't pass without learning the full quality-flag rule.

Run from the repo root:
    python -m task1_data_and_tasks.generate_data
    python -m task1_data_and_tasks.reference
    python -m task1_data_and_tasks.sanity_check
"""

from task1_data_and_tasks.reference import TOL, build_tasks, cold_compounds, suspect_values

MIN_NUMERIC_GAP = 0.1


def main() -> None:
    tasks = build_tasks()
    compounds = cold_compounds()
    suspects = suspect_values()
    failures = []

    for task in tasks:
        ans = task["answer"]
        is_count = isinstance(ans, int)
        variants = task["wrong_variants"]
        print(f"\n{task['id']}: answer = {ans}" + ("  (count)" if is_count else ""))

        # 1. separability: answer vs each variant
        for name, (value, _msg) in variants.items():
            gap = abs(value - ans)
            ok = (gap >= 1) if is_count else (gap > MIN_NUMERIC_GAP)
            print(f"    {name:<16} = {str(value):<10} gap={gap:<10.3f} [{'ok' if ok else 'FAIL'}]")
            if not ok:
                failures.append(f"{task['id']}/{name}: too close to answer (gap={gap:.3f})")

        # 2. no collisions: all of {answer} + variant values mutually distinguishable
        labeled = [("answer", ans)] + [(n, v[0]) for n, v in variants.items()]
        for i in range(len(labeled)):
            for j in range(i + 1, len(labeled)):
                (na, a), (nb, b) = labeled[i], labeled[j]
                collide = (a == b) if is_count else (abs(a - b) <= TOL)
                if collide:
                    failures.append(f"{task['id']}: '{na}' and '{nb}' collide at {a}")

        # 3. compound coverage for multi-rule tasks
        if task["id"] in compounds:
            cval, cint = compounds[task["id"]]
            targets = [ans] + [v[0] for v in variants.values()]
            covered = any((t == cval) if cint else (abs(t - cval) <= TOL) for t in targets)
            tag = "ok" if covered else "UNCOVERED"
            print(f"    compound (both)  = {str(cval):<10} {'(covered)' if covered else '(NOT COVERED)'} [{tag}]")
            if not covered:
                failures.append(f"{task['id']}: compound mistake {cval} matches no variant/answer")

        # 4. flag rule actually tested on mean/count tasks
        if task["id"] in suspects:
            sval, sint = suspects[task["id"]]
            gap = abs(sval - ans)
            tested = (gap >= 1) if sint else (gap > MIN_NUMERIC_GAP)
            tag = "ok" if tested else "UNTESTED"
            print(f"    drop-9999-only   = {str(sval):<10} gap={gap:<10.3f} "
                  f"{'(flag rule tested)' if tested else '(WITHIN TOL - graded correct!)'} [{tag}]")
            if not tested:
                failures.append(f"{task['id']}: 'drop only -9999' ({sval}) is within tolerance -> C1 untested")

    print("\n" + "=" * 56)
    if failures:
        print("SANITY FAILED:")
        for f in failures:
            print("   ", f)
        raise SystemExit(1)
    print(f"SANITY OK - all {len(tasks)} tasks: separable, collision-free, compound-covered.")


if __name__ == "__main__":
    main()
