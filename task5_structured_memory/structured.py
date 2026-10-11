"""Person 5 (<name>): structured memory condition with rules, exceptions and forgetting."""

from shared.interfaces import Memory


class StructuredMemory(Memory):
    def retrieve(self, task: dict) -> str:
        raise NotImplementedError

    def update(self, task: dict, trace: dict, success: bool) -> None:
        raise NotImplementedError

    def snapshot(self) -> str:
        raise NotImplementedError
