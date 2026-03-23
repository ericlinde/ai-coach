import threading
from datetime import timedelta
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .agent import CoachAgent

_MIN_SECONDS = 5 * 60       # 5 minutes
_MAX_SECONDS = 7 * 24 * 3600  # 7 days


class InvalidCadenceError(Exception):
    pass


def parse_interval(interval_str: str) -> int:
    """Parse a cadence string to seconds. Raises InvalidCadenceError if invalid."""
    s = interval_str.strip().lower()

    try:
        if s == "daily":
            seconds = 86400
        elif s == "hourly":
            seconds = 3600
        elif s.endswith("d"):
            seconds = int(s[:-1]) * 86400
        elif s.endswith("h"):
            seconds = int(s[:-1]) * 3600
        elif s.endswith("m"):
            seconds = int(s[:-1]) * 60
        elif s.isdigit():
            seconds = int(s) * 60  # bare integer = minutes
        else:
            raise InvalidCadenceError(f"Unrecognised cadence format: {interval_str!r}")
    except ValueError:
        raise InvalidCadenceError(f"Unrecognised cadence format: {interval_str!r}")

    if seconds < _MIN_SECONDS:
        raise InvalidCadenceError(
            f"Cadence {interval_str!r} is too short (minimum 5 minutes)"
        )
    if seconds > _MAX_SECONDS:
        raise InvalidCadenceError(
            f"Cadence {interval_str!r} is too long (maximum 7 days)"
        )

    return seconds


class Scheduler:
    def __init__(self, apscheduler=None):
        self._scheduler = apscheduler or BackgroundScheduler()
        self._lock = threading.Lock()
        self._job = None
        self._current_seconds: int | None = None

    def start(
        self,
        agent: CoachAgent,
        send_message: Callable[[str], None],
        interval_seconds: int,
    ) -> None:
        def _job():
            result = agent.checkin()
            send_message(result)

        with self._lock:
            self._current_seconds = interval_seconds
            self._job = self._scheduler.add_job(
                _job,
                trigger="interval",
                seconds=interval_seconds,
            )

        self._scheduler.start()

    def update_cadence(self, new_interval: str) -> None:
        """Reschedule the running job. Raises InvalidCadenceError on bad value."""
        new_seconds = parse_interval(new_interval)  # validate first

        with self._lock:
            if self._job is None:
                raise RuntimeError("Scheduler has not been started — call start() first")
            if new_seconds == self._current_seconds:
                return
            trigger = IntervalTrigger(seconds=new_seconds)
            self._job.reschedule(trigger)
            self._current_seconds = new_seconds

    def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)
