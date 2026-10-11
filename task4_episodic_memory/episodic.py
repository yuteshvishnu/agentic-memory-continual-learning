"""Person 4 (<name>): episodic memory condition that stores and retrieves past task episodes."""

from shared.interfaces import Memory


class EpisodicMemory(Memory):
    def retrieve(self, task: dict) -> str:
        raise NotImplementedError

    def update(self, task: dict, trace: dict, success: bool) -> None:
        raise NotImplementedError

    def snapshot(self) -> str:
        raise NotImplementedError
