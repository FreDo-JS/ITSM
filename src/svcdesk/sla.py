# ai-generated: 90% - Claude Code wrote the SLA clocks from API.md sections 3-5; the owner reviewed them against T1-T8
"""Priority matrix, SLA targets and the two clocks (API.md sections 3, 4 and 5).

Decisions implemented here (see DECISIONS.md):
  C1 = wallclock: both P1 targets run on the wall clock, P2-P4 on business hours.
  C3 = vip: a VIP ticket that the matrix puts at P3 or P4 is raised to P2.
"""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")
OPEN = time(8, 0)
CLOSE = time(16, 0)

MATRIX = {
    (1, 1): "P1", (1, 2): "P2", (1, 3): "P3",
    (2, 1): "P2", (2, 2): "P3", (2, 3): "P4",
    (3, 1): "P3", (3, 2): "P4", (3, 3): "P4",
}

# priority -> (acknowledge target, resolve target)
TARGETS = {
    "P1": (timedelta(minutes=15), timedelta(hours=4)),
    "P2": (timedelta(hours=1), timedelta(hours=8)),
    "P3": (timedelta(hours=4), timedelta(hours=24)),
    "P4": (timedelta(hours=8), timedelta(hours=72)),
}

# C1 = wallclock: only P1 runs around the clock.
WALLCLOCK_PRIORITIES = {"P1"}


def compute_priority(impact: int, urgency: int, vip: bool) -> str:
    priority = MATRIX[(impact, urgency)]
    # C3 = vip (R-06 over R-05): VIP tickets are never lower than P2.
    if vip and priority in ("P3", "P4"):
        priority = "P2"
    return priority


def uses_wallclock(priority: str) -> bool:
    return priority in WALLCLOCK_PRIORITIES


def in_business_hours(instant: datetime) -> bool:
    local = instant.astimezone(WARSAW)
    return local.weekday() < 5 and OPEN <= local.time() < CLOSE


def _at(local: datetime, t: time) -> datetime:
    """The same local calendar day at wall time t, with the correct UTC offset for that day."""
    return datetime.combine(local.date(), t, tzinfo=WARSAW)


def _next_opening(local: datetime) -> datetime:
    """local itself if it lies inside a business window, else the next 08:00 of a business day."""
    while True:
        if local.weekday() >= 5 or local.time() >= CLOSE:
            local = _at(local + timedelta(days=1), OPEN)
            continue
        if local.time() < OPEN:
            return _at(local, OPEN)
        return local


def business_due(start: datetime, target: timedelta) -> datetime:
    """Consume target from consecutive business windows starting at start (API.md section 4)."""
    local = _next_opening(start.astimezone(WARSAW))
    remaining = target
    while True:
        close = _at(local, CLOSE)
        available = close - local
        # <= is the tie rule: a target ending exactly at closing is due at 16:00, not the next opening.
        if remaining <= available:
            return (local + remaining).astimezone(timezone.utc)
        remaining -= available
        local = _next_opening(close)


def due_instants(priority: str, created_at: datetime) -> tuple[datetime, datetime]:
    ack_target, resolve_target = TARGETS[priority]
    if uses_wallclock(priority):
        return created_at + ack_target, created_at + resolve_target
    return business_due(created_at, ack_target), business_due(created_at, resolve_target)
