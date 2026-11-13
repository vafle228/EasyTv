"""Single GPU scheduler. Only completed outputs survive a worker restart."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import os
import signal
import struct
import sys
import time
from pathlib import Path

MODEL_VERSION = "e856773350f53036d825404c9ea9228e6dffadca-v1"
TERMINAL = {"ready", "failed", "cancelled"}


def has_fragment(path: Path) -> bool:
    """Only advertise a stream after a complete MP4 moof+mdat pair has been flushed."""
    if not path.exists():
        return False
    size = path.stat().st_size
    with path.open("rb") as source:
        position = 0
        fragment = False
        while position + 8 <= size:
            source.seek(position)
            length, kind = struct.unpack(">I4s", source.read(8))
            if length == 1:
                if position + 16 > size:
                    return False
                length = struct.unpack(">Q", source.read(8))[0]
            if length < 8 or position + length > size:
                return False
            if kind == b"moof":
                fragment = True
            if kind == b"mdat" and fragment:
                return True
            position += length
    return False


class Jobs:
    def __init__(self, cache: Path, limit_bytes: int, runner=None):
        self.cache = cache
        self.limit_bytes = limit_bytes
        self.runner = runner or self._infer
        self.items = {}
        self.sources = {}
        self.readers = {}
        self.active = None
        self.current = None
        self.wake = asyncio.Event()
        cache.mkdir(parents=True, exist_ok=True)
        for path in cache.glob("*.json"):
            try:
                item = json.loads(path.read_text())
                if item["state"] == "ready" and self.path(item["id"]).is_file():
                    self.items[item["id"]] = item
            except (ValueError, KeyError, OSError):
                continue
        for path in cache.glob("*.mp4"):
            if len(path.stem) == 64 and all(c in "0123456789abcdef" for c in path.stem) and path.stem not in self.items:
                path.unlink(missing_ok=True)

    def path(self, job_id):
        if len(job_id) != 64 or any(c not in "0123456789abcdef" for c in job_id):
            raise KeyError(job_id)
        return self.cache / f"{job_id}.mp4"

    def public(self, job_id):
        item = dict(self.items[job_id])
        item["stream_ready"] = item["state"] == "ready" or (
            item["state"] == "running" and has_fragment(self.path(job_id))
        )
        return item

    def submit(self, key, source, priority, retry=False):
        job_id = hashlib.sha256(f"{MODEL_VERSION}:{key}".encode()).hexdigest()
        old = self.items.get(job_id)
        if old and old["state"] not in {"failed", "cancelled"}:
            if old["state"] == "ready" and not self.path(job_id).exists():
                old = None
            else:
                old["priority"] = min(old["priority"], priority)
                old["accessed"] = time.time()
                self._prioritize(job_id, priority)
                return self.public(job_id)
        if old and old["state"] == "failed" and not retry:
            return self.public(job_id)
        if len([i for i in self.items.values() if i["state"] not in TERMINAL]) >= 100:
            raise ValueError("Очередь RelayVSR заполнена")
        self.sources[job_id] = source
        item = old if old is not None else {}
        item.update(id=job_id, key=key, state="pending", priority=priority,
                    progress=0, error=None, frames=0, speed=None, accessed=time.time())
        self.items[job_id] = item
        self._prioritize(job_id, priority)
        self.wake.set()
        return self.public(job_id)

    def _prioritize(self, job_id, priority):
        # An immediate play takes the GPU from precomputation; never interrupt a live reader.
        if priority == 0 and self.active and self.active != job_id and self.current:
            active = self.items[self.active]
            if active["priority"] > 0 and not self.readers.get(self.active):
                self.current.cancel()

    def cancel_background_except(self, keys):
        for job_id, item in self.items.items():
            if item["priority"] > 0 and item["key"] not in keys and item["state"] not in TERMINAL:
                item["state"] = "cancelled"
                self.sources.pop(job_id, None)
                if job_id == self.active and self.current:
                    self.current.cancel()

    def cleanup(self):
        files = [(self.path(k), v) for k, v in self.items.items() if self.path(k).exists()]
        total = sum(path.stat().st_size for path, _ in files)
        for path, item in sorted(files, key=lambda pair: pair[1]["accessed"]):
            if total <= self.limit_bytes:
                break
            if item["state"] != "ready" or self.readers.get(item["id"]) or item["id"] == self.active:
                continue
            total -= path.stat().st_size
            path.unlink(missing_ok=True)
            path.with_suffix(".json").unlink(missing_ok=True)
            self.items.pop(item["id"], None)

    async def serve(self):
        try:
            while True:
                pending = [i for i in self.items.values() if i["state"] == "pending"]
                if not pending:
                    self.wake.clear()
                    await self.wake.wait()
                    continue
                item = min(pending, key=lambda i: (i["priority"], i["accessed"]))
                job_id = item["id"]
                self.cleanup()
                self.path(job_id).unlink(missing_ok=True)
                self.active = job_id
                item["state"] = "loading"
                self.current = asyncio.create_task(self.runner(job_id, self.sources[job_id]))
                try:
                    await self.current
                    if item["state"] != "ready":
                        item.update(state="failed", error=item["error"] or "Обработка RelayVSR прервана")
                except asyncio.CancelledError:
                    if asyncio.current_task().cancelling():
                        raise
                    if item["state"] != "cancelled":
                        item.update(state="pending", frames=0, progress=0)
                except Exception:
                    item.update(state="failed", error="Сервис RelayVSR не смог завершить обработку")
                finally:
                    self.current = None
                    self.active = None
                if item["state"] == "ready":
                    temp = self.cache / f"{job_id}.tmp"
                    temp.write_text(json.dumps(item))
                    temp.replace(self.cache / f"{job_id}.json")
                elif item["state"] in TERMINAL:
                    self.path(job_id).unlink(missing_ok=True)
                if item["state"] in TERMINAL:
                    self.sources.pop(job_id, None)
        finally:
            if self.current:
                self.current.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self.current

    async def _infer(self, job_id, source):
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "worker.inference", stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, start_new_session=True,
        )
        try:
            process.stdin.write(json.dumps({"source": source, "output": str(self.path(job_id))}).encode())
            await process.stdin.drain()
            process.stdin.close()
            async for line in process.stdout:
                try:
                    update = json.loads(line)
                except ValueError:
                    continue
                self.items[job_id].update(update)
                self.cleanup()
                if self.path(job_id).exists() and self.path(job_id).stat().st_size > self.limit_bytes:
                    self.items[job_id].update(state="failed", error="Видео превысило лимит дискового кэша RelayVSR")
                    return
            code = await process.wait()
            if code and self.items[job_id]["state"] != "failed":
                self.items[job_id].update(state="failed", error=f"Процесс RelayVSR завершился с кодом {code}")
        finally:
            if process.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGTERM)
                try:
                    await asyncio.wait_for(process.wait(), 10)
                except TimeoutError:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                    await process.wait()
