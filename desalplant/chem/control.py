"""Dose volume and set point arithmetic."""

from dataclasses import dataclass

SECONDS_PER_HOUR = 3600.0
PPM_SCALE = 1000.0


@dataclass(frozen=True)
class DosingProfile:
    """Rate and flow used to size a dose."""

    rate: float
    flow: float


def dose_volume(profile: DosingProfile, seconds: float) -> float:
    """Product volume delivered over a duration."""
    return profile.rate * profile.flow * seconds / SECONDS_PER_HOUR


def setpoint(flow: float, target: float) -> float:
    """Dosing set point for a feed flow and a target concentration."""
    if flow <= 0:
        return 0.0
    return target * flow / PPM_SCALE
