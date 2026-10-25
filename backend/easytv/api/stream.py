"""Proxies episodes from sites to TVs and the browser player.

The CDN link is resolved on this server right before playback (it expires and is bound to the IP that asked
for it), then bytes are relayed with the client's Range header and the DLNA headers TVs expect.
"""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse

from easytv.core.catalog import CatalogService
from easytv.core.models import StreamRef
from easytv.infrastructure.animego.client import USER_AGENT
from easytv.infrastructure.upnp import DLNA_FLAGS

log = logging.getLogger(__name__)

_PASS = ("content-length", "content-range", "accept-ranges", "last-modified", "etag")
_RANGE_FROM_START = re.compile(r"^bytes=0-\s*$")


def build_router(catalog: CatalogService, transport: httpx.AsyncBaseTransport | None = None) -> APIRouter:
    """`transport` replaces the network in tests."""
    router = APIRouter()
    client = httpx.AsyncClient(timeout=httpx.Timeout(30, read=60), follow_redirects=True, transport=transport)

    @router.api_route(
        "/stream/{source}/{title_id}/{episode}/{translation_id}/{name}", methods=["GET", "HEAD"], include_in_schema=False
    )
    async def stream(source: str, title_id: str, episode: int, translation_id: str, name: str, request: Request) -> Response:
        ref = StreamRef(
            title_id=title_id, episode=episode, translation_id=translation_id, provider=name.split(".", 1)[0], source=source
        )
        headers = {"User-Agent": USER_AGENT}
        if rng := request.headers.get("range"):
            headers["Range"] = rng
        elif request.method == "HEAD":
            headers["Range"] = "bytes=0-0"  # learn the size without downloading the file

        upstream: httpx.Response | None = None
        for attempt in (1, 2):
            link = await catalog.resolve(ref)
            req = client.build_request("GET", link.url, headers={**headers, **link.headers})
            upstream = await client.send(req, stream=True)
            if upstream.status_code < 400 or attempt == 2:
                break
            # An expired or IP-bound link: get a fresh one and try once more.
            log.info("CDN answered %s for %s, refreshing the link", upstream.status_code, ref)
            await upstream.aclose()
            catalog.forget(ref)
        assert upstream is not None

        if upstream.status_code >= 400:
            await upstream.aclose()
            return Response(status_code=502, content=f"CDN ответил {upstream.status_code}".encode())

        out = {k.lower(): v for k, v in upstream.headers.items() if k.lower() in _PASS}
        out.update(
            {
                "content-type": "video/mp4",
                "accept-ranges": "bytes",
                "transferMode.dlna.org": "Streaming",
                "contentFeatures.dlna.org": DLNA_FLAGS,
            }
        )
        status = upstream.status_code
        size = out.get("content-length", "")
        if rng and status == 200 and _RANGE_FROM_START.match(rng) and size.isdigit():
            # CVH (okcdn) ignores "bytes=0-" and sends the whole file with 200. Newer Samsungs probe with exactly
            # that range on SetAVTransportURI and reject a 200 with UPnP error 716, so answer like a file server.
            out["content-range"] = f"bytes 0-{int(size) - 1}/{size}"
            status = 206
        if request.method == "HEAD":
            await upstream.aclose()
            if not rng:  # answer as if the whole file was asked for
                total = (upstream.headers.get("content-range") or "").rpartition("/")[2]
                out.pop("content-range", None)
                if total.isdigit():
                    out["content-length"] = total
                status = 200
            return Response(status_code=status, headers=out)

        async def body() -> AsyncIterator[bytes]:
            try:
                async for chunk in upstream.aiter_bytes(256 * 1024):
                    yield chunk
            finally:
                await upstream.aclose()

        return StreamingResponse(body(), status_code=status, headers=out)

    return router
