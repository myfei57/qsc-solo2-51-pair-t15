"""Brine discharge: valve, stream arithmetic and recovery handling."""

import pytest

from desalplant.brine.control import RecoveryTarget, position_for, recovery_position
from desalplant.brine.limit import RecoveryLimit
from desalplant.brine.recovery import RecoveryGate, recover_alarm
from desalplant.brine.stream import BrineStream
from desalplant.brine.stream_calc import (
    concentration_ratio,
    disposal_volume,
    recovery_rate,
    reject_flow,
)
from desalplant.brine.telemetry import StreamTelemetry
from desalplant.brine.valve import Valve, ValveGate
from desalplant.errors import AlarmNotActiveError, ValveNotOpenError
from desalplant.ro.recovery import Recovery


def test_valve_open_close_and_pressurise():
    valve = Valve()
    valve.open_valve()
    assert valve.open is True
    valve.pressurize(60.0)
    assert valve.stressed is False
    valve.close_valve()
    valve.pressurize(60.0)
    assert valve.stressed is True
    valve.set_emergency()
    assert valve.emergency is True
    valve.release_emergency()
    assert valve.emergency is False


def test_stuck_valve_refuses_to_open():
    valve = Valve(stuck=True)
    valve.open_valve()
    assert valve.open is False
    gate = ValveGate()
    gate.open(valve)
    assert gate.ready() is False
    with pytest.raises(ValveNotOpenError):
        gate.require_ready()


def test_valve_gate_opens_a_working_valve():
    gate = ValveGate()
    valve = Valve()
    gate.open(valve)
    assert gate.ready() is True
    gate.require_ready()


def test_stream_arithmetic():
    assert reject_flow(0.6, 100.0) == 60.0
    assert recovery_rate(0.6, 100.0) == pytest.approx(0.4)
    assert recovery_rate(0.6, 0.0) == 0.0
    assert disposal_volume(0.6, 100.0, 24.0) == 1440.0
    assert concentration_ratio(40.0, 10.0) == 0.8
    assert concentration_ratio(0.0, 10.0) == 0.0


def test_brine_stream_methods():
    stream = BrineStream(concentration=0.6)
    assert stream.recover(40.0) == pytest.approx(40.0 / 40.6)
    assert stream.emergency_flow() == pytest.approx(1.8)
    assert stream.reject_flow(100.0) == 60.0
    assert stream.recovery_rate(100.0) == pytest.approx(0.4)
    assert stream.disposal_volume(100.0, 2.0) == 120.0
    sweep = stream.collect(40.0)
    assert sweep.recovery() == pytest.approx(40.0 / 40.6)
    assert sweep.to_dict() == {"flow": 40.0, "concentration": 0.6}


def test_stream_telemetry_projection():
    sweep = StreamTelemetry(flow=40.0, concentration=10.0)
    assert sweep.recovery() == 0.8


def test_recovery_limit_clamps_and_contains():
    limit = RecoveryLimit(min=30.0, max=55.0)
    assert limit.clamp(20.0) == 30.0
    assert limit.clamp(70.0) == 55.0
    assert limit.clamp(40.0) == 40.0
    assert limit.contains(40.0) is True
    assert limit.contains(70.0) is False
    with pytest.raises(ValueError):
        RecoveryLimit(min=60.0, max=50.0)


def test_recovery_gate_clears_an_active_latch():
    recovery = Recovery()
    recovery.raise_alarm()
    valve = Valve()
    valve.set_emergency()
    RecoveryGate().clear(recovery, valve)
    assert recovery.active() is False
    assert valve.emergency is False


def test_recovery_gate_refuses_when_the_latch_is_down():
    recovery = Recovery()
    valve = Valve()
    with pytest.raises(AlarmNotActiveError):
        RecoveryGate().clear(recovery, valve)
    assert recover_alarm(valve, recovery) is False
    assert valve.emergency is True


def test_recovery_target_deviation():
    target = RecoveryTarget(setpoint=45.0, actual=48.0)
    assert target.deviation() == 3.0
    assert target.within(5.0) is True
    assert target.within(1.0) is False


def test_valve_position_from_recovery():
    valve = Valve()
    assert position_for(valve, 30.0) == "open"
    assert position_for(valve, 50.0) == "closed"
    valve.set_emergency()
    assert position_for(valve, 30.0) == "emergency"
    assert recovery_position(valve, 30.0, RecoveryLimit(min=30.0, max=55.0)) == "emergency"
    valve.release_emergency()
    assert recovery_position(valve, 30.0, RecoveryLimit(min=30.0, max=55.0)) == "open"
    assert recovery_position(valve, 70.0, RecoveryLimit(min=30.0, max=55.0)) == "throttled"
