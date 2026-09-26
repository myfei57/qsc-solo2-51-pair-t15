"""Numeric report over the pump, permeate, schedules and record stream."""

from typing import TYPE_CHECKING, Any

from ..audit import summary as audit_summary
from ..brine.control import recovery_position
from ..brine.limit import RecoveryLimit
from ..chem.dose_calc import DoseHistory
from ..filter.age import MediaAge
from ..flush.control import Program
from ..flush.stage import Stage, plan as build_plan
from ..intake.schedule import CleanSchedule
from ..ns.metrics import Metrics
from ..pump.curve_fit import fitted_flow
from ..pump.curve_set import CurvePoint, new_curve
from ..ro.hydraulics import ConcentrationPolarization, PressureVessel
from ..store.checksum import short
from ..tank.transfer import Transfer, allowed, transfer as move_tanks

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checkers
    from .plant import Plant

FITTED_POWER = 55.0
RECOVERY_LIMIT = RecoveryLimit(min=30.0, max=55.0)
CLEAN_SCHEDULE = CleanSchedule(interval=600, last=100)
FILTER_AGE = MediaAge(days=90, limit=120)
TRANSFER_MOVE = Transfer(source="tank-a", destination="tank-b", amount=10.0)
EMPTY_TRANSFER = Transfer(source="tank-a", destination="tank-b", amount=0.0)
VESSEL = PressureVessel(elements=7, active=7)
POLARIZATION = ConcentrationPolarization(feed=35.0, brine=41.0)
FLUSH_STAGES = (
    Stage(name="pre-rinse", seconds=15),
    Stage(name="chemical-rinse", seconds=20),
    Stage(name="post-rinse", seconds=15),
)


def build_curve() -> Any:
    """Reference efficiency curve used by the report and telemetry sweeps."""
    return new_curve(
        [
            CurvePoint(power=20.0, flow=14.0),
            CurvePoint(power=50.0, flow=38.0),
            CurvePoint(power=80.0, flow=62.0),
        ]
    )


def build_report(plant: "Plant") -> dict[str, Any]:
    """Assemble the numeric report for the console."""
    metrics = Metrics()
    metrics.inc("report")
    metrics.set("supply", plant.hp_pump.supply)
    metrics.observe("recovery", plant.brine_stream.recover(plant.hp_pump.pressure))

    grade = plant.permeate.grade()
    safe = plant.permeate.safe(300.0)
    fitted = fitted_flow(plant.hp_pump, build_curve(), FITTED_POWER)
    valve_position = recovery_position(
        plant.valve, plant.brine_stream.recover(plant.hp_pump.pressure), RECOVERY_LIMIT
    )
    clean_due = plant.intake_pump.clean_due(CLEAN_SCHEDULE, 500)
    age_expired = FILTER_AGE.expired()

    move_tanks(plant.tank_set, TRANSFER_MOVE)

    history = DoseHistory()
    history.record(12.0)
    history.record(14.0)

    flush_plan = build_plan(FLUSH_STAGES)
    program = Program(stages=flush_plan.stages)
    program.advance()
    program.advance()
    complete = program.complete()

    checksum = plant.store.checksum()
    event_summary = audit_summary.counts(plant.store, plant.recorder.sequence)
    recent_start = audit_summary.recent(plant.store, plant.recorder.sequence, "start", 5)

    return {
        "metrics": metrics.snapshot(),
        "grade": grade.to_dict(),
        "safe": safe,
        "fitted_flow": fitted,
        "recovery_position": valve_position,
        "clean_due": clean_due,
        "media_age_expired": age_expired,
        "media_age_remaining": FILTER_AGE.remaining(),
        "transfer_ok": allowed(plant.tank_set, TRANSFER_MOVE),
        "empty_transfer_rejected": not allowed(plant.tank_set, EMPTY_TRANSFER),
        "dose_average": history.average(),
        "dose_total": history.total,
        "flush_valid": flush_plan.valid(),
        "flush_complete": complete,
        "store_checksum": short(checksum),
        "event_summary": event_summary,
        "recent_start": [event.to_dict() for event in recent_start],
        "vessel_packed": VESSEL.packed(),
        "vessel_dead_end": VESSEL.dead_end(),
        "polarization": POLARIZATION.factor(),
    }
