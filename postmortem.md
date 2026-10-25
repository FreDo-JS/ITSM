---
lab4_postmortem:
  ticket: "1224ad8d-06a8-4ae3-865a-da2015a4ddb5"
  detecting_alert: ShopCheckoutErrors
  onset: 2026-10-12T07:05:45Z
  detection: 2026-10-12T07:09:19Z
  acknowledgement: 2026-10-12T07:10:07Z
  recovery: 2026-10-12T07:12:19Z
  mttd_seconds: 214
  mtta_seconds: 48
  mttr_seconds: 394
  identified_flags: [productCatalogFailure, adManualGc, recommendationCacheFailure]
---
<!-- ai-generated: 70% - Claude Code drafted the postmortem from the lab4-rec-3 recording's metrics and the instants of `itsmlab incident 4`; the analysis was reviewed by the repository owner -->

# Postmortem: orders failed at checkout and shop pages slowed to a second, 2026-10-12

## Date

The incident happened on Monday 12 October 2026 between 07:05 and 07:14 UTC. This postmortem was written on
25 October 2026 from the recording of that run (`lab4-rec-3`), on the recorded path of Lab 4.

## Authors

Written by the repository owner (FreDo-JS) in the role of the on-call engineer working the recorded incident, with
Claude Code as an assistant for the queries and the first draft.

## Status

Complete for the incident: service was restored at 07:13:25 UTC. The problem record stays open, and the action items
below are not yet done.

## Summary

For eight minutes three feature flags failed together. Product-catalog answered about one GetProduct call in ten with
an error, so a few orders failed at checkout; the ad service stalled in garbage collection, so every shop page that
shows an ad slowed from about 50 ms to about 0.9 s at the 99th percentile; and the recommendation service started to
grow its cache. The page `ShopCheckoutErrors` fired 3 min 34 s after the onset, the P1 ticket was acknowledged 48 s
after the page, and all three flags were switched off at 07:13:25.

## Impact

Between 07:06 and 07:13 checkout answered about 50 PlaceOrder requests and failed about 2.3 of them, 4.5 % of orders
(`sum(increase(traces_span_metrics_calls_total{service_name="checkout", span_name="oteldemo.CheckoutService/PlaceOrder", status_code="STATUS_CODE_ERROR"}[7m]))`
at 07:13 against the same without the status filter). Product-catalog failed about 42 GetProduct calls in the same
window, up to 0.15 per second, against none on the baseline; the frontend shows those as product pages that fail.
The frontend's p99 latency rose from 47 ms on the baseline to 919 ms at 07:11, and the ad service's from 5.6 ms to
796 ms (`histogram_quantile(0.99, sum by (service_name, le) (rate(traces_span_metrics_duration_milliseconds_bucket{span_kind="SPAN_KIND_SERVER"}[5m])))`).
Traffic stayed at about 4 frontend requests per second throughout: the shop was up, but slow, and some orders failed.

## Root Causes

Three independent defects that the feature flags expose. Product-catalog returns an error for one product in ten when
`productCatalogFailure` is on, and checkout has no fallback for a failed GetProduct: the whole order fails. The ad
service runs a manual full garbage collection on the request path under `adManualGc`, so its latency spikes block
the frontend, which waits for ads synchronously before it renders a page. The recommendation service's cache stops
evicting under `recommendationCacheFailure`, so its memory only grows.

## Trigger

The fault injector switched three flags on at 07:05:45 UTC, one from each class: an error flag, a latency flag and a
resource flag. Nothing else changed: no deployment, and no change in traffic.

## Resolution

The on-call switched the failing flags off through the injector (`POST /flags/<flag>/off`), the workaround; the
injector's fault ended at 07:13:25, when `seeded_fault_active` fell to 0. Checkout's errors stopped at once, and the
frontend's latency fell back to its baseline once the 5-minute windows had slid past the fault.

## Detection

