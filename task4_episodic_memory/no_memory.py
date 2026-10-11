"""Person 4 (<name>): no-memory baseline condition."""

from shared.interfaces import Memory


class NoMemory(Memory):
    def retrieve(self, task: dict) -> str:
        raise NotImplementedError

    def update(self, task: dict, trace: dict, success: bool) -> None:
        raise NotImplementedError

    def snapshot(self) -> str:
        raise NotImplementedError
