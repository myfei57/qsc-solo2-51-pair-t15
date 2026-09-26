"""Build label reported by the console."""

from dataclasses import dataclass

from .. import __version__

NAME = "desalplant"


@dataclass(frozen=True)
class BuildInfo:
    """Name and version of the running service."""

    version: str
    name: str

    def label(self) -> str:
        """Single-string label."""
        return f"{self.name}/{self.version}"


def build() -> BuildInfo:
    """Describe the running build."""
    return BuildInfo(version=__version__, name=NAME)
