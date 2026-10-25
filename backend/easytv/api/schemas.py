from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from easytv.core.models import (
    CatalogTitle,
    Collection,
    Episode,
    PlaybackState,
    PlaybackStatus,
    SavedTitle,
    Stream,
    StreamRef,
    TitleDetails,
    TitleKind,
    TvView,
    Variant,
    Video,
    VideoSource,
    VideoStatus,
)


class Dto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TvDto(Dto):
    id: str
    name: str
    ip: str
    manufacturer: str | None
    model: str | None
    online: bool
    last_seen: datetime | None

    @classmethod
    def of(cls, view: TvView) -> TvDto:
        tv = view.tv
        return cls(
            id=tv.id,
            name=tv.name,
            ip=tv.ip,
            manufacturer=tv.manufacturer,
            model=tv.model,
            online=view.online,
            last_seen=tv.last_seen,
        )


class VideoDto(Dto):
    id: str
    title: str
    source: VideoSource
    status: VideoStatus
    progress: float
    size: int | None
    error: str | None
    origin_url: str | None
    created_at: datetime

    @classmethod
    def of(cls, v: Video) -> VideoDto:
        return cls(
            id=v.id,
            title=v.title,
            source=v.source,
            status=v.status,
            progress=round(v.progress, 3),
            size=v.size,
            error=v.error,
            origin_url=v.origin_url,
            created_at=v.created_at,
        )


class StreamRefDto(Dto):
    """An episode on a site: title, episode (0 for a movie), dub and player ("auto" picks the best)."""

    title_id: str
    episode: int = 0
    translation_id: str
    provider: str = "auto"

    def ref(self) -> StreamRef:
        return StreamRef(
            title_id=self.title_id, episode=self.episode, translation_id=self.translation_id, provider=self.provider
        )

    @classmethod
    def of(cls, r: StreamRef) -> StreamRefDto:
        return cls(title_id=r.title_id, episode=r.episode, translation_id=r.translation_id, provider=r.provider)


class PlaybackDto(Dto):
    state: PlaybackState
    video_id: str | None
    position_s: int | None
    duration_s: int | None
    title: str | None = None
    stream: StreamRefDto | None = None

    @classmethod
    def of(cls, s: PlaybackStatus) -> PlaybackDto:
        return cls(
            state=s.state,
            video_id=s.video_id,
            position_s=s.position_s,
            duration_s=s.duration_s,
            title=s.title,
            stream=StreamRefDto.of(s.stream) if s.stream else None,
        )


class PlayRequest(Dto):
    video_id: str


class PlayStreamRequest(StreamRefDto):
    title: str
    translation: str | None = None


class CatalogTitleDto(Dto):
    id: str
    title: str
    original_title: str | None
    kind: str | None
    year: str | None
    rating: str | None
    poster: str | None
    saved: bool

    @classmethod
    def of(cls, t: CatalogTitle, saved: bool) -> CatalogTitleDto:
        return cls(
            id=t.id,
            title=t.title,
            original_title=t.original_title,
            kind=t.kind,
            year=t.year,
            rating=t.rating,
            poster=t.poster,
            saved=saved,
        )


class CollectionDto(Dto):
    id: str
    title: str

    @classmethod
    def of(cls, c: Collection) -> CollectionDto:
        return cls(id=c.id, title=c.title)


class SavedTitleDto(Dto):
    id: str
    source: str
    title: str
    kind: TitleKind
    poster: str | None
    original_title: str | None
    year: str | None
    episodes_total: int | None
    genres: list[str]
    translation_id: str | None
    translation: str | None
    last_episode: int | None
    watched: list[int]
    added_at: datetime
    updated_at: datetime | None

    @classmethod
    def of(cls, t: SavedTitle) -> SavedTitleDto:
        return cls(
            id=t.id,
            source=t.source,
            title=t.title,
            kind=t.kind,
            poster=t.poster,
            original_title=t.original_title,
            year=t.year,
            episodes_total=t.episodes_total,
            genres=list(t.genres),
            translation_id=t.translation_id,
            translation=t.translation,
            last_episode=t.last_episode,
            watched=sorted(t.watched),
            added_at=t.added_at,
            updated_at=t.updated_at,
        )


class TitleDetailsDto(Dto):
    id: str
    source: str
    title: str
    kind: TitleKind
    url: str | None
    original_title: str | None
    description: str | None
    poster: str | None
    genres: list[str]
    year: str | None
    episodes_total: int | None
    rating: float | None
    studio: str | None
    saved: SavedTitleDto | None

    @classmethod
    def of(cls, d: TitleDetails, source: str, saved: SavedTitle | None) -> TitleDetailsDto:
        return cls(
            id=d.id,
            source=source,
            title=d.title,
            kind=d.kind,
            url=d.url,
            original_title=d.original_title,
            description=d.description,
            poster=d.poster,
            genres=list(d.genres),
            year=d.year,
            episodes_total=d.episodes_total,
            rating=d.rating,
            studio=d.studio,
            saved=SavedTitleDto.of(saved) if saved else None,
        )


class EpisodeDto(Dto):
    number: int
    title: str | None
    date: str | None

    @classmethod
    def of(cls, e: Episode) -> EpisodeDto:
        return cls(number=e.number, title=e.title, date=e.date)


class VariantDto(Dto):
    translation_id: str
    translation: str
    providers: list[str]

    @classmethod
    def of(cls, v: Variant) -> VariantDto:
        return cls(translation_id=v.translation_id, translation=v.translation, providers=list(v.providers))


class ResolvedDto(Dto):
    """A playable address on this server for an episode, plus what was found behind it."""

    url: str
    provider: str
    quality: int | None

    @classmethod
    def of(cls, ref: StreamRef, s: Stream) -> ResolvedDto:
        return cls(url=ref.path, provider=s.provider, quality=s.quality)


class SaveTitleRequest(Dto):
    title_id: str


class SaveEpisodeRequest(StreamRefDto):
    title: str


class AddTvRequest(Dto):
    address: str


class YoutubeRequest(Dto):
    url: str


class ErrorDto(Dto):
    detail: str
