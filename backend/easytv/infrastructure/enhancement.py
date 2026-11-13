from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

import httpx

from easytv.core.errors import EnhancementNotNeeded, EnhancementUnavailable
from easytv.core.models import EnhancementJob, EnhancementSettings, EnhancementSource


class JsonEnhancementSettings:
    def __init__(self, path: Path):
        self.path = path
        self.value = EnhancementSettings()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.value = EnhancementSettings(enabled=data.get("enabled") is True, streaming=data.get("streaming", True) is True)
            except (ValueError, OSError, AttributeError):
                logging.getLogger(__name__).warning("Cannot read enhancement settings; AI remains off")

    def get(self):
        return self.value

    def save(self, settings):
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(settings)), encoding="utf-8")
        temp.replace(self.path)
        self.value = settings


class RelayVsrClient:
    def __init__(self, url: str | None, transport=None):
        self.url = url
        self.transport = transport

    async def _request(self, method, path, **kwargs):
        if not self.url:
            raise EnhancementUnavailable("Контейнер RelayVSR не настроен. Запустите EasyTv с ИИ: run.cmd ai")
        try:
            async with httpx.AsyncClient(base_url=self.url, timeout=20, transport=self.transport) as client:
                response = await client.request(method, path, **kwargs)
                if path == "/jobs" and method == "POST" and response.status_code == 409:
                    payload = response.json()
                    detail = payload.get("detail") if isinstance(payload, dict) else None
                    if isinstance(detail, dict) and detail.get("code") == "already_full_hd":
                        width, height = detail.get("width"), detail.get("height")
                        if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
                            raise EnhancementNotNeeded(width, height)
                response.raise_for_status()
                return response.json() if response.status_code != 204 else None
        except (httpx.HTTPError, ValueError):
            raise EnhancementUnavailable("Контейнер RelayVSR не отвечает или отклонил запрос. Проверьте его логи.") from None

    @staticmethod
    def _job(data):
        return EnhancementJob(**{k: v for k, v in data.items() if k in EnhancementJob.__dataclass_fields__})

    async def health(self):
        try:
            data = await self._request("GET", "/health")
            return bool(data["available"]), data.get("error")
        except EnhancementUnavailable as exc:
            return False, str(exc)

    async def jobs(self):
        return [self._job(data) for data in await self._request("GET", "/jobs")]

    async def submit(self, source: EnhancementSource, *, foreground: bool, retry=False):
        data = asdict(source)
        key = data.pop("key")
        return self._job(await self._request("POST", "/jobs", json={
            "key": key, "source": data, "priority": 0 if foreground else 1, "retry": retry,
        }))

    async def retain(self, keys: set[str]):
        await self._request("POST", "/jobs/retain", json={"keys": sorted(keys)})
