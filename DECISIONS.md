---
svcdesk_decisions:
  C1: wallclock      # wallclock | business
  C2: immutable      # reopen | immutable
  C3: vip            # matrix | vip
---
<!-- ai-generated: 80% - Claude Code drafted the reasoning from REQUIREMENTS.md/API.md, the repository owner reviewed and confirmed each decision -->

# Decisions

## C1 - SLA clock for P1

**Decision:** Both the acknowledge and the resolve target of a P1 ticket run on the wall-clock: `created_at + target`, never paused, day or night. Every other priority (P2-P4) runs on the business-hours clock (Monday-Friday, 08:00-16:00 Europe/Warsaw).

**Rejected alternative:** Every priority, including P1, pauses outside business hours (R-13 read literally, with no exception for P1).

**Reason:** R-14 gives the worked example directly: "a P1 raised on Friday evening is late at 15 minutes past, not on Monday morning." A whole-organisation outage does not become less urgent because it is 18:00; the desk needs to page someone regardless of the calendar, so R-13's general pause rule cannot survive for the priority it would matter for least.

**Service owner:** The on-call incident manager, because they are the one paged against the P1 clock and the one who has to explain a breach to the business; they are the role with standing to say the clock never stops for P1.

**Customer outcome:** A reporter of an organisation-wide outage gets a resolution promise measured in real elapsed hours, not business hours stretched across a weekend, which is what "P1" is supposed to mean to them.

## C2 - Closed tickets and reopening

**Decision:** Reopen is accepted only from `resolved`, within 7 days of `resolved_at`. A `closed` ticket always answers 409 on reopen, at any age; further work on the same issue is a new ticket that references the closed one via `related_to`.

**Rejected alternative:** A closed ticket can also be reopened within 7 days of `closed_at` (R-10 read literally, including "or closed").

**Reason:** R-09 states plainly that "a closed ticket is immutable," and closing is the step where the reporter has confirmed the fix worked; treating it as reopenable anyway would make the closed state mean nothing and would corrupt the Monday report's count of genuinely finished work. R-10's "or closed" is the side of this pair this build does not keep.

**Service owner:** The service desk manager, because immutability of `closed` is what makes the weekly closed-ticket count trustworthy for reporting to the business, and they own that report.

**Customer outcome:** A reporter who confirmed the fix and later hits a new instance of the same problem opens a fresh, clearly linked ticket instead of resurrecting a closed record whose SLA clock and history no longer describe the new problem.

## C3 - VIP reporters and the priority matrix

**Decision:** The impact/urgency matrix decides first; a VIP ticket that lands at P3 or P4 is then raised to P2. A VIP ticket already at P1 or P2 is unchanged.

**Rejected alternative:** Priority is the matrix value alone in every case, and `reporter.vip` is stored but never changes it (R-05 read literally: "from nothing else").

**Reason:** R-06 is explicit and specific: VIP tickets are "never lower than P2, whatever the matrix says, so that executive issues are visible to the desk immediately." That sentence only has content if VIP can override the matrix; R-05's "nothing else" is the general rule this one named exception overrides.

**Service owner:** The service desk manager, because visibility of executive-reported issues to the desk is an escalation-policy call, not an engineering default, and it is theirs to defend to the business.

**Customer outcome:** A VIP reporter whose problem is technically minor (impact 3, urgency 3) still gets a P2 response, so an executive is never left waiting on a queue sized for a cosmetic ticket.
