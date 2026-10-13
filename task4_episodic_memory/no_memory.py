"""Person 4 (Shubhangi): no-memory baseline condition."""

from shared.interfaces import Memory


class NoMemory(Memory):
    """Baseline condition that retains nothing between tasks.

    Each task starts completely cold. The agent must rediscover conventions C1/C2
    on every task from scratch.
    """

    def retrieve(self, task: dict) -> str:
        """Returns empty string; no memory context is injected."""
        return ""

    def update(self, task: dict, trace: dict, success: bool) -> None:
        """No-op; baseline retains no state across tasks."""
        pass

    def snapshot(self) -> str:
        """Returns empty string indicating no memory state."""
        return ""
