"""Raw water intake: feed line, gate, screen, pump and rinse."""

import pytest

from desalplant.errors import FeedAlreadyStoppedError, RinseFailedError
from desalplant.filter.rack import Rack
from desalplant.intake.feed import Feed
from desalplant.intake.flow import FeedRamp
from desalplant.intake.gate import Gate
from desalplant.intake.interlock import GateInterlock
from desalplant.intake.pump import IntakePump
from desalplant.intake.rinse import RinseGate
from desalplant.intake.schedule import CleanSchedule
from desalplant.intake.screen import Screen
from desalplant.intake.telemetry import IntakeTelemetry


def test_feed_flow_lifecycle():
    feed = Feed()
    assert feed.available(10.0) is False
    feed.start()
    assert feed.flowing is True
    assert feed.available(10.0) is True
    assert feed.available(0.0) is False
    feed.set_chem_active(True)
    assert feed.flushing() is True
    feed.stop()
    assert feed.flowing is False
    assert feed.scaled is False


def test_feed_stop_without_dosing_records_scaling():
    feed = Feed()
    feed.start()
    feed.stop()
    assert feed.scaled is True


def test_feed_begin_shutdown_refuses_an_idle_feed():
    feed = Feed()
    with pytest.raises(FeedAlreadyStoppedError):
        feed.begin_shutdown()


def test_gate_opens_only_when_the_interlock_allows():
    gate = Gate()
    interlock = GateInterlock(enabled=True)
    assert gate.interlocked(interlock, 60.0) is False
    assert gate.open is False
    assert gate.interlocked(interlock, 10.0) is True
    assert gate.open is True
    gate.close_gate()
    assert gate.open is False


def test_interlock_can_be_disabled():
    assert GateInterlock(enabled=False).can_open(60.0) is True


def test_screen_head_loss_flags_fouling():
    screen = Screen()
    assert screen.measure(90.0, 70.0) == 20.0
    assert screen.fouled(15.0) is True
    assert screen.fouled(30.0) is False
    screen.clear()
    assert screen.delta == 0.0


def test_clean_schedule_due_and_next():
    schedule = CleanSchedule(interval=100, last=10)
    assert schedule.due(50) is False
    assert schedule.due(110) is True
    assert schedule.next_due() == 110


def test_intake_pump_start_stop_and_shutdown():
    pump = IntakePump()
    pump.start()
    assert pump.running is True
    pump.shutdown(Rack())
    assert pump.running is False
    assert pump.stopped is True


def test_intake_pump_shutdown_refuses_a_stopped_pump():
    with pytest.raises(RinseFailedError):
        IntakePump().shutdown(Rack())


def test_intake_pump_flow_targets_and_ramp():
    pump = IntakePump()
    assert pump.flow_rate(100.0) == 80.0
    assert pump.target_flow(90.0) == 70.0
    assert pump.target_flow(60.0) == 90.0
    assert pump.target_flow(10.0) == 110.0
    assert pump.ramp_feed(FeedRamp(start=0.0, end=50.0)) == 50.0
    assert pump.ramp_feed(FeedRamp(start=60.0, end=20.0)) == 60.0


def test_intake_pump_screen_cleaning_and_schedule():
    pump = IntakePump()
    screen = Screen(delta=25.0)
    assert pump.screen_clean(screen, 30.0) is True
    assert pump.screen_clean(screen, 5.0) is True
    assert screen.delta == 0.0
    assert pump.clean_due(CleanSchedule(interval=10, last=0), 20) is True


def test_intake_pump_collects_a_sweep():
    pump = IntakePump()
    sweep = pump.collect(80.0, Screen(delta=12.0))
    assert sweep.fouled(10.0) is True
    assert sweep.to_dict() == {"flow": 80.0, "screen_delta": 12.0}


def test_intake_pump_feed_backwash_requires_an_open_feed():
    pump = IntakePump()
    ramp = FeedRamp(start=0.0, end=80.0)
    assert pump.feed_backwash(ramp, Feed()) == 0.0
    feed = Feed()
    feed.start()
    assert pump.feed_backwash(ramp, feed) == 80.0


def test_rinse_gate_refuses_a_stopped_pump():
    gate = RinseGate()
    with pytest.raises(RinseFailedError):
        gate.rinse(Rack(), False)
    with pytest.raises(RinseFailedError):
        gate.rinse(Rack(jammed=True), True)
    with pytest.raises(RinseFailedError):
        gate.require_complete()


def test_rinse_gate_completes_while_the_pump_runs():
    gate = RinseGate()
    rack = Rack()
    gate.rinse(rack, True)
    gate.require_complete()
    assert gate.completed is True
    assert rack.was_rinsed() is True


def test_intake_telemetry_projection():
    assert IntakeTelemetry(flow=1.0, screen_delta=2.0).to_dict() == {
        "flow": 1.0,
        "screen_delta": 2.0,
    }
