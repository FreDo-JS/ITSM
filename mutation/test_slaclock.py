# ai-generated: 80% - Claude Code wrote these tests from the docstrings of slaclock.py, boundary by boundary; I reviewed them and ran the practice mutants
"""Tests for slaclock.py. The docstrings are the specification; every test states the boundary it pins."""
from datetime import datetime, timedelta

import pytest

import slaclock

# Calendar anchors (2026): Mon 12 Oct, Tue 13, Wed 14, Thu 15, Fri 16, Sat 17, Sun 18, Mon 19 Oct.
MON = datetime(2026, 10, 12)
FRI = datetime(2026, 10, 16)
SAT = datetime(2026, 10, 17)
SUN = datetime(2026, 10, 18)


def at(day, hour, minute=0, second=0, microsecond=0):
    return day.replace(hour=hour, minute=minute, second=second, microsecond=microsecond)


# --- priority_of -------------------------------------------------------------------------------------------------

MATRIX = {
    (1, 1): "P1", (1, 2): "P2", (1, 3): "P3",
    (2, 1): "P2", (2, 2): "P3", (2, 3): "P4",
    (3, 1): "P3", (3, 2): "P4", (3, 3): "P4",
}


@pytest.mark.parametrize("cell", sorted(MATRIX))
def test_priority_matrix(cell):
    assert slaclock.priority_of(*cell) == MATRIX[cell]
    assert slaclock.priority_of(cell[0], cell[1], False) == MATRIX[cell]


@pytest.mark.parametrize("cell", sorted(MATRIX))
def test_priority_vip_is_never_below_p2(cell):
    expected = MATRIX[cell] if MATRIX[cell] in ("P1", "P2") else "P2"
    assert slaclock.priority_of(cell[0], cell[1], True) == expected
    assert slaclock.priority_of(cell[0], cell[1], vip=True) == expected


def test_priority_returns_a_string():
    assert isinstance(slaclock.priority_of(2, 2), str)


@pytest.mark.parametrize("impact, urgency", [
    (0, 1), (4, 1), (-1, 1), (1, 0), (1, 4), (1, -1), (0, 0), (4, 4),
    (2.0, 1), (1, 2.0), (True, 1), (1, True), (False, 1), (1, False),
    ("1", 1), (1, "1"), (None, 1), (1, None), (1.5, 1), (1, 3.0),
])
def test_priority_rejects_values_outside_one_to_three(impact, urgency):
    with pytest.raises(ValueError):
        slaclock.priority_of(impact, urgency)
    with pytest.raises(ValueError):
        slaclock.priority_of(impact, urgency, True)


# --- targets -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("priority, expected", [
    ("P1", (15, 240)), ("P2", (60, 480)), ("P3", (240, 1440)), ("P4", (480, 4320)),
])
def test_targets(priority, expected):
    assert slaclock.targets(priority) == expected


@pytest.mark.parametrize("priority", ["p1", " P1", "P1 ", "P5", "P0", "", "P", "1", "P12", "p4"])
def test_targets_lookup_is_exact(priority):
    with pytest.raises(ValueError):
        slaclock.targets(priority)


# --- sla_state ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("elapsed, target, expected", [
    (0, 15, "ok"), (1, 15, "ok"), (11, 15, "ok"), (12, 15, "warning"), (14, 15, "warning"),
    (15, 15, "warning"), (16, 15, "breached"), (1000, 15, "breached"),
    (0, 100, "ok"), (74, 100, "ok"), (75, 100, "warning"), (76, 100, "warning"),
    (99, 100, "warning"), (100, 100, "warning"), (101, 100, "breached"),
    (0, 4, "ok"), (2, 4, "ok"), (3, 4, "warning"), (4, 4, "warning"), (5, 4, "breached"),
    (0, 1, "ok"), (1, 1, "warning"), (2, 1, "breached"),
    (179, 240, "ok"), (180, 240, "warning"), (240, 240, "warning"), (241, 240, "breached"),
    (3239, 4320, "ok"), (3240, 4320, "warning"), (4320, 4320, "warning"), (4321, 4320, "breached"),
    (5, 7, "ok"), (6, 7, "warning"), (7, 7, "warning"), (8, 7, "breached"),
])
def test_sla_state(elapsed, target, expected):
    assert slaclock.sla_state(elapsed, target) == expected


@pytest.mark.parametrize("elapsed, target", [(-1, 10), (-100, 10), (5, 0), (5, -1), (0, 0), (-1, -1), (0, -10)])
def test_sla_state_rejects_bad_arguments(elapsed, target):
    with pytest.raises(ValueError):
        slaclock.sla_state(elapsed, target)


