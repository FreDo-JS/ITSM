# ai-generated: 85% - Claude Code wrote the metric engine rule by rule from METRIC-SPEC.md; checked against metrics-practice.json
"""DORA delivery metrics over a supplied event log (METRIC-SPEC.md, rules R-01 to R-17).

A pure function: `compute(body)` takes the request body of POST /dora/metrics and returns the metric object,
or raises `LogError` for a request the specification says must be rejected (section 6).
"""

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from itertools import combinations

SPEC_VERSION = "1.0.0"
EVENT_TYPES = ("commit", "deployment", "incident")


class LogError(ValueError):
    pass


# --- parsing and validation (section 1, section 6) -------------------------------------------------------------


def instant(value, what: str) -> datetime:
    if not isinstance(value, str):
        raise LogError(f"{what} must be an RFC 3339 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise LogError(f"{what} is not an RFC 3339 instant: {value!r}")
    if parsed.tzinfo is None:
        raise LogError(f"{what} has no offset: {value!r}")
    return parsed.astimezone(timezone.utc)


def text(event: dict, field: str, nullable: bool = False):
    value = event.get(field)
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value:
        raise LogError(f"event {event.get('event_id')!r}: {field} must be a non-empty string")
    return value


def string_list(event: dict, field: str) -> list[str]:
    value = event.get(field)
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise LogError(f"event {event.get('event_id')!r}: {field} must be an array of strings")
    return value


def parse_window(body: dict) -> tuple[datetime, datetime]:
    window = body.get("window")
    if not isinstance(window, dict):
        raise LogError("window is required")
    start = instant(window.get("from"), "window.from")
    end = instant(window.get("to"), "window.to")
    if end <= start:
        raise LogError("window.to must be after window.from")
    return start, end


def parse_events(raw) -> tuple[dict, list, dict]:
    """Returns (commits by sha, deployments, incidents by id), after R-05 and the well-formedness rules."""
    if not isinstance(raw, list):
        raise LogError("events must be an array")

    seen_ids = set()
    commits: dict[str, dict] = {}
    deployments: list[dict] = []
    deployment_ids: set[str] = set()
    incidents: dict[str, dict] = {}

    for event in raw:
        if not isinstance(event, dict):
            raise LogError("every event must be an object")
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 64:
            raise LogError("event_id must be a string of 1 to 64 characters")
        if event_id in seen_ids:
            continue  # R-05: the first occurrence wins, later ones are ignored
        seen_ids.add(event_id)

        kind = event.get("type")
        if kind not in EVENT_TYPES:
            raise LogError(f"event {event_id!r}: unknown type {kind!r}")
        at = instant(event.get("at"), f"event {event_id!r} at")

        if kind == "commit":
            sha = text(event, "sha")
            if sha in commits:
                raise LogError(f"sha {sha!r} is not unique")
            if not isinstance(event.get("branch"), str):
                raise LogError(f"event {event_id!r}: branch must be a string")
            change_id = text(event, "change_id", nullable=True)
            reverts = text(event, "reverts", nullable=True)
            if (change_id is None) == (reverts is None):
                raise LogError(f"event {event_id!r}: a commit carries change_id exactly when reverts is null")
            commits[sha] = {"sha": sha, "at": at, "branch": event["branch"],
                            "change_id": change_id, "reverts": reverts}

        elif kind == "deployment":
            deployment_id = text(event, "deployment_id")
            if not isinstance(event.get("environment"), str):
                raise LogError(f"event {event_id!r}: environment must be a string")
            if event.get("outcome") not in ("success", "failure"):
                raise LogError(f"event {event_id!r}: outcome must be success or failure")
            if not isinstance(event.get("unplanned"), bool):
                raise LogError(f"event {event_id!r}: unplanned must be a boolean")
            deployments.append({
                "deployment_id": deployment_id, "at": at, "environment": event["environment"],
                "outcome": event["outcome"], "commits": string_list(event, "commits"),
                "unplanned": event["unplanned"], "caused_by": text(event, "caused_by", nullable=True),
            })
            deployment_ids.add(deployment_id)

        else:
            incident_id = text(event, "incident_id")
            phase = event.get("phase")
            if phase not in ("opened", "resolved"):
                raise LogError(f"event {event_id!r}: phase must be opened or resolved")
            incident = incidents.setdefault(incident_id, {"incident_id": incident_id, "opened": None,
                                                          "resolved": None, "deployments": set()})
            if incident[phase] is not None:
                raise LogError(f"incident {incident_id!r} carries more than one {phase} event")
            incident[phase] = at
            incident["deployments"].update(string_list(event, "deployments"))

    # Well-formedness: every reference names something present in the log.
    for commit in commits.values():
        if commit["reverts"] is not None and commit["reverts"] not in commits:
            raise LogError(f"commit {commit['sha']!r} reverts unknown sha {commit['reverts']!r}")
    for deployment in deployments:
        for sha in deployment["commits"]:
            if sha not in commits:
                raise LogError(f"deployment {deployment['deployment_id']!r} carries unknown sha {sha!r}")
        if deployment["caused_by"] is not None and deployment["caused_by"] not in incidents:
            raise LogError(f"deployment {deployment['deployment_id']!r} caused_by unknown incident")
    for incident in incidents.values():
        if incident["opened"] is None:
            raise LogError(f"incident {incident['incident_id']!r} resolved but never opened")
        for deployment_id in incident["deployments"]:
            if deployment_id not in deployment_ids:
                raise LogError(f"incident {incident['incident_id']!r} names unknown deployment {deployment_id!r}")

    return commits, deployments, incidents


# --- arithmetic (R-03, R-04) ------------------------------------------------------------------------------------


def seconds(later: datetime, earlier: datetime) -> Decimal:
    delta = later - earlier
    return Decimal(delta.days * 86400 + delta.seconds) + Decimal(delta.microseconds) / Decimal(1_000_000)


def whole(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def ratio(numerator: int | Decimal, denominator: int | Decimal) -> float | None:
    if not denominator:
        return None
    return float((Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def median(values: list[Decimal]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return whole(ordered[middle])
    return whole((ordered[middle - 1] + ordered[middle]) / 2)


def fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


# --- the metrics (sections 2 to 5) ------------------------------------------------------------------------------


def resolve_change(sha: str, commits: dict) -> str:
    """R-06: a revert inherits, transitively, the change_id of the commit it reverts."""
    seen = set()
    commit = commits[sha]
    while commit["change_id"] is None:
        if commit["sha"] in seen:
            raise LogError(f"revert cycle through sha {sha!r}")
        seen.add(commit["sha"])
        commit = commits[commit["reverts"]]
    return commit["change_id"]


def compute(body) -> dict:
    if not isinstance(body, dict):
        raise LogError("the request body must be a JSON object")
    start, end = parse_window(body)
    if "events" not in body:
        raise LogError("events is required")
    commits, deployments, incidents = parse_events(body["events"])

    change_of = {sha: resolve_change(sha, commits) for sha in commits}
    first_commit_at: dict[str, datetime] = {}
    for sha, commit in commits.items():
        change = change_of[sha]
        if change not in first_commit_at or commit["at"] < first_commit_at[change]:
            first_commit_at[change] = commit["at"]

    # R-01, R-02: production deployments inside [from, to); stable chronological order for "first".
    in_window = sorted(
        (d for d in deployments if d["environment"] == "production" and start <= d["at"] < end),
        key=lambda d: (d["at"], d["deployment_id"]),
    )
    successful = [d for d in in_window if d["outcome"] == "success"]
    failed = [d for d in in_window if d["outcome"] == "failure"]

    # R-08, R-09, R-10: one pair per sha at its first successful in-window production deployment.
    paired: dict[str, datetime] = {}
    for deployment in successful:
        for sha in deployment["commits"]:
            paired.setdefault(sha, deployment["at"])
    lead_times, negative_pairs = [], 0
    for sha, deployed_at in paired.items():
        lead = seconds(deployed_at, commits[sha]["at"])
        if lead < 0:
            negative_pairs += 1  # E1: clamped to zero and counted, never dropped
            lead = Decimal(0)
        lead_times.append(lead)

    # R-12, R-13: recovery per failed deployment, from its covering incident.
    recovery_times, open_failures = [], 0
    for deployment in failed:
        covering = [i for i in incidents.values() if deployment["deployment_id"] in i["deployments"]]
        covering.sort(key=lambda i: (i["opened"], i["incident_id"].encode()))
        if not covering or covering[0]["resolved"] is None:
            open_failures += 1  # E5: never invent a recovery time
            continue
        recovery = seconds(covering[0]["resolved"], deployment["at"])
        recovery_times.append(max(recovery, Decimal(0)))

    def interval_end(incident):
        return incident["resolved"] if incident["resolved"] is not None else end

    overlapping = sum(
        1 for a, b in combinations(incidents.values(), 2)
        if a["opened"] < interval_end(b) and b["opened"] < interval_end(a)
    )

    rework = [d for d in in_window if d["unplanned"] and d["caused_by"] is not None]
    off_main = {sha for d in in_window for sha in d["commits"] if commits[sha]["branch"] != "main"}

    # R-16, R-17: ground truth per change, from the change's earliest commit anywhere in the log.
    first_delivery: dict[str, datetime] = {}
    for deployment in successful:
        for sha in deployment["commits"]:
            first_delivery.setdefault(change_of[sha], deployment["at"])
    true_lead_times = [max(seconds(at, first_commit_at[change]), Decimal(0))
                       for change, at in first_delivery.items()]

    window_days = seconds(end, start) / Decimal(86400)
    return {
        "spec_version": SPEC_VERSION,
        "window": {"from": fmt(start), "to": fmt(end)},
        "deployment_frequency_per_day": ratio(len(in_window), window_days),
        "change_lead_time_seconds_p50": median(lead_times),
        "failed_deployment_recovery_time_seconds_p50": median(recovery_times),
        "change_fail_rate": ratio(len(failed), len(in_window)),
        "deployment_rework_rate": ratio(len(rework), len(in_window)),
        "counts": {
            "deployments": len(in_window),
            "successful_deployments": len(successful),
            "failed_deployments": len(failed),
            "recovered_failures": len(recovery_times),
            "open_failures": open_failures,
            "rework_deployments": len(rework),
            "lead_time_pairs": len(lead_times),
            "changes": len(first_commit_at),
        },
        "anomalies": {
            "negative_lead_time_pairs": negative_pairs,
            "deployments_without_commits": sum(1 for d in in_window if not d["commits"]),
            "commits_never_on_main": len(off_main),
            "revert_chains_collapsed": sum(1 for c in commits.values() if c["reverts"] is not None),
            "overlapping_incident_pairs": overlapping,
        },
        "ground_truth": {
            "changes_delivered": len(first_delivery),
            "true_change_lead_time_seconds_p50": median(true_lead_times),
        },
    }


# --- GET /dora/ticket-events (section 7) ------------------------------------------------------------------------

PHASES = (("created_at", "created", "new"), ("acknowledged_at", "acknowledged", "acknowledged"),
          ("resolved_at", "resolved", "resolved"), ("closed_at", "closed", "closed"))


def ticket_events(tickets: list[dict]) -> list[dict]:
    stream = []
    for ticket in tickets:
        for field, phase, state in PHASES:
            if ticket.get(field):
                stream.append({"ticket_id": ticket["id"], "at": ticket[field], "phase": phase,
                               "priority": ticket["priority"], "state": state})
    stream.sort(key=lambda e: (instant(e["at"], "at"), e["ticket_id"]))
    return stream
