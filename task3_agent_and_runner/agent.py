"""Person 3 (<name>): LLM agent loop that answers one task, retrying with checker feedback."""


def run_task(task: dict, memory_text: str, max_attempts: int = 3) -> dict:
    raise NotImplementedError