# --- is_business_time --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("day", [MON, MON + timedelta(days=1), MON + timedelta(days=2),
                                 MON + timedelta(days=3), FRI])
def test_business_time_window_edges_on_weekdays(day):
    assert slaclock.is_business_time(at(day, 7, 59)) is False
    assert slaclock.is_business_time(at(day, 8, 0)) is True
    assert slaclock.is_business_time(at(day, 8, 1)) is True
    assert slaclock.is_business_time(at(day, 12, 0)) is True
    assert slaclock.is_business_time(at(day, 15, 59)) is True
    assert slaclock.is_business_time(at(day, 16, 0)) is False
    assert slaclock.is_business_time(at(day, 16, 1)) is False
    assert slaclock.is_business_time(at(day, 0, 0)) is False
    assert slaclock.is_business_time(at(day, 23, 59)) is False


@pytest.mark.parametrize("day", [SAT, SUN])
@pytest.mark.parametrize("hour", [0, 7, 8, 12, 15, 16, 23])
def test_weekend_is_never_business_time(day, hour):
    assert slaclock.is_business_time(at(day, hour, 0)) is False
    assert slaclock.is_business_time(at(day, hour, 30)) is False


def test_business_time_ignores_seconds():
    assert slaclock.is_business_time(at(MON, 15, 59, 59, 999999)) is True
    assert slaclock.is_business_time(at(MON, 16, 0, 0)) is False
    assert slaclock.is_business_time(at(MON, 7, 59, 59)) is False
    assert slaclock.is_business_time(at(MON, 8, 0, 30)) is True


def test_business_time_uses_the_minute_of_the_hour():
    assert slaclock.is_business_time(at(MON, 9, 45)) is True
    assert slaclock.is_business_time(at(MON, 7, 0)) is False
    assert slaclock.is_business_time(at(MON, 15, 0)) is True
    assert slaclock.is_business_time(at(MON, 16, 30)) is False


# --- add_business_minutes ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("start, minutes, expected", [
    (at(MON, 12, 0), 60, at(MON, 13, 0)),
    (at(MON, 12, 0), 0, at(MON, 12, 0)),
    (at(MON, 8, 0), 0, at(MON, 8, 0)),
    (at(MON, 15, 59), 0, at(MON, 15, 59)),
    (at(MON, 8, 0), 1, at(MON, 8, 1)),
    (at(MON, 8, 0), 479, at(MON, 15, 59)),
    # a target that ends exactly at closing is due at 16:00 the same day (the tie rule)
    (at(MON, 8, 0), 480, at(MON, 16, 0)),
    (at(MON, 8, 0), 481, at(MON, 8, 1) + timedelta(days=1)),
    (at(MON, 15, 59), 1, at(MON, 16, 0)),
    (at(MON, 15, 59), 2, at(MON, 8, 1) + timedelta(days=1)),
    (at(FRI, 15, 30), 30, at(FRI, 16, 0)),
    (at(FRI, 15, 30), 31, at(MON, 8, 1) + timedelta(days=7)),
    (at(FRI, 15, 59), 2, at(MON, 8, 1) + timedelta(days=7)),
    # a start outside business hours first moves to the next opening
    (at(MON, 7, 0), 0, at(MON, 8, 0)),
    (at(MON, 7, 59), 30, at(MON, 8, 30)),
    (at(MON, 0, 0), 1, at(MON, 8, 1)),
    (at(MON, 16, 0), 0, at(MON, 8, 0) + timedelta(days=1)),
    (at(MON, 16, 0), 10, at(MON, 8, 10) + timedelta(days=1)),
    (at(MON, 23, 59), 0, at(MON, 8, 0) + timedelta(days=1)),
    (at(FRI, 16, 0), 0, at(MON, 8, 0) + timedelta(days=7)),
    (at(FRI, 17, 0), 15, at(MON, 8, 15) + timedelta(days=7)),
    (at(FRI, 23, 59), 0, at(MON, 8, 0) + timedelta(days=7)),
    (at(SAT, 12, 0), 0, at(MON, 8, 0) + timedelta(days=7)),
    (at(SAT, 0, 0), 1, at(MON, 8, 1) + timedelta(days=7)),
    (at(SUN, 10, 0), 60, at(MON, 9, 0) + timedelta(days=7)),
    (at(SUN, 23, 59), 480, at(MON, 16, 0) + timedelta(days=7)),
    # the course's SLA vectors: Friday 15:30 with a 4 h and with a 24 h target
    (at(FRI, 15, 30), 240, at(MON, 11, 30) + timedelta(days=7)),
    (at(FRI, 15, 30), 1440, at(FRI, 15, 30) + timedelta(days=5)),
    # whole days and whole weeks
    (at(MON, 8, 0), 960, at(MON, 16, 0) + timedelta(days=1)),
    (at(MON, 8, 0), 2400, at(MON, 16, 0) + timedelta(days=4)),
    (at(MON, 8, 0), 2401, at(MON, 8, 1) + timedelta(days=7)),
    (at(MON, 12, 0), 4320, at(MON, 12, 0) + timedelta(days=11)),
    # month and year boundaries; public holidays are business days
    (datetime(2026, 10, 30, 15, 0), 120, datetime(2026, 11, 2, 9, 0)),
    (datetime(2026, 10, 29, 15, 0), 120, datetime(2026, 10, 30, 9, 0)),
    (datetime(2026, 12, 31, 15, 0), 120, datetime(2027, 1, 1, 9, 0)),
    (datetime(2027, 1, 1, 15, 0), 120, datetime(2027, 1, 4, 9, 0)),
])
def test_add_business_minutes(start, minutes, expected):
    assert slaclock.add_business_minutes(start, minutes) == expected


