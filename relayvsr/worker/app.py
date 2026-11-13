from __future__ import annotations

import asyncio
import contextlib
import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, Field, model_validator
from starlette.background import BackgroundTask

from .jobs import Jobs, TERMINAL


class Source(BaseModel):
    file: str | None = None
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_source(self):
        if (self.file is None) == (self.url is None):
            raise ValueError("Укажите один источник")
        if self.file is not None:
            root = Path(os.environ.get("RELAYVSR_INPUT", "/input")).resolve()
            path = (root / self.file).resolve()
            if root not in path.parents or not path.is_file():
                raise ValueError("Исходник отсутствует в библиотеке")
        if self.url is not None:
            parts = urlsplit(self.url)
            if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username:
                raise ValueError("Требуется HTTP(S)-адрес")
        if any("\r" in k + v or "\n" in k + v for k, v in self.headers.items()):
            raise ValueError("Некорректные заголовки источника")
        return self


class Submit(BaseModel):
    key: str = Field(min_length=1, max_length=300)
    source: Source
    priority: int = Field(default=1, ge=0, le=1)
    retry: bool = False


class Retain(BaseModel):
    keys: list[str]


def create_app(jobs=None, health=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.jobs = jobs or Jobs(Path(os.environ.get("RELAYVSR_CACHE", "/cache")),
                                     int(float(os.environ.get("RELAYVSR_CACHE_GB", "30")) * 1024**3))
        task = asyncio.create_task(app.state.jobs.serve())
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title="EasyTv RelayVSR worker", lifespan=lifespan)

    @app.get("/health")
    async def get_health():
        if health:
            return health()
        weights = Path(os.environ.get("RELAYVSR_WEIGHTS", "/weights"))
        missing = [name for name in ("wan.safetensors", "flash.safetensors") if not (weights / name).is_file()]
        if missing:
            return {"available": False, "error": "Не загружены веса: " + ", ".join(missing)}
        import torch
        available = torch.cuda.is_available()
        return {"available": available, "error": None if available else "CUDA недоступна",
                "gpu": torch.cuda.get_device_name() if available else None}

    @app.get("/jobs")
    async def list_jobs():
        return [app.state.jobs.public(k) for k in app.state.jobs.items]

    @app.post("/jobs", status_code=202)
    async def submit(body: Submit):
        try:
            return app.state.jobs.submit(body.key, body.source.model_dump(exclude_none=True), body.priority, body.retry)
        except ValueError as exc:
            raise HTTPException(429, str(exc)) from None

    @app.post("/jobs/retain", status_code=204)
    async def retain(body: Retain):
        app.state.jobs.cancel_background_except(set(body.keys))

    def get(job_id):
        try:
            return app.state.jobs.public(job_id)
        except KeyError:
            raise HTTPException(404, "Задание не найдено") from None

    @app.get("/jobs/{job_id}")
    async def status(job_id: str):
        return get(job_id)

    @app.api_route("/jobs/{job_id}/video.mp4", methods=["GET", "HEAD"])
    async def video(job_id: str, request: Request):
        item = get(job_id)
        manager = app.state.jobs
        path = manager.path(job_id)
        if item["state"] == "ready":
            if not path.is_file():
                raise HTTPException(404, "Файл удалён из кэша")
            manager.readers[job_id] = manager.readers.get(job_id, 0) + 1
            def release():
                manager.readers[job_id] -= 1
            return FileResponse(path, media_type="video/mp4", background=BackgroundTask(release))
        if item["state"] in {"failed", "cancelled"}:
            raise HTTPException(409, item["error"] or "Обработка отменена")
        if not item["stream_ready"]:
            raise HTTPException(425, "Подготовка первых кадров", headers={"Retry-After": "2"})
        # A growing file has no final length. Ignore Range per HTTP semantics; never invent a size.
        headers = {"Accept-Ranges": "none", "Cache-Control": "no-store"}
        if request.method == "HEAD":
            response = Response(media_type="video/mp4", headers=headers)
            del response.headers["content-length"]
            return response

        async def chunks():
            manager.readers[job_id] = manager.readers.get(job_id, 0) + 1
            try:
                with path.open("rb") as source:
                    while True:
                        data = source.read(256 * 1024)
                        if data:
                            yield data
                        elif manager.items[job_id]["state"] == "ready":
                            break
                        elif manager.items[job_id]["state"] in TERMINAL:
                            raise RuntimeError("Обработка видео прервана")
                        else:
                            await asyncio.sleep(0.1)
            finally:
                manager.readers[job_id] -= 1

        return StreamingResponse(chunks(), media_type="video/mp4", headers=headers)

    return app


app = create_app()
