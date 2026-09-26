"""Antiscalant dosing pump and its stop ordering."""

from ..errors import ResidualAntiscalantError
from ..intake.feed import Feed
from .control import DosingProfile, dose_volume, setpoint
from .dose_rate import DoseRate


class Doser:
    """Dosing pump that keeps the antiscalant ahead of the feed stop."""

    def __init__(self) -> None:
        self.dosing = False
        self.rate = DoseRate(ppm=0.0)

    def start(self, feed: Feed) -> None:
        """Start dosing and mark the chemical as active on the feed."""
        self.dosing = True
        feed.set_chem_active(True)

    def stop(self, feed: Feed) -> None:
        """Stop the feed while the chemical is still injected, then stop dosing."""
        feed.begin_shutdown()
        feed.stop()
        if feed.scaled:
            raise ResidualAntiscalantError("residual antiscalant scaled membrane")
        self.dosing = False
        feed.set_chem_active(False)

    def set_dose_rate(self, rate: DoseRate) -> float:
        """Adopt a dose rate and report the concentration in use."""
        self.dosing = True
        self.rate = rate
        return rate.ppm

    def target_dose(self, flow: float, rate: float) -> float:
        """Dosing set point for a flow and a concentration."""
        return setpoint(flow, rate)

    def dose_volume(self, rate: float, flow: float, seconds: float) -> float:
        """Product volume delivered over a duration."""
        return dose_volume(DosingProfile(rate=rate, flow=flow), seconds)
