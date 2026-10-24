"""Serves video files to TVs: HTTP Range support plus the DLNA headers Samsung and others expect."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from easytv.core.errors import VideoNotFound
from easytv.core.models import VideoStatus
from easytv.core.services import VideoLibrary
from easytv.infrastructure.upnp import DLNA_FLAGS

CHUNK = 256 * 1024
_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")


def _read(path: Path, start: int, length: int) -> Iterator[bytes]:
    with path.open("rb") as f:
        f.seek(start)
        left = length
        while left > 0:
            data = f.read(min(CHUNK, left))
            if not data:
                break
            left -= len(data)
            yield data


def build_router(library: VideoLibrary) -> APIRouter:
    router = APIRouter()

    @router.api_route("/media/{name}", methods=["GET", "HEAD"], include_in_schema=False)
    def media(name: str, request: Request) -> Response:
        video_id = name.split(".", 1)[0]
        try:
            video = library.get(video_id)
        except VideoNotFound:
            raise HTTPException(404) from None
        if video.status is not VideoStatus.READY or video.path is None or not video.path.exists():
            raise HTTPException(404)

        size = video.path.stat().st_size
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": video.mime,
            "transferMode.dlna.org": "Streaming",
            "contentFeatures.dlna.org": DLNA_FLAGS,
        }
        start, end, status = 0, size - 1, 200
        range_header = request.headers.get("range", "").strip()
        if match := _RANGE.match(range_header):
            first, last = match.groups()
            if first:
                start = int(first)
                if last:
                    end = min(int(last), size - 1)
            elif last:
                start = max(0, size - int(last))
            else:
                start = size  # "bytes=-" is invalid
            if start >= size or start > end:
                return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
            status = 206
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"

        length = end - start + 1
        headers["Content-Length"] = str(length)
        if request.method == "HEAD":
            return Response(status_code=status, headers=headers)
        return StreamingResponse(_read(video.path, start, length), status_code=status, headers=headers)

    return router
