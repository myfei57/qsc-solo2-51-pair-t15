"""Report that exercises the peripheral components in a single pass."""

from typing import TYPE_CHECKING, Any

from ..brine.stream import BrineStream
from ..brine.valve import Valve
from ..chem.control import setpoint
from ..chem.dose_rate import DoseRate
from ..filter.backwash import finish_backwash, start_backwash
from ..intake.gate import Gate
from ..intake.interlock import GateInterlock
from ..ns.metrics import Metrics
from ..ns.state import PlantState
from ..ns.telemetry import Telemetry
from ..pump.state import new
from ..ro.array import MembraneArray
from ..ro.permeate import Permeate

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checkers
    from .plant import Plant

BACKWASH_FLOW = 80.0
GATE_PRESSURE = 10.0
REJECT_FLOW = 52.0
DOSE_FLOW = 80.0
DOSE_PPM = 2.5
REFILL = 2.0
RECOVERY_RATE = 46.0


def build_integration(plant: "Plant") -> dict[str, Any]:
    """Drive each peripheral component once and report the outcome."""
    plant.chem_tank.refill(REFILL)
    plant.doser.set_dose_rate(DoseRate(ppm=DOSE_PPM))
    dose_target = plant.doser.target_dose(DOSE_FLOW, DOSE_PPM)
    dose_setpoint = setpoint(DOSE_FLOW, DOSE_PPM)

    interlock = GateInterlock(enabled=True)
    spare_gate = Gate()
    gate_opened = spare_gate.interlocked(interlock, GATE_PRESSURE)
    spare_gate.close_gate()

    cycle = start_backwash(plant.media, BACKWASH_FLOW)
    finished = finish_backwash(plant.media)
    plant.rack.clean()
    rack_state = plant.rack.inspect()

    rejected = plant.permeate.reject_volume(REJECT_FLOW)
    array = MembraneArray(2)
    array_stages = array.stage_sensors("stage1")
    plant.recovery.update_rate(RECOVERY_RATE)
    plant.recovery.rate()

    trip_pump = new()
    trip_pump.trip("manual")
    idle_pump = new()
    idle_pump.idle()

    valve = Valve()
    valve.set_emergency()
    valve.release_emergency()
    emergency_flow = BrineStream().emergency_flow()

    store = plant.store
    store_keys = store.keys()
    store_count = store.count()
    store_export = store.export()
    checksum = store.checksum()
    store_valid = store.verify(checksum)

    sweep = Telemetry()
    sweep.add("feed_flow", plant.membrane.flow)
    latest_flow = sweep.latest("feed_flow")

    metrics = Metrics()
    metrics.inc("integration")
    metrics.inc("integration", 2)
    metrics.set("integration", 1.0)
    metrics.observe("integration", 1.0)

    permeate = Permeate(max_cond=300.0)
    permeate.update_conductivity(200.0)
    grade = permeate.grade()

    return {
        "dose_target": dose_target,
        "dose_setpoint": dose_setpoint,
        "gate_opened": gate_opened,
        "backwash_drop": cycle.pressure_drop,
        "backwash_completed": finished.completed,
        "media_ready": plant.media.ready(),
        "rack_growth": rack_state.growth_score,
        "rejected_volume": rejected,
        "array_stages": list(array_stages),
        "trip_reason": trip_pump.trip_reason,
        "idle_stopped": idle_pump.stopped,
        "emergency_flow": emergency_flow,
        "store_keys": list(store_keys),
        "store_count": store_count,
        "store_export": len(store_export),
        "store_valid": store_valid,
        "latest_flow": latest_flow,
        "metric_get": metrics.get("integration"),
        "metric_gauge": metrics.gauge("integration"),
        "metric_average": metrics.average("integration"),
        "severity_text": PlantState.STOPPING.value,
        "tank_level": plant.tank_set.level(),
        "grade": grade.to_dict(),
        "tank_empty": plant.chem_tank.empty(),
    }
