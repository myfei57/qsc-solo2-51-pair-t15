"""Pressure differential computed from the freshest sensor map."""

from ..ro.array import MembraneArray
from .state import Pump


def differential(pump: Pump, array: MembraneArray, readings: dict[str, float]) -> float:
    """Sum the readings mapped to the final stage; zero on a stale map."""
    if not _differential_valid(array):
        return 0.0
    last = array.last_stage()
    return sum(value for sensor, value in readings.items() if array.sensor_stage(sensor) == last)


def _differential_valid(array: MembraneArray) -> bool:
    return array.map_fresh() and array.stage_count() > 0
