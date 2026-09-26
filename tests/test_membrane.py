"""Membrane train: elements, flow gate, permeate, recovery and hydraulics."""

import pytest

from desalplant.errors import FlowNotReadyError, InvalidStagesError
from desalplant.ns.alarm import Severity
from desalplant.ro.alarm import MembraneAlarm
from desalplant.ro.array import MembraneArray
from desalplant.ro.batch import Batch
from desalplant.ro.flow import FlowCheck, FlowGate
from desalplant.ro.hydraulics import (
    ConcentrationPolarization,
    Flux,
    PressureVessel,
)
from desalplant.ro.membrane import Membrane
from desalplant.ro.output import Output, valid_efficiency
from desalplant.ro.permeate import Permeate, PermeateStats
from desalplant.ro.quality import PermeateGrade
from desalplant.ro.recovery import Recovery
from desalplant.ro.train import Train


def test_membrane_pressurises_with_enough_flow():
    membrane = Membrane(flow=80.0, min_flow=50.0)
    membrane.pressurize(60.0)
    assert membrane.pressurized is True
    assert membrane.cracked is False
    assert membrane.alarm().severity is Severity.INFO
    assert membrane.status() == MembraneAlarm(cracked=False, fouled=False)
    assert str(membrane) == "flow=80.0 min=50.0 cracked=False"


def test_membrane_cracks_when_pressurised_below_minimum_flow():
    membrane = Membrane(flow=20.0, min_flow=50.0)
    membrane.pressurize(60.0)
    assert membrane.cracked is True
    assert membrane.alarm().severity is Severity.CRITICAL
    assert membrane.status().cracked is True
    assert membrane.status().fouled is True


def test_membrane_without_flow_raises_a_warning():
    membrane = Membrane(flow=10.0, min_flow=50.0)
    assert membrane.alarm().severity is Severity.WARNING


def test_membrane_recovery_and_cleaning_threshold():
    membrane = Membrane(flow=50.0, min_flow=10.0)
    assert membrane.recovery(100.0) == 50.0
    assert membrane.recovery(0.0) == 0.0
    assert membrane.needs_clean(25.0, 20.0) is True
    assert membrane.needs_clean(18.0, 20.0) is False


def test_flow_gate_confirms_and_refuses():
    gate = FlowGate(50.0)
    assert gate.satisfied(60.0) is True
    assert gate.confirm(60.0) == 60.0
    with pytest.raises(FlowNotReadyError):
        gate.confirm(40.0)


def test_flow_check_reads_the_element():
    check = FlowCheck()
    assert check.measure(Membrane(flow=42.0, min_flow=10.0)) == 42.0
    assert check.reading == 42.0


def test_membrane_array_map_and_regroup():
    array = MembraneArray(2)
    assert array.count() == 2
    assert array.stage_count() == 2
    assert array.last_stage() == "stage2"
    assert array.sensor_stage("s1") == "stage1"
    assert array.sensor_stage("missing") == ""
    assert array.stage_sensors("stage1") == ("s1",)
    assert array.sensors() == {"s1": "stage1", "s2": "stage2"}
    assert array.map_fresh() is True
    array.regroup(3)
    assert array.count() == 3
    assert array.stage_sensors("stage3") == ("s3",)
    with pytest.raises(InvalidStagesError):
        array.regroup(0)


def test_permeate_latch_clears_on_a_normal_reading():
    permeate = Permeate(max_cond=300.0)
    assert permeate.rejecting_now() is True
    permeate.update_conductivity(420.0)
    assert permeate.recovered() is False
    assert permeate.conductivity_normal() is False
    permeate.update_conductivity(120.0)
    assert permeate.recovered() is True
    assert permeate.rejecting_now() is False
    assert permeate.conductivity_normal() is True
    assert permeate.safe(300.0) is True
    assert permeate.grade().grade == "acceptable"


def test_permeate_grade_and_flow_measurements():
    permeate = Permeate(max_cond=100.0)
    permeate.update_conductivity(150.0)
    assert permeate.grade() == PermeateGrade(grade="reject", safe=False)
    stats = permeate.measure_flow(30.0)
    assert stats == PermeateStats(flow_rate=30.0, rejected_volume=30.0)
    assert stats.to_dict() == {"flow_rate": 30.0, "rejected_volume": 30.0}
    assert permeate.reject_volume(30.0) == 30.0
    permeate.update_conductivity(50.0)
    assert permeate.reject_volume(30.0) == 0.0


def test_permeate_grade_factory():
    assert PermeateGrade.from_conductivity(50.0, 100.0).to_dict() == {
        "grade": "acceptable",
        "safe": True,
    }


def test_recovery_rate_freezes_while_latched():
    recovery = Recovery()
    assert recovery.active() is False
    assert recovery.update_rate(42.0) == 42.0
    recovery.raise_alarm()
    assert recovery.active() is True
    assert recovery.update_rate(60.0) == 42.0
    recovery.clear_alarm()
    assert recovery.rate() == 42.0
    assert recovery.update_rate(50.0) == 50.0


def test_train_geometry_and_arithmetic():
    train = Train(stages=3, elements_per_stage=7)
    assert train.total_elements() == 21
    assert train.stage_feed(100.0) == (100.0, 92.0, 84.0)
    assert train.recovery(80.0, 20.0) == 75.0
    assert train.recovery(0.0, 0.0) == 0.0
    assert round(train.flux(21.0), 3) == 1.0
    assert Train(stages=0, elements_per_stage=0).flux(10.0) == 0.0


def test_flux_vessel_and_polarization():
    assert Flux(permeate=36.0, area=36.0).lmh() == 1.0
    assert Flux(permeate=10.0, area=0.0).lmh() == 0.0
    assert Flux(permeate=1.0, area=2.0).to_dict()["lmh"] == 0.5
    vessel = PressureVessel(elements=7, active=7)
    assert vessel.packed() == 1.0
    assert vessel.dead_end() is False
    assert PressureVessel(elements=0, active=0).packed() == 0.0
    assert PressureVessel(elements=7, active=0).dead_end() is True
    assert ConcentrationPolarization(feed=35.0, brine=42.0).factor() == 1.2
    assert ConcentrationPolarization(feed=0.0, brine=42.0).factor() == 0.0


def test_batch_quality_yield_and_blend():
    batch = Batch(id="b1", permeate=52.0, conductivity=120.0)
    assert batch.acceptable(300.0) is True
    assert batch.yield_percent(80.0) == 65.0
    assert batch.yield_percent(0.0) == 0.0
    blended = batch.blend(Batch(id="b2", permeate=48.0, conductivity=160.0), 0.25)
    assert blended.permeate == 51.0
    assert blended.conductivity == 130.0
    assert batch.blend(batch, 5.0).permeate == 52.0
    assert batch.to_dict()["id"] == "b1"


def test_output_uses_a_valid_efficiency_baseline():
    output = Output()
    assert valid_efficiency(0.8) is True
    assert valid_efficiency(0.0) is False
    assert valid_efficiency(1.5) is False
    assert output.check(0.8, 100.0) == 80.0
    assert output.actual_flow == 80.0
    assert output.check(0.0, 100.0) == 0.0
