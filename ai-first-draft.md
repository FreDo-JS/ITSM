---
lab3_first_draft:
  source: ai
  tool: "Claude Code (Claude Opus 5.5) in the Claude desktop app, 12 October 2026"
  ladder: [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1, 2, 5]
  verdict: refuted
  evidence: {p99_seconds: 0.184, bucket: [0.15, 0.2], relative_width: 0.272}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: 0.184, bucket: [0.04, 0.5], relative_width: 2.500}
---
<!-- ai-generated: 90% - the answer is Claude Code's, given before any measurement; Claude Code also wrote the verdicts from our `itsmlab load 3` runs, reviewed by the repository owner -->

# The assistant's first draft, and two verdicts

The assistant was asked first, before `kb-index` was measured or any ladder designed; its answer is quoted below
exactly as given.

## Prompt

I am adding a knowledge-base search endpoint, GET /kb/search, to a FastAPI service (svcdesk). Every request calls
an upstream search index over HTTP once. I am instrumenting it with a Prometheus histogram
http_server_request_duration_seconds (labels http_request_method, http_route, http_response_status_code).
Before I have measured anything: propose histogram bucket boundaries in seconds for this endpoint, and a
Prometheus alerting rule for it.

## Answer

> For an endpoint whose latency is dominated by one upstream HTTP call, a sensible starting ladder is denser than
> the client library's default between 50 ms and 1 s, where a search backend usually lives, and keeps a few coarse
> buckets above for timeouts:
>
>     buckets = [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1, 2, 5]
>
> Fourteen boundaries keep the series count low (14 buckets + `+Inf` + `_sum` + `_count` per label set). Once you
> have real traffic, look at where your p95/p99 fall and add boundaries around them.
>
> For alerting, use an error-ratio SLO alert rather than a raw latency threshold, with a long and a short window so
> that it both catches sustained burns and recovers quickly:
>
>     - alert: KbSearchHighErrorRate
>       expr: |
>         (
>           sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search", http_response_status_code=~"5.."}[1h]))
>           /
>           sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search"}[1h]))
>         ) > 14.4 * (1 - 0.99)
>         and
>         (
>           sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search", http_response_status_code=~"5.."}[5m]))
>           /
>           sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search"}[5m]))
>         ) > 14.4 * (1 - 0.99)
>       for: 2m
>       labels:
>         severity: page
>       annotations:
>         summary: "/kb/search is burning its 99% availability budget 14.4x too fast"
>
> 14.4 is the SRE Workbook's fast-burn rate for a 30-day window: at that rate 2 % of the monthly budget is gone in
> one hour. Pair it with a slower ticket-level alert (for example burn rate 6 over 6h and 30m).

## Verdict on the draft ladder

Our measured p99 is **0.184 s** (`itsmlab load 3`, second run, 2,398 responses; the first run gave 0.199 s). In the
draft ladder `[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1, 2, 5]` it falls in the bucket
**(0.15, 0.2]**, which is 0.05 s wide: 0.05 / 0.184 = **27.2 %** of the p99, above the 20 % M-11 allows. The first
run's 0.199 s sits in the same bucket at 25.1 %, and anything from 0.2 s up lands in (0.2, 0.3], which is 50 % of q.

`histogram_quantile` assumes the requests in a bucket are spread evenly, so from (0.15, 0.2] it can report any p99
between 150 and 200 ms, a 50 ms spread on a 184 ms number, and a p99 just above 0.2 s could be reported anywhere up
to 300 ms. The draft was the right shape - denser between 50 ms and 1 s than the library default - but it put one
boundary every 50 to 100 ms exactly where our slow mode lives. Verdict: **refuted**.

## The draft alert rule

The draft rule was already a multiwindow burn-rate alert (14.4 over 1h and 5m on the 5xx ratio of `/kb/search`),
and we kept its structure and its numbers for `KbSearchErrorsBurnFast`. We changed three things: it selected no
`job`, so we added `job="svcdesk"` to match the scrape job the SLO queries use; it carried `severity: page`, which
Lab 4's routing does not know, so it became `severity: P1` with the `service` and `slo` labels M-17 requires; and we
kept its suggested slower companion (6 over 6h and 30m) as `KbSearchErrorsBurnSlow`, at P2, to chat. Its `for: 2m`
stayed: it keeps a single bad scrape from paging and gives the mutation tests a `for` to shift.

## Verdict on the instructor's flawed ladder

The flawed ladder spends twelve of its fourteen boundaries below 40 ms - where our p50 (40 to 43 ms) sits, so the
median is well resolved - and then jumps to 0.5 s. Our p99 of **0.184 s** falls in **(0.04, 0.5]**, 0.46 s wide:
0.46 / 0.184 = **250 %** of the p99. From that bucket `histogram_quantile` could report anything between 40 ms and
half a second, so the dashboard's p99 would be meaningless, and a latency threshold anywhere in the slow mode could
not be a boundary at all. Verdict: **refuted**, as for every profile of this lab.
