"""Person 2 (<name>): grade an agent answer against the task's ground truth and return reviewer feedback."""


def check(task: dict, answer: str) -> tuple[bool, str]:
    raise NotImplementedError
