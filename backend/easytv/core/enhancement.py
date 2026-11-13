"""Enhancement policy shared by TV playback, browser playback and queue precomputation."""

from __future__ import annotations

import asyncio
import logging

from .errors import EnhancementPending, EnhancementUnavailable, EasyTvError, VideoNotReady
from .models import EnhancementJob, EnhancementSettings, EnhancementSource, StreamRef, VideoStatus
from .ports import EnhancementSettingsRepository, VideoEnhancer

log = logging.getLogger(__name__)


class EnhancementService:
    def __init__(self, worker: VideoEnhancer, settings: EnhancementSettingsRepository, library, catalog):
        self.worker, self.settings, self.library, self.catalog = worker, settings, library, catalog
        self.jobs: dict[str, EnhancementJob] = {}
        self.titles: dict[str, str] = {}
        self.error: str | None = None
        self._lock = asyncio.Lock()

    @staticmethod
    def key(video_id: str | None, ref: StreamRef | None) -> str:
        return f"video:{video_id}" if video_id else f"stream:{ref.path}"

    async def configure(self, enabled: bool, streaming: bool):
        async with self._lock:
            if enabled:
                available, error = await self.worker.health()
                if not available:
                    raise EnhancementUnavailable(error or "RelayVSR недоступен")
            self.settings.save(EnhancementSettings(enabled=enabled, streaming=streaming))
            if not enabled:
                try:
                    await self.worker.retain(set())
                except EnhancementUnavailable:
                    pass

    async def refresh(self):
        jobs = await self.worker.jobs()
        self.jobs = {job.key: job for job in jobs}

    async def prepare(self, *, video_id=None, ref=None, title=None, foreground=False, retry=False):
        async with self._lock:
            if not self.settings.get().enabled:
                return None
            key = self.key(video_id, ref)
            await self.refresh()
            existing = self.jobs.get(key)
            if existing and existing.state not in {"failed", "cancelled"}:
                # Resubmit only to promote a background job; its original source stays in the worker.
                if not foreground or existing.state == "ready":
                    return existing
            if existing and existing.state == "failed" and not retry:
                return existing
            if ref and retry and existing and existing.state == "failed":
                self.catalog.forget(ref)
            if video_id:
                video = self.library.get(video_id)
                if video.status != VideoStatus.READY or video.path is None:
                    raise VideoNotReady(video_id)
                source = EnhancementSource(key=key, file=video.path.name)
                title = video.title
            else:
                stream = await self.catalog.resolve(ref)
                source = EnhancementSource(key=key, url=stream.url, headers=stream.headers)
            job = await self.worker.submit(source, foreground=foreground, retry=retry)
            self.jobs[key] = job
            self.titles[key] = title or key
            return job

    async def playback(self, *, video_id=None, ref=None, title=None):
        job = await self.prepare(video_id=video_id, ref=ref, title=title, foreground=True)
        if job is None:
            return None
        if job.state in {"failed", "cancelled"}:
            raise EnhancementUnavailable(job.error or "Улучшение видео отменено")
        if job.state != "ready" and not (self.settings.get().streaming and job.stream_ready):
            raise EnhancementPending()
        return job

    async def retry_failed(self, *, video_id=None, ref=None, title=None):
        if not self.settings.get().enabled:
            return
        await self.refresh()
        job = self.jobs.get(self.key(video_id, ref))
        if job and job.state == "failed":
            await self.prepare(video_id=video_id, ref=ref, title=title, foreground=True, retry=True)

    def complete(self, job_id: str) -> bool:
        return any(j.id == job_id and j.state == "ready" for j in self.jobs.values())

    async def prefetch(self, items):
        if not self.settings.get().enabled:
            return
        keys = {self.key(item.video_id, item.stream) for item in items}
        await self.worker.retain(keys)
        for item in items:
            try:
                await self.prepare(video_id=item.video_id, ref=item.stream, title=item.title)
            except EasyTvError as exc:
                self.error = str(exc)

    async def watch(self, queue_items):
        while True:
            if self.settings.get().enabled or any(job.state not in {"ready", "failed", "cancelled"} for job in self.jobs.values()):
                try:
                    self.error = None
                    await self.prefetch(queue_items())
                    await self.refresh()
                except EasyTvError as exc:
                    self.error = str(exc)
                except Exception:
                    log.exception("Enhancement queue poll failed")
                    self.error = "Не удалось обновить очередь улучшения"
            await asyncio.sleep(3)
