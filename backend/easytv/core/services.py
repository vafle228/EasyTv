"""Use cases. They orchestrate ports and never touch sockets, files or HTTP directly."""

from __future__ import annotations

import asyncio
import logging
import re
from collections import defaultdict
from collections.abc import AsyncIterator, Coroutine
from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from .errors import (
    EnhancementPending,
    EasyTvError,
    InvalidDirectVideoUrl,
    InvalidVideoUrl,
    PlaybackNotSeekable,
    QueueChanged,
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
    QueueItem,
    Stream,
    StreamRef,
    Tv,
    TvView,
    Video,
    VideoSource,
    VideoStatus,
)
from .ports import (
    Clock,
    FileFetcher,
    IdGenerator,
    MediaUrlResolver,
    PlaybackQueueRepository,
    TvController,
    TvDiscovery,
    TvLocator,
    TvRepository,
    VideoDownloader,
    VideoRepository,
    VideoStorage,
)

if TYPE_CHECKING:
    from .catalog import CatalogService, CinemaService
    from .enhancement import EnhancementService

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
        fetcher: FileFetcher | None = None,
        *,
        direct_downloader: VideoDownloader,
    ) -> None:
        self._repo = repo
        self._storage = storage
        self._downloader = downloader
        self._direct_downloader = direct_downloader
        self._fetcher = fetcher
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
        self._start(self._download(video, self._downloader))
        return video

    def add_direct(self, url: str) -> Video:
        url = url.strip()
        try:
            parsed = urlsplit(url)
            valid = (
                parsed.scheme in ("http", "https")
                and parsed.hostname
                and parsed.username is None
                and parsed.port != 0
                and not any(char.isspace() for char in url)
            )
        except ValueError:
            raise InvalidDirectVideoUrl() from None
        if not valid:
            raise InvalidDirectVideoUrl()
        video = Video(
            id=self._ids.new_id(),
            title=parsed.hostname or "Видео по ссылке",
            source=VideoSource.DIRECT,
            status=VideoStatus.PENDING,
            created_at=self._clock.now(),
            origin_url=url,
        )
        self._repo.add(video)
        self._start(self._download(video, self._direct_downloader))
        return video

    def add_stream(self, stream: Stream, title: str, origin: str) -> Video:
        """Save an episode from a site: download its direct link in the background."""
        if self._fetcher is None:
            raise RuntimeError("no FileFetcher configured")
        video = Video(
            id=self._ids.new_id(),
            title=title,
            source=VideoSource.ANIMEGO,
            status=VideoStatus.PENDING,
            created_at=self._clock.now(),
            origin_url=origin,
        )
        self._repo.add(video)
        self._start(self._fetch(video, stream))
        return video

    def _start(self, job: Coroutine[Any, Any, None]) -> None:
        task = asyncio.get_running_loop().create_task(job)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def wait_downloads(self) -> None:
        """Wait for background downloads (used on shutdown and in tests)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    def delete(self, video_id: str) -> None:
        video = self.get(video_id)
        if video.path:
            self._storage.delete(video.path)
        self._repo.delete(video_id)

    async def _download(self, video: Video, downloader: VideoDownloader) -> None:
        if self._repo.get(video.id) is None:
            return
        video.status = VideoStatus.DOWNLOADING
        self._repo.update(video)

        def on_progress(fraction: float, title: str | None) -> None:
            if video.source is VideoSource.DIRECT and self._repo.get(video.id) is None:
                raise RuntimeError("Загрузка отменена")
            video.progress = max(0.0, min(fraction, 1.0))
            if title:
                video.title = title

        try:
            result = await asyncio.to_thread(
                downloader.download, video.origin_url or "", self._storage.directory, video.id, on_progress
            )
        except Exception as exc:  # downloader errors are reported to the user, not raised
            if self._repo.get(video.id) is None:
                return
            log.warning("Download of %s failed: %s", video.id, exc)
            video.status = VideoStatus.FAILED
            video.error = str(exc) or exc.__class__.__name__
            self._repo.update(video)
            return

        if self._repo.get(video.id) is None:
            self._storage.delete(result.path)
            return
        video.path = result.path
        video.title = result.title or video.title
        video.content_type = result.content_type
        video.size = result.path.stat().st_size if result.path.exists() else None
        video.progress = 1.0
        video.status = VideoStatus.READY
        self._repo.update(video)

    async def _fetch(self, video: Video, stream: Stream) -> None:
        assert self._fetcher is not None
        video.status = VideoStatus.DOWNLOADING
        self._repo.update(video)
        target = self._storage.directory / f"{video.id}.mp4"

        def on_progress(fraction: float, _: str | None) -> None:
            video.progress = max(0.0, min(fraction, 0.99))

        try:
            size = await asyncio.to_thread(self._fetcher.fetch, stream.url, stream.headers, target, on_progress)
        except Exception as exc:
            log.warning("Download of %s failed: %s", video.origin_url, exc)
            self._storage.delete(target)
            video.status = VideoStatus.FAILED
            video.error = str(exc) or exc.__class__.__name__
            self._repo.update(video)
            return
        video.path, video.size, video.progress, video.status = target, size, 1.0, VideoStatus.READY
        self._repo.update(video)


_IDLE_STATES = (PlaybackState.STOPPED, PlaybackState.NO_MEDIA)
_END_MARGIN_S = 3
_END_SAMPLE_MAX_AGE_S = 8
_PLAY_START_GRACE_S = 8


@dataclass
class _Playing:
    status: PlaybackStatus
    uri: str
    started_at: float
    near_end_at: float | None = None


class PlaybackService:
    def __init__(
        self,
        tvs: TvService,
        videos: VideoLibrary,
        controller: TvController,
        urls: MediaUrlResolver,
        catalog: CatalogService,
        cinema: CinemaService,
        queues: PlaybackQueueRepository,
        ids: IdGenerator,
        enhancement: EnhancementService,
    ) -> None:
        self._tvs = tvs
        self._videos = videos
        self._controller = controller
        self._urls = urls
        self._catalog = catalog
        self._cinema = cinema
        self._queues = queues
        self._ids = ids
        self._enhancement = enhancement
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._playing: dict[str, _Playing] = {}
        self._queue_errors: dict[str, str] = {}
        self._preparing: dict[str, asyncio.Task] = {}
        self._preparation_status: dict[str, PlaybackStatus] = {}

    async def play(self, tv_id: str, video_id: str) -> PlaybackStatus:
        async with self._locks[tv_id]:
            tv = self._tvs.get(tv_id).tv
            await self._enhancement.retry_failed(video_id=video_id)
            return await self._begin(
                tv, lambda: self._play_video(tv, video_id),
                PlaybackStatus(state=PlaybackState.TRANSITIONING, video_id=video_id, seekable=False),
            )

    async def play_stream(
        self, tv_id: str, ref: StreamRef, title: str, translation: str | None = None
    ) -> PlaybackStatus:
        async with self._locks[tv_id]:
            tv = self._tvs.get(tv_id).tv
            await self._enhancement.retry_failed(ref=ref, title=title)
            async def start():
                status = await self._play_stream(tv, ref, title)
                self._cinema.started(ref, translation)
                return status
            return await self._begin(tv, start, PlaybackStatus(
                state=PlaybackState.TRANSITIONING, title=title, stream=ref, seekable=False,
            ))

    async def _begin(self, tv, action, status):
        previous = self._preparing.pop(tv.id, None)
        if previous:
            previous.cancel()
        self._preparation_status.pop(tv.id, None)
        try:
            return await action()
        except EnhancementPending:
            self._preparation_status[tv.id] = status
            self._preparing[tv.id] = asyncio.create_task(self._await_preparation(tv, action))
            return status

    async def _await_preparation(self, tv, action):
        try:
            while True:
                await asyncio.sleep(2)
                async with self._locks[tv.id]:
                    try:
                        await action()
                    except EnhancementPending:
                        continue
                    self._preparation_status.pop(tv.id, None)
                    return
        except EasyTvError as exc:
            self._preparation_status[tv.id] = PlaybackStatus(state=PlaybackState.STOPPED, error=str(exc))
        except Exception:
            log.exception("Failed to start enhanced playback")
            self._preparation_status[tv.id] = PlaybackStatus(
                state=PlaybackState.STOPPED, error="Не удалось запустить улучшенное видео",
            )
        finally:
            if self._preparing.get(tv.id) is asyncio.current_task():
                self._preparing.pop(tv.id, None)

    async def close(self):
        tasks = list(self._preparing.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    def enhancement_queue(self):
        # Limit speculative work; later entries become eligible as the queue advances.
        return [item for tv in self._tvs.list() for item in self._queues.get(tv.tv.id)[:2]]

    def _ready_video(self, video_id: str) -> Video:
        video = self._videos.get(video_id)
        if video.status is not VideoStatus.READY or video.path is None:
            raise VideoNotReady(video_id)
        return video

    async def _play_video(self, tv: Tv, video_id: str) -> PlaybackStatus:
        video = self._ready_video(video_id)
        job = await self._enhancement.playback(video_id=video_id)
        url = self._urls.url_for_path(job.path, tv) if job else self._urls.url_for(video, tv)
        media = MediaItem(url=url, title=video.title, mime="video/mp4" if job else video.mime,
                          seekable=not job or job.state == "ready")
        return await self._start(tv, media, PlaybackStatus(
            state=PlaybackState.TRANSITIONING, video_id=video_id,
            enhancement_notice=self._enhancement.notice(video_id=video_id),
            enhancement_id=job.id if job else None, seekable=not job or job.state == "ready",
        ))

    async def _play_stream(self, tv: Tv, ref: StreamRef, title: str) -> PlaybackStatus:
        # Resolve at playback time since the CDN link can expire while the episode waits in the queue.
        job = await self._enhancement.playback(ref=ref, title=title)
        if not job:
            await self._catalog.resolve(ref)
        media = MediaItem(url=self._urls.url_for_path(job.path if job else ref.path, tv), title=title, mime="video/mp4",
                          seekable=not job or job.state == "ready")
        status = PlaybackStatus(state=PlaybackState.TRANSITIONING, title=title, stream=ref,
                                enhancement_notice=self._enhancement.notice(ref=ref),
                                enhancement_id=job.id if job else None, seekable=not job or job.state == "ready")
        return await self._start(tv, media, status)

    async def _start(self, tv: Tv, media: MediaItem, status: PlaybackStatus) -> PlaybackStatus:
        # A failed AVTransport play can still have replaced or stopped the old media.
        self._reset_end_sample(tv.id)
        await self._controller.play(tv, media)
        self._playing[tv.id] = _Playing(status=status, uri=media.url, started_at=monotonic())
        return status

    def queue(self, tv_id: str) -> tuple[tuple[QueueItem, ...], str | None]:
        self._tvs.get(tv_id)
        return self._queues.get(tv_id), self._queue_errors.get(tv_id)

    async def enqueue_video(self, tv_id: str, video_id: str) -> None:
        async with self._locks[tv_id]:
            self._tvs.get(tv_id)
            video = self._ready_video(video_id)
            self._enqueue(tv_id, QueueItem(id=self._ids.new_id(), title=video.title, video_id=video_id))

    async def enqueue_stream(self, tv_id: str, ref: StreamRef, title: str, translation: str | None) -> None:
        async with self._locks[tv_id]:
            self._tvs.get(tv_id)
            self._enqueue(tv_id, QueueItem(id=self._ids.new_id(), title=title, stream=ref, translation=translation))

    def _enqueue(self, tv_id: str, item: QueueItem) -> None:
        items = self._queues.get(tv_id)
        if any((queued.video_id, queued.stream) == (item.video_id, item.stream) for queued in items):
            return
        self._queues.save(tv_id, (*items, item))

    async def remove_queued(self, tv_id: str, item_id: str) -> None:
        async with self._locks[tv_id]:
            self._tvs.get(tv_id)
            items = self._queues.get(tv_id)
            remaining = tuple(item for item in items if item.id != item_id)
            if remaining == items:
                return
            self._queues.save(tv_id, remaining)
            if items[0].id == item_id:
                self._queue_errors.pop(tv_id, None)

    async def next(self, tv_id: str, item_id: str) -> PlaybackStatus:
        async with self._locks[tv_id]:
            tv = self._tvs.get(tv_id).tv
            items = self._queues.get(tv_id)
            if not items or items[0].id != item_id:
                raise QueueChanged()
            await self._enhancement.retry_failed(video_id=items[0].video_id, ref=items[0].stream, title=items[0].title)
            return await self._begin(tv, lambda: self._play_next(tv, items), PlaybackStatus(
                state=PlaybackState.TRANSITIONING, title=items[0].title, seekable=False,
            ))

    async def _play_next(self, tv: Tv, items: tuple[QueueItem, ...]) -> PlaybackStatus:
        item = items[0]
        current = self._queues.get(tv.id)
        if not current or current[0].id != item.id:
            raise QueueChanged()
        if item.stream is not None:
            status = await self._play_stream(tv, item.stream, item.title)
        else:
            assert item.video_id is not None
            status = await self._play_video(tv, item.video_id)
        self._queues.save(tv.id, current[1:])
        self._queue_errors.pop(tv.id, None)
        if item.stream is not None:
            self._cinema.started(item.stream, item.translation)
        return status

    def _reset_end_sample(self, tv_id: str) -> None:
        playing = self._playing.get(tv_id)
        if playing:
            playing.near_end_at = None

    async def watch_queues(self) -> None:
        """Advance active queues independently of browser polling and of other TVs."""
        pending: dict[str, asyncio.Task[None]] = {}
        async with asyncio.TaskGroup() as group:
            while True:
                pending = {tv_id: task for tv_id, task in pending.items() if not task.done()}
                for view in self._tvs.list():
                    tv_id = view.tv.id
                    if (
                        view.online and tv_id in self._playing and tv_id not in pending
                        and tv_id not in self._queue_errors and tv_id not in self._preparing and self._queues.get(tv_id)
                    ):
                        pending[tv_id] = group.create_task(self._check_queue(view.tv))
                await asyncio.sleep(1)

    async def _check_queue(self, tv: Tv) -> None:
        async with self._locks[tv.id]:
            playing = self._playing.get(tv.id)
            items = self._queues.get(tv.id)
            if not playing or not items or tv.id in self._queue_errors:
                return
            try:
                await self._advance_if_finished(tv, playing, items)
            except EasyTvError as exc:
                self._queue_errors[tv.id] = str(exc)
            except Exception:
                log.exception("Failed to advance the playback queue on %s", tv.id)
                self._queue_errors[tv.id] = "Не удалось запустить следующее видео"

    async def _advance_if_finished(self, tv: Tv, playing: _Playing, items: tuple[QueueItem, ...]) -> None:
        info = await self._controller.info(tv)
        now = monotonic()
        if info.state in _IDLE_STATES:
            near_end = playing.near_end_at
            if near_end is not None and now - near_end <= _END_SAMPLE_MAX_AGE_S:
                self._playing.pop(tv.id)
                await self._begin(tv, lambda: self._play_next(tv, items), PlaybackStatus(
                    state=PlaybackState.TRANSITIONING, title=items[0].title, seekable=False,
                ))
            elif now - playing.started_at > _PLAY_START_GRACE_S:
                self._playing.pop(tv.id)
            return

        if info.track_uri and info.track_uri != playing.uri:
            self._playing.pop(tv.id)
            return

        if info.state is PlaybackState.TRANSITIONING:
            return

        # STOPPED alone could be the TV remote, a failure or an app switch.
        position, duration = info.position_s, info.duration_s
        at_end = (
            info.state is PlaybackState.PLAYING and info.track_uri == playing.uri
            and position is not None and duration is not None and 0 < position <= duration
            and duration - position <= _END_MARGIN_S
        )
        playing.near_end_at = now if at_end else None

    async def pause(self, tv_id: str) -> None:
        tv = self._tvs.get(tv_id).tv
        async with self._locks[tv_id]:
            self._reset_end_sample(tv_id)
            await self._controller.pause(tv)

    async def resume(self, tv_id: str) -> None:
        tv = self._tvs.get(tv_id).tv
        async with self._locks[tv_id]:
            await self._controller.resume(tv)

    async def seek(self, tv_id: str, seconds: int, *, relative: bool = False) -> None:
        tv = self._tvs.get(tv_id).tv
        async with self._locks[tv_id]:
            playing = self._playing.get(tv_id)
            if tv_id in self._preparing or (playing and playing.status.enhancement_id
                    and not self._enhancement.complete(playing.status.enhancement_id)):
                raise PlaybackNotSeekable("Перемотка улучшенного видео доступна после завершения обработки")
            info = await self._controller.info(tv)
            if info.state not in (PlaybackState.PLAYING, PlaybackState.PAUSED):
                raise PlaybackNotSeekable("Перемотка доступна во время воспроизведения или паузы")
            target = seconds
            if relative:
                if info.position_s is None:
                    raise PlaybackNotSeekable("Телевизор не сообщил текущую позицию видео")
                target += info.position_s
            target = max(0, target)
            if info.duration_s is not None:
                target = min(target, info.duration_s)
            self._reset_end_sample(tv_id)
            await self._controller.seek(tv, target)

    async def stop(self, tv_id: str) -> None:
        tv = self._tvs.get(tv_id).tv
        async with self._locks[tv_id]:
            task = self._preparing.pop(tv_id, None)
            if task:
                task.cancel()
            self._preparation_status.pop(tv_id, None)
            self._reset_end_sample(tv_id)
            await self._controller.stop(tv)
            self._playing.pop(tv_id, None)

    async def status(self, tv_id: str) -> PlaybackStatus:
        tv = self._tvs.get(tv_id).tv
        preparation = self._preparation_status.get(tv_id)
        if preparation and not preparation.error:
            return preparation
        info = await self._controller.info(tv)
        playing = self._playing.get(tv_id)
        status = (
            playing.status
            if playing and info.state not in _IDLE_STATES and info.track_uri in (None, playing.uri)
            else PlaybackStatus(state=info.state)
        )
        seekable = not status.enhancement_id or self._enhancement.complete(status.enhancement_id)
        return replace(status, state=info.state, position_s=info.position_s, duration_s=info.duration_s,
                       seekable=seekable, error=preparation.error if preparation else status.error)
