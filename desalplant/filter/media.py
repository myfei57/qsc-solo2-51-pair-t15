"""Media bed that has to be backwashed before it filters again."""

from ..errors import MediaNotReadyError

CLEAN_DROP_FACTOR = 0.18
DIRTY_DROP_FACTOR = 0.42


class MediaFilter:
    """Media bed whose head loss depends on the last backwash."""

    def __init__(self) -> None:
        self.backwashed = False

    def backwash(self) -> None:
        """Mark the bed as freshly backwashed."""
        self.backwashed = True

    def ready(self) -> bool:
        """Whether the bed has been backwashed."""
        return self.backwashed

    def require_ready(self) -> None:
        """Raise unless the bed has been backwashed."""
        if not self.backwashed:
            raise MediaNotReadyError("media bed has not been backwashed")

    def pressure_drop(self, flow: float) -> float:
        """Head loss across the bed at a given flow."""
        if flow <= 0:
            return 0.0
        if self.backwashed:
            return flow * CLEAN_DROP_FACTOR
        return flow * DIRTY_DROP_FACTOR

    def needs_backwash(self, drop: float, limit: float) -> bool:
        """Whether the measured head loss or the flag calls for a backwash."""
        return drop > limit or not self.backwashed