def test_add_business_minutes_ignores_seconds_and_microseconds():
    result = slaclock.add_business_minutes(at(MON, 12, 0, 45, 123456), 60)
    assert result == at(MON, 13, 0)
    assert result.second == 0 and result.microsecond == 0
    assert slaclock.add_business_minutes(at(MON, 15, 59, 59, 999999), 1) == at(MON, 16, 0)
    assert slaclock.add_business_minutes(at(MON, 16, 0, 0), 0) == at(MON, 8, 0) + timedelta(days=1)
    assert slaclock.add_business_minutes(at(MON, 7, 59, 59), 0) == at(MON, 8, 0)


def test_add_business_minutes_returns_a_datetime():
    assert isinstance(slaclock.add_business_minutes(at(MON, 9, 0), 5), datetime)


@pytest.mark.parametrize("minutes", [-1, -60, -1000])
def test_add_business_minutes_rejects_negative_minutes(minutes):
    with pytest.raises(ValueError):
        slaclock.add_business_minutes(at(MON, 9, 0), minutes)


def _business_days_between(first, last):
    """Weekdays in [first, last), counted independently of the module."""
    days, day = 0, first
    while day < last:
        days += 1 if day.weekday() < 5 else 0
        day += timedelta(days=1)
    return days


def test_add_business_minutes_accepts_a_due_date_366_days_out_and_rejects_367():
    start = at(MON, 8, 0)
    for offset, accepted in ((366, True), (367, False)):
        target_day = start + timedelta(days=offset)
        assert target_day.weekday() < 5
        minutes = 480 * _business_days_between(start, target_day) + 10
        if accepted:
            assert slaclock.add_business_minutes(start, minutes) == at(target_day, 8, 10)
        else:
            with pytest.raises(ValueError):
                slaclock.add_business_minutes(start, minutes)


def test_add_business_minutes_rejects_a_far_future_due_date():
    with pytest.raises(ValueError):
        slaclock.add_business_minutes(at(MON, 9, 0), 10_000_000)


def test_add_business_minutes_counts_the_limit_from_the_start_date_not_the_start_time():
    start = at(MON, 15, 59)
    target_day = at(MON, 0, 0) + timedelta(days=366)
    minutes = 1 + 480 * (_business_days_between(start, target_day) - 1) + 10
    assert slaclock.add_business_minutes(start, minutes) == at(target_day, 8, 10)


# --- business_minutes_between ------------------------------------------------------------------------------------

