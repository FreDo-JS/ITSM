<!-- ai-generated: 80% - Claude Code wrote the explanation from our Toxiproxy runs and the checker's re-measurement; reviewed by the repository owner -->
# The client-server latency gap (Lab 3, Stretch 2)

**Setup.** Toxiproxy 2.12.0 sits in front of `svcdesk` with one toxic: `latency`, downstream, toxicity 1, 100 ms
with 10 ms of jitter. Every response leaving `svcdesk` is held back about 100 ms before the client sees its bytes.
The load is the M-08 run: open-loop, 40 requests per second, latency-corrected, through the proxy.

**The numbers in `gap.json`.** The server's p99, 0.19 s, is what our own histogram reports for `/kb/search` on a
quiet machine (0.183 to 0.19 s in our `itsmlab load 3` and `verify 3` runs). The gap, 0.11 s, is the checker's own
re-measurement through its proxy with this toxic (`gap_remeasured_seconds=0.1096` in `verify 3`). The client's
p99 is the sum, 0.30 s.

**Why the gap is about 110 ms.** The server's histogram stops its timer when the response leaves the application:
it measures the time to look the query up in `kb-index` and build the answer. The toxic acts after that, on the
wire, so the server never sees it. The client's latency is measured from the instant oha scheduled the request to
the last byte received, so it includes everything the server measured plus every delay between the two - here, the
toxic's 100 ms and its jitter, which can add up to 10 ms more at the tail. That is why the gap is close to 100 ms +
10 ms and not to 100 ms: at the 99th percentile the client sees nearly the worst jitter.

**Why it matters.** A server-side histogram is the right instrument for the service's own SLO, but it is blind to
the network, a proxy, a load balancer or TLS between the user and the service. A latency SLO measured only on the
server can be met while users wait 100 ms longer on every request. The gap is also where coordinated omission hides:
our first attempt to measure through the proxy from the Windows host, via `host.docker.internal`, on a laptop at
85 % CPU, gave a client p99 of 1.36 s against a server p99 of 0.85 s - queueing in Docker Desktop's port forwarding
and a saturated CPU, not the toxic. That run is why we report the checker's in-network measurement and not our own.
