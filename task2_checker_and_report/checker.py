"""Person 2(Sreemae): grade an agent answer against the task's ground truth and return reviewer feedback."""


def check(task: dict, answer: float) -> tuple[bool, str]:
    # 1. The answer must be a single number.
    try:
        value = float(str(answer).strip())
    except ValueError:
        return False, "Could not read a single numeric answer."

    # 2. Correct if within tolerance (1e-9 absorbs floating-point noise).
    tol = task["tol"] + 1e-9
    if abs(value - task["answer"]) <= tol:
        return True, "Correct."

    # 3. A known mistake: return the reviewer message that names the broken rule.
    for wrong_value, message in task.get("wrong_variants", {}).values():
        if abs(value - wrong_value) <= tol:
            return False, message

    # 4. Anything else: generic message that leaks no rule.
    return False, "Incorrect. Re-check how the data was processed."