@pytest.mark.parametrize("start, end, expected", [
    (at(MON, 9, 0), at(MON, 9, 0), 0),
    (at(MON, 8, 0), at(MON, 8, 1), 1),
    (at(MON, 15, 59), at(MON, 16, 0), 1),
    (at(MON, 8, 0), at(MON, 16, 0), 480),
    (at(MON, 7, 0), at(MON, 17, 0), 480),
    (at(MON, 0, 0), at(MON, 23, 59), 480),
    (at(MON, 10, 0), at(MON, 11, 30), 90),
    (at(MON, 16, 0), at(MON, 8, 0) + timedelta(days=1), 0),
    (at(MON, 17, 0), at(MON, 18, 0), 0),
    (at(MON, 6, 0), at(MON, 7, 0), 0),
    (at(MON, 16, 0), at(MON, 17, 0), 0),
    (at(MON, 8, 0), at(MON, 8, 0) + timedelta(days=1), 480),
    (at(MON, 15, 0), at(MON, 9, 0) + timedelta(days=1), 120),
    (at(MON, 15, 0), at(MON, 17, 0) + timedelta(days=1), 60 + 480),
    (at(FRI, 15, 0), at(MON, 9, 0) + timedelta(days=7), 120),
    (at(SAT, 10, 0), at(SUN, 10, 0), 0),
    (at(SAT, 0, 0), at(MON, 0, 0) + timedelta(days=7), 0),
    (at(SAT, 10, 0), at(MON, 9, 0) + timedelta(days=7), 60),
    (at(FRI, 17, 0), at(SAT, 9, 0), 0),
    (at(MON, 8, 0), at(MON, 8, 0) + timedelta(days=7), 2400),
    (at(MON, 8, 0), at(MON, 16, 0) + timedelta(days=4), 2400),
    (at(MON, 8, 0), at(MON, 8, 0) + timedelta(days=14), 4800),
    (at(MON, 12, 0), at(MON, 12, 0) + timedelta(days=21), 7200),
    (datetime(2026, 12, 31, 15, 0), datetime(2027, 1, 4, 9, 0), 600),
    (datetime(2026, 10, 30, 15, 0), datetime(2026, 11, 2, 9, 0), 120),
])
def test_business_minutes_between(start, end, expected):
    assert slaclock.business_minutes_between(start, end) == expected


def test_business_minutes_between_ignores_seconds_and_microseconds():
    assert slaclock.business_minutes_between(at(MON, 8, 0, 59), at(MON, 8, 1, 1)) == 1
    assert slaclock.business_minutes_between(at(MON, 8, 0, 0, 999999), at(MON, 8, 0, 59)) == 0
    assert slaclock.business_minutes_between(at(MON, 15, 59, 30), at(MON, 16, 0, 30)) == 1
    assert slaclock.business_minutes_between(at(MON, 7, 59, 59), at(MON, 8, 0, 0)) == 0


def test_business_minutes_between_is_half_open():
    assert slaclock.business_minutes_between(at(MON, 8, 0), at(MON, 8, 0)) == 0
    assert slaclock.business_minutes_between(at(MON, 16, 0), at(MON, 16, 0)) == 0
    assert slaclock.business_minutes_between(at(MON, 15, 59), at(MON, 15, 59)) == 0


def test_business_minutes_between_returns_an_int():
    assert isinstance(slaclock.business_minutes_between(at(MON, 9, 0), at(MON, 10, 0)), int)


@pytest.mark.parametrize("start, end", [
    (at(MON, 9, 1), at(MON, 9, 0)),
    (at(MON, 9, 0), at(MON, 8, 0)),
    (at(MON, 9, 0), at(MON, 9, 0) - timedelta(days=1)),
    (at(SAT, 12, 0), at(SAT, 11, 0)),
    (at(MON, 9, 1), at(MON, 9, 0, 30)),
])
def test_business_minutes_between_rejects_end_before_start(start, end):
    with pytest.raises(ValueError):
        slaclock.business_minutes_between(start, end)


def test_business_minutes_between_limits_the_span_to_366_days():
    start = at(MON, 8, 0)
    assert slaclock.business_minutes_between(start, at(start + timedelta(days=366), 8, 0)) == \
        480 * _business_days_between(start, at(start + timedelta(days=366), 8, 0))
    with pytest.raises(ValueError):
        slaclock.business_minutes_between(start, at(start + timedelta(days=367), 8, 0))
    with pytest.raises(ValueError):
        slaclock.business_minutes_between(start, start + timedelta(days=1000))


def test_business_minutes_between_counts_the_span_in_calendar_dates():
    start = at(MON, 23, 0)
    end_ok = at(start + timedelta(days=366), 0, 30)
    end_bad = at(start + timedelta(days=367), 0, 30)
    assert slaclock.business_minutes_between(start, end_ok) >= 0
    with pytest.raises(ValueError):
        slaclock.business_minutes_between(start, end_bad)
    late_start = at(MON, 23, 59)
    assert slaclock.business_minutes_between(late_start, at(late_start + timedelta(days=366), 0, 0)) >= 0


STARTS = [
    at(MON, 0, 0), at(MON, 7, 59), at(MON, 8, 0), at(MON, 8, 1), at(MON, 12, 30), at(MON, 15, 59),
    at(MON, 16, 0), at(MON, 23, 59), at(FRI, 7, 0), at(FRI, 15, 30), at(FRI, 16, 0), at(FRI, 17, 0),
    at(SAT, 0, 0), at(SAT, 12, 0), at(SUN, 12, 0), at(SUN, 23, 59), datetime(2026, 12, 31, 15, 0),
    datetime(2027, 2, 28, 9, 17), datetime(2028, 2, 28, 16, 0),
]


