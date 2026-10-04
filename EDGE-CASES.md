---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 2}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
<!-- ai-generated: 75% - Claude Code drafted the sections from the practice log and METRIC-SPEC.md; the counts are what our own POST /dora/metrics returns -->

# Edge cases in the practice event log

Every count above is the value `POST /dora/metrics` of this repository returns for
`fixtures/events-practice.jsonl` over the published window (the same object is committed as `metrics.json`).

## E1 - clock skew produces a negative lead time

- What the log contains: three (deployment, commit) pairs in which the commit is timestamped after the successful production deployment that shipped it, because the committing machine's clock ran ahead of the deploy pipeline's.
- What a default definition would have done: it would either drop those pairs as "bad data", silently shrinking the sample, or keep the raw negative seconds, which pull the median down and can in principle report a lead time below zero.
- Why the rule is defensible: the change really was delivered, so it belongs in the sample; clamping to zero records "as fast as we can measure" without inventing negative time, and reporting the count tells the reader how much of the median rests on untrustworthy clocks.

## E2 - a revert of a revert

- What the log contains: `sha-0070` reverts `sha-0069`, and `sha-0071` then reverts `sha-0070`; both reverts carry no `change_id` of their own, so `revert_chains_collapsed` is 2.
- What a default definition would have done: counting each commit, or each distinct non-null `change_id` plus each revert, as a unit of work turns one piece of work that went back and forth into three changes, inflating throughput exactly when the team was struggling with it.
- Why the rule is defensible: a revert and a re-apply are rework on the same change, not new value; resolving reverts transitively to the original `change_id` keeps the number of changes honest and keeps the change's first commit instant at the moment the work really started.

## E3 - a hotfix that never touched `main`

- What the log contains: four commits on `hotfix/...` branches (`sha-0019`, `sha-0077`, `sha-0108`, `sha-0127`) that were deployed straight to production from the hotfix branch and never merged through `main`.
- What a default definition would have done: filtering commits on `branch == "main"` drops exactly the emergency fixes, so the fastest deliveries vanish from lead time and the dashboard looks slower than the team actually is under pressure.
- Why the rule is defensible: the metric measures what reached production, not which branch it travelled on; branch names are a team convention, and a rule that depends on them breaks the day someone renames the trunk or adopts a release-branch flow.

## E4 - a deployment with zero linked commits

- What the log contains: four production deployments with an empty `commits` list - DEP-0026 and DEP-0032 succeeded, DEP-0043 and DEP-0044 failed - typically configuration pushes or re-runs of an existing artifact.
- What a default definition would have done: dropping them, because they produce no lead-time pair, removes two failures from the change fail rate and four deployments from the frequency; dividing by their commit count crashes or produces NaN.
- Why the rule is defensible: a configuration push can break production just as code can, so it must count in frequency, in the fail rate and in the rework denominator; it simply has no commit to measure lead time from, so it adds no pair.

## E5 - a deployment that failed and never recovered

- What the log contains: DEP-0015 failed on 7 September; its only covering incident, INC-0004, was opened and never resolved within the log, so it is the one open failure.
- What a default definition would have done: closing the incident at the window's end invents a recovery time that depends on when the report was run, and dropping the deployment hides a failure; either way the recovery median looks better than reality.
- Why the rule is defensible: an unrecovered failure has no recovery time to report, so it stays out of the median, but it is still a failure: it counts in `change_fail_rate` and is reported separately as `open_failures`, so the reader sees it instead of a flattering number.

## E6 - overlapping incidents

- What the log contains: eleven unordered pairs of incidents whose `[opened, resolved)` intervals intersect, for example INC-0010 and INC-0011 on 7 September covering DEP-0043 and DEP-0044, and the cluster INC-0006 to INC-0008 on 19 September.
- What a default definition would have done: merging overlapping incidents into one outage gives several failed deployments a single, shared recovery, and summing their durations double-counts the same wall-clock hours, so recovery time is either understated or overstated.
- Why the rule is defensible: the question the metric answers is how long each failed deployment hurt users, so recovery is measured per failed deployment from its own covering incident; overlaps are counted and reported, never merged or summed.

## Gaming demonstration

`gaming.json` names `change_lead_time_seconds_p50` and rule **R-08**. In `gaming/after.jsonl` every base
production deployment is moved three days later, and 30 extra successful deployments are added, two per working
day, each carrying six trivial commits made ten minutes before they ship. Nothing is deleted, no commit is
re-timed and no outcome is flipped, so R-19 conservation holds.

R-08 is a median over (deployment, commit) **pairs**, so 180 ten-minute pairs outnumber the 114 real ones still in the window and the
median falls from 375 643 s (about 4.3 days) to 600 s - a drop of more than 99 %. Deployment frequency rises from
2.0 to 3.0 per day as a side effect. Meanwhile the real work got worse: measured on the base changes alone (R-21),
the true change lead time rises from 539 452 s to 791 959 s (147 % of the base) and only 58 of the 65 base changes
are delivered inside the window, because their deployments were pushed past its end.

The incentive that produces this in a real team is a quarterly target or bonus on "median lead time" read off a
dashboard. Splitting work into many tiny commits that ship immediately (version bumps, formatting, flag flips)
while batching the substantial changes into a later release is cheap and looks like improvement. The people
rewarded are the team lead and the engineers whose dashboard turns green; the cost falls on the requesters whose
actual changes now wait three days longer, which is exactly what `ground_truth` measures and the five metrics do
not.
