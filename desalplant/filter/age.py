"""Age limit for the filtration media bed."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MediaAge:
    """Age of the media in days against its service limit."""

    days: int
    limit: int

    def expired(self) -> bool:
        """True once the media has reached its service limit."""
        return self.days >= self.limit

    def remaining(self) -> int:
        """Days left before the media expires, never negative."""
        return max(self.limit - self.days, 0)
