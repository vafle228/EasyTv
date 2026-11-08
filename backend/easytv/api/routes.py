from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, UploadFile

from easytv.core.services import PlaybackService, TvService, VideoLibrary

from .schemas import (
    AddTvRequest,
    DirectVideoRequest,
    NextRequest,
    PlaybackDto,
    PlayRequest,
    QueueDto,
    QueueItemDto,
    QueueRequest,
    SeekRequest,
    TvDto,
    VideoDto,
    YoutubeRequest,
)


def build_router(tvs: TvService, library: VideoLibrary, playback: PlaybackService) -> APIRouter:
    router = APIRouter(prefix="/api")

    # ---- TVs

    @router.get("/tvs", response_model=list[TvDto])
    def list_tvs() -> list[TvDto]:
        return [TvDto.of(v) for v in tvs.list()]

    @router.post("/tvs/refresh", response_model=list[TvDto])
    async def refresh_tvs() -> list[TvDto]:
        return [TvDto.of(v) for v in await tvs.refresh()]

    @router.post("/tvs", response_model=TvDto, status_code=201)
    async def add_tv(body: AddTvRequest) -> TvDto:
        return TvDto.of(await tvs.add(body.address))

    @router.delete("/tvs/{tv_id}", status_code=204)
    def forget_tv(tv_id: str) -> None:
        tvs.forget(tv_id)

    @router.get("/tvs/{tv_id}", response_model=TvDto)
    def get_tv(tv_id: str) -> TvDto:
        return TvDto.of(tvs.get(tv_id))

    @router.get("/tvs/{tv_id}/playback", response_model=PlaybackDto)
    async def playback_status(tv_id: str) -> PlaybackDto:
        return PlaybackDto.of(await playback.status(tv_id))

    @router.post("/tvs/{tv_id}/play", response_model=PlaybackDto)
    async def play(tv_id: str, body: PlayRequest) -> PlaybackDto:
        return PlaybackDto.of(await playback.play(tv_id, body.video_id))

    @router.post("/tvs/{tv_id}/pause", status_code=204)
    async def pause(tv_id: str) -> None:
        await playback.pause(tv_id)

    @router.post("/tvs/{tv_id}/resume", status_code=204)
    async def resume(tv_id: str) -> None:
        await playback.resume(tv_id)

    @router.post("/tvs/{tv_id}/seek", status_code=204)
    async def seek(tv_id: str, body: SeekRequest) -> None:
        if body.position_s is not None:
            await playback.seek(tv_id, body.position_s)
        else:
            assert body.offset_s is not None
            await playback.seek(tv_id, body.offset_s, relative=True)

    @router.post("/tvs/{tv_id}/stop", status_code=204)
    async def stop(tv_id: str) -> None:
        await playback.stop(tv_id)

    @router.get("/tvs/{tv_id}/queue", response_model=QueueDto)
    async def list_queue(tv_id: str) -> QueueDto:
        items, error = playback.queue(tv_id)
        return QueueDto(items=[QueueItemDto.of(item) for item in items], error=error)

    @router.post("/tvs/{tv_id}/queue", status_code=204)
    async def enqueue(tv_id: str, body: QueueRequest) -> None:
        if body.stream is not None:
            assert body.title is not None
            await playback.enqueue_stream(tv_id, body.stream.ref(), body.title, body.translation)
        else:
            assert body.video_id is not None
            await playback.enqueue_video(tv_id, body.video_id)

    @router.delete("/tvs/{tv_id}/queue/{item_id}", status_code=204)
    async def remove_queued(tv_id: str, item_id: str) -> None:
        await playback.remove_queued(tv_id, item_id)

    @router.post("/tvs/{tv_id}/next", response_model=PlaybackDto)
    async def play_next(tv_id: str, body: NextRequest) -> PlaybackDto:
        return PlaybackDto.of(await playback.next(tv_id, body.item_id))

    # ---- Video library

    @router.get("/videos", response_model=list[VideoDto])
    def list_videos() -> list[VideoDto]:
        return [VideoDto.of(v) for v in library.list()]

    @router.post("/videos/upload", response_model=VideoDto, status_code=201)
    async def upload(file: UploadFile) -> VideoDto:
        async def chunks() -> AsyncIterator[bytes]:
            while data := await file.read(1024 * 1024):
                yield data

        return VideoDto.of(await library.upload(file.filename or "video.mp4", chunks()))

    @router.post("/videos/youtube", response_model=VideoDto, status_code=202)
    async def add_youtube(body: YoutubeRequest) -> VideoDto:  # async: starts a task on the event loop
        return VideoDto.of(library.add_youtube(body.url))

    @router.post("/videos/direct", response_model=VideoDto, status_code=202)
    async def add_direct(body: DirectVideoRequest) -> VideoDto:
        return VideoDto.of(library.add_direct(body.url))

    @router.delete("/videos/{video_id}", status_code=204)
    async def delete_video(video_id: str) -> None:
        library.delete(video_id)

    return router
