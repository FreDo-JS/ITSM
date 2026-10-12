# ai-generated: 85% - Claude Code wrote the RED histogram from MONITORING-SPEC.md M-03 to M-07; the ladder is ours, from our own measurement
"""Request histogram and /metrics (MONITORING-SPEC.md section 2).

One histogram, `http_server_request_duration_seconds`, labelled with the OpenTelemetry HTTP semantic conventions in
their Prometheus form. `http_route` is always a route template or the constant `unmatched`, so no id, raw path or
query string can ever become a label value (M-05, M-07).
"""

import time

from prometheus_client import (CONTENT_TYPE_LATEST, CollectorRegistry, Histogram, disable_created_metrics,
                               generate_latest)
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

# Seconds. Designed from our own measurement of /kb/search (see slo.md, "Buckets"); at most 30 finite boundaries.
# Our p99 sits in kb-index's slow mode near 0.2 s, so 19 of the 30 boundaries are spent 10 ms apart from 0.12 s
# to 0.30 s: any q in that band lands in a bucket at most 8.3 % of q wide. 0.35 to 0.5 s in 50 ms steps still
# resolves a q pushed up to 0.5 s by a loaded machine. 0.3 s is the latency SLI's threshold.
LADDER = (
    0.01, 0.025, 0.05, 0.075, 0.1,
    0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19, 0.2, 0.21,
    0.22, 0.23, 0.24, 0.25, 0.26, 0.27, 0.28, 0.29, 0.3,
    0.35, 0.4, 0.45, 0.5, 1, 2.5,
)

UNMATCHED = "unmatched"
disable_created_metrics()  # no `_created` series: only _bucket, _sum and _count per label set
REGISTRY = CollectorRegistry(auto_describe=True)
REQUEST_DURATION = Histogram(
    "http_server_request_duration_seconds",
    "Duration of HTTP server requests, from the first byte received to the response headers sent.",
    ["http_request_method", "http_route", "http_response_status_code"],
    buckets=LADDER,
    registry=REGISTRY,
)


def route_template(app, scope) -> str:
    """The path template of the route that handles this request, or UNMATCHED."""
    for route in app.router.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return getattr(route, "path", UNMATCHED)
    return UNMATCHED


def install(app) -> None:
    @app.middleware("http")
    async def observe(request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            REQUEST_DURATION.labels(
                http_request_method=request.method,
                http_route=route_template(app, request.scope),
                http_response_status_code=str(status),
            ).observe(time.perf_counter() - start)

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
