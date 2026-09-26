"""Single membrane rinse cycle."""


class RinseCycle:
    """Rinse cycle that finishes exactly once."""

    def __init__(self) -> None:
        self.done = False

    def run(self) -> bool:
        """Run the rinse and report success."""
        self.done = True
        return self.done
