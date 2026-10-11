"""Shared (whole team): Memory base class that every memory condition implements."""


class Memory:
    def retrieve(self, task: dict) -> str:
        raise NotImplementedError

    def update(self, task: dict, trace: dict, success: bool) -> None:
        raise NotImplementedError

    def snapshot(self) -> str:
        raise NotImplementedError
