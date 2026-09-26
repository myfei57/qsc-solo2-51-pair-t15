"""Membrane array and the sensor-to-stage mapping it owns."""

from ..errors import InvalidStagesError


class MembraneArray:
    """Array of membrane stages with a refreshed sensor map."""

    def __init__(self, stages: int) -> None:
        self.stages = 0
        self.sensor_map: dict[str, str] = {}
        self._set_stages(stages)

    def _set_stages(self, stages: int) -> None:
        self.stages = stages
        self._refresh_map()

    def _refresh_map(self) -> None:
        self.sensor_map = {
            f"s{index}": f"stage{index}" for index in range(1, self.stages + 1)
        }

    def regroup(self, stages: int) -> None:
        """Rebuild the array onto a new stage count."""
        if stages <= 0:
            raise InvalidStagesError("invalid membrane stages")
        self.stages = stages
        self._refresh_map()

    def count(self) -> int:
        """Number of stages in the array."""
        return self.stages

    def stage_count(self) -> int:
        """Number of stages, kept for symmetry with the pressure reading."""
        return self.stages

    def sensor_stage(self, sensor: str) -> str:
        """Stage a sensor belongs to, or an empty string when unknown."""
        return self.sensor_map.get(sensor, "")

    def stage_sensors(self, stage: str) -> tuple[str, ...]:
        """Sensors mapped onto one stage."""
        return tuple(
            sorted(sensor for sensor, current in self.sensor_map.items() if current == stage)
        )

    def sensors(self) -> dict[str, str]:
        """A detached copy of the sensor map."""
        return dict(self.sensor_map)

    def last_stage(self) -> str:
        """Name of the final stage."""
        return f"stage{self.stages}"

    def map_fresh(self) -> bool:
        """Whether every stage still has a mapped sensor."""
        for index in range(1, self.stages + 1):
            if not self.sensor_map.get(f"s{index}"):
                return False
        return True
