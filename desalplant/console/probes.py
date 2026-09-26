"""Console probes: staged operations run one at a time for inspection."""

from typing import TYPE_CHECKING, Any

from ..audit import summary as audit_summary
from ..brine.control import RecoveryTarget, position_for
from ..chem.control import DosingProfile, dose_volume, setpoint
from ..chem.dose_rate import DoseRate
from ..chem.dose_calc import DoseHistory
from ..errors import ContractError
from ..filter.backwash import finish_backwash
from ..filter.control import schedule
from ..flush.control import Program
from ..flush.stage import Stage, plan as build_plan
from ..intake.flow import FeedRamp
from ..pump.batch import record_run
from ..pump.controller import hold
from ..pump.ramp import RampProfile, apply_profile
from ..ro.batch import Batch
from ..ro.hydraulics import ConcentrationPolarization, Flux, PressureVessel
from ..tank.band import LevelBand
from ..tank.capacity import capacity

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checkers
    from .plant import Plant

BACKWASH_FLOW = 80.0
BACKWASH_LIMIT = 20.0
FEED_END = 80.0
FEED_START = 0.0
SCREEN_LIMIT = 30.0
RECOVERY_SETPOINT = 45.0
DOSE_PPM = 2.5
DOSE_FLOW = 80.0
DOSE_SECONDS = 3600.0
HYDRAULIC_FLOW = 52.0
MEMBRANE_FEED = 80.0
LEVEL_BAND = LevelBand(low=20.0, high=85.0)
LEVEL_TARGET = 72.0
TANK_VOLUME = 1000.0
SELFTEST_BATCH = Batch(id="b-1001", permeate=52.0, conductivity=120.0)
SELFTEST_FEED = 80.0
FLUSH_STAGES = (
    Stage(name="pre-rinse", seconds=15),
    Stage(name="chemical-rinse", seconds=20),
    Stage(name="post-rinse", seconds=15),
)


def run_ramp_profile(plant: "Plant") -> dict[str, Any]:
    """Walk a stepped pressure ramp and hold the result."""
    profile = RampProfile(start=0.0, end=60.0, step=5.0)
    pressure = apply_profile(plant.hp_pump, profile)
    return {
        "pressure": pressure,
        "steps": profile.steps(),
        "held": hold(plant.hp_pump, pressure),
    }


def run_backwash_check(plant: "Plant") -> dict[str, Any]:
    """Measure the media head loss and check the backwash schedule."""
    drop = plant.media.pressure_drop(BACKWASH_FLOW)
    needs = plant.media.needs_backwash(drop, BACKWASH_LIMIT)
    backwash_schedule = schedule(120)
    return {
        "pressure_drop": drop,
        "needs_backwash": needs,
        "due": backwash_schedule.due(180),
    }


def run_feed_ramp(plant: "Plant") -> dict[str, Any]:
    """Ramp the feed and check the screen and the rinse path."""
    feed_ramp = FeedRamp(start=FEED_START, end=FEED_END)
    flow = plant.intake_pump.ramp_feed(feed_ramp)
    cleaned = plant.intake_pump.screen_clean(plant.screen, SCREEN_LIMIT)
    sweep = plant.intake_pump.collect(flow, plant.screen)
    available = plant.intake_pump.feed_backwash(feed_ramp, plant.feed)
    return {
        "flow": flow,
        "screen_cleaned": cleaned,
        "sweep": sweep.to_dict(),
        "feed_flow": available,
    }


def run_recovery_control(plant: "Plant") -> dict[str, Any]:
    """Compare the measured recovery with its set point and position the valve."""
    actual = plant.membrane.recovery(MEMBRANE_FEED)
    target = RecoveryTarget(setpoint=RECOVERY_SETPOINT, actual=actual)
    position = position_for(plant.valve, actual)
    if position == "closed":
        plant.valve.close_valve()
    elif position == "open":
        plant.valve.open_valve()
    return {
        "deviation": target.deviation(),
        "within": target.within(1.0),
        "position": position,
        "emergency": plant.valve.emergency,
    }


def run_flush_program(plant: "Plant") -> dict[str, Any]:
    """Advance a staged flush program and report what remains."""
    flush_plan = build_plan(FLUSH_STAGES)
    program = Program(stages=flush_plan.stages)
    program.advance()
    program.advance()
    return {
        "remaining": program.remaining(),
        "total": flush_plan.total_seconds(),
        "names": list(flush_plan.names()),
    }


