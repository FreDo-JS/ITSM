<!-- ai-generated: 75% - Claude Code drafted the comparison from the two scored ledgers; reviewed by the repository owner -->
# Two investigators of the lab4-rec-3 incident

| | first (`ai-rca-eval.json`) | second (`ai-rca-eval-2.json`) |
|---|---|---|
| agent, model | the course agent loop, `qwen3:4b-instruct` (the recorded transcript) | the course agent loop, `qwen3:1.7b` on a local Ollama |
| hypotheses | 4 | 5, over three runs |
| verdicts | 1 correct, 1 partially correct, 2 hallucinated | 1 correct, 2 partially correct, 1 hallucinated, 1 unfalsifiable |

**Where they agreed.** Both put checkout at the centre and both were half right about it (first H1, second H2): checkout
did fail, but neither said why until a downstream service was named. Both were scored `partially_correct` by the same
split - checkout's errors only together with product-catalog's.

**Where they parted.** The 4b model queried checkout's failed spans, saw the failed `GetProduct` client span among
them, and named product-catalog as the origin (first H2, `correct`: 0.149 failed GetProduct calls per second at
07:11, none on the baseline). That is the closest either came to the real fault. The 1.7b model never got a useful
metric query through: three of its `list_metrics` calls failed on a malformed argument, its range queries used a
2023 date, and its useful answer came from `alerts_at`, which returns our own alert labels. Its hypotheses H1 to H4
are those labels read back as claims - the list of services with alerts, each with "critical" or "moderate" taken
from the alert's severity. The list itself was right (H1, `correct`), but it did not go beyond what the alerts told
it, and it never mentioned product-catalog as a cause.

**Which one the data proved right, entry by entry.** Payment (first H3) and high load (first H4) were contradicted by
the data: payment answered 0.125 Charge calls per second with no errors, and the frontend's traffic was flat. The
proxy layer (second H4) was contradicted too: the proxy's errors were half the frontend's, so they were passed
through, not made. "Backend instability or high latency" (second H5) could not be tested at all. Neither
investigator noticed the ad service's latency (5.6 ms to 796 ms) or the recommendation memory growth; our own
queries found those, and the postmortem names them.

**What it means.** The larger model with direct metric queries produced one hypothesis that pointed at the cause;
the smaller one, with tool calls that kept failing, mostly restated our alerts. Neither replaced the on-call's own
queries, and every claim needed one of ours before it could enter the timeline.
