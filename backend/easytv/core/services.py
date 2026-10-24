"""Use cases. They orchestrate ports and never touch sockets, files or HTTP directly."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from .errors import (
    InvalidVideoUrl,
    TvNotFound,
    TvNotReachable,
    UnsupportedVideoFormat,
    VideoNotFound,
    VideoNotReady,
)
from .models import (
    SUPPORTED_EXTENSIONS,
    MediaItem,
    PlaybackState,
    PlaybackStatus,
    Tv,
    TvView,
    Video,
    VideoSource,
    VideoStatus,
)
from .ports import (
    Clock,
    IdGenerator,
    MediaUrlResolver,
    TvController,
    TvDiscovery,
    TvLocator,
    TvRepository,
    VideoDownloader,
    VideoRepository,
    VideoStorage,
)

log = logging.getLogger(__name__)

_YOUTUBE_URL = re.compile(
    r"^(https?://)?((www|m|music)\.)?(youtube\.com/(watch\?|shorts/|live/|embed/)|youtu\.be/)\S+$",
    re.IGNORECASE,
)


class TvService:
    """Keeps the list of TVs fresh.

    Each refresh combines three sources, so TVs are found even where multicast doesn't work (Docker):
    1. discovery (SSDP);
    2. re-reading the description URL of every TV seen before;
    3. configured addresses ("seeds") that haven't resolved to a known TV yet.
    """

    def __init__(
        self,
        discovery: TvDiscovery,
        locator: TvLocator,
        repo: TvRepository,
        clock: Clock,
        offline_after: timedelta,
        seeds: list[str] | None = None,
    ) -> None:
        self._discovery = discovery
        self._locator = locator
        self._repo = repo
        self._clock = clock
        self._offline_after = offline_after
        self._seeds = list(dict.fromkeys(seeds or []))
        self._lock = asyncio.Lock()
        self._last_online: set[str] | None = None

    async def refresh(self) -> list[TvView]:
        async with self._lock:
            found: dict[str, Tv] = {}
            try:
                for tv in await self._discovery.discover():
                    found[tv.id] = tv
            except Exception:
                log.exception("SSDP discovery failed")

            known = [tv for tv in self._repo.list() if tv.id not in found and tv.location]
            for tv in await asyncio.gather(*(self._locator.describe(t.location or "") for t in known)):
                if tv is not None:
                    found.setdefault(tv.id, tv)

            # Configured addresses not answered yet this round: try to locate them (cheap when offline).
            resolved = {tv.location for tv in found.values()} | {tv.ip for tv in found.values()}
            pending = [s for s in self._seeds if s not in resolved]
            for tv in await asyncio.gather(*(self._locator.locate(s) for s in pending)):
                if tv is not None:
                    found.setdefault(tv.id, tv)

            now = self._clock.now()
            for tv in found.values():
                self._repo.upsert(replace(tv, last_seen=now))
            online = {f"{tv.name} ({tv.ip})" for tv in found.values()}
            if online != self._last_online:  # log only changes, the loop runs every few seconds
                log.info("TVs online: %s", ", ".join(sorted(online)) or "none")
                self._last_online = online
        return self.list()

    async def add(self, address: str) -> TvView:
        """Add a TV by IP or description URL (for networks where discovery can't see it)."""
        address = address.strip()
        tv = await self._locator.locate(address)
        if tv is None:
            raise TvNotReachable(address)
        self._repo.upsert(replace(tv, last_seen=self._clock.now()))
        return self.get(tv.id)

    def forget(self, tv_id: str) -> None:
        self.get(tv_id)
        self._repo.delete(tv_id)

    def list(self) -> list[TvView]:
        views = [self._view(tv) for tv in self._repo.list()]
        return sorted(views, key=lambda v: (not v.online, v.tv.name.lower()))

    def get(self, tv_id: str) -> TvView:
        tv = self._repo.get(tv_id)
        if tv is None:
            raise TvNotFound(tv_id)
        return self._view(tv)

    def _view(self, tv: Tv) -> TvView:
        now = self._clock.now()
        return TvView(tv=tv, online=tv.last_seen is not None and now - tv.last_seen <= self._offline_after)


class VideoLibrary:
    def __init__(
        self,
        repo: VideoRepository,
        storage: VideoStorage,
        downloader: VideoDownloader,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._repo = repo
        self._storage = storage
        self._downloader = downloader
        self._clock = clock
        self._ids = ids
        self._tasks: set[asyncio.Task[None]] = set()

    def list(self) -> list[Video]:
        return sorted(self._repo.list(), key=lambda v: v.created_at, reverse=True)

    def get(self, video_id: str) -> Video:
        video = self._repo.get(video_id)
        if video is None:
            raise VideoNotFound(video_id)
        return video

    async def upload(self, filename: str, chunks: AsyncIterator[bytes]) -> Video:
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise UnsupportedVideoFormat(filename)
        video_id = self._ids.new_id()
        path, size = await self._storage.save(f"{video_id}{ext}", chunks)
        video = Video(
            id=video_id,
            title=Path(filename).stem or video_id,
            source=VideoSource.UPLOAD,
            status=VideoStatus.READY,
            created_at=self._clock.now(),
            path=path,
            size=size,
            progress=1.0,
        )
        self._repo.add(video)
        return video

    def add_youtube(self, url: str) -> Video:
        """Register a YouTube video and start downloading it in the background."""
        url = url.strip()
        if not _YOUTUBE_URL.match(url):
            raise InvalidVideoUrl(url)
        video = Video(
            id=self._ids.new_id(),
            title=url,
            source=VideoSource.YOUTUBE,
            status=VideoStatus.PENDING,
            created_at=self._clock.now(),
            origin_url=url,
        )
        self._repo.add(video)
        task = asyncio.get_running_loop().create_task(self._download(video))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return video

    async def wait_downloads(self) -> None:
        """Wait for background downloads (used on shutdown and in tests)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    def delete(self, video_id: str) -> None:
        video = self.get(video_id)
        if video.path:
            self._storage.delete(video.path)
        self._repo.delete(video_id)

    async def _download(self, video: Video) -> None:
        video.status = VideoStatus.DOWNLOADING
        self._repo.update(video)

        def on_progress(fraction: float, title: str | None) -> None:
            video.progress = max(0.0, min(fraction, 1.0))
            if title:
                video.title = title

        try:
            result = await asyncio.to_thread(
                self._downloader.download, video.origin_url or "", self._storage.directory, video.id, on_progress
            )
        except Exception as exc:  # downloader errors are reported to the user, not raised
            log.warning("Download of %s failed: %s", video.origin_url, exc)
            video.status = VideoStatus.FAILED
            video.error = str(exc) or exc.__class__.__name__
            self._repo.update(video)
            return

        video.path = result.path
        video.title = result.title or video.title
        video.size = result.path.stat().st_size if result.path.exists() else None
        video.progress = 1.0
        video.status = VideoStatus.READY
        self._repo.update(video)


class PlaybackService:
    def __init__(
        self,
        tvs: TvService,
        videos: VideoLibrary,
        controller: TvController,
        urls: MediaUrlResolver,
    ) -> None:
        self._tvs = tvs
        self._videos = videos
        self._controller = controller
        self._urls = urls
        self._now_playing: dict[str, str] = {}

    async def play(self, tv_id: str, video_id: str) -> PlaybackStatus:
        tv = self._tvs.get(tv_id).tv
        video = self._videos.get(video_id)
        if video.status is not VideoStatus.READY or video.path is None:
            raise VideoNotReady(video_id)
        media = MediaItem(url=self._urls.url_for(video, tv), title=video.title, mime=video.mime)
        await self._controller.play(tv, media)
        self._now_playing[tv_id] = video_id
        return PlaybackStatus(state=PlaybackState.TRANSITIONING, video_id=video_id)

    async def pause(self, tv_id: str) -> None:
        await self._controller.pause(self._tvs.get(tv_id).tv)

    async def resume(self, tv_id: str) -> None:
        await self._controller.resume(self._tvs.get(tv_id).tv)

    async def stop(self, tv_id: str) -> None:
        await self._controller.stop(self._tvs.get(tv_id).tv)
        self._now_playing.pop(tv_id, None)

    async def status(self, tv_id: str) -> PlaybackStatus:
        tv = self._tvs.get(tv_id).tv
        info = await self._controller.info(tv)
        video_id = self._now_playing.get(tv_id)
        if info.state in (PlaybackState.STOPPED, PlaybackState.NO_MEDIA):
            video_id = None
        return PlaybackStatus(
            state=info.state, video_id=video_id, position_s=info.position_s, duration_s=info.duration_s
        )
