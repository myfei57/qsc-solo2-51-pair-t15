"""Persisted maintenance ledger entries.

An entry is one recurring task series.  Its *due instance* is described by
:attr:`LedgerEntry.base_due`; every postpone moves :attr:`LedgerEntry.due_at`
forward while keeping the base instance, so a duplicate postpone of the same
instance can be recognised and rejected as a no-op (idempotency).
"""

import threading
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..store import keys
from ..store.store import Store

# Maintenance tasks are never blocked forever: without an explicit window a
# postponed task comes back after this many ticks.
DEFAULT_SLIP = 30
HISTORY_LIMIT = 20


@dataclass
class LedgerEntry:
    """One recurring maintenance task and the state of its current instance."""

    task_id: str
    label: str
    interval: int
    lead: int
    priority: int
    created_at: int
    base_due: int
    due_at: int
    state: str = "pending"
    postponements: int = 0
    completed_count: int = 0
    last_completed_at: int = 0
    active_since: int = 0
    reminder_due: int = -1
    last_postpone_token: str = ""
    postponed_instance: bool = False
    history: list[dict[str, Any]] = field(default_factory=list)

    @property
    def active(self) -> bool:
        """Whether the task is currently being carried out."""
        return self.state == "active"

    @property
    def postponed(self) -> bool:
        """Whether the current instance has already been postponed."""
        return self.due_at > self.base_due

    def is_due(self, now: int) -> bool:
        """Whether the task is due now (or overdue)."""
        return not self.active and now >= self.due_at

    def remind_at(self) -> int:
        """Tick at which the advance reminder for this instance becomes due."""
        return self.due_at - self.lead

    def is_reminder_due(self, now: int) -> bool:
        """Whether the advance reminder should fire and has not done so yet."""
        return not self.active and self.reminder_due != self.due_at and now >= self.remind_at()

    def mark_reminded(self) -> None:
        """Remember that the reminder for the current instance was raised."""
        self.reminder_due = self.due_at

    def open_instance(self, due_at: int) -> None:
        """(Re)start an instance at ``due_at`` and clear one-off markers."""
        self.base_due = due_at
        self.due_at = due_at
        self.state = "pending"
        self.postponements = 0
        self.active_since = 0
        self.reminder_due = -1
        self.last_postpone_token = ""
        self.postponed_instance = False

    def apply_postpone(self, until: int, reason: str, token: str, at: int) -> None:
        """Move the current instance forward and append its decision record."""
        from_due = self.due_at
        self.due_at = until
        self.postponements += 1
        self.last_postpone_token = token
        self.postponed_instance = True
        # A later due means a later reminder; the old reminder no longer applies.
        self.reminder_due = -1
        self._record(
            {
                "action": "postpone",
                "at": at,
                "from_due": from_due,
                "to_due": until,
                "reason": reason,
                "token": token,
            }
        )

    def apply_skip(self, reason: str, at: int, until: int | None = None) -> None:
        """Record a manual skip, optionally postponing the instance."""
        record: dict[str, Any] = {"action": "skip", "at": at, "reason": reason}
        if until is not None:
            record["to_due"] = until
            self.due_at = until
            self.reminder_due = -1
        self._record(record)

    def activate(self, at: int) -> None:
        """Mark the task as running; active work must not be interrupted."""
        self.state = "active"
        self.active_since = at

    def complete(self, at: int) -> int:
        """Close the instance, reschedule the next one and return its due tick."""
        self.completed_count += 1
        self.last_completed_at = at
        next_due = at + self.interval
        self._record({"action": "complete", "at": at, "done_due": self.due_at})
        self.open_instance(next_due)
        return next_due

    def _record(self, row: dict[str, Any]) -> None:
        self.history.append(row)
        if len(self.history) > HISTORY_LIMIT:
            del self.history[:-HISTORY_LIMIT]

    def to_dict(self) -> dict[str, Any]:
        """JSON-friendly projection persisted by the store."""
        return {
            "task_id": self.task_id,
            "label": self.label,
            "interval": self.interval,
            "lead": self.lead,
            "priority": self.priority,
            "created_at": self.created_at,
            "base_due": self.base_due,
            "due_at": self.due_at,
            "state": self.state,
            "postponements": self.postponements,
            "completed_count": self.completed_count,
            "last_completed_at": self.last_completed_at,
            "active_since": self.active_since,
            "reminder_due": self.reminder_due,
            "last_postpone_token": self.last_postpone_token,
            "postponed_instance": self.postponed_instance,
            "history": list(self.history),
        }

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> "LedgerEntry":
        """Rebuild an entry from a persisted row."""
        return cls(
            task_id=str(row["task_id"]),
            label=str(row.get("label", row["task_id"])),
            interval=int(row["interval"]),
            lead=int(row.get("lead", 0)),
            priority=int(row.get("priority", 99)),
            created_at=int(row.get("created_at", 0)),
            base_due=int(row["base_due"]),
            due_at=int(row["due_at"]),
            state=str(row.get("state", "pending")),
            postponements=int(row.get("postponements", 0)),
            completed_count=int(row.get("completed_count", 0)),
            last_completed_at=int(row.get("last_completed_at", 0)),
            active_since=int(row.get("active_since", 0)),
            reminder_due=int(row.get("reminder_due", -1)),
            last_postpone_token=str(row.get("last_postpone_token", "")),
            postponed_instance=bool(row.get("postponed_instance", False)),
            history=[dict(item) for item in row.get("history", ())],
        )


class Ledger:
    """Task entries held in the file-backed store under one prefix."""

    def __init__(self, store: Store) -> None:
        self._store = store
        self._lock = threading.RLock()

    def register(
        self,
        task_id: str,
        label: str,
        interval: int,
        lead: int,
        priority: int,
        now: int,
    ) -> LedgerEntry:
        """Add a task when it is not on the ledger yet and return its entry."""
        with self._lock:
            existing = self.find(task_id)
            if existing is not None:
                return existing
            entry = LedgerEntry(
                task_id=task_id,
                label=label,
                interval=interval,
                lead=lead,
                priority=priority,
                created_at=now,
                base_due=now + interval,
                due_at=now + interval,
            )
            self._persist(entry)
            return entry

    def list(self) -> tuple[LedgerEntry, ...]:
        """All entries, ordered by their key."""
        with self._lock:
            return tuple(
                LedgerEntry.from_dict(self._store.require(key))
                for key in self._store.keys(keys.MAINTENANCE_PREFIX)
            )

    def find(self, task_id: str) -> LedgerEntry | None:
        """Look up one entry, or ``None`` when it is not registered."""
        row = self._store.get(keys.maintenance_task_key(task_id))
        if row is None:
            return None
        return LedgerEntry.from_dict(row)

    def require(self, task_id: str) -> LedgerEntry:
        """Look up one entry, raising when it is not registered."""
        entry = self.find(task_id)
        if entry is None:
            raise KeyError(f"maintenance task {task_id} is not registered")
        return entry

    def save(self, entry: LedgerEntry) -> None:
        """Persist an entry."""
        with self._lock:
            self._persist(entry)

    def lock(self):
        """Expose the compound-operation lock to the planner."""
        return self._lock

    def _persist(self, entry: LedgerEntry) -> None:
        self._store.put(keys.maintenance_task_key(entry.task_id), entry.to_dict())
