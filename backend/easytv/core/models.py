from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from urllib.parse import quote


@dataclass
class Tv:
    """A DLNA media renderer (TV) found in the network."""

    id: str
    name: str
    ip: str
    control_url: str
    service_type: str
    manufacturer: str | None = None
    model: str | None = None
    # URL of the UPnP device description; re-reading it is how we check the TV is still there.
    location: str | None = None
    last_seen: datetime | None = None


class VideoSource(str, Enum):
    UPLOAD = "upload"
    YOUTUBE = "youtube"
    ANIMEGO = "animego"


class VideoStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    READY = "ready"
    FAILED = "failed"


@dataclass
class Video:
    """A video in the library that can be streamed to a TV."""

    id: str
    title: str
    source: VideoSource
    status: VideoStatus
    created_at: datetime
    path: Path | None = None
    size: int | None = None
    origin_url: str | None = None
    progress: float = 0.0
    error: str | None = None

    @property
    def extension(self) -> str:
        return self.path.suffix.lower() if self.path else ".mp4"

    @property
    def mime(self) -> str:
        return mime_for(self.extension)


@dataclass(frozen=True)
class MediaItem:
    """What a TV needs to start playback: where to fetch the video and how to describe it."""

    url: str
    title: str
    mime: str


class PlaybackState(str, Enum):
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    TRANSITIONING = "transitioning"
    NO_MEDIA = "no_media"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PlaybackInfo:
    """Raw state reported by the TV."""

    state: PlaybackState
    position_s: int | None = None
    duration_s: int | None = None


@dataclass(frozen=True)
class PlaybackStatus:
    """Playback state enriched with what EasyTv sent to this TV."""

    state: PlaybackState
    video_id: str | None = None
    position_s: int | None = None
    duration_s: int | None = None
    # What is on screen when it isn't a library video (an episode streamed from a site).
    title: str | None = None
    stream: StreamRef | None = None


# ---- Site catalogs (animego and the like)


class TitleKind(str, Enum):
    SERIES = "series"
    MOVIE = "movie"


@dataclass(frozen=True)
class CatalogTitle:
    """A search hit on a site."""

    id: str  # the site's own key, e.g. "provozhayuschaya-v-posledniy-put-friren-2430"
    title: str
    original_title: str | None = None
    kind: str | None = None  # as the site writes it: «Сериал», «Фильм»…
    year: str | None = None
    rating: str | None = None
    poster: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class Collection:
    """A list a site keeps for browsing: ongoing, this season, top rated…"""

    id: str
    title: str


@dataclass(frozen=True)
class TitleDetails:
    id: str
    title: str
    kind: TitleKind
    url: str | None = None
    original_title: str | None = None
    description: str | None = None
    poster: str | None = None
    genres: tuple[str, ...] = ()
    year: str | None = None
    episodes_total: int | None = None
    rating: float | None = None
    studio: str | None = None


@dataclass(frozen=True)
class Episode:
    number: int
    title: str | None = None
    date: str | None = None


@dataclass(frozen=True)
class Variant:
    """One dub/subtitle track of an episode and the players that carry it."""

    translation_id: str
    translation: str
    providers: tuple[str, ...]


@dataclass(frozen=True)
class Stream:
    """A fresh direct link to the video. Links expire and may be bound to our IP: never store them."""

    provider: str
    translation: str
    kind: str  # mp4 / hls / dash
    quality: int | None
    url: str
    headers: dict[str, str] = field(default_factory=dict, hash=False, compare=False)


@dataclass(frozen=True)
class StreamRef:
    """The stable address of an episode on a site; resolved to a `Stream` right before playback.

    `episode` is 0 for movies; `provider` "auto" means the first player that gives a direct MP4.
    """

    title_id: str
    episode: int
    translation_id: str
    provider: str = "auto"
    source: str = "animego"

    @property
    def path(self) -> str:
        """Where this server proxies the episode (for TVs and the browser player)."""
        return "/stream/{}/{}/{}/{}/{}.mp4".format(
            self.source, quote(self.title_id), self.episode, quote(self.translation_id), self.provider
        )


@dataclass
class SavedTitle:
    """A site title kept in the cinema, with where the user stopped."""

    id: str
    source: str
    title: str
    kind: TitleKind
    added_at: datetime
    poster: str | None = None
    original_title: str | None = None
    year: str | None = None
    episodes_total: int | None = None
    genres: tuple[str, ...] = ()
    translation_id: str | None = None
    translation: str | None = None
    last_episode: int | None = None
    watched: set[int] = field(default_factory=set)
    updated_at: datetime | None = None


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    title: str


_MIME = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".ts": "video/mp2t",
    ".m2ts": "video/mp2t",
    ".wmv": "video/x-ms-wmv",
    ".webm": "video/webm",
    ".mpg": "video/mpeg",
    ".mpeg": "video/mpeg",
}

SUPPORTED_EXTENSIONS = frozenset(_MIME)


def mime_for(extension: str) -> str:
    return _MIME.get(extension.lower(), "video/mp4")


@dataclass
class TvView:
    tv: Tv
    online: bool = field(default=True)
