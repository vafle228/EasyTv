"""Interfaces the core depends on. Implementations live in `easytv.infrastructure`."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import datetime
from pathlib import Path
from typing import Protocol

from .models import DownloadResult, MediaItem, PlaybackInfo, Tv, Video


class TvDiscovery(Protocol):
    async def discover(self) -> list[Tv]:
        """Find TVs (DLNA media renderers) currently reachable."""


class TvLocator(Protocol):
    """Finds a TV by a known address. Works without multicast (e.g. from inside Docker)."""

    async def describe(self, location: str) -> Tv | None:
        """Read the device description at `location`; None if unreachable or not a media renderer."""

    async def locate(self, address: str) -> Tv | None:
        """`address` is an IP (try well-known description URLs) or a description URL."""


class TvController(Protocol):
    async def play(self, tv: Tv, media: MediaItem) -> None: ...
    async def pause(self, tv: Tv) -> None: ...
    async def resume(self, tv: Tv) -> None: ...
    async def stop(self, tv: Tv) -> None: ...
    async def info(self, tv: Tv) -> PlaybackInfo: ...


ProgressCallback = Callable[[float, "str | None"], None]


class VideoDownloader(Protocol):
    def download(self, url: str, target_dir: Path, basename: str, on_progress: ProgressCallback) -> DownloadResult:
        """Blocking download. `on_progress(fraction 0..1, title or None)` may be called from the worker thread."""


class VideoStorage(Protocol):
    @property
    def directory(self) -> Path: ...
    async def save(self, name: str, chunks: AsyncIterator[bytes]) -> tuple[Path, int]: ...
    def delete(self, path: Path) -> None: ...


class TvRepository(Protocol):
    def upsert(self, tv: Tv) -> None: ...
    def get(self, tv_id: str) -> Tv | None: ...
    def list(self) -> list[Tv]: ...
    def delete(self, tv_id: str) -> None: ...


class VideoRepository(Protocol):
    def add(self, video: Video) -> None: ...
    def update(self, video: Video) -> None: ...
    def get(self, video_id: str) -> Video | None: ...
    def list(self) -> list[Video]: ...
    def delete(self, video_id: str) -> None: ...


class MediaUrlResolver(Protocol):
    def url_for(self, video: Video, tv: Tv) -> str:
        """Absolute http URL at which `tv` can fetch `video`."""


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self) -> str: ...
