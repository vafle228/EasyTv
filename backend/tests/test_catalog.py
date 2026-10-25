"""Scenarios of the site catalog: find an anime, keep it in the cinema, watch an episode on a TV or in the browser."""

from __future__ import annotations

import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from easytv.api.app import create_app
from easytv.config import Settings
from easytv.container import build_container
from easytv.core.errors import CatalogItemNotFound
from easytv.core.models import CatalogTitle, Episode, Stream, StreamRef, TitleDetails, TitleKind, Variant

from test_scenarios import FakeController, FakeDiscovery, FakeDownloader, ManualClock

FRIREN = "provozhayuschaya-v-posledniy-put-friren-2430"
VIDEO = bytes(range(256)) * 400  # what the CDN serves


class FakeSite:
    """animego with one title, two episodes and two dubs; the second dub exists only as HLS."""

    name = "animego"

    def __init__(self) -> None:
        self.resolved: list[StreamRef] = []

    def search(self, query: str) -> list[CatalogTitle]:
        return [CatalogTitle(id=FRIREN, title="Провожающая в последний путь Фрирен", kind="Сериал", year="2023")]

    def title(self, title_id: str) -> TitleDetails:
        if title_id != FRIREN:
            raise CatalogItemNotFound(f"нет тайтла {title_id}")
        return TitleDetails(id=FRIREN, title="Провожающая в последний путь Фрирен", kind=TitleKind.SERIES, episodes_total=28)

    def episodes(self, title_id: str) -> list[Episode]:
        return [Episode(1, "The Journey's End"), Episode(2)]

    def variants(self, title_id: str, episode: int) -> list[Variant]:
        return [Variant("81", "Dream Cast", ("cvh", "kodik")), Variant("30", "Субтитры", ("aniboom",))]

    def streams(self, ref: StreamRef) -> list[Stream]:
        self.resolved.append(ref)
        if ref.translation_id == "30":
            return [Stream("aniboom", "Субтитры", "hls", 1080, "https://cdn.test/master.m3u8")]
        n = len(self.resolved)
        return [
            Stream("cvh", "Dream Cast", "mp4", 1080, f"https://cdn.test/v{n}.mp4"),
            Stream("cvh", "Dream Cast", "mp4", 720, f"https://cdn.test/v{n}-720.mp4"),
        ]


