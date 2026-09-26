"""Read-only console handlers."""

from . import probes, routes
from .http import Request, Response, json_response


def health(console, request: Request) -> Response:
    """Liveness probe."""
    return json_response({"status": "ok"})


def status(console, request: Request) -> Response:
    """Current state of the line."""
    return json_response(console.plant.status())


def telemetry(console, request: Request) -> Response:
    """One telemetry sweep."""
    return json_response(console.plant.telemetry().to_dict())


def events(console, request: Request) -> Response:
    """Newest-first audit events."""
    limit = request.integer("limit", 100)
    return json_response(
        {
            "count": console.plant.event_count(),
            "events": [event.to_dict() for event in console.plant.events(limit)],
        }
    )


def alarms(console, request: Request) -> Response:
    """Current component alarms."""
    return json_response([alarm.to_dict() for alarm in console.plant.alarms()])


def diagnostics(console, request: Request) -> Response:
    """Structural diagnostics."""
    return json_response(console.plant.diagnostics())


def ramp(console, request: Request) -> Response:
    """Walk a stepped pressure ramp."""
    return json_response(probes.run_ramp_profile(console.plant))


def backwash(console, request: Request) -> Response:
    """Measure the media head loss."""
    return json_response(probes.run_backwash_check(console.plant))


def feed(console, request: Request) -> Response:
    """Ramp the feed and clean the screen."""
    return json_response(probes.run_feed_ramp(console.plant))


def recovery(console, request: Request) -> Response:
    """Position the brine valve from the recovery figure."""
    return json_response(probes.run_recovery_control(console.plant))


def flush(console, request: Request) -> Response:
    """Advance a flush program."""
    return json_response(probes.run_flush_program(console.plant))


def dosing(console, request: Request) -> Response:
    """Size a dose."""
    return json_response(probes.run_dosing_control(console.plant))


def hydraulics(console, request: Request) -> Response:
    """Report flux and vessel load."""
    return json_response(probes.run_hydraulics(console.plant))


def tank(console, request: Request) -> Response:
    """Fill the product tank and report the tank set."""
    return json_response(probes.run_tank_level(console.plant))


def report(console, request: Request) -> Response:
    """Numeric report."""
    return json_response(console.plant.report())


def audit(console, request: Request) -> Response:
    """Audit report."""
    return json_response(console.plant.audit_report())


def summary(console, request: Request) -> Response:
    """Summary over the curves and stream."""
    return json_response(console.plant.summary())


def selftest(console, request: Request) -> Response:
    """Full-cycle self test."""
    return json_response(console.plant.selftest())


def version(console, request: Request) -> Response:
    """Build label of the running service."""
    return json_response({"label": console.plant.build().label()})


ROUTE_TABLE = (
    (routes.HEALTH, health),
    (routes.STATUS, status),
    (routes.TELEMETRY, telemetry),
    (routes.EVENTS, events),
    (routes.ALARMS, alarms),
    (routes.DIAGNOSTICS, diagnostics),
    (routes.OPS_RAMP, ramp),
    (routes.OPS_BACKWASH, backwash),
    (routes.OPS_FEED, feed),
    (routes.OPS_RECOVERY, recovery),
    (routes.OPS_FLUSH, flush),
    (routes.OPS_DOSING, dosing),
    (routes.OPS_HYDRAULICS, hydraulics),
    (routes.OPS_TANK, tank),
    (routes.REPORT, report),
    (routes.AUDIT, audit),
    (routes.SUMMARY, summary),
    (routes.SELFTEST, selftest),
    (routes.VERSION, version),
)
