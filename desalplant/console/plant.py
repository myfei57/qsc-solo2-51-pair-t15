"""Wiring of the subsystems behind the console actions."""

from typing import Any

from ..audit.event import Event
from ..audit.recorder import Recorder
from ..brine.stream import BrineStream
from ..brine.valve import Valve
from ..chem.doser import Doser
from ..chem.tank import ChemicalTank
from ..clock import LogicalClock
from ..filter.media import MediaFilter
from ..filter.rack import Rack
from ..flush.rinse import RinseCycle
from ..flush.start import Flusher
from ..intake.feed import Feed
from ..intake.gate import Gate
from ..intake.interlock import GateInterlock
from ..intake.pump import IntakePump
from ..intake.screen import Screen
from ..maintenance import Catalog, Ledger, Planner
from ..ns.state import PlantState
from ..pump import differential, new, ramp, ramp_pressure, stop
from ..ro.array import MembraneArray
from ..ro.flow import FlowCheck
from ..ro.membrane import Membrane
from ..ro.output import Output
from ..ro.permeate import Permeate
from ..ro.recovery import Recovery
from ..store import keys
from ..store.snapshot import Snapshot
from ..store.store import Store
from ..tank.handoff import handoff
from ..tank.level import Level
from ..tank.product import ProductTank
from ..tank.tanks import TankSet
from . import alarms, audit_report, integration, probes, reports, summary, telemetry, version
from .version import BuildInfo

RAMP_TARGET = 60.0
PRODUCE_CONDUCTIVITY = 120.0
PRODUCE_POWER = 100.0
PRODUCE_LEVEL = 68.0
MAINTENANCE_EFFICIENCY = 0.8
MAINTENANCE_DRAW = 0.1
LAST_STAGE_READINGS = {"s3": 5.0}


