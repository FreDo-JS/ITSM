# ai-generated: 90% - Claude Code wrote the HTTP layer from API.md; the owner checked it against CHECKS.md
"""svcdesk HTTP API (API.md sections 1, 2, 6, 7 and 8).

Decision C2 = immutable lives here: reopen is accepted from `resolved` only; a closed ticket answers 409.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import dora
from .sla import compute_priority, due_instants, in_business_hours, uses_wallclock
from .store import open_store

REOPEN_WINDOW = timedelta(days=7)
TEST_CLOCK_ENABLED = os.environ.get("SVCDESK_TEST_CLOCK", "").strip().lower() in ("1", "true")

app = FastAPI(title="svcdesk")
store = open_store()


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError):
    return JSONResponse(error_body(exc.code, exc.message), status_code=exc.status)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, exc: StarletteHTTPException):
    code = "not_found" if exc.status_code == 404 else "http_error"
    return JSONResponse(error_body(code, str(exc.detail)), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(error_body("validation", str(exc.errors())), status_code=422)


# --- time -------------------------------------------------------------------------------------------------------


def fmt(instant: datetime | None) -> str | None:
    if instant is None:
        return None
    return instant.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def now(request: Request) -> datetime:
    """The clock of this request only (API.md section 8)."""
    header = request.headers.get("x-test-clock")
    if TEST_CLOCK_ENABLED and header is not None:
        try:
            instant = datetime.fromisoformat(header.strip())
        except ValueError:
            raise ApiError(400, "validation", "X-Test-Clock is not an RFC 3339 instant")
        if instant.tzinfo is None:
            raise ApiError(400, "validation", "X-Test-Clock must carry an offset")
        return instant.astimezone(timezone.utc)
    return datetime.now(timezone.utc).replace(microsecond=0)


# --- validation -------------------------------------------------------------------------------------------------


def invalid(message: str) -> ApiError:
    return ApiError(422, "validation", message)


def is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_create(body) -> dict:
    if not isinstance(body, dict):
        raise invalid("request body must be a JSON object")

    title = body.get("title")
    if title is None:
        raise invalid("title is required")
    if not isinstance(title, str) or not 1 <= len(title) <= 200:
        raise invalid("title must be a string of 1 to 200 characters")

    description = body.get("description", "")
    if description is None:
        description = ""
    if not isinstance(description, str) or len(description) > 4000:
        raise invalid("description must be a string of at most 4000 characters")

    reporter = body.get("reporter")
    if not isinstance(reporter, dict):
        raise invalid("reporter is required")
    name = reporter.get("name")
    if not isinstance(name, str) or not 1 <= len(name) <= 100:
        raise invalid("reporter.name must be a string of 1 to 100 characters")
    email = reporter.get("email")
    if email is not None and not isinstance(email, str):
        raise invalid("reporter.email must be a string or null")
    vip = reporter.get("vip", False)
    if vip is None:
        vip = False
    if not isinstance(vip, bool):
        raise invalid("reporter.vip must be a boolean")

    for field in ("impact", "urgency"):
        value = body.get(field)
        if value is None:
            raise invalid(f"{field} is required")
        if not is_int(value) or not 1 <= value <= 3:
            raise invalid(f"{field} must be an integer from 1 to 3")

    related_to = body.get("related_to")
    if related_to is not None and not isinstance(related_to, str):
        raise invalid("related_to must be a string or null")

    return {
        "title": title,
        "description": description,
        "reporter": {"name": name, "email": email, "vip": vip},
        "impact": body["impact"],
        "urgency": body["urgency"],
        "related_to": related_to,
    }


# --- tickets ----------------------------------------------------------------------------------------------------


def load(ticket_id: str) -> dict:
    ticket = store.get(ticket_id)
    if ticket is None:
        raise ApiError(404, "not_found", f"ticket {ticket_id} not found")
    return ticket


def conflict(ticket: dict, action: str, code: str = "invalid_transition") -> ApiError:
    return ApiError(409, code, f"cannot {action} a ticket in state {ticket['state']}")


@app.get("/health")
def health():
    return {"status": "ok", "service": "svcdesk"}


@app.post("/tickets", status_code=201)
async def create_ticket(request: Request):
    at = now(request)
    try:
        body = await request.json()
    except ValueError:
        raise invalid("request body must be valid JSON")
    fields = validate_create(body)

    priority = compute_priority(fields["impact"], fields["urgency"], fields["reporter"]["vip"])
    ack_due, resolve_due = due_instants(priority, at)
    ticket = {
        "id": str(uuid.uuid4()),
        **fields,
        "priority": priority,
        "state": "new",
        "created_at": fmt(at),
        "acknowledged_at": None,
        "resolved_at": None,
        "closed_at": None,
        "sla": {"ack_due_at": fmt(ack_due), "resolve_due_at": fmt(resolve_due)},
    }
    store.put(ticket)
    return ticket


@app.get("/tickets")
def list_tickets(state: str | None = None, priority: str | None = None):
    return [
        t for t in store.all()
        if (state is None or t["state"] == state) and (priority is None or t["priority"] == priority)
    ]


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    return load(ticket_id)


@app.get("/tickets/{ticket_id}/sla")
def get_sla(ticket_id: str, request: Request):
    ticket = load(ticket_id)
    at = now(request)
    ack_due = parse(ticket["sla"]["ack_due_at"])
    resolve_due = parse(ticket["sla"]["resolve_due_at"])
    acknowledged_at = parse(ticket["acknowledged_at"])
    resolved_at = parse(ticket["resolved_at"])
    is_open = ticket["state"] not in ("resolved", "closed")

    return {
        "priority": ticket["priority"],
        "ack_due_at": ticket["sla"]["ack_due_at"],
        "resolve_due_at": ticket["sla"]["resolve_due_at"],
        "ack_breached": (acknowledged_at > ack_due) if acknowledged_at else at > ack_due,
        "resolve_breached": (resolved_at > resolve_due) if resolved_at else at > resolve_due,
        "paused": is_open and not uses_wallclock(ticket["priority"]) and not in_business_hours(at),
    }


def transition(ticket_id: str, request: Request, action: str, source: str, target: str, stamp: str | None):
    ticket = load(ticket_id)
    at = now(request)
    if ticket["state"] != source:
        raise conflict(ticket, action)
    ticket["state"] = target
    if stamp:
        ticket[stamp] = fmt(at)
    store.put(ticket)
    return ticket


@app.post("/tickets/{ticket_id}/ack")
def ack(ticket_id: str, request: Request):
    return transition(ticket_id, request, "acknowledge", "new", "acknowledged", "acknowledged_at")


@app.post("/tickets/{ticket_id}/start")
def start(ticket_id: str, request: Request):
    return transition(ticket_id, request, "start", "acknowledged", "in_progress", None)


@app.post("/tickets/{ticket_id}/resolve")
def resolve(ticket_id: str, request: Request):
    return transition(ticket_id, request, "resolve", "in_progress", "resolved", "resolved_at")


@app.post("/tickets/{ticket_id}/close")
def close(ticket_id: str, request: Request):
    return transition(ticket_id, request, "close", "resolved", "closed", "closed_at")


@app.post("/dora/metrics")
async def dora_metrics(request: Request):
    """Lab 2: a pure function of the request body (METRIC-SPEC.md section 6); nothing is stored."""
    try:
        body = await request.json()
    except ValueError:
        raise invalid("request body must be valid JSON")
    try:
        return dora.compute(body)
    except dora.LogError as exc:
        raise invalid(str(exc))


@app.get("/dora/ticket-events")
def dora_ticket_events():
    """Lab 2: every lifecycle instant of every ticket, ordered by (at, ticket_id) (METRIC-SPEC.md section 7)."""
    return dora.ticket_events(store.all())


@app.post("/tickets/{ticket_id}/reopen")
def reopen(ticket_id: str, request: Request):
    ticket = load(ticket_id)
    at = now(request)
    if ticket["state"] == "closed":
        # C2 = immutable (R-09 over R-10): a closed ticket is never reopened; open a new one with related_to.
        raise conflict(ticket, "reopen", "ticket_closed")
    if ticket["state"] != "resolved":
        raise conflict(ticket, "reopen")
    if at > parse(ticket["resolved_at"]) + REOPEN_WINDOW:
        raise ApiError(409, "reopen_window_expired", "the 7-day reopen window has passed")
    # R-11: resolve_due_at is left as it was; reopening never extends the target.
    ticket["state"] = "in_progress"
    ticket["resolved_at"] = None
    ticket["closed_at"] = None
    store.put(ticket)
    return ticket
