from __future__ import annotations

from dataclasses import asdict

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from easytv.core.enhancement import EnhancementService
from easytv.core.errors import EnhancementUnavailable
from easytv.infrastructure.upnp import DLNA_FLAGS

from .schemas import Dto, QueueRequest


class ConfigureRequest(Dto):
    enabled: bool
    streaming: bool = True


class PrepareRequest(QueueRequest):
    retry: bool = False


class JobDto(Dto):
    id: str
    key: str
    state: str
    stream_ready: bool
    progress: float | None
    speed: float | None
    error: str | None
    width: int | None
    height: int | None
    title: str | None = None


def build_router(service: EnhancementService, worker_url: str | None, transport=None):
    router = APIRouter()

    def dto(job):
        return JobDto(**asdict(job), title=service.titles.get(job.key)).model_dump(by_alias=True)

    @router.get("/api/enhancement")
    async def status():
        available, error = await service.worker.health()
        if available:
            try:
                await service.refresh()
            except EnhancementUnavailable as exc:
                available, error = False, str(exc)
        return {**asdict(service.settings.get()), "available": available, "error": error or service.error,
                "jobs": [dto(job) for job in service.jobs.values()]}

    @router.put("/api/enhancement")
    async def configure(body: ConfigureRequest):
        await service.configure(body.enabled, body.streaming)
        return asdict(service.settings.get())

    @router.post("/api/enhancement/prepare")
    async def prepare(body: PrepareRequest):
        ref = body.stream.ref() if body.stream else None
        job = await service.prepare(video_id=body.video_id, ref=ref, title=body.title,
                                    foreground=True, retry=body.retry)
        if job is None:
            return {"url": ref.path if ref else f"/media/{body.video_id}", "job": None}
        ready = job.state == "ready" or (job.state == "running" and service.settings.get().streaming and job.stream_ready)
        return {"url": job.path if ready else None, "job": dto(job)}

    @router.api_route("/enhanced/{name}", methods=["GET", "HEAD"], include_in_schema=False)
    async def media(name: str, request: Request):
        job_id = name.removesuffix(".mp4")
        if len(job_id) != 64 or any(c not in "0123456789abcdef" for c in job_id):
            raise HTTPException(404)
        if not worker_url:
            raise EnhancementUnavailable("Контейнер RelayVSR не настроен")
        client = httpx.AsyncClient(base_url=worker_url, timeout=httpx.Timeout(20, read=300), transport=transport)
        try:
            upstream = await client.send(client.build_request(
                request.method, f"/jobs/{job_id}/video.mp4",
                headers={"Range": request.headers["range"]} if "range" in request.headers else {},
            ), stream=True)
        except httpx.HTTPError:
            await client.aclose()
            raise EnhancementUnavailable("Поток RelayVSR недоступен") from None
        headers = {key: value for key, value in upstream.headers.items() if key in {
            "content-type", "content-length", "content-range", "accept-ranges", "etag", "last-modified", "retry-after",
        }}
        seekable = headers.get("accept-ranges") == "bytes"
        headers.update({"transferMode.dlna.org": "Streaming", "contentFeatures.dlna.org":
                        DLNA_FLAGS if seekable else DLNA_FLAGS.replace("DLNA.ORG_OP=01", "DLNA.ORG_OP=00")})
        if request.method == "HEAD":
            await upstream.aclose()
            await client.aclose()
            response = Response(status_code=upstream.status_code, headers=headers)
            if "content-length" not in headers:
                del response.headers["content-length"]
            return response

        async def chunks():
            try:
                async for chunk in upstream.aiter_bytes():
                    yield chunk
            finally:
                await upstream.aclose()
                await client.aclose()

        return StreamingResponse(chunks(), status_code=upstream.status_code, headers=headers)

    return router
