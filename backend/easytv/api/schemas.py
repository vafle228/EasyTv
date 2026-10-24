from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from easytv.core.models import PlaybackState, PlaybackStatus, TvView, Video, VideoSource, VideoStatus


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


class PlaybackDto(Dto):
    state: PlaybackState
    video_id: str | None
    position_s: int | None
    duration_s: int | None

    @classmethod
    def of(cls, s: PlaybackStatus) -> PlaybackDto:
        return cls(state=s.state, video_id=s.video_id, position_s=s.position_s, duration_s=s.duration_s)


class PlayRequest(Dto):
    video_id: str


class AddTvRequest(Dto):
    address: str


class YoutubeRequest(Dto):
    url: str


class ErrorDto(Dto):
    detail: str
