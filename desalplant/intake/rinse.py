"""Rack rinse gate used before the intake pump stops."""

from ..errors import RinseFailedError


class RinseGate:
    """Runs one rack rinse and remembers whether it completed."""

    def __init__(self) -> None:
        self.completed = False

    def rinse(self, rack, running: bool) -> None:
        """Rinse the rack; the pump has to be running for the rinse to count."""
        if not running:
            raise RinseFailedError("intake pump not running during rinse")
        if not rack.rinse(running):
            raise RinseFailedError("rack rinse did not clear the rack")
        self.completed = True

    def require_complete(self) -> None:
        """Raise unless the rinse finished."""
        if not self.completed:
            raise RinseFailedError("rack rinse failed")