def run_dosing_control(plant: "Plant") -> dict[str, Any]:
    """Size a dose and report the dosing set point."""
    profile = DosingProfile(rate=DOSE_PPM, flow=DOSE_FLOW)
    volume = plant.doser.dose_volume(DOSE_PPM, DOSE_FLOW, DOSE_SECONDS)
    return {
        "volume": volume,
        "setpoint": setpoint(DOSE_FLOW, DOSE_PPM),
        "profile_volume": dose_volume(profile, DOSE_SECONDS),
        "dosing": plant.doser.dosing,
        "flushing": plant.feed.flushing(),
    }


def run_hydraulics(plant: "Plant") -> dict[str, Any]:
    """Report flux, vessel load, polarization and permeate flow."""
    flux = Flux(permeate=HYDRAULIC_FLOW, area=36.0)
    vessel = PressureVessel(elements=7, active=7)
    polarization = ConcentrationPolarization(feed=35.0, brine=41.0)
    stats = plant.permeate.measure_flow(HYDRAULIC_FLOW)
    return {
        "flux": flux.to_dict(),
        "recovery_percent": plant.membrane.recovery(MEMBRANE_FEED),
        "vessel_packed": vessel.packed(),
        "vessel_dead_end": vessel.dead_end(),
        "polarization": polarization.factor(),
        "permeate": stats.to_dict(),
    }


def run_tank_level(plant: "Plant") -> dict[str, Any]:
    """Fill the product tank to a target and report the tank set."""
    previous = plant.level.percent
    plant.level.fill_to(LEVEL_TARGET)
    projection = capacity(plant.product, TANK_VOLUME)
    return {
        "level": plant.level.percent,
        "within": plant.level.within(LEVEL_BAND),
        "trend": plant.level.trend(previous),
        "active": plant.tank_set.active_id(),
        "ids": list(plant.tank_set.ids()),
        "standby_open": plant.tank_set.is_open(plant.tank_set.standby),
        "tanks": [tank.to_dict() for tank in plant.tank_set.tanks.values()],
        "capacity": projection.to_dict(),
    }


def build_selftest(plant: "Plant") -> dict[str, Any]:
    """Drive the line through a full cycle and report every step."""
    start_error = attempt(plant.start)
    produce_error = attempt(plant.produce)

    batch = SELFTEST_BATCH
    blended = batch.blend(Batch(id="b-1002", permeate=48.0, conductivity=160.0), 0.25)
    run = record_run(plant.hp_pump, 60.0, 46.0)
    dose_rate = DoseRate(ppm=DOSE_PPM).scaled(2.0)

    sweep = plant.telemetry()
    inspection = plant.snapshot()
    history = DoseHistory()
    history.record(dose_rate.ppm)
    ready = finish_backwash(plant.media)
    actionable = sum(1 for alarm in plant.alarms() if alarm.severity.is_actionable)

    shutdown_error = attempt(plant.shutdown)

    return {
        "start_error": start_error,
        "produce_error": produce_error,
        "shutdown_error": shutdown_error,
        "acceptable": batch.acceptable(300.0),
        "yield": batch.yield_percent(SELFTEST_FEED),
        "blend": blended.to_dict(),
        "specific_energy": run.specific_energy(),
        "run_stable": run.stable(5.0),
        "dose_avg": history.average(),
        "backwash_ready": ready.completed,
        "actionable_alarms": actionable,
        "telemetry": sweep.to_dict(),
        "telemetry_count": sweep.count(),
        "telemetry_total": sweep.total(),
        "telemetry_sensors": list(sweep.sensors()),
        "diagnostics": plant.diagnostics(),
        "report": plant.report(),
        "summary": plant.summary(),
        "audit": plant.audit_report(),
        "integration": plant.integration(),
        "event_total": audit_summary.total(plant.store, plant.recorder.sequence),
        "snapshot": inspection.to_dict(),
    }


def attempt(action) -> str:
    """Run an action, returning an empty string on success and its error text otherwise."""
    try:
        action()
    except ContractError as error:
        return str(error)
    return ""
