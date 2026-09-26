"""Alarms gathered from the monitored components."""

from typing import TYPE_CHECKING

from ..chem.alarm import tank_alarm
from ..ns.alarm import Alarm
from ..pump.alarm import pump_alarm
from ..tank.alarm import level_alarm

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checkers
    from .plant import Plant


def alarms(plant: "Plant") -> list[Alarm]:
    """Current alarms of the chemical tank, high pressure pump and product level."""
    return [
        tank_alarm(plant.chem_tank),
        pump_alarm(plant.hp_pump),
        level_alarm(plant.level),
    ]
