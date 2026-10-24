from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from pathlib import Path


class LocalVideoStorage:
    """VideoStorage port: video files in a directory on disk."""

    def __init__(self, directory: Path) -> None:
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def directory(self) -> Path:
        return self._dir

    async def save(self, name: str, chunks: AsyncIterator[bytes]) -> tuple[Path, int]:
        path = self._dir / name
        tmp = path.with_name(path.name + ".part")
        size = 0
        try:
            with tmp.open("wb") as f:
                async for chunk in chunks:
                    f.write(chunk)
                    size += len(chunk)
            tmp.replace(path)
        except BaseException:
            with contextlib.suppress(OSError):
                tmp.unlink()
            raise
        return path, size

    def delete(self, path: Path) -> None:
        resolved = path.resolve()
        if self._dir.resolve() in resolved.parents:
            with contextlib.suppress(FileNotFoundError):
                resolved.unlink()
