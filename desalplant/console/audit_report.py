"""Report over the train geometry, histograms and schedules."""

from typing import TYPE_CHECKING, Any

from ..chem.schedule import DoseSchedule, schedule_due
from ..filter.history import BackwashHistory
from ..flush.history import History
from ..flush.stage import Stage, plan as build_plan
from ..pump.telemetry import collect
from ..ro.train import Train
from ..tank.history import LevelHistory

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checkers
    from .plant import Plant

TRAIN = Train(stages=3, elements_per_stage=7)
TRAIN_FEED = 80.0
TRAIN_CONCENTRATE = 20.0
TRAIN_PERMEATE = 52.0
PUMP_POWER = 60.0
PUMP_FLOW = 46.0
INTAKE_FLOW = 80.0
SCREEN_LIMIT = 30.0
DOSE_SCHEDULE = DoseSchedule(interval=900, last=100)
DOSE_NOW = 600
FLUSH_STAGES = (
    Stage(name="pre-rinse", seconds=15),
    Stage(name="chemical-rinse", seconds=20),
    Stage(name="post-rinse", seconds=15),
)
BACKWASH_DROPS = (12.0, 15.0, 11.0)
LEVEL_SAMPLES = (40.0, 58.0, 72.0)


def build_audit_report(plant: "Plant") -> dict[str, Any]:
    """Assembly of the audit report payload."""
    stage_feeds = TRAIN.stage_feed(TRAIN_FEED)
    pump_telemetry = collect(plant.hp_pump, PUMP_POWER, PUMP_FLOW)
    stream_telemetry = plant.brine_stream.collect(plant.hp_pump.pressure)
    intake_telemetry = plant.intake_pump.collect(INTAKE_FLOW, plant.screen)
    dose_due = schedule_due(plant.doser, DOSE_SCHEDULE, DOSE_NOW)

    flush_history = History()
    flush_plan = build_plan(FLUSH_STAGES)
    flush_history.record(flush_plan)
    flush_history.record(flush_plan)

    level_history = LevelHistory()
    for sample in LEVEL_SAMPLES:
        level_history.record(sample)

    backwash_history = BackwashHistory()
    for drop in BACKWASH_DROPS:
        backwash_history.record(drop)

    return {
        "train_elements": TRAIN.total_elements(),
        "train_recovery": TRAIN.recovery(TRAIN_FEED, TRAIN_CONCENTRATE),
        "train_flux": TRAIN.flux(TRAIN_PERMEATE),
        "stage_feeds": list(stage_feeds),
        "pump_efficiency": pump_telemetry.efficiency(),
        "pump_pressure": pump_telemetry.pressure,
        "stream_recovery": stream_telemetry.recovery(),
        "intake_fouled": intake_telemetry.fouled(SCREEN_LIMIT),
        "dose_due": dose_due,
        "flush_average": flush_history.average_seconds(),
        "flush_runs": flush_history.runs,
        "level_min": level_history.min(),
        "level_max": level_history.max(),
        "level_average": level_history.average(),
        "level_span": level_history.span(),
        "backwash_average": backwash_history.average_drop(),
        "backwash_worst": backwash_history.worst_drop(),
        "stream": stream_telemetry.to_dict(),
        "stream_concentration": plant.brine_stream.concentration,
    }
