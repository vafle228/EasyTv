"""FileFetcher port: downloads a direct video link (an episode from a site) to disk with httpx."""

from __future__ import annotations

import contextlib
from pathlib import Path

import httpx

from easytv.core.ports import ProgressCallback

from .animego.client import USER_AGENT


class HttpFileFetcher:
    def __init__(self, timeout: float = 30) -> None:
        self._timeout = timeout

    def fetch(self, url: str, headers: dict[str, str], target: Path, on_progress: ProgressCallback) -> int:
        tmp = target.with_name(target.name + ".part")
        done = 0
        try:
            with httpx.stream(
                "GET", url, headers={"User-Agent": USER_AGENT, **headers}, timeout=self._timeout, follow_redirects=True
            ) as r:
                if r.status_code >= 400:
                    raise RuntimeError(f"CDN ответил {r.status_code}")
                total = int(r.headers.get("content-length") or 0)
                with tmp.open("wb") as f:
                    for chunk in r.iter_bytes(1 << 20):
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            on_progress(done / total, None)
            tmp.replace(target)
        except BaseException:
            with contextlib.suppress(OSError):
                tmp.unlink()
            raise
        return done