class Plant:
    """Every subsystem of the line, wired together behind the console."""

    def __init__(self, store: Store, clock: LogicalClock, recorder: Recorder) -> None:
        self.store = store
        self.clock = clock
        self.recorder = recorder
        self.state = PlantState.IDLE

        self.feed = Feed()
        self.intake_pump = IntakePump()
        self.gate = Gate()
        self.interlock = GateInterlock(enabled=True)
        self.screen = Screen()
        self.media = MediaFilter()
        self.rack = Rack()
        self.doser = Doser()
        self.chem_tank = ChemicalTank(level=100.0)
        self.membrane = Membrane(flow=80.0, min_flow=50.0)
        self.permeate = Permeate(max_cond=300.0)
        self.array = MembraneArray(2)
        self.output = Output()
        self.recovery = Recovery()
        self.valve = Valve()
        self.hp_pump = new()
        self.flusher = Flusher()
        self.rinse = RinseCycle()
        self.tank_set = TankSet(current="tank-a", standby="tank-b")
        self.product = ProductTank()
        self.level = Level()
        self.brine_stream = BrineStream(concentration=0.6)

        self.maintenance_catalog = Catalog()
        self.ledger = Ledger(store)
        self.planner = Planner(
            self.ledger,
            self.maintenance_catalog,
            clock,
            recorder,
            lambda: self.state is PlantState.RUNNING,
        )
        # Default tasks are virtual until the first sweep or mutation touches
        # them, so building the plant leaves the store empty.

    # ------------------------------------------------------------- lifecycle

    def start(self) -> Event:
        """Bring the line up: intake, media, dosing, flow and pressure."""
        self.clock.advance()
        self.gate.open_gate()
        self.media.backwash()
        self.media.require_ready()
        self.intake_pump.start()
        self.feed.start()
        self.doser.start(self.feed)
        self.hp_pump.start()
        ramp(self.hp_pump, self.membrane, RAMP_TARGET)
        ramp_pressure(self.hp_pump, self.valve, RAMP_TARGET)
        self.state = PlantState.RUNNING
        self.store.put(keys.PLANT_STATE, self.state.value)
        self.store.put(keys.PLANT_STARTED_AT, self.clock.tick)
        event = self.recorder.log("start", "line started")
        # Reminders still fire while running; only running-safe tasks start.
        self.planner.sweep()
        return event

    def produce(self) -> Event:
        """Produce permeate and hand it to the tank when the quality allows."""
        self.clock.advance()
        check = FlowCheck()
        check.measure(self.membrane)
        self.permeate.update_conductivity(PRODUCE_CONDUCTIVITY)
        self.product.fill(self.permeate)
        self.output.check(self.hp_pump.efficiency, PRODUCE_POWER)
        self.level.update(PRODUCE_LEVEL)
        return self.recorder.log("produce", "permeate produced")

    def shutdown(self) -> Event:
        """Stop the line after stopping dosing, flushing and rinsing."""
        self.clock.advance()
        self.doser.stop(self.feed)
        stop(self.hp_pump, self.flusher)
        self.intake_pump.shutdown(self.rack)
        self.state = PlantState.IDLE
        self.store.put(keys.PLANT_STATE, self.state.value)
        self.store.put(keys.PLANT_STOPPED_AT, self.clock.tick)
        event = self.recorder.log("shutdown", "line stopped")
        # The shutdown window opens: anything that waited for the stop runs now.
        self.planner.sweep()
        return event

    def switch_tank(self) -> Event:
        """Move production to the standby tank."""
        self.clock.advance()
        active = handoff(self.tank_set, self.hp_pump)
        return self.recorder.log("switch", f"product tank switched to {active}")

    def maintain(self) -> Event:
        """Run the maintenance routine and record it."""
        self.clock.advance()
        self.array.regroup(3)
        self.pump_differential()
        self.hp_pump.recalibrate(MAINTENANCE_EFFICIENCY)
        self.output.check(self.hp_pump.efficiency, PRODUCE_POWER)
        self.recovery.raise_alarm()
        self.valve.set_emergency()
        from ..brine.recovery import recover_alarm

        recover_alarm(self.valve, self.recovery)
        self.chem_tank.draw(MAINTENANCE_DRAW)
        self.rinse.run()
        self.store.put(keys.PLANT_MAINTAINED_AT, self.clock.tick)
        return self.recorder.log("maintain", "maintenance completed")

    def pump_differential(self) -> float:
        """Pressure differential over the array's final stage."""
        return differential(self.hp_pump, self.array, dict(LAST_STAGE_READINGS))

    # --------------------------------------------------------- maintenance

    def maintenance_sweep(self) -> dict[str, Any]:
        """Raise due reminders and start or postpone due tasks in order."""
        self.clock.advance()
        return self.planner.sweep().to_dict(self.clock.tick)

    def maintenance_ledger(self) -> dict[str, Any]:
        """Full ledger with the ordered plan, for the console."""
        now = self.clock.tick
        tasks: list[dict[str, Any]] = []
        projected = {task.task_id: task for task in self.planner.upcoming()}
        for definition in self.maintenance_catalog.types():
            task_id = str(definition.type)
            entry = self.planner.entry_for(task_id)
            if task_id in projected:
                plan = projected[task_id]
                blocked, reason, cause = plan.blocked, plan.block_reason, plan.block_cause
            else:
                # The active task is excluded from the upcoming plan; the
                # console still shows it as the work that must not be stopped.
                blocked, reason, cause = False, "", ""
            tasks.append(
                {
                    "task_id": task_id,
                    "label": definition.label,
                    "priority": definition.priority,
                    "base_due": entry.base_due,
                    "due_at": entry.due_at,
                    "overdue": max(0, now - entry.due_at) if not entry.active else 0,
                    "postponed": entry.postponed,
                    "postponements": entry.postponements,
                    "window": str(definition.policy.window),
                    "preemptive": definition.policy.preemptive,
                    "blocked": blocked,
                    "block_reason": reason,
                    "block_cause": cause,
                    "lead": definition.lead,
                    "state": entry.state,
                    "remind_at": entry.remind_at(),
                    "reminded": entry.reminder_due == entry.due_at,
                    "completed_count": entry.completed_count,
                    "last_completed_at": entry.last_completed_at,
                    "active_since": entry.active_since,
                    "history": list(entry.history),
                }
            )
        tasks.sort(key=lambda row: (row["due_at"], row["priority"], row["task_id"]))
        return {"tick": now, "running": self.state is PlantState.RUNNING, "tasks": tasks}

    def maintenance_queue(self) -> dict[str, Any]:
        """Only the tasks due now that the current window could start."""
        now = self.clock.tick
        return {
            "tick": now,
            "running": self.state is PlantState.RUNNING,
            "queue": [task.to_dict(now) for task in self.planner.queue()],
        }

    def maintenance_start(self, task_id: str) -> dict[str, Any]:
        """Start one due maintenance task."""
        self._require_maintenance_task(task_id)
        return self.planner.start(task_id).to_dict()

    def maintenance_complete(self, task_id: str) -> dict[str, Any]:
        """Complete one active maintenance task and reschedule it."""
        self._require_maintenance_task(task_id)
        return self.planner.complete(task_id).to_dict()

    def maintenance_postpone(self, task_id: str, reason: str, slip: int) -> dict[str, Any]:
        """Skip the current instance for ``reason`` and postpone it."""
        self._require_maintenance_task(task_id)
        return self.planner.postpone(task_id, reason, slip=slip).to_dict()

    def maintenance_skip(
        self, task_id: str, reason: str, reschedule: bool, slip: int
    ) -> dict[str, Any]:
        """Manually skip the current instance for ``reason``."""
        self._require_maintenance_task(task_id)
        return self.planner.skip(task_id, reason, reschedule=reschedule, slip=slip).to_dict()

    def _require_maintenance_task(self, task_id: str) -> None:
        if not self.maintenance_catalog.has(task_id):
            from ..errors import UnknownMaintenanceTaskError

            raise UnknownMaintenanceTaskError(f"unknown maintenance task {task_id}")

    # --------------------------------------------------------------- reading

    def status(self) -> dict[str, Any]:
        """Compact view of the line's current state."""
        checkpoint = self.snapshot()
        started = self.store.has(keys.PLANT_STARTED_AT)
        started_at = int(self.store.require(keys.PLANT_STARTED_AT)) if started else 0
        running_ticks = self.clock.elapsed(started_at) if started_at <= self.clock.tick else 0
        return {
            "state": str(self.state),
            "tick": self.clock.tick,
            "started": started,
            "running_ticks": running_ticks,
            "feed_flowing": self.feed.flowing,
            "feed_scaled": self.feed.scaled,
            "membrane": str(self.membrane),
            "valve_open": self.valve.open,
            "valve_stressed": self.valve.stressed,
            "valve_emergency": self.valve.emergency,
            "pump_pressure": self.hp_pump.pressure,
            "supply": self.hp_pump.supply,
            "stalled": self.hp_pump.stalled,
            "dumping": self.product.dumping,
            "filling": self.product.filling,
            "rack_blocked": self.rack.blocked,
            "flush_started": self.flusher.started,
            "flush_effective": self.flusher.effective,
            "store_entries": checkpoint.count,
        }

    def report(self) -> dict[str, Any]:
        """Numeric report over the pump, permeate and schedules."""
        return reports.build_report(self)

    def audit_report(self) -> dict[str, Any]:
        """Numeric report over the train, histograms and schedules."""
        return audit_report.build_audit_report(self)

    def integration(self) -> dict[str, Any]:
        """Report that exercises the peripheral components in one pass."""
        return integration.build_integration(self)

    def summary(self) -> dict[str, Any]:
        """Summary over the curves, stream arithmetic and membranes."""
        return summary.build_summary(self)

    def telemetry(self):
        """One telemetry sweep."""
        return telemetry.telemetry(self)

    def diagnostics(self) -> dict[str, Any]:
        """Structural diagnostics."""
        return telemetry.diagnostics(self)

    def alarms(self) -> list[dict[str, Any]]:
        """Current alarms."""
        return alarms.alarms(self)

    def selftest(self) -> dict[str, Any]:
        """Drive the whole line once and report every step."""
        return probes.build_selftest(self)

    def events(self, limit: int = 0) -> tuple[Event, ...]:
        """Newest-first audit events."""
        return self.recorder.events(limit)

    def event_count(self) -> int:
        """Number of audit events recorded."""
        return self.recorder.count()

    def build(self) -> BuildInfo:
        """Describe the running build."""
        return version.build()

    def snapshot(self) -> Snapshot:
        """Frozen view of the persisted document."""
        return self.store.snapshot()
