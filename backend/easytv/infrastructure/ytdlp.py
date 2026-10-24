"""VideoDownloader port on top of yt-dlp (the maintained fork of youtube-dl, same API)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from easytv.core.models import DownloadResult
from easytv.core.ports import ProgressCallback

# H.264 + AAC in mp4 plays on practically every TV, including 2013 Samsungs.
FORMAT_WITH_FFMPEG = "bv*[vcodec^=avc1][height<={h}]+ba[ext=m4a]/b[ext=mp4][height<={h}]/b[ext=mp4]/b"
FORMAT_WITHOUT_FFMPEG = "b[ext=mp4]/b"


class YtDlpDownloader:
    def __init__(self, max_height: int = 1080) -> None:
        self._max_height = max_height

    def download(self, url: str, target_dir: Path, basename: str, on_progress: ProgressCallback) -> DownloadResult:
        from yt_dlp import YoutubeDL  # imported lazily: heavy module

        has_ffmpeg = shutil.which("ffmpeg") is not None
        stages = {"done": 0}

        def hook(d: dict[str, Any]) -> None:
            title = (d.get("info_dict") or {}).get("title")
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                fraction = (d.get("downloaded_bytes") or 0) / total if total else 0.0
                # video and audio are downloaded one after another when merging
                parts = 2 if has_ffmpeg and "+" in str((d.get("info_dict") or {}).get("format_id", "")) else 1
                on_progress(min((stages["done"] + fraction) / parts, 0.99), title)
            elif d.get("status") == "finished":
                stages["done"] += 1

        options: dict[str, Any] = {
            "format": (FORMAT_WITH_FFMPEG.format(h=self._max_height) if has_ffmpeg else FORMAT_WITHOUT_FFMPEG),
            "merge_output_format": "mp4",
            "outtmpl": str(target_dir / f"{basename}.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "progress_hooks": [hook],
        }
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise RuntimeError("yt-dlp не вернул информацию о ролике")
            path = _final_path(info, target_dir, basename, ydl.prepare_filename(info))
        on_progress(1.0, info.get("title"))
        return DownloadResult(path=path, title=info.get("title") or basename)


def _final_path(info: dict[str, Any], target_dir: Path, basename: str, prepared: str) -> Path:
    for item in info.get("requested_downloads") or []:
        candidate = item.get("filepath")
        if candidate and Path(candidate).exists():
            return Path(candidate)
    if Path(prepared).exists():
        return Path(prepared)
    matches = [p for p in target_dir.glob(f"{basename}.*") if p.suffix not in (".part", ".ytdl")]
    if not matches:
        raise RuntimeError("yt-dlp закончил работу, но файл не найден")
    return max(matches, key=lambda p: p.stat().st_mtime)
