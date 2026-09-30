"""Shutdown-window availability and the skip reasons it produces.

A maintenance chore needs a settled line.  While the line is running there is
no window; while it is settling just after a stop it is also unsafe to enter.
Only the ``IDLE`` state offers a window.  The skip reason recorded on the audit
trail distinguishes the two so the console can show *why* a chore was deferred.
"""

from ..ns.state import PlantState

REASON_RUNNING = "running"
REASON_STOPPING = "stopping"
REASON_WINDOW = "window"


def window_available(state: PlantState) -> bool:
    """Whether the line is settled and safe to work on."""
    return state == PlantState.IDLE


def skip_reason(state: PlantState) -> str | None:
    """Why a chore cannot run now, or ``None`` when a window exists."""
    if state == PlantState.IDLE:
        return None
    if state == PlantState.STOPPING:
        return REASON_STOPPING
    return REASON_RUNNING


def window_label(state: PlantState) -> str:
    """Audit/console label for the current window state."""
    if state == PlantState.IDLE:
        return REASON_WINDOW
    return skip_reason(state) or REASON_RUNNING
