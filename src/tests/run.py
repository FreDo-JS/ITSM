# ai-generated: 90% - Claude Code wrote the suite from API.md and DECISIONS.md; the owner picked the cases
"""Own black-box tests for svcdesk (Stretch S3), standard library only.

Reads the service URL from SVCDESK_URL, runs every test, and prints
`ITSMLAB-TESTS: passed=<n> failed=<m>` as the last line; exits 1 if anything failed.
"""

import json
import os
import sys
import time
import traceback
import urllib.error
import urllib.request

BASE = os.environ.get("SVCDESK_URL", "http://svcdesk:8080").rstrip("/")

T1 = "2026-10-14T10:00:00Z"   # Wed 12:00 CEST
T2 = "2026-10-16T13:30:00Z"   # Fri 15:30 CEST
T3 = "2026-10-16T15:00:00Z"   # Fri 17:00 CEST
T4 = "2026-10-17T10:00:00Z"   # Sat 12:00 CEST
T5 = "2027-01-14T14:30:00Z"   # Thu 15:30 CET
T6 = "2027-01-15T15:50:00Z"   # Fri 16:50 CET
T8 = "2026-10-23T13:00:00Z"   # Fri 15:00 CEST, DST ends on the Sunday after


def call(method, path, body=None, clock=T1):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if clock:
        req.add_header("X-Test-Clock", clock)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as err:
        raw = err.read()
        return err.code, json.loads(raw) if raw else None


def create(impact=2, urgency=2, vip=False, clock=T1, **extra):
    body = {"title": "own test", "reporter": {"name": "Desk Tester", "vip": vip},
            "impact": impact, "urgency": urgency, **extra}
    status, ticket = call("POST", "/tickets", body, clock)
    assert status == 201, (status, ticket)
    return ticket


def drive(ticket, *actions, clock=T1):
    for action in actions:
        status, body = call("POST", f"/tickets/{ticket['id']}/{action}", clock=clock)
        assert status == 200, (action, status, body)
    return body


def assert_due(clock, impact, urgency, ack, resolve):
    sla = create(impact, urgency, clock=clock)["sla"]
    assert (sla["ack_due_at"], sla["resolve_due_at"]) == (ack, resolve), sla


# --- tests ------------------------------------------------------------------------------------------------------


def test_health():
    status, body = call("GET", "/health")
    assert status == 200 and body["status"] == "ok" and body["service"] == "svcdesk", body


def test_unknown_path_is_json_404():
    status, body = call("GET", "/no-such-path")
    assert status == 404 and isinstance(body, dict), (status, body)


def test_unknown_ticket_404():
    status, body = call("GET", "/tickets/does-not-exist")
    assert status == 404 and "error" in body, (status, body)


def test_matrix_every_cell():
    expected = {(1, 1): "P1", (1, 2): "P2", (1, 3): "P3", (2, 1): "P2", (2, 2): "P3",
                (2, 3): "P4", (3, 1): "P3", (3, 2): "P4", (3, 3): "P4"}
    for (impact, urgency), priority in expected.items():
        assert create(impact, urgency)["priority"] == priority, (impact, urgency)


def test_vip_raised_to_p2_and_body_priority_ignored():
    assert create(3, 3, vip=True, priority="P1")["priority"] == "P2"
    assert create(1, 1, vip=True)["priority"] == "P1"


def test_validation_errors():
    good = {"title": "x", "reporter": {"name": "n"}, "impact": 1, "urgency": 1}
    bad = [
        {k: v for k, v in good.items() if k != "title"},
        {**good, "title": "x" * 201},
        {**good, "impact": 5},
        {**good, "urgency": "high"},
        {**good, "impact": True},
        {**good, "reporter": {}},
        {**good, "description": "d" * 4001},
    ]
    for body in bad:
        status, resp = call("POST", "/tickets", body)
        assert status in (400, 422) and "error" in resp, (body, status, resp)


def test_server_owned_fields_ignored():
    ticket = create(state="closed", id="mine", created_at="2020-01-01T00:00:00Z", unknown=1)
    assert ticket["state"] == "new" and ticket["id"] != "mine" and ticket["created_at"] == T1, ticket


def test_malformed_clock_rejected():
    body = {"title": "x", "reporter": {"name": "n"}, "impact": 1, "urgency": 1}
    for clock in ("yesterday", "2026-10-14T10:00:00"):
        status, _ = call("POST", "/tickets", body, clock=clock)
        assert status in (400, 422), (clock, status)


