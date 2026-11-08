"""Scenario tests: the user's journeys through the HTTP API, with the network-facing ports faked."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event

import httpx
import pytest
from fastapi.testclient import TestClient

from easytv.api.app import create_app
from easytv.config import Settings
from easytv.container import build_container
from easytv.core.errors import TvCommandError
from easytv.core.models import DownloadResult, MediaItem, PlaybackInfo, PlaybackState, Tv
from easytv.infrastructure.fetch import HttpVideoDownloader
from easytv.infrastructure.repositories import JsonVideoRepository

LIVING_ROOM = Tv(
    id="tv-living",
    name="[TV] Samsung LED40",
    ip="192.168.0.72",
    control_url="http://192.168.0.72:7676/AVTransport/control",
    service_type="urn:schemas-upnp-org:service:AVTransport:1",
    manufacturer="Samsung Electronics",
    model="UE40F7000",
    location="http://192.168.0.72:7676/smp_15_",
)

BEDROOM = Tv(
    id="tv-bedroom",
    name="Samsung AU7170 43 TV",
    ip="192.168.0.180",
    control_url="http://192.168.0.180:9197/upnp/control/AVTransport1",
    service_type="urn:schemas-upnp-org:service:AVTransport:1",
    manufacturer="Samsung",
    model="UE43AU7170UXRU",
    location="http://192.168.0.180:9197/dmr",
)


class FakeDiscovery:
    def __init__(self) -> None:
        self.visible: list[Tv] = [LIVING_ROOM]

    async def discover(self) -> list[Tv]:
        return list(self.visible)


class FakeLocator:
    """TVs reachable over HTTP even when SSDP can't see them (the Docker case)."""

    def __init__(self) -> None:
        self.reachable: dict[str, Tv] = {}

    async def describe(self, location: str) -> Tv | None:
        return next((tv for tv in self.reachable.values() if tv.location == location), None)

    async def locate(self, address: str) -> Tv | None:
        return self.reachable.get(address) or await self.describe(address)


class FakeController:
    def __init__(self) -> None:
        self.commands: list[tuple[str, str, MediaItem | int | None]] = []
        self.state = PlaybackState.STOPPED
        self.position_s: int | None = None
        self.reject_seek = False
        self.reject_play = False
        self.track_uri: str | None = None
        self.position_sampled = Event()

    async def play(self, tv: Tv, media: MediaItem) -> None:
        if self.reject_play:
            raise TvCommandError("Телевизор отклонил воспроизведение")
        self.commands.append(("play", tv.id, media))
        self.track_uri = media.url
        self.state = PlaybackState.PLAYING
        self.position_s = 0

    async def pause(self, tv: Tv) -> None:
        self.commands.append(("pause", tv.id, None))
        self.state = PlaybackState.PAUSED

    async def resume(self, tv: Tv) -> None:
        self.commands.append(("resume", tv.id, None))
        self.state = PlaybackState.PLAYING

    async def seek(self, tv: Tv, position_s: int) -> None:
        if self.reject_seek:
            raise TvCommandError("Телевизор отклонил перемотку")
        self.commands.append(("seek", tv.id, position_s))
        self.position_s = position_s

    async def stop(self, tv: Tv) -> None:
        self.commands.append(("stop", tv.id, None))
        self.state = PlaybackState.STOPPED

    async def info(self, tv: Tv) -> PlaybackInfo:
        if self.state in (PlaybackState.PLAYING, PlaybackState.PAUSED):
            info = PlaybackInfo(state=self.state, position_s=self.position_s, duration_s=120, track_uri=self.track_uri)
            self.position_sampled.set()
            return info
        return PlaybackInfo(state=self.state)


class FakeDownloader:
    """Pretends to download from YouTube by writing a small file."""

    def __init__(self) -> None:
        self.fail = False

    def download(self, url, target_dir: Path, basename: str, on_progress) -> DownloadResult:
        on_progress(0.5, "Never Gonna Give You Up")
        if self.fail:
            raise RuntimeError("Video unavailable")
        path = target_dir / f"{basename}.mp4"
        path.write_bytes(b"youtube-video-bytes")
        return DownloadResult(path=path, title="Never Gonna Give You Up")


class ManualClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 10, 24, 20, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current


@pytest.fixture
def direct_responses() -> dict[str, httpx.Response]:
    return {}


