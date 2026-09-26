<!-- ai-generated: 85% - Claude Code drafted this spec from REQUIREMENTS.md/API.md/CHECKS.md; the three decisions and their justification were reviewed and confirmed by the repository owner -->

# svcdesk - specification (Lab 1)

## Purpose

A minimal HTTP service desk API for about 400 people in three offices. It replaces a spreadsheet: it computes
ticket priority, tracks SLA clocks, drives tickets through a fixed lifecycle, and refuses actions that would
make the Monday SLA report wrong. Scope: Lab 1 only (R-01 to R-25 of REQUIREMENTS.md; the exact wire contract is
API.md, which wins wherever the two differ).

## Interface

JSON over HTTP on port 8080 (R-01):

- `GET /health` -> `{"status": "ok", "service": "svcdesk"}` (R-02)
- `POST /tickets` -> create a ticket (R-03, R-04, R-05, R-06, R-20)
- `GET /tickets` (optional `?state=` and `?priority=` exact-match filters) -> all matching tickets, no pagination (R-19)
- `GET /tickets/{id}` -> a single ticket, 404 if unknown (R-25)
- `GET /tickets/{id}/sla` -> priority, both due instants, both breach flags, and whether the ticket is paused (R-15, R-16)
- `POST /tickets/{id}/ack|start|resolve|close|reopen` -> the state machine below, 409 on any other transition, 404 if unknown (R-07, R-08)

Unknown fields and server-owned fields in a request body (`id`, `priority`, `state`, timestamps, `sla`) are
silently ignored (R-20). Validation failures return 400/422 with a top-level `error` object.

## Data model

A ticket carries: `id` (opaque, server-assigned, unique), `title` (1-200 chars), `description` (0-4000 chars,
optional), `reporter` (`name` 1-100 chars, optional `email`, optional `vip` default false), `impact` and
`urgency` (each 1-3), a server-computed `priority`, `state`, the four event timestamps (`created_at`,
`acknowledged_at`, `resolved_at`, `closed_at`, null until the event happens), an optional `related_to`, and an
`sla` block (`ack_due_at`, `resolve_due_at`) fixed at creation time (R-03, R-18, R-23).

## Priority

Computed once, at creation, from impact and urgency via the matrix in R-04/API.md §3, and from nothing else a
client can set (R-05). `priority` in a request body is ignored (R-05, check 2.48).

## State machine

`new -> acknowledged -> in_progress -> resolved -> closed`, one action per transition
(`ack`, `start`, `resolve`, `close`), each stamping its own timestamp (R-07). Any other transition - including
skipping a state - is 409 (R-08). Actions on an unknown id are 404.

## Test clock

When `SVCDESK_TEST_CLOCK` is `1`/`true`, any request to an endpoint that consumes "now" (create, the five
transition actions, `GET /tickets/{id}/sla`) may carry `X-Test-Clock` with an RFC 3339 instant that is "now" for
that request only; a header that fails to parse, or carries no offset, is 400/422 (R-21, API.md §8). `GET
/tickets` and `GET /tickets/{id}` read no clock, so the header is irrelevant there.

## The three contradictions and this service's resolution

REQUIREMENTS.md contains three pairs that cannot both hold in full. Each is resolved below; `DECISIONS.md` is
the defended, authoritative record - this section states only which side this build takes, so the two documents
agree by construction.

**C1 - the SLA clock for P1** (R-13 "clocks pause outside business hours" vs. R-14 "P1 ... around the clock").
This build takes `wallclock`: **P1's** acknowledge and resolve targets are `created_at + target`, never paused;
every other priority's targets run on the business-hours clock (Mon-Fri, 08:00-16:00 Europe/Warsaw, DST-aware),
computed by consuming the target across consecutive business windows, with the tie rule that a target ending
exactly at closing is due at that closing instant, not the next opening (API.md §4).

**C2 - closed tickets and reopening** (R-09 "a closed ticket is immutable" vs. R-10 "reporter may reopen a
resolved **or closed** ticket"). This build takes `immutable`: reopen is accepted only from `resolved`, within 7
days of `resolved_at`; a `closed` ticket always answers 409 on reopen, whatever its age, and further work on the
same issue is a new ticket referencing it via `related_to` (API.md §6).

**C3 - VIP reporters and the priority matrix** (R-05 "priority ... from nothing else" vs. R-06 "VIP ... never
lower than P2"). This build takes `vip`: the matrix decides first, then a VIP ticket computed at P3 or P4 is
raised to P2; a VIP ticket already at P1 or P2 is unchanged (API.md §3).

## Persistence

Tickets are kept in a SQLite file inside a named Docker volume, so they survive a container restart (R-23);
not exercised by the Lab 1 Tier A checker (API.md §10), but required by R-23 and relevant from Lab 2 on.

## Out of scope for Lab 1

Validating that `related_to` names an existing ticket (R-03 says "not validated in Lab 1"); authentication;
pagination; any storage engine beyond a single SQLite file.
