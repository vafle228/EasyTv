from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path

from easytv.core.models import SavedTitle, TitleKind, Tv, Video, VideoSource, VideoStatus

log = logging.getLogger(__name__)


class JsonTvRepository:
    """TVs seen so far, persisted so that after a restart we know where to look for them."""

    def __init__(self, path: Path | None) -> None:
        self._path = path
        self._items: dict[str, Tv] = {}
        self._lock = threading.Lock()
        self._load()

    def upsert(self, tv: Tv) -> None:
        with self._lock:
            previous = self._items.get(tv.id)
            self._items[tv.id] = tv
        # last_seen changes every refresh; only write when something else changed
        if previous is None or replace(previous, last_seen=None) != replace(tv, last_seen=None):
            self._save()

    def get(self, tv_id: str) -> Tv | None:
        return self._items.get(tv_id)

    def list(self) -> list[Tv]:
        return list(self._items.values())

    def delete(self, tv_id: str) -> None:
        with self._lock:
            self._items.pop(tv_id, None)
        self._save()

    def _load(self) -> None:
        if not self._path or not self._path.exists():
            return
        try:
            for item in json.loads(self._path.read_text(encoding="utf-8")):
                tv = Tv(**{k: v for k, v in item.items() if k in Tv.__dataclass_fields__ and k != "last_seen"})
                self._items[tv.id] = tv
        except (OSError, ValueError, TypeError) as exc:
            log.warning("Cannot read %s: %s", self._path, exc)

    def _save(self) -> None:
        if not self._path:
            return
        with self._lock:
            data = [{k: v for k, v in asdict(tv).items() if k != "last_seen"} for tv in self._items.values()]
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self._path)


class JsonVideoRepository:
    """Video library kept in memory and persisted to a JSON file so it survives restarts."""

    def __init__(self, path: Path | None) -> None:
        self._path = path
        self._items: dict[str, Video] = {}
        self._lock = threading.Lock()
        self._load()

    def add(self, video: Video) -> None:
        with self._lock:
            self._items[video.id] = video
        self._save()

    def update(self, video: Video) -> None:
        self.add(video)

    def get(self, video_id: str) -> Video | None:
        return self._items.get(video_id)

    def list(self) -> list[Video]:
        return list(self._items.values())

    def delete(self, video_id: str) -> None:
        with self._lock:
            self._items.pop(video_id, None)
        self._save()

    def _load(self) -> None:
        if not self._path or not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.warning("Cannot read %s: %s", self._path, exc)
            return
        for item in raw:
            video = Video(
                id=item["id"],
                title=item["title"],
                source=VideoSource(item["source"]),
                status=VideoStatus(item["status"]),
                created_at=datetime.fromisoformat(item["created_at"]),
                path=Path(item["path"]) if item.get("path") else None,
                size=item.get("size"),
                origin_url=item.get("origin_url"),
                progress=item.get("progress", 0.0),
                error=item.get("error"),
            )
            if video.status in (VideoStatus.PENDING, VideoStatus.DOWNLOADING):
                video.status, video.error = VideoStatus.FAILED, "Загрузка прервана перезапуском"
            if video.status is VideoStatus.READY and (video.path is None or not video.path.exists()):
                continue  # file is gone
            self._items[video.id] = video

    def _save(self) -> None:
        if not self._path:
            return
        with self._lock:
            data = [
                {
                    "id": v.id,
                    "title": v.title,
                    "source": v.source.value,
                    "status": v.status.value,
                    "created_at": v.created_at.isoformat(),
                    "path": str(v.path) if v.path else None,
                    "size": v.size,
                    "origin_url": v.origin_url,
                    "progress": v.progress,
                    "error": v.error,
                }
                for v in self._items.values()
            ]
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self._path)


class JsonSavedTitleRepository:
    """Titles saved from sites (the cinema), persisted to a JSON file."""

    def __init__(self, path: Path | None) -> None:
        self._path = path
        self._items: dict[str, SavedTitle] = {}
        self._lock = threading.Lock()
        self._load()

    def upsert(self, item: SavedTitle) -> None:
        with self._lock:
            self._items[item.id] = item
        self._save()

    def get(self, title_id: str) -> SavedTitle | None:
        return self._items.get(title_id)

    def list(self) -> list[SavedTitle]:
        return list(self._items.values())

    def delete(self, title_id: str) -> None:
        with self._lock:
            self._items.pop(title_id, None)
        self._save()

    def _load(self) -> None:
        if not self._path or not self._path.exists():
            return
        try:
            for raw in json.loads(self._path.read_text(encoding="utf-8")):
                item = SavedTitle(
                    id=raw["id"],
                    source=raw["source"],
                    title=raw["title"],
                    kind=TitleKind(raw["kind"]),
                    added_at=datetime.fromisoformat(raw["added_at"]),
                    poster=raw.get("poster"),
                    original_title=raw.get("original_title"),
                    year=raw.get("year"),
                    episodes_total=raw.get("episodes_total"),
                    genres=tuple(raw.get("genres") or ()),
                    translation_id=raw.get("translation_id"),
                    translation=raw.get("translation"),
                    last_episode=raw.get("last_episode"),
                    watched=set(raw.get("watched") or ()),
                    updated_at=datetime.fromisoformat(raw["updated_at"]) if raw.get("updated_at") else None,
                )
                self._items[item.id] = item
        except (OSError, ValueError, KeyError, TypeError) as exc:
            log.warning("Cannot read %s: %s", self._path, exc)

    def _save(self) -> None:
        if not self._path:
            return
        with self._lock:
            data = [
                {
                    **asdict(t),
                    "kind": t.kind.value,
                    "genres": list(t.genres),
                    "watched": sorted(t.watched),
                    "added_at": t.added_at.isoformat(),
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                }
                for t in self._items.values()
            ]
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self._path)
