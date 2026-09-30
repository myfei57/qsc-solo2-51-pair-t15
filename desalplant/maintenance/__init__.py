"""Unified maintenance ledger.

Recurring maintenance that used to be tracked by hand -- the intake screen
rinse ("格栅冲洗"), the media bed backwash ("反洗") and the antiscalant dosing
check ("加药") -- is held in one ledger.  Every task type carries its own
interval, lead time, priority and a *fixed* execution policy; the planner in
:mod:`desalplant.maintenance.planner` turns the ledger into a priority-ordered
queue, records skip/postpone decisions and never interrupts work in progress.
"""

from .catalog import Catalog, TaskDef, TaskType
from .ledger import Ledger, LedgerEntry
from .planner import PlannedTask, Planner, SweepResult
from .policy import ExecutionPolicy, WindowRequirement

__all__ = [
    "Catalog",
    "ExecutionPolicy",
    "Ledger",
    "LedgerEntry",
    "PlannedTask",
    "Planner",
    "SweepResult",
    "TaskDef",
    "TaskType",
    "WindowRequirement",
]
