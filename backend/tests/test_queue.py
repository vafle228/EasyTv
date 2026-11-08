"""Queue scenarios against the HTTP API and the background server poll."""

import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from easytv.config import Settings
from easytv.container import build_container
from easytv.core.models import PlaybackState

from test_scenarios import BEDROOM, FakeController, FakeDiscovery, FakeDownloader, direct_responses, env

TV = "/api/tvs/tv-living"
QUEUE = f"{TV}/queue"


def _upload(client, filename):
    result = client.post("/api/videos/upload", files={"file": (filename, b"fixture", "video/mp4")})
    assert result.status_code == 201
    return result.json()["id"]


def _enqueue(client, video_id, path=QUEUE):
    assert client.post(path, json={"videoId": video_id}).status_code == 204


def _ids(client, path=QUEUE):
    return [item["videoId"] for item in client.get(path).json()["items"]]


def _head(client):
    return client.get(QUEUE).json()["items"][0]["id"]


def _eventually(load, matches):
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        result = load()
        if matches(result):
            return result
        time.sleep(0.05)
    pytest.fail(f"Queue did not reach the expected state: {result!r}")


def test_queue_is_fifo_and_persists_per_tv(env, tmp_path):
    client, discovery, controller, *_ = env
    discovery.visible.append(BEDROOM)
    client.post("/api/tvs/refresh")
    first, second, third = (_upload(client, f"clip-{n}.mp4") for n in range(3))
    bedroom = "/api/tvs/tv-bedroom/queue"
    _enqueue(client, first)
    _enqueue(client, second)
    _enqueue(client, third)
    _enqueue(client, second)
    _enqueue(client, second, bedroom)
    assert _ids(client) == [first, second, third]
    assert not controller.commands  # enqueueing on an idle TV does not start playback

    head = _head(client)
    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = [pool.submit(client.post, f"{TV}/next", json={"itemId": head}) for _ in range(2)]
        assert sorted(attempt.result().status_code for attempt in attempts) == [200, 409]
    assert len(controller.commands) == 1 and controller.commands[0][2].title == "clip-0"
    assert _ids(client) == [second, third]
    assert client.delete(f"{QUEUE}/{_head(client)}").status_code == 204

    restarted = build_container(
        Settings(data_dir=tmp_path, discovery_interval_s=0),
        discovery=FakeDiscovery(),
        controller=FakeController(),
        downloader=FakeDownloader(),
    )
    items, error = restarted.playback.queue("tv-living")
    assert [item.video_id for item in items] == [third] and error is None
    assert _ids(client, bedroom) == [second]


def test_rejected_next_keeps_head_for_retry(env):
    client, _, controller, *_ = env
    client.post("/api/tvs/refresh")
    video = _upload(client, "clip.mp4")
    _enqueue(client, video)
    head = _head(client)

    controller.reject_play = True
    assert client.post(f"{TV}/next", json={"itemId": head}).status_code == 502
    assert _head(client) == head
    controller.reject_play = False
    assert client.post(f"{TV}/next", json={"itemId": head}).json()["videoId"] == video
    assert _ids(client) == []


@pytest.mark.parametrize("reject_next", [False, True])
def test_queue_advances_on_natural_end_without_playback_requests(env, reject_next):
    client, _, controller, *_ = env
    client.post("/api/tvs/refresh")
    first, second = (_upload(client, f"clip-{n}.mp4") for n in range(2))
    assert client.post(f"{TV}/play", json={"videoId": first}).status_code == 200
    controller.position_s = 119
    _enqueue(client, second)
    assert controller.position_sampled.wait(3)
    controller.reject_play = reject_next
    controller.state = PlaybackState.STOPPED

    queue = _eventually(
        lambda: client.get(QUEUE).json(),
        lambda queue: bool(queue["error"]) if reject_next else not queue["items"],
    )
    if reject_next:
        assert queue["items"][0]["videoId"] == second
        assert "отклонил" in queue["error"]
        assert len(controller.commands) == 1
    else:
        assert queue["error"] is None
        assert client.get(f"{TV}/playback").json()["videoId"] == second
        assert len(controller.commands) == 2


@pytest.mark.parametrize("stop", ["api", "early", "foreign"])
def test_manual_or_unrelated_stop_leaves_queue_intact(env, stop):
    client, _, controller, *_ = env
    client.post("/api/tvs/refresh")
    first, second = (_upload(client, f"clip-{n}.mp4") for n in range(2))
    assert client.post(f"{TV}/play", json={"videoId": first}).status_code == 200
    controller.position_s = 40 if stop == "early" else 119
    if stop == "foreign":
        controller.track_uri = "http://another-device.test/video.mp4"
    _enqueue(client, second)
    assert controller.position_sampled.wait(3)

    if stop == "api":
        assert client.post(f"{TV}/stop").status_code == 204
    else:
        controller.state = PlaybackState.STOPPED
    time.sleep(1.1)  # allow another background poll
    assert _ids(client) == [second]
    assert [cmd[0] for cmd in controller.commands].count("play") == 1


def test_invalid_queue_sources(env):
    client, *_ = env
    client.post("/api/tvs/refresh")
    assert client.post(QUEUE, json={}).status_code == 422
    assert client.post(QUEUE, json={"videoId": "gone"}).status_code == 404
    assert client.post(QUEUE, json={"stream": {"titleId": "x", "translationId": "1"}}).status_code == 422
    assert client.get("/api/tvs/unknown/queue").status_code == 404
