"""Filter rack whose rinse state is checked before the pump stops."""

from .state import RackState

BLOCKED_GROWTH = 100.0
UNRINSED_GROWTH = 35.0


class Rack:
    """Rack that has to be rinsed while the intake pump still runs."""

    def __init__(self, jammed: bool = False) -> None:
        self.rinsed = False
        self.blocked = False
        self.jammed = jammed

    def rinse(self, pump_running: bool) -> bool:
        """Rinse the rack; a stopped pump or a jam leaves it blocked."""
        if not pump_running or self.jammed:
            self.rinsed = False
            self.blocked = True
            return False
        self.rinsed = True
        self.blocked = False
        return True

    def was_rinsed(self) -> bool:
        """Whether the last rinse succeeded."""
        return self.rinsed

    def clean(self) -> None:
        """Clear the rack by hand during maintenance."""
        self.rinsed = True
        self.blocked = False

    def inspect(self) -> RackState:
        """Score how much growth the rack carries."""
        growth = 0.0
        if self.blocked:
            growth = BLOCKED_GROWTH
        if not self.was_rinsed():
            growth += UNRINSED_GROWTH
        return RackState(growth_score=growth, blocked=self.blocked)
