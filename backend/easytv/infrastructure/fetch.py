"""Download direct HTTP video files to disk."""

from __future__ import annotations

import contextlib
import mimetypes
import re
from email.message import Message
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

import httpx

from easytv.core.models import SUPPORTED_EXTENSIONS, DownloadResult, mime_for
from easytv.core.ports import ProgressCallback

from .animego.client import USER_AGENT


class HttpFileFetcher:
    def __init__(self, timeout: float = 30) -> None:
        self._timeout = timeout

    def fetch(self, url: str, headers: dict[str, str], target: Path, on_progress: ProgressCallback) -> int:
        with httpx.stream(
            "GET", url, headers={"User-Agent": USER_AGENT, **headers}, timeout=self._timeout, follow_redirects=True
        ) as response:
            if response.status_code >= 400:
                raise RuntimeError(f"CDN ответил {response.status_code}")
            return _save_response(response, target, on_progress)


class HttpVideoDownloader:
    def __init__(self, timeout: float = 30, transport: httpx.BaseTransport | None = None) -> None:
        self._timeout = timeout
        self._transport = transport

    def download(self, url: str, target_dir: Path, basename: str, on_progress: ProgressCallback) -> DownloadResult:
        try:
            with httpx.Client(timeout=self._timeout, follow_redirects=True, transport=self._transport) as client:
                with client.stream("GET", url, headers={"User-Agent": USER_AGENT}) as response:
                    if response.status_code != 200:
                        raise RuntimeError(f"Сервер ответил HTTP {response.status_code}")
                    title, ext, mime = _video_metadata(response)
                    target = target_dir / f"{basename}{ext}"
                    on_progress(0, title)
                    _save_response(response, target, on_progress)
        except (httpx.RequestError, httpx.InvalidURL) as exc:
            raise RuntimeError("Не удалось скачать видео по ссылке") from exc
        return DownloadResult(path=target, title=title, content_type=mime)


def _save_response(response: httpx.Response, target: Path, on_progress: ProgressCallback) -> int:
    tmp = target.with_name(target.name + ".part")
    total = int(response.headers.get("content-length") or 0)
    done = 0
    try:
        with tmp.open("wb") as f:
            for chunk in response.iter_bytes(1 << 20):
                f.write(chunk)
                done += len(chunk)
                on_progress(done / total if total else 0, None)
        if not done:
            raise RuntimeError("Сервер вернул пустой видеофайл")
        tmp.replace(target)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise
    return done


_BINARY_TYPES = {"", "application/octet-stream", "binary/octet-stream", "application/force-download"}
_VIDEO_TYPE = re.compile(r"video/[a-z0-9][a-z0-9.+_-]*")
_FILE_EXTENSION = re.compile(r"\.[a-z0-9]{1,12}")
_EXTENSIONS_BY_MIME = {mime_for(ext): ext for ext in sorted(SUPPORTED_EXTENSIONS)}


def _is_video_type(mime: str) -> bool:
    return _VIDEO_TYPE.fullmatch(mime) is not None and "mpegurl" not in mime


def _video_metadata(response: httpx.Response) -> tuple[str, str, str]:
    mime = response.headers.get("content-type", "").partition(";")[0].strip().lower()
    disposition = Message()
    disposition["Content-Disposition"] = response.headers.get("content-disposition", "")
    paths = (
        disposition.get_filename() or "",
        unquote(response.url.path),
        unquote(response.history[0].request.url.path) if response.history else "",
    )
    names = [PurePosixPath(path.replace("\\", "/")).name for path in paths if path]
    for name in names:
        ext = PurePosixPath(name).suffix.lower()
        if not _FILE_EXTENSION.fullmatch(ext):
            continue
        guessed = mime_for(ext) if ext in SUPPORTED_EXTENSIONS else mimetypes.guess_type(f"video{ext}")[0] or ""
        if _is_video_type(guessed) and (mime in _BINARY_TYPES or mime == guessed):
            return PurePosixPath(name).stem, ext, guessed

    if _is_video_type(mime):
        ext = _EXTENSIONS_BY_MIME.get(mime) or mimetypes.guess_extension(mime) or ""
        if not _FILE_EXTENSION.fullmatch(ext):
            ext = ".video"
        name = next((name for name in names if name), "")
        return PurePosixPath(name).stem or "Видео по ссылке", ext, mime

    raise RuntimeError("Ссылка не ведёт напрямую на видеофайл")
