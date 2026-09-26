"""Identifier source used for alarms and audit events."""

import uuid


def new_id() -> str:
    """Return a fresh, collision-free textual identifier."""
    return uuid.uuid4().hex
