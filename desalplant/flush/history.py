"""Running history of flush durations."""

from dataclasses import dataclass

from .stage import FlushPlan


@dataclass
class History:
    """Accumulates the duration of each flush run."""

    runs: int = 0
    total_seconds: int = 0

    def record(self, flush_plan: FlushPlan) -> int:
        """Record one run and return its duration."""
        duration = flush_plan.total_seconds()
        self.runs += 1
        self.total_seconds += duration
        return duration

    def average_seconds(self) -> float:
        """Mean duration across the recorded runs."""
        if self.runs == 0:
            return 0.0
        return self.total_seconds / self.runs
