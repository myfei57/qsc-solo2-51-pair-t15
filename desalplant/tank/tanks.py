"""Set of product tanks with a current and a standby member."""

from dataclasses import dataclass, field


@dataclass
class Tank:
    """One product tank and whether its outlet is open."""

    id: str
    open: bool = False
    blocked: bool = False

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "open": self.open, "blocked": self.blocked}


@dataclass
class TankSet:
    """A current tank paired with a standby tank."""

    current: str
    standby: str
    tanks: dict[str, Tank] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.tanks.setdefault(self.current, Tank(id=self.current, open=True))
        self.tanks.setdefault(self.standby, Tank(id=self.standby, open=False))

    def open_count(self) -> int:
        """How many tanks currently have their outlet open."""
        return sum(1 for tank in self.tanks.values() if tank.open)

    def open(self, tank_id: str) -> bool:
        """Open one tank's outlet, reporting whether the actuator moved."""
        tank = self._require(tank_id)
        if tank.blocked:
            return False
        tank.open = True
        return True

    def close(self, tank_id: str) -> bool:
        """Close one tank's outlet, reporting whether the actuator moved."""
        tank = self._require(tank_id)
        if tank.blocked:
            return False
        tank.open = False
        return True

    def is_open(self, tank_id: str) -> bool:
        """Whether one tank's outlet is open."""
        return self._require(tank_id).open

    def swap(self) -> None:
        """Exchange the current and standby roles."""
        self.current, self.standby = self.standby, self.current

    def active_id(self) -> str:
        """Identifier of the tank currently receiving product."""
        return self.current

    def level(self) -> float:
        """Open count expressed as a numeric level."""
        return float(self.open_count())

    def ids(self) -> tuple[str, ...]:
        """Sorted tank identifiers."""
        return tuple(sorted(self.tanks))

    def _require(self, tank_id: str) -> Tank:
        if tank_id not in self.tanks:
            raise KeyError(tank_id)
        return self.tanks[tank_id]
