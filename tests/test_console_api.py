"""Console routes, payload shapes and error mapping."""

from support import call, ok, refused


def test_health_reports_ok(console):
    assert ok(console, "GET", "/health") == {"status": "ok"}


def test_routes_are_method_and_path_pairs(console):
    routes = console.routes()
    assert ("GET", "/api/status") in routes
    assert ("POST", "/api/start") in routes
    assert ("GET", "/health") in routes


def test_unknown_route_is_not_found(console):
    response = refused(console, "GET", "/api/missing")
    assert response.status == 404


def test_status_starts_idle(console):
    body = ok(console, "GET", "/api/status")
    assert body["state"] == "idle"
    assert body["started"] is False
    assert body["store_entries"] == 0


def test_start_then_status_then_shutdown(console):
    ok(console, "POST", "/api/start", {})
    running = ok(console, "GET", "/api/status")
    assert running["state"] == "running"
    assert running["valve_open"] is True
    assert running["feed_flowing"] is True
    ok(console, "POST", "/api/shutdown", {})
    assert ok(console, "GET", "/api/status")["state"] == "idle"


def test_shutdown_before_start_is_refused(console):
    response = refused(console, "POST", "/api/shutdown", {})
    assert "feed already stopped" in response.body["error"]


def test_switch_moves_production_to_the_standby_tank(console):
    ok(console, "POST", "/api/start", {})
    body = ok(console, "POST", "/api/switch", {})
    assert "tank-b" in body["event"]["detail"]


def test_maintain_updates_the_efficiency_baseline(console, plant):
    ok(console, "POST", "/api/maintain", {})
    assert plant.hp_pump.efficiency == 0.8
    assert plant.recovery.active() is False


def test_telemetry_reports_named_readings(console):
    body = ok(console, "GET", "/api/telemetry")
    sensors = {reading["sensor"] for reading in body["readings"]}
    assert {"feed_flow", "screen_delta", "brine_recovery"} <= sensors


def test_events_grow_with_operations(console):
    assert ok(console, "GET", "/api/events")["count"] == 0
    ok(console, "POST", "/api/start", {})
    body = ok(console, "GET", "/api/events", )
    assert body["count"] == 1
    assert body["events"][0]["kind"] == "start"


def test_events_honour_the_limit_parameter(console):
    ok(console, "POST", "/api/start", {})
    ok(console, "POST", "/api/switch", {})
    body = ok(console, "GET", "/api/events?limit=1")
    assert len(body["events"]) == 1
    assert body["events"][0]["kind"] == "switch"


def test_alarms_cover_every_monitored_component(console):
    alarms = ok(console, "GET", "/api/alarms")
    assert len(alarms) == 3
    assert all(set(alarm) == {"id", "severity", "message"} for alarm in alarms)


def test_diagnostics_expose_the_sensor_map(console, plant):
    body = ok(console, "GET", "/api/diagnostics")
    assert body["array_sensors"] == plant.array.sensors()
    assert "rack" in body


def test_operation_probes_answer(console):
    for path in (
        "/api/ops/ramp",
        "/api/ops/backwash",
        "/api/ops/feed",
        "/api/ops/recovery",
        "/api/ops/flush",
        "/api/ops/dosing",
        "/api/ops/hydraulics",
        "/api/ops/tank",
    ):
        assert call(console, "GET", path).status == 200


def test_recovery_probe_positions_the_valve_both_ways(console, plant):
    closed = ok(console, "GET", "/api/ops/recovery")
    assert closed["position"] == "closed"
    assert plant.valve.open is False
    plant.membrane.flow = 20.0
    opened = ok(console, "GET", "/api/ops/recovery")
    assert opened["position"] == "open"
    assert plant.valve.open is True


def test_attempt_reports_success_and_failure():
    from desalplant.console import probes
    from desalplant.errors import ContractError

    assert probes.attempt(lambda: None) == ""

    def explode():
        raise ContractError("nope")

    assert probes.attempt(explode) == "nope"


def test_report_is_reproducible(console):
    first = ok(console, "GET", "/api/report")
    second = ok(console, "GET", "/api/report")
    assert first == second
    assert first["flush_valid"] is True
    assert first["transfer_ok"] is True
    assert first["empty_transfer_rejected"] is True


def test_audit_report_carries_the_train_geometry(console):
    body = ok(console, "GET", "/api/audit")
    assert body["train_elements"] == 21
    assert len(body["stage_feeds"]) == 3
    assert body["flush_runs"] == 2


def test_summary_reports_the_curve_range(console):
    body = ok(console, "GET", "/api/summary")
    assert body["curve_span"] == 60.0
    assert body["membrane_alarm"]["severity"] == "info"


def test_version_reports_a_label(console):
    assert ok(console, "GET", "/api/version") == {"label": "desalplant/1.0.0"}


def test_selftest_drives_a_full_cycle(console):
    body = ok(console, "GET", "/api/selftest")
    assert body["start_error"] == ""
    assert body["produce_error"] == ""
    assert body["shutdown_error"] == ""
    assert body["acceptable"] is True
    assert body["snapshot"]["count"] > 0


def test_malformed_body_is_refused(console):
    response = call(console, "POST", "/api/start", [1, 2, 3])
    assert response.status == 400
    assert "malformed request" in response.body["error"]
