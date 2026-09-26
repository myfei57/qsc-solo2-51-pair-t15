"""Recovery latch that freezes the rate while it is raised."""


class Recovery:
    """Recovery rate with a latch that blocks rate updates."""

    def __init__(self) -> None:
        self.alarm = False
        self._rate = 0.0

    def raise_alarm(self) -> None:
        """Raise the latch so the rate stops following the line."""
        self.alarm = True

    def clear_alarm(self) -> None:
        """Clear the latch."""
        self.alarm = False

    def active(self) -> bool:
        """Whether the latch is raised."""
        return self.alarm

    def update_rate(self, rate: float) -> float:
        """Adopt a new rate unless the latch is raised."""
        if self.alarm:
            return self._rate
        self._rate = float(rate)
        return self._rate

    def rate(self) -> float:
        """Latest adopted recovery rate."""
        return self._rate
