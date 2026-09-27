<!-- ai-generated: 90% - Claude Code compared spec.md with src/ requirement by requirement; the owner reviewed the table -->

# Converge report - spec.md against the implementation (Lab 1)

A requirement-by-requirement comparison of `specs/001-svcdesk/spec.md` with what `src/svcdesk/` actually does,
checked against the running service by `src/tests/run.py` and by `itsmlab verify 1`.

| requirement | specification says | implementation | status |
|---|---|---|---|
| R-01 | JSON over HTTP on 8080 | FastAPI under uvicorn on 0.0.0.0:8080; every response is JSON, errors included | converged |
| R-02 | `GET /health` -> `{"status":"ok","service":"svcdesk"}` | `main.health` | converged |
| R-03 | ticket fields and their limits | `main.validate_create`: title 1..200, description <= 4000, reporter.name 1..100, email, vip, related_to | converged |
| R-04 | impact x urgency matrix | `sla.MATRIX`, all nine cells tested | converged |
| R-05 / R-06 | C3 = `vip`: matrix first, VIP at P3/P4 raised to P2 | `sla.compute_priority`; a `priority` in the body is ignored | converged |
| R-07 / R-08 | fixed lifecycle, 409 on any other transition, 404 on unknown id | `main.transition` checks the one allowed source state per action | converged |
| R-09 / R-10 | C2 = `immutable`: reopen from `resolved` only | `main.reopen` answers 409 `ticket_closed` for every closed ticket | converged |
| R-11 | 7-day window, target not extended | `now <= resolved_at + 7 days`; `sla` block never rewritten | converged |
| R-12 | targets per priority | `sla.TARGETS` | converged |
| R-13 / R-14 | C1 = `wallclock`: P1 around the clock, P2-P4 business hours | `sla.due_instants` and `sla.business_due` (tie rule at 16:00, DST via zoneinfo); T1-T8 reproduced | converged |
| R-15 / R-16 | `/sla` with breach flags and pause | `main.get_sla`; equality is not a breach; wall-clock P1 never pauses | converged |
| R-17 | UTC instants with `Z` | `main.fmt` | converged |
| R-18 | opaque unique id | UUID4 | converged |
| R-19 | list with exact-match filters | `main.list_tickets` | converged |
| R-20 | 400/422 with `error`; server-owned and unknown fields ignored | 422 `validation`; only known client fields are read | converged |
| R-21 | per-request `X-Test-Clock` | `main.now`; malformed or offset-less header is 400 | converged |
| R-22 / R-24 | compose contract, healthy within 120 s | `docker-compose.yml` with `build: .`, named volume, healthcheck | converged |
| R-23 | tickets survive a restart | SQLite at `/data/svcdesk.db` on the named volume `svcdesk-data` | converged |
| R-25 | JSON 404 for unknown paths and ids | Starlette HTTP errors rewritten to `{"error": {...}}` | converged |

No remediation tasks remain. The one point the specification leaves open, validating that `related_to` names an
existing ticket, stays out of scope for Lab 1 as spec.md states.
