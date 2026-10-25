"""Interfaces the core depends on. Implementations live in `easytv.infrastructure`."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import datetime
from pathlib import Path
from typing import Protocol

from .models import (
    CatalogTitle,
    DownloadResult,
    Episode,
    MediaItem,
    PlaybackInfo,
    SavedTitle,
    Stream,
    StreamRef,
    TitleDetails,
    Tv,
    Variant,
    Video,
)


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


class FileFetcher(Protocol):
    def fetch(self, url: str, headers: dict[str, str], target: Path, on_progress: ProgressCallback) -> int:
        """Blocking download of a direct link to `target`; returns its size."""


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


class CatalogSource(Protocol):
    """A site with titles to browse and watch (animego). Blocking calls; errors are `CatalogError`."""

    name: str

    def search(self, query: str) -> list[CatalogTitle]: ...
    def title(self, title_id: str) -> TitleDetails: ...
    def episodes(self, title_id: str) -> list[Episode]:
        """Episodes of a series; empty for a movie."""

    def variants(self, title_id: str, episode: int) -> list[Variant]:
        """Dubs and players of an episode (`episode` 0 for a movie)."""

    def streams(self, ref: StreamRef) -> list[Stream]:
        """Fresh direct links, best first. Tries the players of the dub in priority order."""


class SavedTitleRepository(Protocol):
    def upsert(self, item: SavedTitle) -> None: ...
    def get(self, title_id: str) -> SavedTitle | None: ...
    def list(self) -> list[SavedTitle]: ...
    def delete(self, title_id: str) -> None: ...


class MediaUrlResolver(Protocol):
    def url_for(self, video: Video, tv: Tv) -> str:
        """Absolute http URL at which `tv` can fetch `video`."""

    def url_for_path(self, path: str, tv: Tv) -> str:
        """Absolute http URL of a path on this server, as `tv` reaches it."""


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self) -> str: ...
