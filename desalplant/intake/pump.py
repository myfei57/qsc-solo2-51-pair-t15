"""Raw water pump feeding the treatment train."""

from .feed import Feed
from .flow import FeedRamp
from .schedule import CleanSchedule
from .screen import Screen
from .telemetry import IntakeTelemetry


class IntakePump:
    """Raw water pump with its screen and rinse interlock."""

    def __init__(self) -> None:
        self.running = False
        self.stopped = False

    def start(self) -> None:
        """Start the pump."""
        self.running = True
        self.stopped = False

    def shutdown(self, rack) -> None:
        """Rinse the rack while running, then stop the pump."""
        from .rinse import RinseGate

        gate = RinseGate()
        gate.rinse(rack, self.running)
        gate.require_complete()
        self.running = False
        self.stopped = True

    def flow_rate(self, speed: float) -> float:
        """Flow delivered at a relative pump speed."""
        return speed * 0.8

    def target_flow(self, level: float) -> float:
        """Feed flow chosen from the upstream level."""
        if level >= 80:
            return 70.0
        if level >= 50:
            return 90.0
        return 110.0

    def ramp_feed(self, ramp: FeedRamp) -> float:
        """Apply a feed ramp and return the resulting flow."""
        self.running = True
        if not ramp.ascending():
            return ramp.start
        return ramp.end

    def screen_clean(self, screen: Screen, limit: float) -> bool:
        """Clear the screen when it is fouled beyond ``limit``."""
        if not screen.fouled(limit):
            return True
        screen.clear()
        return True

    def clean_due(self, schedule: CleanSchedule, now: int) -> bool:
        """Whether a scheduled screen cleaning is due."""
        return schedule.due(now)

    def collect(self, flow: float, screen: Screen) -> IntakeTelemetry:
        """Capture one intake sweep."""
        return IntakeTelemetry(flow=flow, screen_delta=screen.delta)

    def feed_backwash(self, ramp: FeedRamp, feed: Feed) -> float:
        """Ramp the feed and report availability of the resulting flow."""
        flow = self.ramp_feed(ramp)
        if not feed.available(flow):
            return 0.0
        return flow
