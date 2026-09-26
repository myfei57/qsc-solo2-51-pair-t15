"""Shared vocabulary: identifiers, alarms, states, metrics and readings."""

from desalplant.ns.alarm import Alarm, Severity, make_alarm
from desalplant.ns.ids import new_id
from desalplant.ns.metrics import Metrics
from desalplant.ns.state import PlantState
from desalplant.ns.telemetry import Reading, Telemetry


def test_new_id_is_unique_and_textual():
    first = new_id()
    second = new_id()
    assert first != second
    assert len(first) == 32
    int(first, 16)


def test_severity_labels_and_actionability():
    assert Severity.INFO.label() == "info"
    assert Severity.WARNING.label() == "warning"
    assert Severity.CRITICAL.label() == "critical"
    assert Severity.INFO.is_actionable is False
    assert Severity.WARNING.is_actionable is True
    assert Severity.CRITICAL.is_actionable is True


def test_alarm_carries_an_identifier_and_renders_to_a_mapping():
    alarm = make_alarm(Severity.WARNING, "level low")
    assert isinstance(alarm, Alarm)
    assert alarm.id
    assert alarm.to_dict() == {
        "id": alarm.id,
        "severity": "warning",
        "message": "level low",
    }


def test_plant_state_renders_as_its_value():
    assert str(PlantState.RUNNING) == "running"
    assert PlantState("idle") is PlantState.IDLE


def test_metrics_track_counters_gauges_and_samples():
    metrics = Metrics()
    metrics.inc("starts")
    metrics.inc("starts", 2)
    metrics.set("recovery", 42.5)
    metrics.observe("rate", 10.0)
    metrics.observe("rate", 20.0)
    assert metrics.get("starts") == 3
    assert metrics.gauge("recovery") == 42.5
    assert metrics.average("rate") == 15.0
    assert metrics.get("missing") == 0
    assert metrics.gauge("missing") == 0.0
    assert metrics.average("missing") == 0.0
    assert metrics.snapshot() == {
        "counters": {"starts": 3},
        "gauges": {"recovery": 42.5},
    }


def test_telemetry_keeps_reading_order_and_latest_value():
    sweep = Telemetry()
    sweep.add("flow", 10.0)
    sweep.add("pressure", 5.0)
    sweep.add("flow", 12.0)
    assert sweep.count() == 3
    assert sweep.total() == 27.0
    assert sweep.latest("flow") == 12.0
    assert sweep.latest("missing") is None
    assert sweep.sensors() == ("flow", "pressure")
    assert sweep.to_dict()["readings"][0] == {"sensor": "flow", "value": 10.0}


def test_reading_projects_to_a_mapping():
    assert Reading(sensor="flow", value=3.0).to_dict() == {"sensor": "flow", "value": 3.0}
