"""Brine stream arithmetic."""


def reject_flow(concentration: float, feed: float) -> float:
    """Concentrate flow leaving the train."""
    return feed * concentration


def recovery_rate(concentration: float, feed: float) -> float:
    """Fraction of the feed that leaves as permeate."""
    if feed <= 0:
        return 0.0
    return 1 - reject_flow(concentration, feed) / feed


def disposal_volume(concentration: float, feed: float, hours: float) -> float:
    """Concentrate volume produced over a number of hours."""
    return reject_flow(concentration, feed) * hours


def concentration_ratio(flow: float, concentration: float) -> float:
    """Share of the combined stream carried by the permeate."""
    if flow <= 0:
        return 0.0
    return flow / (flow + concentration)
