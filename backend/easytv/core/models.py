from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


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