`ShopCheckoutErrors` (P1, more than 2 % of checkout's requests failing over 5 minutes) detected the fault at
07:09:19, 214 s after the onset: the shop's span metrics arrive once a minute, and a 5-minute ratio needs three or
four of those samples before it crosses 2 %. It paged the on-call through the `pager` route. Without it the first
people to notice would have been shoppers whose orders failed, or the ad team hours later. Our own rules in
`prometheus/demo-alerts.yml` would also have raised `ShopFrontendLatency` (P2) on the frontend's 0.9 s p99, which
the lecturer's rule set did not watch.

## Action Items

| Action Item | Type | Owner | Bug |
|---|---|---|---|
| Page on checkout latency as well as errors (`ShopCheckoutLatency`), so a latency-only fault pages too | prevent | on-call team | ITSM-101 |
| Retry or skip one failed GetProduct in checkout instead of failing the whole order | prevent | checkout team | ITSM-102 |
| Load ads asynchronously in the frontend with a 200 ms budget, so a slow ad service cannot slow every page | mitigate | frontend team | ITSM-103 |
| Remove the manual GC call from the ad service's request path | prevent | ad team | ITSM-104 |
| Alert in chat on recommendation memory growth over 30 minutes | process | on-call team | ITSM-105 |

## Lessons Learned

### What went well

The page fired within four minutes and the ticket was acknowledged 48 s after it. Switching the flags off restored
the shop at once, without a deployment.

### What went wrong

The detecting alert resolved at 07:12:19, a minute before the last flag went off, because checkout's error ratio fell
below 2 % while ad latency was still high: the recovery the clocks report is not the end of the fault. Nothing paged
on the shop's slow pages, which affected every shopper, not only the few failed orders.

### Where we got lucky

Only one product in ten failed, so most orders still went through, and the recommendation leak was switched off long
before it could exhaust memory.

## Timeline

All times UTC, 12 October 2026.

- 06:55:45 - the injector's baseline is complete; no P1 is firing.
- 07:05:45 - onset: the three flags switch on (`seeded_fault_active` = 1).
- 07:06 - product-catalog starts failing GetProduct; ad latency spikes.
- 07:09:19 - detection: `ShopCheckoutErrors` (P1) starts firing; the pager receives the page.
- 07:09:37 - the on-call opens P1 ticket 1224ad8d-06a8-4ae3-865a-da2015a4ddb5.
- 07:10:00 - `ShopServiceErrors` (P2) fires for four label sets (the per-service error symptoms), a minute after the page.
- 07:10:07 - acknowledgement of the P1 ticket.
- 07:11 - the investigation sees product-catalog's errors and ad's 0.8 s p99; ledger H2 (`product-catalog` GetProduct errors > 0.01/s, true at 07:11:00) confirms the catalog, H3 (payment errors > 2 %, false) rules payment out.
- 07:12:19 - recovery: `ShopCheckoutErrors` resolves (end of its firing run).
- 07:13:25 - the last flag is off; `seeded_fault_active` = 0.

## Supporting information

The Prometheus snapshot `incident/tsdb-snapshot.tar.gz` and the ticket `incident/ticket.json` (recording
`lab4-rec-3`); the AI ledger `ai-rca-eval.json` with the investigator's transcript `ai-rca/transcript.md`; our alert
rules `prometheus/demo-alerts.yml` and routing tree `alertmanager/alertmanager.yml`.

## Problem record

Incident record: 1224ad8d-06a8-4ae3-865a-da2015a4ddb5 (P1, acknowledged at 07:10:07, service restored at 07:13:25)
Root cause: checkout fails a whole order on one failed GetProduct, and the frontend waits synchronously on a slow ad service
Known error: product-catalog intermittently fails GetProduct and ad latency spikes under GC, both propagating to shoppers unguarded
Workaround: switch the failing feature flags off through the injector; no code change is needed to restore service