class FakeCdn:
    """Serves VIDEO with Range; links listed in `expired` answer 403."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.expired: set[str] = set()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if str(request.url) in self.expired:
            return httpx.Response(403)
        rng = request.headers.get("range")
        if rng:
            first, last = rng.removeprefix("bytes=").split("-")
            start, end = int(first), int(last) if last else len(VIDEO) - 1
            return httpx.Response(
                206,
                content=VIDEO[start : end + 1],
                headers={"Content-Range": f"bytes {start}-{end}/{len(VIDEO)}", "Content-Type": "video/mp4"},
            )
        return httpx.Response(200, content=VIDEO, headers={"Content-Type": "video/mp4"})


class FakeFetcher:
    def fetch(self, url, headers, target: Path, on_progress) -> int:
        on_progress(0.5, None)
        target.write_bytes(VIDEO)
        return len(VIDEO)


@pytest.fixture
def env(tmp_path: Path):
    site, cdn, controller = FakeSite(), FakeCdn(), FakeController()
    settings = Settings(data_dir=tmp_path, public_host="192.168.0.10", port=8080, discovery_interval_s=0)
    container = build_container(
        settings,
        discovery=FakeDiscovery(),
        controller=controller,
        downloader=FakeDownloader(),
        catalog_source=site,
        fetcher=FakeFetcher(),
        clock=ManualClock(),
    )
    with TestClient(create_app(container, httpx.MockTransport(cdn))) as client:
        client.post("/api/tvs/refresh")
        yield client, site, cdn, controller


def test_find_save_and_watch_on_tv(env):
    client, site, cdn, controller = env

    # 1. Search on the site, open the title, pick an episode and a dub
    hits = client.get("/api/catalog/search", params={"q": "фрирен"}).json()
    assert [(h["id"], h["saved"]) for h in hits] == [(FRIREN, False)]
    title = client.get(f"/api/catalog/titles/{FRIREN}").json()
    assert title["kind"] == "series" and title["saved"] is None
    assert [e["number"] for e in client.get(f"/api/catalog/titles/{FRIREN}/episodes").json()] == [1, 2]
    dubs = client.get(f"/api/catalog/titles/{FRIREN}/variants", params={"episode": 2}).json()
    assert dubs[0] == {"translationId": "81", "translation": "Dream Cast", "providers": ["cvh", "kodik"]}

    # 2. Keep it in the cinema
    assert client.post("/api/cinema", json={"titleId": FRIREN}).status_code == 201
    assert client.get("/api/catalog/search", params={"q": "фрирен"}).json()[0]["saved"] is True

    # 3. Show episode 2 on the TV: it gets our proxy address, not the CDN link
    body = {"titleId": FRIREN, "episode": 2, "translationId": "81", "title": "Фрирен, 2 серия", "translation": "Dream Cast"}
    resp = client.post("/api/tvs/tv-living/play-stream", json=body)
    assert resp.status_code == 200
    media = controller.commands[-1][2]
    assert media.url == f"http://192.168.0.10:8080/stream/animego/{FRIREN}/2/81/auto.mp4"
    status = client.get("/api/tvs/tv-living/playback").json()
    assert status["title"] == "Фрирен, 2 серия" and status["stream"]["episode"] == 2

    # 4. The TV reads it like a file: HEAD, then ranges; the CDN link is resolved once for all of them
    path = media.url.removeprefix("http://192.168.0.10:8080")
    head = client.head(path)
    assert head.status_code == 200 and head.headers["content-length"] == str(len(VIDEO))
    assert head.headers["contentfeatures.dlna.org"].startswith("DLNA.ORG_OP=01")
    part = client.get(path, headers={"Range": "bytes=100-199"})
    assert part.status_code == 206 and part.content == VIDEO[100:200]
    assert part.headers["content-range"] == f"bytes 100-199/{len(VIDEO)}"
    assert len(site.resolved) == 1 and str(cdn.requests[-1].url) == "https://cdn.test/v1.mp4"

    # 5. The cinema remembers where we are
    saved = client.get("/api/cinema").json()[0]
    assert (saved["lastEpisode"], saved["translation"], saved["watched"]) == (2, "Dream Cast", [2])


def test_watch_in_browser_and_expired_link_is_refreshed(env):
    client, site, cdn, _ = env
    ready = client.post("/api/catalog/resolve", json={"titleId": FRIREN, "episode": 1, "translationId": "81"}).json()
    assert ready == {"url": f"/stream/animego/{FRIREN}/1/81/auto.mp4", "provider": "cvh", "quality": 1080}

    cdn.expired.add("https://cdn.test/v1.mp4")
    resp = client.get(ready["url"], headers={"Range": "bytes=0-9"})
    assert resp.status_code == 206 and resp.content == VIDEO[:10]
    assert len(site.resolved) == 2  # a fresh link was fetched after the CDN said 403


def test_quality_is_capped(env, tmp_path):
    client, *_ = env
    container = build_container(
        Settings(data_dir=tmp_path / "capped", discovery_interval_s=0, max_video_height=720),
        discovery=FakeDiscovery(), controller=FakeController(), downloader=FakeDownloader(),
        catalog_source=FakeSite(), fetcher=FakeFetcher(),
    )  # fmt: skip
    with TestClient(create_app(container)) as capped:
        ready = capped.post("/api/catalog/resolve", json={"titleId": FRIREN, "episode": 1, "translationId": "81"})
        assert ready.json()["quality"] == 720


def test_hls_only_dub_is_explained(env):
    client, *_ = env
    resp = client.post("/api/catalog/resolve", json={"titleId": FRIREN, "episode": 1, "translationId": "30"})
    assert resp.status_code == 422 and "HLS" in resp.json()["detail"]
    assert client.get(f"/api/catalog/titles/nope-1").status_code == 404


def test_episode_is_downloaded_to_the_library(env):
    client, *_ = env
    body = {"titleId": FRIREN, "episode": 2, "translationId": "81", "title": "Фрирен, 2 серия"}
    video = client.post("/api/catalog/download", json=body).json()
    assert video["source"] == "animego"
    for _ in range(100):
        video = next(v for v in client.get("/api/videos").json() if v["id"] == video["id"])
        if video["status"] == "ready":
            break
        time.sleep(0.02)
    assert video["status"] == "ready" and video["size"] == len(VIDEO)
    assert client.get(f"/media/{video['id']}.mp4").content == VIDEO


def test_cinema_survives_restart_and_can_be_cleared(env, tmp_path):
    client, *_ = env
    client.post("/api/cinema", json={"titleId": FRIREN})
    restarted = build_container(
        Settings(data_dir=tmp_path, discovery_interval_s=0),
        discovery=FakeDiscovery(), controller=FakeController(), downloader=FakeDownloader(),
        catalog_source=FakeSite(), fetcher=FakeFetcher(),
    )  # fmt: skip
    assert [t.id for t in restarted.cinema.list()] == [FRIREN]
    assert client.delete(f"/api/cinema/{FRIREN}").status_code == 204
    assert client.delete(f"/api/cinema/{FRIREN}").status_code == 404
