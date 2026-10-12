# ai-generated: 90% - Claude Code wrote the kb-index client from MONITORING-SPEC.md M-02
"""GET /kb/search: one call to kb-index per request, no cache and no retry (M-02)."""

import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

KB_INDEX_URL = os.environ.get("KB_INDEX_URL", "http://kb-index:8080").rstrip("/")
TIMEOUT_SECONDS = 5.0  # M-02 asks for at least 2 s; kb-index's slow mode stays far below this

# The blocking HTTP call runs here, so a slow upstream never starves the event loop or FastAPI's own pool.
_EXECUTOR = ThreadPoolExecutor(max_workers=128, thread_name_prefix="kb-index")


class UpstreamUnavailable(Exception):
    pass


def _fetch(q: str) -> dict:
    url = f"{KB_INDEX_URL}/search?q={urllib.parse.quote(q, safe='')}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise UpstreamUnavailable(f"kb-index answered {response.status}")
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise UpstreamUnavailable(f"kb-index answered {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise UpstreamUnavailable(f"kb-index unreachable: {exc}") from exc


async def search(q: str) -> dict:
    loop = asyncio.get_running_loop()
    body = await loop.run_in_executor(_EXECUTOR, _fetch, q)
    return {"query": q, "hits": body.get("hits")}
