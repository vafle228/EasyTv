"""Real HTTP/use-case flow with a fake GPU port; no network or television required."""

import time
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient

from easytv.api.app import create_app
from easytv.config import Settings
from easytv.container import build_container
from easytv.core.errors import EnhancementNotNeeded, EnhancementUnavailable
from easytv.core.models import EnhancementJob, EnhancementSettings, EnhancementSource
from easytv.infrastructure.enhancement import JsonEnhancementSettings, RelayVsrClient

from test_scenarios import FakeController, FakeDiscovery, FakeDownloader, FakeLocator
from test_catalog import FakeSite, FRIREN

TV = "/api/tvs/tv-living"


class FakeEnhancer:
    def __init__(self):
        self.available = True
        self.items = {}
        self.requests = []
        self.retained = set()
        self.next_state = "pending"
        self.rejection = None

    async def health(self):
        return self.available, None if self.available else "CUDA недоступна"

    async def jobs(self):
        return list(self.items.values())

    async def submit(self, source, *, foreground, retry=False):
        self.requests.append((source, foreground, retry))
        if self.rejection:
            raise self.rejection
        job = self.items.get(source.key)
        if job is None or retry:
            job = EnhancementJob(id=f"{len(self.items) + 1:064x}", key=source.key, state=self.next_state,
                                 stream_ready=self.next_state in {"ready", "running"})
            self.items[source.key] = job
        return job

    async def retain(self, keys):
        self.retained = keys

    def update(self, state, **kwargs):
        for key, job in self.items.items():
            self.items[key] = replace(job, state=state, **kwargs)


@pytest.fixture
def ai_env(tmp_path):
    worker, controller = FakeEnhancer(), FakeController()
    container = build_container(
        Settings(data_dir=tmp_path, discovery_interval_s=0, public_host="192.168.0.10"),
        discovery=FakeDiscovery(), locator=FakeLocator(), controller=controller,
        downloader=FakeDownloader(), enhancer=worker,
        catalog_source=FakeSite(),
    )
    with TestClient(create_app(container)) as client:
        client.post("/api/tvs/refresh")
        video = client.post("/api/videos/upload", files={"file": ("movie.mp4", b"original-content", "video/mp4")}).json()
        yield client, container, worker, controller, video["id"]


def enable(client, streaming=True):
    response = client.put("/api/enhancement", json={"enabled": True, "streaming": streaming})
    assert response.status_code == 200


def eventually(action, condition):
    deadline = time.monotonic() + 7
    while time.monotonic() < deadline:
        value = action()
        if condition(value):
            return value
        time.sleep(0.05)
    pytest.fail(f"Preparation did not complete: {value!r}")


def test_disabled_keeps_original_and_range(ai_env):
    client, _, worker, controller, video = ai_env
    assert client.post(f"{TV}/play", json={"videoId": video}).status_code == 200
    assert "/media/" in controller.commands[0][2].url
    assert not worker.requests
    media = client.get(f"/media/{video}", headers={"Range": "bytes=0-7"})
    assert media.status_code == 206 and media.content == b"original"
    assert "contentFeatures.dlna.org" in media.headers


def test_unavailable_worker_does_not_enable_or_replace_settings(ai_env):
    client, container, worker, _, _ = ai_env
    worker.available = False
    response = client.put("/api/enhancement", json={"enabled": True})
    assert response.status_code == 503 and "CUDA" in response.json()["detail"]
    assert not container.enhancement.settings.get().enabled


def test_setting_survives_restart(ai_env):
    client, container, *_ = ai_env
    enable(client, streaming=False)
    reloaded = JsonEnhancementSettings(container.settings.data_dir / "enhancement.json")
    assert reloaded.get() == EnhancementSettings(enabled=True, streaming=False)


def test_new_play_waits_then_starts_enhanced_url_without_second_click(ai_env):
    client, container, worker, controller, video = ai_env
    enable(client)
    result = client.post(f"{TV}/play", json={"videoId": video})
    assert result.json()["state"] == "transitioning" and not controller.commands
    worker.update("running", stream_ready=True)
    eventually(lambda: controller.commands, bool)
    assert "/enhanced/" in controller.commands[0][2].url
    assert client.get(f"{TV}/playback").json()["enhanced"]
    assert client.post(f"{TV}/seek", json={"positionS": 5}).status_code == 409
    worker.update("ready", stream_ready=True)
    client.get("/api/enhancement")
    assert client.post(f"{TV}/seek", json={"positionS": 5}).status_code == 204
    assert container.library.get(video).path.read_bytes() == b"original-content"


