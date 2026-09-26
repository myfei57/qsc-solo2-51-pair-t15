"""Product storage: tank set, handoff, level, capacity and transfer."""

import pytest

from desalplant.errors import (
    HandoffIncompleteError,
    PermeateRejectedError,
    SupplyInterruptedError,
    TransferFailedError,
)
from desalplant.ns.alarm import Severity
from desalplant.pump import new
from desalplant.ro.permeate import Permeate
from desalplant.tank.alarm import level_alarm
from desalplant.tank.band import LevelBand
from desalplant.tank.capacity import capacity
from desalplant.tank.handoff import HandoffGate, handoff
from desalplant.tank.history import LevelHistory
from desalplant.tank.level import Level
from desalplant.tank.product import ProductTank
from desalplant.tank.tanks import TankSet
from desalplant.tank.transfer import Transfer, allowed, transfer


def test_tank_set_starts_with_one_open_outlet():
    tanks = TankSet(current="a", standby="b")
    assert tanks.open_count() == 1
    assert tanks.active_id() == "a"
    assert tanks.ids() == ("a", "b")
    assert tanks.level() == 1.0
    assert tanks.is_open("a") is True
    assert tanks.is_open("b") is False
    tanks.open("b")
    tanks.close("a")
    tanks.swap()
    assert tanks.active_id() == "b"
    assert tanks.open_count() == 1
    assert tanks.tanks["b"].to_dict() == {"id": "b", "open": True, "blocked": False}


def test_tank_set_refuses_an_unknown_tank():
    tanks = TankSet(current="a", standby="b")
    with pytest.raises(KeyError):
        tanks.open("missing")


def test_blocked_tank_outlet_cannot_move():
    tanks = TankSet(current="a", standby="b")
    tanks.tanks["b"].blocked = True
    assert tanks.open("b") is False
    assert tanks.close("b") is False


def test_handoff_keeps_a_supply_online():
    tanks = TankSet(current="a", standby="b")
    pump = new()
    assert handoff(tanks, pump) == "b"
    assert tanks.active_id() == "b"
    assert pump.stalled is False


def test_handoff_gate_detects_an_incomplete_move():
    gate = HandoffGate()
    assert gate.complete() is False
    gate.opened = True
    assert gate.complete() is False
    gate.closed = True
    assert gate.complete() is True


def test_handoff_reports_a_dropped_supply():
    class DroppingTanks(TankSet):
        def open_count(self):
            return 0

    with pytest.raises(SupplyInterruptedError):
        handoff(DroppingTanks(current="a", standby="b"), new())


def test_handoff_reports_a_blocked_standby_tank():
    tanks = TankSet(current="a", standby="b")
    tanks.tanks["b"].blocked = True
    with pytest.raises(HandoffIncompleteError):
        handoff(tanks, new())


def test_handoff_reports_a_stuck_current_outlet():
    tanks = TankSet(current="a", standby="b")
    tanks.tanks["a"].blocked = True
    with pytest.raises(HandoffIncompleteError):
        handoff(tanks, new())


def test_product_tank_fill_lifecycle():
    permeate = Permeate(max_cond=300.0)
    permeate.update_conductivity(120.0)
    tank = ProductTank()
    tank.fill(permeate)
    assert tank.filling is True
    assert tank.dumping is False

    rejecting = Permeate(max_cond=300.0)
    rejecting.update_conductivity(400.0)
    with pytest.raises(PermeateRejectedError):
        tank.fill(rejecting)
    assert tank.dumping is True


def test_level_band_and_level_updates():
    band = LevelBand(low=20.0, high=85.0)
    assert band.contains(50.0) is True
    assert band.contains(90.0) is False
    with pytest.raises(ValueError):
        LevelBand(low=90.0, high=20.0)
    level = Level()
    assert level.update(40.0) == 40.0
    assert level.fill_to(70.0) == 70.0
    assert level.fill_to(30.0) == 70.0
    assert level.within(band) is True
    assert level.trend(60.0) == 10.0


def test_capacity_projection_follows_the_fill_state():
    tank = ProductTank()
    assert capacity(tank, 1000.0).current == 0.0
    tank.filling = True
    projected = capacity(tank, 1000.0)
    assert projected.current == 800.0
    assert projected.free() == 200.0
    assert projected.to_dict()["total"] == 1000.0
    tank.filling = False
    tank.dumping = True
    assert capacity(tank, 1000.0).current == 0.0


def test_transfer_validates_endpoints_and_amount():
    tanks = TankSet(current="a", standby="b")
    move = Transfer(source="a", destination="b", amount=10.0)
    assert transfer(tanks, move) == 10.0
    with pytest.raises(TransferFailedError):
        transfer(tanks, Transfer(source="a", destination="b", amount=0.0))
    with pytest.raises(TransferFailedError):
        transfer(tanks, Transfer(source="a", destination="c", amount=1.0))
    with pytest.raises(TransferFailedError):
        transfer(tanks, Transfer(source="c", destination="b", amount=1.0))


def test_allowed_reports_whether_a_transfer_would_apply():
    tanks = TankSet(current="a", standby="b")
    assert allowed(tanks, Transfer(source="a", destination="b", amount=1.0)) is True
    assert allowed(tanks, Transfer(source="a", destination="b", amount=0.0)) is False


def test_level_history_summarises():
    history = LevelHistory()
    assert history.min() == 0.0
    assert history.max() == 0.0
    assert history.average() == 0.0
    assert history.span() == 0.0
    assert history.record(40.0) == 1
    history.record(70.0)
    assert history.min() == 40.0
    assert history.max() == 70.0
    assert history.average() == 55.0
    assert history.span() == 30.0


def test_level_alarm_thresholds():
    assert level_alarm(Level(95.0)).severity is Severity.WARNING
    assert level_alarm(Level(5.0)).severity is Severity.CRITICAL
    assert level_alarm(Level(50.0)).severity is Severity.INFO
