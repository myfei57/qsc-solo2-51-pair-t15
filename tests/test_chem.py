"""Antiscalant dosing: pump, tank, dose arithmetic and stops."""

import pytest

from desalplant.chem.alarm import tank_alarm
from desalplant.chem.control import DosingProfile, dose_volume, setpoint
from desalplant.chem.dose_calc import DoseHistory
from desalplant.chem.dose_rate import DoseRate
from desalplant.chem.doser import Doser
from desalplant.chem.schedule import DoseSchedule, schedule_due
from desalplant.chem.tank import ChemicalTank
from desalplant.errors import ResidualAntiscalantError
from desalplant.intake.feed import Feed
from desalplant.ns.alarm import Severity


def test_chemical_tank_draw_refill_and_empty():
    tank = ChemicalTank(level=100.0)
    assert tank.draw(10.0) == 90.0
    assert tank.refill(5.0) == 95.0
    assert tank.empty() is False
    tank.draw(95.0)
    assert tank.empty() is True


def test_dose_rate_rejects_negative_and_scales():
    assert DoseRate(ppm=2.5).scaled(2.0) == DoseRate(ppm=5.0)
    with pytest.raises(ValueError):
        DoseRate(ppm=-1.0)


def test_dose_volume_and_setpoint():
    profile = DosingProfile(rate=2.5, flow=80.0)
    assert dose_volume(profile, 3600.0) == 200.0
    assert setpoint(80.0, 2.5) == 0.2
    assert setpoint(0.0, 2.5) == 0.0


def test_dose_history_summarises():
    history = DoseHistory()
    assert history.average() == 0.0
    assert history.largest() == 0.0
    history.record(12.0)
    history.record(18.0)
    assert history.count == 2
    assert history.average() == 15.0
    assert history.largest() == 18.0


def test_doser_start_and_runtime_setters():
    feed = Feed()
    doser = Doser()
    doser.start(feed)
    assert doser.dosing is True
    assert feed.chem_active is True
    assert doser.set_dose_rate(DoseRate(ppm=2.5)) == 2.5
    assert doser.target_dose(80.0, 2.5) == 0.2
    assert doser.dose_volume(2.5, 80.0, 3600.0) == 200.0


def test_doser_stop_leaves_no_residual():
    feed = Feed()
    feed.start()
    doser = Doser()
    doser.start(feed)
    doser.stop(feed)
    assert doser.dosing is False
    assert feed.chem_active is False
    assert feed.scaled is False


def test_doser_stop_reports_residual_scaling():
    feed = Feed()
    feed.start()
    with pytest.raises(ResidualAntiscalantError):
        Doser().stop(feed)


def test_dose_schedule_due():
    schedule = DoseSchedule(interval=900, last=100)
    assert schedule.due(600) is False
    assert schedule_due(Doser(), schedule, 1000) is True


def test_tank_alarm_levels():
    assert tank_alarm(ChemicalTank(level=5.0)).severity is Severity.WARNING
    assert tank_alarm(ChemicalTank(level=50.0)).severity is Severity.INFO
