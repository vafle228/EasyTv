"""Use cases of site catalogs: browse a site, keep titles in the cinema, get a playable link right before watching."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timedelta

from .errors import StreamUnavailable, TitleNotSaved
from .models import CatalogTitle, Collection, Episode, SavedTitle, Stream, StreamRef, TitleDetails, Variant
from .ports import CatalogSource, Clock, SavedTitleRepository


class CatalogService:
    """Thin async facade over a `CatalogSource` (whose calls block on the network) plus a short-lived link cache.

    Links are cached per episode address because a TV asks for the same video many times while seeking,
    and the site must not be hit for each request. They are never persisted: they expire and are bound to our IP.
    """

    def __init__(
        self,
        source: CatalogSource,
        clock: Clock,
        max_height: int = 1080,
        link_ttl: timedelta = timedelta(minutes=30),
    ) -> None:
        self._source = source
        self._clock = clock
        self._max_height = max_height
        self._ttl = link_ttl
        self._links: dict[StreamRef, tuple[Stream, datetime]] = {}
        self._locks: dict[StreamRef, asyncio.Lock] = {}

    @property
    def name(self) -> str:
        return self._source.name

    async def search(self, query: str) -> list[CatalogTitle]:
        query = query.strip()
        if not query:
            return []
        return await asyncio.to_thread(self._source.search, query)

    def collections(self) -> list[Collection]:
        return self._source.collections()

    async def collection(self, collection_id: str, page: int = 1) -> list[CatalogTitle]:
        return await asyncio.to_thread(self._source.collection, collection_id, max(page, 1))

    async def title(self, title_id: str) -> TitleDetails:
        return await asyncio.to_thread(self._source.title, title_id)

    async def episodes(self, title_id: str) -> list[Episode]:
        return await asyncio.to_thread(self._source.episodes, title_id)

    async def variants(self, title_id: str, episode: int) -> list[Variant]:
        return await asyncio.to_thread(self._source.variants, title_id, episode)

    async def resolve(self, ref: StreamRef) -> Stream:
        """A direct MP4 link for the episode, fresh or from the cache."""
        lock = self._locks.setdefault(ref, asyncio.Lock())
        async with lock:  # a TV opens several connections at once: resolve only once
            cached = self._links.get(ref)
            now = self._clock.now()
            if cached and now - cached[1] < self._ttl:
                return cached[0]
            streams = await asyncio.to_thread(self._source.streams, ref)
            stream = self._pick(streams)
            self._links[ref] = (stream, now)
            return stream

    def forget(self, ref: StreamRef) -> None:
        """Drop a cached link the CDN no longer accepts."""
        self._links.pop(ref, None)

    def _pick(self, streams: list[Stream]) -> Stream:
        mp4 = [s for s in streams if s.kind == "mp4"]
        if not mp4:
            players = ", ".join(sorted({s.provider for s in streams})) or "плеер"
            raise StreamUnavailable(
                f"{players} отдаёт только HLS, а его без ffmpeg не показать. Выберите другую озвучку или плеер"
            )
        mp4.sort(key=lambda s: -(s.quality or 0))
        return next((s for s in mp4 if s.quality and s.quality <= self._max_height), mp4[-1])


class CinemaService:
    """Titles saved from sites, with the dub the user picked and the episodes they have started."""

    def __init__(self, repo: SavedTitleRepository, catalog: CatalogService, clock: Clock) -> None:
        self._repo = repo
        self._catalog = catalog
        self._clock = clock

    def list(self) -> list[SavedTitle]:
        return sorted(self._repo.list(), key=lambda t: t.updated_at or t.added_at, reverse=True)

    def find(self, title_id: str) -> SavedTitle | None:
        return self._repo.get(title_id)

    async def save(self, title_id: str) -> SavedTitle:
        existing = self._repo.get(title_id)
        if existing:
            return existing
        d = await self._catalog.title(title_id)
        item = SavedTitle(
            id=d.id,
            source=self._catalog.name,
            title=d.title,
            kind=d.kind,
            added_at=self._clock.now(),
            poster=d.poster,
            original_title=d.original_title,
            year=d.year,
            episodes_total=d.episodes_total,
            genres=d.genres,
        )
        self._repo.upsert(item)
        return item

    def remove(self, title_id: str) -> None:
        if not self._repo.get(title_id):
            raise TitleNotSaved(title_id)
        self._repo.delete(title_id)

    def started(self, ref: StreamRef, translation: str | None) -> None:
        """Remember where the user is: called whenever an episode of a saved title starts playing."""
        item = self._repo.get(ref.title_id)
        if not item:
            return
        self._repo.upsert(
            replace(
                item,
                translation_id=ref.translation_id,
                translation=translation or item.translation,
                last_episode=ref.episode,
                watched=item.watched | {ref.episode},
                updated_at=self._clock.now(),
            )
        )