def test_stop_cancels_pending_tv_start(ai_env):
    client, _, worker, controller, video = ai_env
    enable(client)
    client.post(f"{TV}/play", json={"videoId": video})
    assert client.post(f"{TV}/stop").status_code == 204
    worker.update("ready", stream_ready=True)
    time.sleep(2.2)
    assert all(command[0] != "play" for command in controller.commands)


def test_full_file_mode_browser_waits_and_failed_job_is_explicit(ai_env):
    client, _, worker, _, video = ai_env
    enable(client, streaming=False)
    worker.next_state = "running"
    body = {"videoId": video}
    result = client.post("/api/enhancement/prepare", json=body).json()
    assert result["url"] is None and result["job"]["streamReady"]
    worker.update("failed", error="Недостаточно памяти")
    result = client.post("/api/enhancement/prepare", json=body).json()
    assert result["url"] is None and result["job"]["error"] == "Недостаточно памяти"
    worker.next_state = "ready"
    result = client.post("/api/enhancement/prepare", json={**body, "retry": True}).json()
    assert result["url"].startswith("/enhanced/")


def test_queue_prepares_in_background_and_removal_releases_job(ai_env):
    client, _, worker, controller, video = ai_env
    enable(client)
    client.post(f"{TV}/queue", json={"videoId": video})
    eventually(lambda: worker.requests, bool)
    assert worker.requests[0][1] is False
    assert not controller.commands
    head = client.get(f"{TV}/queue").json()["items"][0]["id"]
    client.delete(f"{TV}/queue/{head}")
    eventually(lambda: worker.retained, lambda keys: not keys)


def test_queue_keeps_head_while_preparing_then_advances(ai_env):
    client, _, worker, controller, video = ai_env
    enable(client, streaming=False)
    client.post(f"{TV}/queue", json={"videoId": video})
    head = client.get(f"{TV}/queue").json()["items"][0]["id"]
    assert client.post(f"{TV}/next", json={"itemId": head}).status_code == 200
    assert client.get(f"{TV}/queue").json()["items"][0]["id"] == head
    worker.update("ready", stream_ready=True)
    eventually(lambda: client.get(f"{TV}/queue").json()["items"], lambda items: not items)
    assert len(controller.commands) == 1 and "/enhanced/" in controller.commands[0][2].url


def test_proxy_preserves_completed_ranges_and_head(ai_env):
    _, container, *_ = ai_env
    container.settings.relayvsr_url = "http://worker"
    def upstream(request):
        assert request.headers["range"] == "bytes=1-3"
        return httpx.Response(206, content=b"bcd" if request.method == "GET" else b"",
                              headers={"Content-Range": "bytes 1-3/6", "Accept-Ranges": "bytes", "Content-Length": "3"})
    with TestClient(create_app(container, stream_transport=httpx.MockTransport(upstream))) as client:
        for method in ("GET", "HEAD"):
            response = client.request(method, f"/enhanced/{'a' * 64}.mp4", headers={"Range": "bytes=1-3"})
            assert response.status_code == 206 and response.headers["content-range"] == "bytes 1-3/6"
            assert "DLNA.ORG_OP=01" in response.headers["contentFeatures.dlna.org"]
            assert response.content == (b"bcd" if method == "GET" else b"")


def test_catalog_preparation_reuses_stable_key_and_marks_watched_only_on_play(ai_env):
    client, _, worker, controller, _ = ai_env
    enable(client)
    client.post("/api/cinema", json={"titleId": FRIREN})
    source = {"titleId": FRIREN, "episode": 1, "translationId": "81"}
    client.post(f"{TV}/queue", json={"stream": source, "title": "Серия 1"})
    eventually(lambda: worker.requests, bool)
    request, foreground, _ = worker.requests[0]
    assert request.url.startswith("https://cdn.test/") and request.file is None and not foreground
    assert request.key.startswith("stream:/stream/")
    assert client.get("/api/cinema").json()[0]["watched"] == []
    worker.update("ready", stream_ready=True)
    head = client.get(f"{TV}/queue").json()["items"][0]["id"]
    assert client.post(f"{TV}/next", json={"itemId": head}).status_code == 200
    assert len(worker.requests) == 1  # reuse prepared output instead of resolving another expiring URL
    assert "/enhanced/" in controller.commands[0][2].url
    assert client.get("/api/cinema").json()[0]["watched"] == [1]