def test_sla_vectors_business_clock():
    assert_due(T1, 2, 1, "2026-10-14T11:00:00Z", "2026-10-15T10:00:00Z")   # T7, P2
    assert_due(T2, 2, 2, "2026-10-19T09:30:00Z", "2026-10-21T13:30:00Z")   # T2, P3
    assert_due(T4, 1, 2, "2026-10-19T07:00:00Z", "2026-10-19T14:00:00Z")   # T4, P2, tie at closing
    assert_due(T5, 2, 3, "2027-01-15T14:30:00Z", "2027-01-27T14:30:00Z")   # T5, P4, CET
    assert_due(T8, 2, 2, "2026-10-26T10:00:00Z", "2026-10-28T14:00:00Z")   # T8, P3, across DST end


def test_sla_p1_wallclock():
    assert_due(T1, 1, 1, "2026-10-14T10:15:00Z", "2026-10-14T14:00:00Z")   # T1
    assert_due(T3, 1, 1, "2026-10-16T15:15:00Z", "2026-10-16T19:00:00Z")   # T3, C1 = wallclock
    assert_due(T6, 1, 1, "2027-01-15T16:05:00Z", "2027-01-15T19:50:00Z")   # T6, C1 = wallclock


def test_breach_and_pause():
    ticket = create(2, 2, clock=T2)
    _, sla = call("GET", f"/tickets/{ticket['id']}/sla", clock="2026-10-19T09:30:00Z")
    assert sla["ack_breached"] is False, sla          # reaching the due instant is not a breach
    _, sla = call("GET", f"/tickets/{ticket['id']}/sla", clock="2026-10-19T09:31:00Z")
    assert sla["ack_breached"] is True and sla["resolve_breached"] is False, sla
    _, sla = call("GET", f"/tickets/{ticket['id']}/sla", clock=T4)
    assert sla["paused"] is True, sla
    p1 = create(1, 1, clock=T2)
    _, sla = call("GET", f"/tickets/{p1['id']}/sla", clock=T4)
    assert sla["paused"] is False, sla                # wall-clock P1 never pauses


def test_state_machine_and_shortcuts():
    ticket = create()
    for action in ("start", "resolve", "close", "reopen"):
        status, _ = call("POST", f"/tickets/{ticket['id']}/{action}")
        assert status == 409, (action, status)
    drive(ticket, "ack")
    assert call("POST", f"/tickets/{ticket['id']}/ack")[0] == 409
    assert call("POST", f"/tickets/{ticket['id']}/resolve")[0] == 409
    body = drive(ticket, "start", "resolve", "close", clock="2026-10-14T12:00:00Z")
    assert body["state"] == "closed" and body["closed_at"] == "2026-10-14T12:00:00Z", body


def test_reopen_window_and_closed_is_immutable():
    ticket = create()
    drive(ticket, "ack", "start", "resolve", clock=T1)
    status, body = call("POST", f"/tickets/{ticket['id']}/reopen", clock="2026-10-21T10:00:00Z")
    assert status == 200 and body["state"] == "in_progress" and body["resolved_at"] is None, body

    late = create()
    drive(late, "ack", "start", "resolve", clock=T1)
    assert call("POST", f"/tickets/{late['id']}/reopen", clock="2026-10-21T10:00:01Z")[0] == 409

    closed = create()
    drive(closed, "ack", "start", "resolve", "close", clock=T1)
    assert call("POST", f"/tickets/{closed['id']}/reopen", clock="2026-10-14T11:00:00Z")[0] == 409


def test_list_filters():
    p1, p4 = create(1, 1), create(3, 3)
    status, listed = call("GET", "/tickets?priority=P1")
    ids = {t["id"] for t in listed}
    assert status == 200 and p1["id"] in ids and p4["id"] not in ids
    _, new = call("GET", "/tickets?state=new")
    assert p4["id"] in {t["id"] for t in new}


# --- runner -----------------------------------------------------------------------------------------------------


def wait_for_service(seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if call("GET", "/health", clock=None)[0] == 200:
                return
        except OSError:
            pass
        time.sleep(1)


def main():
    wait_for_service()
    tests = [(name, fn) for name, fn in globals().items() if name.startswith("test_") and callable(fn)]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"PASS {name}")
        except Exception:
            failed += 1
            print(f"FAIL {name}")
            traceback.print_exc(file=sys.stdout)
    print(f"ITSMLAB-TESTS: passed={passed} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
