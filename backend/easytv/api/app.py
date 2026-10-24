from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from easytv.container import Container
from easytv.core.errors import (
    EasyTvError,
    InvalidVideoUrl,
    TvCommandError,
    TvNotFound,
    TvNotReachable,
    UnsupportedVideoFormat,
    VideoNotFound,
    VideoNotReady,
)

from . import media, routes

log = logging.getLogger(__name__)

_ERROR_STATUS: dict[type[EasyTvError], int] = {
    TvNotFound: 404,
    TvNotReachable: 422,
    VideoNotFound: 404,
    VideoNotReady: 409,
    InvalidVideoUrl: 422,
    UnsupportedVideoFormat: 415,
    TvCommandError: 502,
}


async def _discovery_loop(c: Container) -> None:
    while True:
        try:
            views = await c.tvs.refresh()
            log.debug("Discovery: %d TV(s) known", len(views))
        except Exception:
            log.exception("Discovery failed")
        await asyncio.sleep(c.settings.discovery_interval_s)


def create_app(c: Container) -> FastAPI:
    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        task = asyncio.create_task(_discovery_loop(c)) if c.settings.discovery_interval_s > 0 else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(title="EasyTv", lifespan=lifespan)

    @app.exception_handler(EasyTvError)
    async def domain_error(_: Request, exc: EasyTvError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=_ERROR_STATUS.get(type(exc), 400))

    app.include_router(routes.build_router(c.tvs, c.library, c.playback))
    app.include_router(media.build_router(c.library))

    if c.settings.static_dir and (c.settings.static_dir / "index.html").exists():
        _mount_spa(app, c.settings.static_dir)
    return app


def _mount_spa(app: FastAPI, root: Path) -> None:
    """Serve the built React app; unknown paths fall back to index.html for client-side routing."""
    root = root.resolve()
    index = root / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> Response:
        if path.startswith(("api/", "media/")):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        candidate = (root / path).resolve()
        if path and root in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
