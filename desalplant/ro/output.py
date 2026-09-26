"""Permeate output derived from the pump efficiency baseline."""


def valid_efficiency(efficiency: float) -> bool:
    """Whether an efficiency factor sits inside the admissible band."""
    return 0.0 < efficiency <= 1.0


class Output:
    """Actual permeate output for a given power draw."""

    def __init__(self) -> None:
        self.actual_flow = 0.0

    def check(self, efficiency: float, power: float) -> float:
        """Expected flow for a power draw; a stale baseline yields nothing."""
        if not valid_efficiency(efficiency):
            self.actual_flow = 0.0
            return 0.0
        expected = efficiency * power
        self.actual_flow = expected
        return expected
