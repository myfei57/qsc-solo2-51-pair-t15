"""Product tank level."""

from .band import LevelBand


class Level:
    """Tank level as a percentage."""

    def __init__(self, percent: float = 0.0) -> None:
        self.percent = float(percent)

    def update(self, value: float) -> float:
        """Adopt a fresh level reading."""
        self.percent = float(value)
        return self.percent

    def fill_to(self, target: float) -> float:
        """Raise the level towards a target, never lowering it."""
        if target > self.percent:
            self.percent = float(target)
        return self.percent

    def within(self, band: LevelBand) -> bool:
        """Whether the level sits inside a band."""
        return band.contains(self.percent)

    def trend(self, previous: float) -> float:
        """Change against a previous reading."""
        return self.percent - previous
