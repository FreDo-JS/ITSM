---
lab4_comms:
  awareness: 2026-10-12T07:15:00Z
  detection: 2026-10-12T07:09:19Z
  classification: 2026-10-12T07:40:00Z
  nis2:
    early_warning_due: 2026-10-13T07:15:00Z
    notification_due: 2026-10-15T07:15:00Z
    notification_sent: 2026-10-13T09:00:00Z
    final_report_due: 2026-11-13T09:00:00Z
  ksc:
    early_warning_due: 2026-10-13T07:09:19Z
    notification_due: 2026-10-15T07:09:19Z
    notification_sent: 2026-10-13T09:00:00Z
    final_report_due: 2026-11-13T09:00:00Z
  dora:
    initial_due: 2026-10-12T11:40:00Z
    initial_sent: 2026-10-12T11:00:00Z
    intermediate_due: 2026-10-15T11:00:00Z
    intermediate_sent: 2026-10-14T10:00:00Z
    final_due: 2026-11-14T10:00:00Z
  log:
    - {at: 2026-10-12T07:20:00Z, to: the CSIRT (NIS2 and KSC), what: early warning of a significant incident affecting online orders}
    - {at: 2026-10-12T11:00:00Z, to: the financial supervisor (DORA), what: initial notification of a major ICT-related incident}
    - {at: 2026-10-13T09:00:00Z, to: the CSIRT (NIS2 and KSC), what: incident notification with impact, root cause and workaround}
    - {at: 2026-10-14T10:00:00Z, to: the financial supervisor (DORA), what: intermediate report}
---
<!-- ai-generated: 75% - Claude Code drafted the instants and did the deadline arithmetic in UTC; the choice of instants was reviewed by the repository owner -->

# Communications log: the regulators' clocks

The shop is treated as an entity that NIS2, the Polish KSC act and DORA all apply to; the incident of
`postmortem.md` (12 October 2026) is taken as significant under the first two and major under DORA. Every instant
is UTC.

## The three instants you defend

**Detection (KSC), 07:09:19Z.** KSC counts "od momentu jego wykrycia", from the moment the incident was detected.
That is the instant our monitoring detected it: the P1 page `ShopCheckoutErrors` started firing at 07:09:19, the
detection of `itsmlab incident 4`. The clock does not wait for a human to read the page.

**Awareness (NIS2), 07:15:00Z.** NIS2 counts from "becoming aware" of a *significant* incident, which needs a
judgement, not only an alert. At 07:10:07 the on-call acknowledged the page, by 07:13:25 the flags were off, and at
07:15 the impact was clear: orders had failed at checkout for seven minutes and every shop page had slowed to a
second. That is when the incident was judged significant.

**Classification (DORA), 07:40:00Z.** The classification as major under the DORA criteria (clients affected,
duration, service criticality) was made in the incident review 25 minutes after awareness, once the number of failed
orders (about 2.3 of 50) and the eight-minute duration had been counted from the metrics.

## The arithmetic

- NIS2: early warning due 07:15 + 24 h = 2026-10-13T07:15:00Z; notification due + 72 h = 2026-10-15T07:15:00Z;
  notification sent 2026-10-13T09:00:00Z, so the final report is due a calendar month later, 2026-11-13T09:00:00Z.
- KSC: the same from detection: 2026-10-13T07:09:19Z and 2026-10-15T07:09:19Z; notification sent with the NIS2 one,
  final report due 2026-11-13T09:00:00Z.
- DORA: classified within 24 h of awareness, so the initial notification is due at the earlier of classification +
  4 h (11:40Z) and awareness + 24 h (next day 07:15Z): 2026-10-12T11:40:00Z. Sent at 11:00Z, so the intermediate
  report is due 72 h later, 2026-10-15T11:00:00Z; sent 2026-10-14T10:00:00Z, so the final report is due
  2026-11-14T10:00:00Z.

## The log

| when (UTC) | to | what | which clock |
|---|---|---|---|
| 2026-10-12 07:20 | the CSIRT | early warning: significant incident affecting online orders | NIS2 and KSC early warning, well inside 24 h |
| 2026-10-12 11:00 | the financial supervisor | initial notification of a major ICT-related incident | DORA initial, 40 min before its deadline |
| 2026-10-13 09:00 | the CSIRT | incident notification: impact, root cause, workaround | NIS2 and KSC notification, inside 72 h |
| 2026-10-14 10:00 | the financial supervisor | intermediate report | DORA intermediate, a day before its deadline |
