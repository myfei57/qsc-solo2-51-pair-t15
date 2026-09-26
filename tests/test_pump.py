"""High pressure pump: ramp gating, curves, supply and telemetry."""

import pytest

from desalplant.brine.valve import Valve
from desalplant.errors import (
    FlushNotEffectiveError,
    FlowNotReadyError,
    InvalidEfficiencyError,
    MembraneCrackedError,
)
from desalplant.flush.start import Flusher
from desalplant.ns.alarm import Severity
from desalplant.pump.alarm import pump_alarm
from desalplant.pump.batch import RunRecord, record_run
from desalplant.pump.controller import hold, idle
from desalplant.pump.curve import efficiency, recalibrate
from desalplant.pump.curve_builder import build_curve
from desalplant.pump.curve_fit import fitted_flow, interpolate
from desalplant.pump.curve_set import CurvePoint, new_curve
from desalplant.pump.differential import differential
from desalplant.pump.pressure import ramp_pressure
from desalplant.pump.ramp import RampProfile, apply_profile, ramp
from desalplant.pump.state import Pump, new
from desalplant.pump.stop import stop
from desalplant.pump.supply import supply_continuous, track_supply
from desalplant.pump.telemetry import collect
from desalplant.ro.array import MembraneArray
from desalplant.ro.membrane import Membrane

CURVE_POINTS = ((20.0, 14.0), (50.0, 38.0), (80.0, 62.0))


def test_pump_state_transitions():
    pump = new()
    assert isinstance(pump, Pump)
    pump.start()
    assert pump.running is True
    pump.set_pressure(30.0)
    assert pump.pressure == 30.0
    assert pump.hold(45.0) is True
    assert pump.hold(0.0) is False
    pump.trip("overload")
    assert pump.trip_reason == "overload"
    assert pump.stopped is True
    idle(pump)
    assert pump.pressure == 0.0


def test_recalibration_band_and_efficiency():
    pump = new()
    assert efficiency(pump) == 1.0
    assert recalibrate(pump, 0.75) == 0.75
    with pytest.raises(InvalidEfficiencyError):
        recalibrate(pump, 0.0)
    with pytest.raises(InvalidEfficiencyError):
        recalibrate(pump, 1.5)


def test_hold_helper_settles_a_positive_pressure():
    assert hold(new(), 55.0) is True
    assert hold(new(), -1.0) is False


def test_ramp_profile_walks_to_the_end():
    pump = new()
    profile = RampProfile(start=0.0, end=60.0, step=5.0)
    assert profile.steps() == 12
    assert apply_profile(pump, profile) == 60.0
    assert RampProfile(start=0.0, end=10.0, step=0.0).steps() == 1
    assert apply_profile(pump, RampProfile(start=0.0, end=10.0, step=0.0)) == 10.0


def test_ramp_is_flow_gated():
    pump = new()
    membrane = Membrane(flow=80.0, min_flow=50.0)
    assert ramp(pump, membrane, 60.0) == 60.0


def test_ramp_refuses_when_the_flow_is_below_minimum():
    pump = new()
    membrane = Membrane(flow=80.0, min_flow=50.0)
    membrane.flow = 10.0
    with pytest.raises(FlowNotReadyError):
        ramp(pump, membrane, 60.0)
    assert membrane.pressurized is False


def test_ramp_refuses_a_non_positive_target():
    pump = new()
    with pytest.raises(Exception):
        ramp(pump, Membrane(flow=80.0, min_flow=50.0), 0.0)


def test_pressure_ramp_opens_the_brine_path():
    pump = new()
    valve = Valve()
    assert ramp_pressure(pump, valve, 60.0) == 60.0
    assert valve.open is True
    assert valve.stressed is False


def test_stop_requires_a_flush():
    pump = new()
    pump.start()
    assert stop(pump, Flusher()) is True
    stopped = new()
    with pytest.raises(Exception):
        stop(stopped, Flusher())


