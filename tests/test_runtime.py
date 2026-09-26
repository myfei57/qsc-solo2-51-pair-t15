"""Clock, configuration, application wiring and the HTTP layer types."""

import json

import pytest

from desalplant import __version__
from desalplant.app import Application, build_application
from desalplant.clock import LogicalClock
from desalplant.config import Config, parse_args
from desalplant.console.http import Request, error_response, json_response
from desalplant.console.router import status_for
from desalplant.errors import (
    ContractError,
    InvalidStagesError,
    MediaNotReadyError,
    StoreError,
    UnknownKeyError,
)


def test_clock_advances_and_measures_elapsed():
    clock = LogicalClock()
    assert clock.tick == 0
    assert clock.advance() == 1
    assert clock.advance(4) == 5
    assert clock.elapsed(1) == 4
    with pytest.raises(ValueError):
        clock.advance(0)
    with pytest.raises(ValueError):
        clock.elapsed(9)
    with pytest.raises(ValueError):
        LogicalClock(-1)


def test_config_resolves_address_and_store_path():
    config = Config(host="0.0.0.0", port=1234, data_dir="state")
    assert config.listen() == ("0.0.0.0", 1234)
    assert config.store_path() == "state/plant.json"


def test_parse_args_reads_flags():
    config = parse_args(["--host", "0.0.0.0", "--port", "9100", "--data", "tmp"])
    assert config == Config(host="0.0.0.0", port=9100, data_dir="tmp")


def test_build_application_wires_the_console():
    application = build_application(Config(data_dir="unused"))
    assert isinstance(application, Application)
    assert application.plant is not None
    assert application.console.plant is application.plant
    assert application.snapshot().count == 0


def test_service_survives_a_restart(tmp_path):
    config = Config(data_dir=str(tmp_path / "data"))
    first = build_application(config)
    first.plant.start()
    assert first.store.get("plant/state") == "running"
    reopened = build_application(config)
    assert reopened.store.get("plant/state") == "running"
    assert reopened.plant.event_count() == 1


def test_request_parses_target_and_body():
    request = Request.parse("get", "/api/events?limit=5&empty=", json.dumps({"ok": True}))
    assert request.method == "GET"
    assert request.path == "/api/events"
    assert request.integer("limit") == 5
    assert request.integer("missing", 3) == 3
    assert request.param("empty") is None
    assert request.param("missing", "fallback") == "fallback"
    assert request.number("missing", 1.5) == 1.5
    assert request.body() == {"ok": True}
    scaled = Request.parse("GET", "/api/ops/ramp?target=12.5")
    assert scaled.number("target") == 12.5


def test_request_rejects_a_non_object_body():
    request = Request.parse("POST", "/api/start", "[1, 2]")
    with pytest.raises(ValueError):
        request.body()
    assert Request.parse("POST", "/api/start", "").body() == {}


def test_response_renders_json_and_errors():
    response = json_response({"a": 1})
    assert response.status == 200
    assert json.loads(response.to_bytes()) == {"a": 1}
    failure = error_response("bad", status=409)
    assert failure.status == 409
    assert json.loads(failure.to_bytes()) == {"error": "bad", "status": 409}


def test_status_mapping_covers_each_group():
    assert status_for(MediaNotReadyError("x")) == 409
    assert status_for(UnknownKeyError("x")) == 404
    assert status_for(StoreError("x")) == 500
    assert status_for(InvalidStagesError("x")) == 422
    assert status_for(ContractError("x")) == 400


def test_package_reports_its_version():
    assert __version__ == "1.0.0"


def test_main_serves_once(monkeypatch, tmp_path):
    import desalplant.__main__ as entry

    served = {}

    def fake_serve(config, console):
        served["config"] = config
        served["routes"] = console.routes()

    monkeypatch.setattr(entry, "serve", fake_serve)
    code = entry.main(["--data", str(tmp_path / "data"), "--port", "8123"])
    assert code == 0
    assert served["config"].port == 8123
    assert ("GET", "/health") in served["routes"]


def test_module_entry_point_serves(monkeypatch, tmp_path):
    import runpy
    import sys

    import desalplant.console.server as server_module

    served = []
    monkeypatch.setattr(server_module, "serve", lambda config, console: served.append(config.port))
    monkeypatch.setattr(
        sys,
        "argv",
        ["desalplant", "--data", str(tmp_path / "entry"), "--port", "8123"],
    )
    sys.modules.pop("desalplant.__main__", None)
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("desalplant", run_name="__main__", alter_sys=True)
    assert exit_info.value.code == 0
    assert served == [8123]


def test_serve_opens_and_closes_the_server(monkeypatch, config, console):
    import desalplant.console.server as server_module

    events = []

    class FakeServer:
        def __init__(self, address, received):
            events.append(("open", address, received is console))

        def serve_forever(self):
            events.append(("serve",))

        def server_close(self):
            events.append(("close",))

    monkeypatch.setattr(server_module, "ControlServer", FakeServer)
    server_module.serve(config, console)
    assert events == [("open", config.listen(), True), ("serve",), ("close",)]


def test_http_server_answers_requests(services):
    import json
    import threading
    import urllib.request

    from desalplant.console.http import JSON_CONTENT_TYPE
    from desalplant.console.server import ControlServer

    server = ControlServer(("127.0.0.1", 0), services.console)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    base = f"http://{host}:{port}"
    try:
        with urllib.request.urlopen(f"{base}/health", timeout=5) as response:
            assert response.status == 200
            assert response.headers["Content-Type"] == JSON_CONTENT_TYPE
            assert json.loads(response.read()) == {"status": "ok"}
        start = urllib.request.Request(f"{base}/api/start", data=b"{}", method="POST")
        with urllib.request.urlopen(start, timeout=5) as response:
            assert json.loads(response.read())["status"] == "started"
        missing = urllib.request.Request(f"{base}/api/start", data=b"[]", method="POST")
        with pytest.raises(urllib.error.HTTPError) as failure:
            urllib.request.urlopen(missing, timeout=5)
        assert failure.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
