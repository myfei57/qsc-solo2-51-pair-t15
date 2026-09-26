"""Feed line that carries raw water towards the membrane train."""

from ..errors import FeedAlreadyStoppedError


class Feed:
    """Tracks whether the feed flows and whether dosing is still active."""

    def __init__(self) -> None:
        self.flowing = False
        self.chem_active = False
        self.scaled = False

    def start(self) -> None:
        """Open the feed and clear any previous scaling flag."""
        self.flowing = True
        self.scaled = False

    def stop(self) -> None:
        """Close the feed.

        Stopping while the chemical is still active leaves residual antiscalant
        on the membrane, which is recorded on the feed itself.
        """
        self.flowing = False
        self.scaled = not self.chem_active

    def set_chem_active(self, active: bool) -> None:
        """Record whether the dosing pump is currently feeding chemical."""
        self.chem_active = bool(active)

    def begin_shutdown(self) -> None:
        """Guard a shutdown attempt, refusing one on an already idle feed."""
        if not self.flowing:
            raise FeedAlreadyStoppedError("feed already stopped")

    def flushing(self) -> bool:
        """True while feed water is moving with chemical still injected."""
        return self.flowing and self.chem_active

    def available(self, required: float) -> bool:
        """Whether the feed can supply at least ``required`` units."""
        return self.flowing and required > 0
