from __future__ import annotations

from fastapi import APIRouter

from easytv.core.catalog import CatalogService, CinemaService
from easytv.core.services import PlaybackService, VideoLibrary

from .schemas import (
    CatalogTitleDto,
    EpisodeDto,
    PlaybackDto,
    PlayStreamRequest,
    ResolvedDto,
    SavedTitleDto,
    SaveEpisodeRequest,
    SaveTitleRequest,
    StreamRefDto,
    TitleDetailsDto,
    VariantDto,
    VideoDto,
)


class ResolveRequest(StreamRefDto):
    translation: str | None = None


def build_router(
    catalog: CatalogService, cinema: CinemaService, library: VideoLibrary, playback: PlaybackService
) -> APIRouter:
    router = APIRouter(prefix="/api")

    # ---- Site catalog (animego)

    @router.get("/catalog/search", response_model=list[CatalogTitleDto])
    async def search(q: str) -> list[CatalogTitleDto]:
        return [CatalogTitleDto.of(t, cinema.find(t.id) is not None) for t in await catalog.search(q)]

    @router.get("/catalog/titles/{title_id}", response_model=TitleDetailsDto)
    async def title(title_id: str) -> TitleDetailsDto:
        return TitleDetailsDto.of(await catalog.title(title_id), catalog.name, cinema.find(title_id))

    @router.get("/catalog/titles/{title_id}/episodes", response_model=list[EpisodeDto])
    async def episodes(title_id: str) -> list[EpisodeDto]:
        return [EpisodeDto.of(e) for e in await catalog.episodes(title_id)]

    @router.get("/catalog/titles/{title_id}/variants", response_model=list[VariantDto])
    async def variants(title_id: str, episode: int = 0) -> list[VariantDto]:
        return [VariantDto.of(v) for v in await catalog.variants(title_id, episode)]

    @router.post("/catalog/resolve", response_model=ResolvedDto)
    async def resolve(body: ResolveRequest) -> ResolvedDto:
        """Prepare an episode for the browser player: finds a fresh link and remembers where the user is."""
        ref = body.ref()
        stream = await catalog.resolve(ref)
        cinema.started(ref, body.translation)
        return ResolvedDto.of(ref, stream)

    @router.post("/catalog/download", response_model=VideoDto, status_code=202)
    async def download(body: SaveEpisodeRequest) -> VideoDto:
        ref = body.ref()
        stream = await catalog.resolve(ref)
        origin = f"https://animego.me/anime/{ref.title_id}"
        return VideoDto.of(library.add_stream(stream, body.title, origin))

    @router.post("/tvs/{tv_id}/play-stream", response_model=PlaybackDto)
    async def play_stream(tv_id: str, body: PlayStreamRequest) -> PlaybackDto:
        ref = body.ref()
        status = await playback.play_stream(tv_id, ref, body.title)
        cinema.started(ref, body.translation)
        return PlaybackDto.of(status)

    # ---- Cinema: titles kept from sites

    @router.get("/cinema", response_model=list[SavedTitleDto])
    def list_saved() -> list[SavedTitleDto]:
        return [SavedTitleDto.of(t) for t in cinema.list()]

    @router.post("/cinema", response_model=SavedTitleDto, status_code=201)
    async def save(body: SaveTitleRequest) -> SavedTitleDto:
        return SavedTitleDto.of(await cinema.save(body.title_id))

    @router.delete("/cinema/{title_id}", status_code=204)
    def remove(title_id: str) -> None:
        cinema.remove(title_id)

    return router
