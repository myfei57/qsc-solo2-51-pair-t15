"""Console handlers for the unified maintenance ledger."""

from .http import Request, Response, json_response

DEFAULT_SLIP = 30


def ledger(console, request: Request) -> Response:
    """Every registered task with its ordered plan and decision history."""
    return json_response(console.plant.maintenance_ledger())


def queue(console, request: Request) -> Response:
    """Due tasks the current window could start, in execution order."""
    return json_response(console.plant.maintenance_queue())


def sweep(console, request: Request) -> Response:
    """Raise due reminders and start or postpone due tasks."""
    return json_response(console.plant.maintenance_sweep())


def start(console, request: Request) -> Response:
    """Start one due maintenance task."""
    body = request.body()
    task_id = str(body["task_id"])
    return json_response(console.plant.maintenance_start(task_id))


def complete(console, request: Request) -> Response:
    """Complete one active maintenance task and reschedule the next one."""
    body = request.body()
    task_id = str(body["task_id"])
    return json_response(console.plant.maintenance_complete(task_id))


def postpone(console, request: Request) -> Response:
    """Skip a due instance for a written reason and postpone it.

    Repeating the same postpone for the same due instance is idempotent.
    """
    body = request.body()
    task_id = str(body["task_id"])
    reason = str(body["reason"])
    slip = int(body.get("slip", DEFAULT_SLIP))
    return json_response(console.plant.maintenance_postpone(task_id, reason, slip))


def skip(console, request: Request) -> Response:
    """Manually skip a due instance, recording the reason."""
    body = request.body()
    task_id = str(body["task_id"])
    reason = str(body["reason"])
    reschedule = bool(body.get("reschedule", True))
    slip = int(body.get("slip", DEFAULT_SLIP))
    return json_response(console.plant.maintenance_skip(task_id, reason, reschedule, slip))