def test_curve_interpolation_and_bounds():
    curve = new_curve([CurvePoint(power=power, flow=flow) for power, flow in CURVE_POINTS])
    assert curve.min_power() == 20.0
    assert curve.max_power() == 80.0
    assert curve.span() == 60.0
    assert curve.flow_at(50.0) == 38.0
    assert curve.flow_at(10.0) == 14.0
    assert interpolate(curve, 5.0) == 14.0
    assert interpolate(curve, 100.0) == 62.0
    assert interpolate(curve, 35.0) == 26.0
    assert fitted_flow(new(), curve, 50.0) == 38.0


def test_empty_curve_is_inert():
    empty = new_curve([])
    assert empty.flow_at(10.0) == 0.0
    assert empty.min_power() == 0.0
    assert empty.max_power() == 0.0
    assert interpolate(empty, 35.0) == 0.0


def test_curve_builder_accepts_coordinate_pairs():
    curve = build_curve(CURVE_POINTS)
    assert curve.points[0] == CurvePoint(power=20.0, flow=14.0)


def test_curve_requires_strictly_ascending_power():
    with pytest.raises(ValueError):
        new_curve([CurvePoint(power=10.0, flow=1.0), CurvePoint(power=10.0, flow=2.0)])
    with pytest.raises(ValueError):
        new_curve([CurvePoint(power=20.0, flow=1.0), CurvePoint(power=10.0, flow=2.0)])


def test_supply_tracking_stalls_on_zero():
    pump = new()
    assert track_supply(pump, 2) == 2
    assert pump.stalled is False
    track_supply(pump, 0)
    assert pump.stalled is True
    assert supply_continuous(1, 2) is True
    assert supply_continuous(0, 1) is False
    pump.reset_stall()
    assert pump.stalled is False


def test_differential_uses_the_freshest_map():
    pump = new()
    array = MembraneArray(3)
    readings = {"s1": 1.0, "s2": 2.0, "s3": 3.0}
    assert differential(pump, array, readings) == 3.0
    stale = MembraneArray(3)
    stale.sensor_map = {}
    assert differential(pump, stale, readings) == 0.0


def test_pump_telemetry_efficiency():
    pump = new()
    pump.set_pressure(60.0)
    sweep = collect(pump, 60.0, 46.0)
    assert sweep.pressure == 60.0
    assert round(sweep.efficiency(), 4) == round(46.0 / 60.0, 4)
    assert sweep.to_dict() == {"pressure": 60.0, "flow": 46.0, "power": 60.0}
    assert collect(pump, 0.0, 10.0).efficiency() == 0.0


def test_run_records_energy_and_stability():
    pump = new()
    run = record_run(pump, 60.0, 46.0)
    assert pump.pressure == 60.0
    assert run.specific_energy() == pytest.approx(60.0 / 46.0)
    assert run.stable(5.0) is True
    assert RunRecord(pressure=60.0, flow=0.0).specific_energy() == 0.0
    assert run.to_dict() == {"pressure": 60.0, "flow": 46.0}


def test_pump_alarm_follows_supply_and_pressure():
    pump = new()
    assert pump_alarm(pump).severity is Severity.INFO
    pump.set_pressure(80.0)
    assert pump_alarm(pump).severity is Severity.WARNING
    pump.track_supply(0)
    assert pump_alarm(pump).severity is Severity.CRITICAL


def test_membrane_cracked_error_is_raised_after_pressurising():
    from desalplant.pump.ramp import ramp as do_ramp

    membrane = Membrane(flow=80.0, min_flow=50.0)
    membrane.cracked = True
    with pytest.raises(MembraneCrackedError):
        do_ramp(new(), membrane, 60.0)


def test_stop_refuses_a_flush_that_never_took_effect():
    pump = new()
    pump.start()
    with pytest.raises(FlushNotEffectiveError):
        stop(pump, Flusher(available=False))
    assert pump.running is True