@pytest.fixture
def env(tmp_path: Path, direct_responses):
    discovery, controller, downloader, clock = FakeDiscovery(), FakeController(), FakeDownloader(), ManualClock()
    locator = FakeLocator()
    settings = Settings(
        data_dir=tmp_path,
        public_host="192.168.0.10",
        port=8080,
        discovery_interval_s=0,  # tests trigger discovery explicitly
        offline_after_s=60,
        tv_hosts=["192.168.0.180"],
    )
    def serve_file(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return direct_responses.pop(str(request.url))

    direct_downloader = HttpVideoDownloader(transport=httpx.MockTransport(serve_file))
    container = build_container(
        settings, discovery=discovery, locator=locator, controller=controller, downloader=downloader,
        direct_downloader=direct_downloader, clock=clock,
    )
    with TestClient(create_app(container)) as client:
        yield client, discovery, controller, downloader, clock, locator


def _wait_ready(client: TestClient, video_id: str) -> dict:
    for _ in range(100):
        video = next(v for v in client.get("/api/videos").json() if v["id"] == video_id)
        if video["status"] in ("ready", "failed"):
            return video
        time.sleep(0.02)
    raise AssertionError("download did not finish")


@pytest.mark.parametrize(("path", "headers", "title", "extension", "mime"), [
    ("/Holiday.MP4?sig=AbCd", {"Content-Type": "application/octet-stream"}, "Holiday", ".mp4", "video/mp4"),
    ("/download?sig=AbCd", {"Content-Type": "video/mp4"}, "download", ".mp4", "video/mp4"),
    ("/download?sig=AbCd", {"Content-Type": "Video/WebM; charset=binary"}, "download", ".webm", "video/webm"),
    ("/file/42", {
        "Content-Type": "application/octet-stream",
        "Content-Disposition": "attachment; filename*=UTF-8''%D0%9A%D0%BB%D0%B8%D0%BF.mkv",
    }, "Клип", ".mkv", "video/x-matroska"),
    ("/file/42", {"Content-Type": "video/x-custom-container"}, "42", ".video", "video/x-custom-container"),
])
def test_direct_file_download_and_play(env, direct_responses, tmp_path, path, headers, title, extension, mime):
    client, _, controller, _, _, _ = env
    link = "https://media.example/redirect"
    direct_responses[link] = httpx.Response(302, headers={"Location": path})
    content = b"fixture video bytes"
    direct_responses["https://media.example" + path] = httpx.Response(200, headers=headers, content=content)

    response = client.post("/api/videos/direct", json={"url": link})
    assert response.status_code == 202
    pending = response.json()
    assert pending["status"] == "pending"
    assert pending["source"] == "direct"
    assert pending["originUrl"] == link
    video_id = pending["id"]

    ready = _wait_ready(client, video_id)
    assert (ready["status"], ready["title"], ready["size"], ready["progress"]) == ("ready", title, len(content), 1.0)
    assert not direct_responses
    client.post("/api/tvs/refresh")
    assert client.post("/api/tvs/tv-living/play", json={"videoId": video_id}).status_code == 200
    restored = JsonVideoRepository(tmp_path / "videos.json").get(video_id)
    assert restored is not None and restored.mime == mime
    _, _, media = controller.commands[-1]
    media_path = f"/media/{video_id}{extension}"
    assert media.url == "http://192.168.0.10:8080" + media_path
    assert media.mime == mime
    part = client.get(media_path, headers={"Range": "bytes=2-5"})
    assert part.status_code == 206
    assert part.headers["content-type"] == mime
    assert part.content == content[2:6]


@pytest.mark.parametrize(("status", "mime", "content", "error"), [
    (200, "text/html", b"<html>Expired link</html>", "Ссылка не ведёт напрямую на видеофайл"),
    (200, "video/vnd.mpegurl", b"#EXTM3U", "Ссылка не ведёт напрямую на видеофайл"),
    (200, "video/mp4", b"", "Сервер вернул пустой видеофайл"),
    (206, "video/mp4", b"partial response", "Сервер ответил HTTP 206"),
    (403, "text/plain", b"Forbidden", "Сервер ответил HTTP 403"),
])
def test_direct_file_download_fails_without_saving(env, direct_responses, tmp_path, status, mime, content, error):
    client, _, _, _, _, _ = env
    link = "https://media.example/clip.mp4"
    direct_responses[link] = httpx.Response(status, headers={"Content-Type": mime}, content=content)

    response = client.post("/api/videos/direct", json={"url": link})
    assert response.status_code == 202
    video = _wait_ready(client, response.json()["id"])
    assert video["status"] == "failed"
    assert video["error"] == error
    assert not list((tmp_path / "videos").iterdir())


@pytest.mark.parametrize("url", ["file:///clip.mp4", "https://", "https://media.example:bad/clip.mp4",
                                 "https://user:password@media.example/clip.mp4"])
def test_invalid_direct_url_is_not_queued(env, url):
    client, _, _, _, _, _ = env
    assert client.post("/api/videos/direct", json={"url": url}).status_code == 400
    assert client.get("/api/videos").json() == []


def test_deleted_direct_download_is_not_restored(env, direct_responses, tmp_path):
    client, _, _, _, _, _ = env
    started, resume, closed = Event(), Event(), Event()

    class PausedStream(httpx.SyncByteStream):
        def __iter__(self):
            started.set()
            assert resume.wait(5)
            yield b"x" * (1 << 20)

        def close(self):
            closed.set()

    link = "https://media.example/download"
    direct_responses[link] = httpx.Response(200, headers={"Content-Type": "video/mp4"}, stream=PausedStream())
    response = client.post("/api/videos/direct", json={"url": link})
    assert response.status_code == 202
    try:
        assert started.wait(5)
        assert client.delete(f"/api/videos/{response.json()['id']}").status_code == 204
    finally:
        resume.set()
    assert closed.wait(5)
    assert client.get("/api/videos").json() == []
    assert not list((tmp_path / "videos").iterdir())


def test_found_tv_plays_uploaded_file_and_streams_it(env):
    client, _, controller, _, _, _ = env

    # 1. TV appears on the dashboard after discovery
    tvs = client.post("/api/tvs/refresh").json()
    assert [(t["id"], t["name"], t["online"]) for t in tvs] == [("tv-living", "[TV] Samsung LED40", True)]

    # 2. User uploads a file from the computer
    content = bytes(range(256)) * 100
    video = client.post("/api/videos/upload", files={"file": ("Отпуск 2025.mp4", content, "video/mp4")}).json()
    assert video["status"] == "ready" and video["title"] == "Отпуск 2025"

    # 3. ...and plays it on the TV
    resp = client.post("/api/tvs/tv-living/play", json={"videoId": video["id"]})
    assert resp.status_code == 200
    _, tv_id, media = controller.commands[-1]
    assert tv_id == "tv-living"
    assert media.url == f"http://192.168.0.10:8080/media/{video['id']}.mp4"
    assert media.mime == "video/mp4"

    status = client.get("/api/tvs/tv-living/playback").json()
    assert status["state"] == "playing" and status["videoId"] == video["id"]

    # 4. The TV fetches the file the way DLNA players do: HEAD, then byte ranges
    path = media.url.removeprefix("http://192.168.0.10:8080")
    head = client.head(path)
    assert head.status_code == 200 and head.headers["content-length"] == str(len(content))
    assert head.headers["contentfeatures.dlna.org"].startswith("DLNA.ORG_OP=01")
    part = client.get(path, headers={"Range": "bytes=100-199"})
    assert part.status_code == 206
    assert part.headers["content-range"] == f"bytes 100-199/{len(content)}"
    assert part.content == content[100:200]
    assert client.get(path).content == content

    # 5. Pause / resume / stop
    for cmd in ("pause", "resume", "stop"):
        assert client.post(f"/api/tvs/tv-living/{cmd}").status_code == 204
    assert [c[0] for c in controller.commands] == ["play", "pause", "resume", "stop"]


def test_seek_uploaded_video_by_position_and_offset(env):
    client, _, controller, _, _, _ = env
    client.post("/api/tvs/refresh")
    video = client.post("/api/videos/upload", files={"file": ("clip.mp4", b"video", "video/mp4")}).json()
    base = "/api/tvs/tv-living"
    assert client.post(f"{base}/play", json={"videoId": video["id"]}).status_code == 200

    # Skip forward from zero, then choose an exact position.
    assert client.post(f"{base}/seek", json={"offsetS": 10}).status_code == 204
    assert controller.commands[-1] == ("seek", "tv-living", 10)
    assert client.post(f"{base}/seek", json={"positionS": 117}).status_code == 204
    assert controller.commands[-1] == ("seek", "tv-living", 117)
    assert client.post(f"{base}/seek", json={"offsetS": 10}).status_code == 204
    assert controller.commands[-1] == ("seek", "tv-living", 120)

    # Seeking while paused keeps the same video and does not resume playback.
    assert client.post(f"{base}/pause").status_code == 204
    assert client.post(f"{base}/seek", json={"positionS": 5}).status_code == 204
    response = client.post(f"{base}/seek", json={"offsetS": -10})
    assert response.status_code == 204 and response.content == b""
    assert controller.commands[-1] == ("seek", "tv-living", 0)
    status = client.get(f"{base}/playback").json()
    assert (status["state"], status["videoId"], status["positionS"]) == ("paused", video["id"], 0)


@pytest.mark.parametrize("body", [{}, {"positionS": -1}, {"positionS": 1.5}, {"positionS": 3, "offsetS": 10}])
def test_seek_rejects_invalid_target(env, body):
    client, _, controller, _, _, _ = env
    client.post("/api/tvs/refresh")
    assert client.post("/api/tvs/tv-living/seek", json=body).status_code == 422
    assert controller.commands == []


def test_seek_reports_missing_position_and_tv_rejection(env):
    client, _, controller, _, _, _ = env
    client.post("/api/tvs/refresh")
    seek = "/api/tvs/tv-living/seek"
    assert client.post("/api/tvs/unknown/seek", json={"positionS": 5}).status_code == 404
    assert client.post(seek, json={"positionS": 5}).status_code == 409
    controller.state = PlaybackState.PLAYING
    assert client.post(seek, json={"offsetS": 10}).status_code == 409

    controller.reject_seek = True
    response = client.post(seek, json={"positionS": 5})
    assert response.status_code == 502
    assert response.json() == {"detail": "Телевизор отклонил перемотку"}
    assert controller.commands == []


def test_youtube_video_is_downloaded_then_played(env):
    client, _, controller, _, _, _ = env
    client.post("/api/tvs/refresh")

    video = client.post("/api/videos/youtube", json={"url": "https://youtu.be/dQw4w9WgXcQ"}).json()
    assert video["source"] == "youtube" and video["status"] in ("pending", "downloading", "ready")

    # Not playable until the download finishes
    ready = _wait_ready(client, video["id"])
    assert ready["status"] == "ready"
    assert ready["title"] == "Never Gonna Give You Up"

    assert client.post("/api/tvs/tv-living/play", json={"videoId": video["id"]}).status_code == 200
    media = controller.commands[-1][2]
    assert client.get(media.url.removeprefix("http://192.168.0.10:8080")).content == b"youtube-video-bytes"


def test_user_errors_are_explained(env):
    client, _, _, downloader, _, _ = env
    client.post("/api/tvs/refresh")

    assert client.post("/api/videos/youtube", json={"url": "https://example.com/x"}).status_code == 422
    assert client.post("/api/videos/upload", files={"file": ("notes.txt", b"x", "text/plain")}).status_code == 415
    assert client.post("/api/tvs/nope/play", json={"videoId": "x"}).status_code == 404

    downloader.fail = True
    video = client.post("/api/videos/youtube", json={"url": "https://www.youtube.com/watch?v=xxxxxxxxxxx"}).json()
    failed = _wait_ready(client, video["id"])
    assert failed["status"] == "failed" and "unavailable" in failed["error"]
    resp = client.post("/api/tvs/tv-living/play", json={"videoId": video["id"]})
    assert resp.status_code == 409 and resp.json()["detail"]


def test_tv_that_disappears_is_shown_offline_and_library_survives_restart(env, tmp_path):
    client, discovery, _, _, clock, _ = env
    client.post("/api/tvs/refresh")
    client.post("/api/videos/upload", files={"file": ("clip.mkv", b"mkv", "video/x-matroska")})

    discovery.visible = []
    clock.current += timedelta(minutes=5)
    tvs = client.post("/api/tvs/refresh").json()
    assert [(t["id"], t["online"]) for t in tvs] == [("tv-living", False)]

    # Library is persisted in the data dir
    restarted = build_container(Settings(data_dir=tmp_path, discovery_interval_s=0), discovery=FakeDiscovery(),
                                controller=FakeController(), downloader=FakeDownloader())
    assert [v.title for v in restarted.library.list()] == ["clip"]


def test_tvs_invisible_to_ssdp_are_found_by_address(env, tmp_path):
    """Inside Docker multicast doesn't reach the TVs: they are found via configured or typed-in addresses."""
    client, discovery, _, _, clock, locator = env
    discovery.visible = []

    # Configured address (EASYTV_TV_HOSTS) resolves once the TV answers over HTTP
    assert client.post("/api/tvs/refresh").json() == []
    locator.reachable["192.168.0.180"] = BEDROOM
    assert [t["id"] for t in client.post("/api/tvs/refresh").json()] == ["tv-bedroom"]

    # A TV typed in by the user
    bad = client.post("/api/tvs", json={"address": "192.168.0.99"})
    assert bad.status_code == 422 and "192.168.0.99" in bad.json()["detail"]
    locator.reachable["192.168.0.72"] = LIVING_ROOM
    added = client.post("/api/tvs", json={"address": "192.168.0.72"})
    assert added.status_code == 201 and added.json()["online"] is True

    # Known TVs are re-checked through their description URL, so they stay online without SSDP
    clock.current += timedelta(minutes=5)
    tvs = client.post("/api/tvs/refresh").json()
    assert {(t["id"], t["online"]) for t in tvs} == {("tv-bedroom", True), ("tv-living", True)}

    # The list of TVs survives a restart (they show up as offline until the next check)
    restarted = build_container(Settings(data_dir=tmp_path, discovery_interval_s=0), discovery=FakeDiscovery(),
                                locator=FakeLocator(), controller=FakeController(), downloader=FakeDownloader())
    assert {(v.tv.id, v.online) for v in restarted.tvs.list()} == {("tv-bedroom", False), ("tv-living", False)}

    # Forget a TV
    assert client.delete("/api/tvs/tv-living").status_code == 204
    assert [t["id"] for t in client.get("/api/tvs").json()] == ["tv-bedroom"]