@pytest.mark.parametrize("start", STARTS)
@pytest.mark.parametrize("minutes", [0, 1, 59, 60, 479, 480, 481, 960, 1000, 2400, 2401, 5000, 20000])
def test_round_trip_between_and_add(start, minutes):
    due = slaclock.add_business_minutes(start, minutes)
    assert slaclock.business_minutes_between(start, due) == minutes
    assert slaclock.is_business_time(due) or (due.hour, due.minute) == (16, 0)


# --- escalation_tier ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("priority, breached, reopens, expected", [
    ("P1", False, 0, 1), ("P1", False, 1, 1), ("P1", False, 2, 2), ("P1", False, 3, 2), ("P1", False, 10, 2),
    ("P1", True, 0, 3), ("P1", True, 1, 3), ("P1", True, 2, 3), ("P1", True, 3, 3), ("P1", True, 10, 3),
    ("P2", False, 0, 1), ("P2", False, 1, 1), ("P2", False, 2, 2), ("P2", False, 3, 2),
    ("P2", True, 0, 2), ("P2", True, 1, 2), ("P2", True, 2, 3), ("P2", True, 3, 3), ("P2", True, 10, 3),
    ("P3", False, 0, 0), ("P3", False, 1, 0), ("P3", False, 2, 1), ("P3", False, 3, 1),
    ("P3", True, 0, 1), ("P3", True, 1, 1), ("P3", True, 2, 2), ("P3", True, 3, 2),
    ("P4", False, 0, 0), ("P4", False, 1, 0), ("P4", False, 2, 1), ("P4", False, 3, 1),
    ("P4", True, 0, 1), ("P4", True, 1, 1), ("P4", True, 2, 2), ("P4", True, 3, 2),
])
def test_escalation_tier(priority, breached, reopens, expected):
    assert slaclock.escalation_tier(priority, breached, reopens) == expected


def test_escalation_tier_is_capped_at_three():
    assert slaclock.escalation_tier("P1", True, 2) == 3
    assert slaclock.escalation_tier("P1", True, 100) == 3
    assert slaclock.escalation_tier("P2", True, 5) == 3


@pytest.mark.parametrize("priority, reopens", [
    ("P5", 0), ("p1", 0), ("", 0), (" P1", 0), ("P0", 1), ("P1", -1), ("P3", -1), ("P4", -5), ("XX", -1),
])
def test_escalation_tier_rejects_bad_arguments(priority, reopens):
    with pytest.raises(ValueError):
        slaclock.escalation_tier(priority, False, reopens)
    with pytest.raises(ValueError):
        slaclock.escalation_tier(priority, True, reopens)


def test_escalation_tier_accepts_zero_reopens():
    assert slaclock.escalation_tier("P4", False, 0) == 0


# --- parse_duration ----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("90m", 90), ("1m", 1), ("59m", 59), ("60m", 60), ("61m", 61), ("100m", 100), ("4h", 240), ("1h", 60),
    ("1h30m", 90), ("1h59m", 119), ("1h1m", 61), ("2h0m", 120), ("2d", 2880), ("1d", 1440), ("1d4h", 1680),
    ("1d0h5m", 1445), ("1d1m", 1441), ("1d59m", 1499), ("0h60m", 60), ("0d60m", 60), ("0d0h60m", 60),
    ("0d1h", 60), ("0d0h1m", 1), ("3d2h1m", 3 * 1440 + 121), ("100d", 144000), ("24h", 1440), ("25h", 1500),
    ("  90m", 90), ("90m  ", 90), ("\t1h\n", 60), (" 2d ", 2880), ("0h90m", 90), ("0d0h90m", 90),
])
def test_parse_duration(text, expected):
    assert slaclock.parse_duration(text) == expected


def test_parse_duration_returns_an_int():
    assert type(slaclock.parse_duration("1h")) is int


@pytest.mark.parametrize("text", [
    "", " ", "0m", "0h", "0d", "0h0m", "0d0h0m", "00m", "1.5h", "30m1h", "1h2d", "-5m", "+5m", "1 h", "1h 30m",
    "1h30", "30", "m", "h", "d", "abc", "1H", "1D", "90M", "1h60m", "1d60m", "1d1h60m", "2h61m", "1h99m", "1d100m",
    "1hh", "1h30mm", "1d1d", "1h1h", "1m1m", "5 m", "1,5h", "1h-30m", "h1", "1w",
])
def test_parse_duration_rejects_everything_else(text):
    with pytest.raises(ValueError):
        slaclock.parse_duration(text)