def test_manual_tv_retry_restarts_failure_but_polling_does_not(ai_env):
    client, _, worker, controller, video = ai_env
    enable(client)
    client.post(f"{TV}/play", json={"videoId": video})
    worker.update("failed", error="GPU недоступен")
    eventually(lambda: client.get(f"{TV}/playback").json(), lambda state: state["error"] is not None)
    assert not controller.commands
    assert len(worker.requests) == 1
    worker.next_state = "ready"
    assert client.post(f"{TV}/play", json={"videoId": video}).status_code == 200
    assert worker.requests[-1][2] is True
    assert len(controller.commands) == 1


@pytest.mark.parametrize("dimensions", [(1920, 1080), (2560, 1440), (3840, 2160)])
def test_full_hd_plays_original_with_notice_in_browser_tv_and_queue(ai_env, dimensions):
    client, container, worker, controller, video = ai_env
    enable(client)
    worker.rejection = EnhancementNotNeeded(*dimensions)
    body = {"videoId": video}
    prepared = client.post("/api/enhancement/prepare", json=body).json()
    assert prepared["url"] == f"/media/{video}" and prepared["job"] is None
    assert f"{dimensions[0]}×{dimensions[1]}" in prepared["notice"]
    assert client.post("/api/enhancement/prepare", json=body).json() == prepared
    playback = client.post(f"{TV}/play", json=body).json()
    assert not playback["enhanced"] and playback["seekable"] and playback["error"] is None
    assert playback["enhancementNotice"] == prepared["notice"]
    assert "/media/" in controller.commands[0][2].url
    status = client.get("/api/enhancement").json()
    assert status["jobs"] == []
    assert status["notices"][container.enhancement.key(video, None)] == prepared["notice"]
    assert len(worker.requests) == 1  # polling/prefetch must not repeatedly probe a skipped source
    client.post(f"{TV}/queue", json=body)
    queued = client.get(f"{TV}/queue").json()["items"][0]
    assert client.post(f"{TV}/next", json={"itemId": queued["id"]}).json()["enhancementNotice"]
    assert not client.get(f"{TV}/queue").json()["items"]
    assert len(worker.requests) == 1 and "/media/" in controller.commands[-1][2].url
    client.put("/api/enhancement", json={"enabled": False})
    assert client.post("/api/enhancement/prepare", json=body).json()["notice"] is None


def test_full_hd_catalog_stream_plays_original_and_retry_rechecks_source(ai_env):
    client, _, worker, controller, _ = ai_env
    enable(client)
    worker.rejection = EnhancementNotNeeded(1920, 1080)
    stream = {"titleId": FRIREN, "episode": 1, "translationId": "81"}
    body = {"stream": stream, "title": "Серия 1"}
    prepared = client.post("/api/enhancement/prepare", json=body).json()
    assert prepared["url"].startswith("/stream/") and prepared["notice"]
    worker.rejection = None
    worker.next_state = "ready"
    retried = client.post("/api/enhancement/prepare", json={**body, "retry": True}).json()
    assert retried["url"].startswith("/enhanced/") and retried["notice"] is None


def test_old_native_x4_cache_is_not_reused(ai_env):
    client, _, worker, _, video = ai_env
    old_key = f"video:{video}"
    worker.items[old_key] = EnhancementJob(id="a" * 64, key=old_key, state="ready")
    enable(client)
    result = client.post("/api/enhancement/prepare", json={"videoId": video}).json()
    assert result["url"] is None and result["job"]["state"] == "pending"
    assert result["job"]["id"] != "a" * 64
    assert len(client.get("/api/enhancement").json()["jobs"]) == 1


def test_worker_rejection_is_distinguished_from_probe_failure():
    import asyncio
    async def scenario():
        response = httpx.Response(409, json={"detail": {"code": "already_full_hd", "width": 1920, "height": 1080}})
        worker = RelayVsrClient("http://worker", httpx.MockTransport(lambda _: response))
        with pytest.raises(EnhancementNotNeeded, match="1920×1080"):
            await worker.submit(EnhancementSource(key="clip", file="clip.mp4"), foreground=True)
        for response in (httpx.Response(503, json={"detail": "private source address"}),
                         httpx.Response(409, json={"detail": {"code": "already_full_hd"}})):
            with pytest.raises(EnhancementUnavailable, match="не отвечает"):
                await worker.submit(EnhancementSource(key="clip", file="clip.mp4"), foreground=True)
    asyncio.run(scenario())
