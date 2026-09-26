"""Cross-component ordering invariants of the line."""

import pytest

from desalplant.brine.recovery import recover_alarm
from desalplant.chem.doser import Doser
from desalplant.errors import (
    FlushNotEffectiveError,
    FlowNotReadyError,
    PermeateRejectedError,
    ResidualAntiscalantError,
    ValveNotOpenError,
)
from desalplant.flush.start import Flusher
from desalplant.intake.feed import Feed
from desalplant.ro.flow import FlowGate
from desalplant.ro.membrane import Membrane
from desalplant.ro.permeate import Permeate
from desalplant.ro.recovery import Recovery
from desalplant.brine.valve import Valve
from desalplant.tank.product import ProductTank
from desalplant.pump import new, ramp, ramp_pressure, stop


def test_pump_ramp_waits_for_the_membrane_flow():
    pump = new()
    membrane = Membrane(flow=20.0, min_flow=50.0)
    with pytest.raises(FlowNotReadyError):
        ramp(pump, membrane, 60.0)
    assert pump.pressure == 0.0
    assert membrane.cracked is False


def test_pump_ramp_is_accepted_once_the_flow_is_enough():
    pump = new()
    membrane = Membrane(flow=80.0, min_flow=50.0)
    assert ramp(pump, membrane, 60.0) == 60.0
    assert membrane.pressurized is True


def test_flow_gate_reports_whether_the_flow_is_enough():
    gate = FlowGate(50.0)
    assert gate.minimum == 50.0
    assert gate.satisfied(60.0) is True
    assert gate.satisfied(40.0) is False
    assert gate.confirm(60.0) == 60.0
    with pytest.raises(FlowNotReadyError):
        gate.confirm(40.0)


def test_pump_stops_only_after_an_effective_flush():
    pump = new()
    pump.start()
    flusher = Flusher()
    assert stop(pump, flusher) is True
    assert flusher.started is True
    assert flusher.effective is True


def test_pump_stop_is_refused_without_flush_headroom():
    pump = new()
    with pytest.raises(Exception):
        stop(pump, Flusher())


def test_flush_gate_reports_water_that_never_arrived():
    from desalplant.flush.start import StopGate

    with pytest.raises(FlushNotEffectiveError):
        StopGate(True).flush(Flusher(available=False))


def test_pressure_ramp_needs_an_open_brine_path():
    pump = new()
    valve = Valve()
    valve.open_valve()
    assert ramp_pressure(pump, valve, 60.0) == 60.0


def test_pressure_ramp_refuses_a_shut_outlet():
    from desalplant.brine.valve import ValveGate

    gate = ValveGate()
    shut = Valve(stuck=True)
    gate.open(shut)
    with pytest.raises(ValveNotOpenError):
        gate.require_ready()
    assert shut.stressed is False


def test_pressurising_a_shut_valve_marks_it_stressed():
    valve = Valve()
    valve.pressurize(60.0)
    assert valve.stressed is True


def test_dosing_stops_only_after_the_feed_flush():
    feed = Feed()
    feed.start()
    doser = Doser()
    doser.start(feed)
    doser.stop(feed)
    assert doser.dosing is False
    assert feed.flowing is False
    assert feed.scaled is False


def test_dosing_leaves_residue_when_the_chemical_was_already_off():
    feed = Feed()
    feed.start()
    doser = Doser()
    with pytest.raises(ResidualAntiscalantError):
        doser.stop(feed)


def test_tank_fill_refuses_rejected_permeate():
    permeate = Permeate(max_cond=300.0)
    permeate.update_conductivity(420.0)
    tank = ProductTank()
    with pytest.raises(PermeateRejectedError):
        tank.fill(permeate)
    assert tank.dumping is True


def test_tank_fill_accepts_recovered_permeate():
    permeate = Permeate(max_cond=300.0)
    permeate.update_conductivity(120.0)
    tank = ProductTank()
    tank.fill(permeate)
    assert tank.filling is True
    assert tank.dumping is False


def test_recovery_latch_freezes_the_rate_and_releases_the_valve():
    recovery = Recovery()
    recovery.update_rate(40.0)
    recovery.raise_alarm()
    assert recovery.update_rate(55.0) == 40.0
    valve = Valve()
    valve.set_emergency()
    assert recover_alarm(valve, recovery) is True
    assert valve.emergency is False
    assert recovery.active() is False


def test_recovery_latch_stays_raised_when_it_was_never_set():
    recovery = Recovery()
    valve = Valve()
    assert recover_alarm(valve, recovery) is False
    assert valve.emergency is True
