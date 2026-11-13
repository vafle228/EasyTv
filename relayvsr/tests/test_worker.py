import asyncio
import contextlib
import json
import struct

from fastapi.testclient import TestClient

from relayvsr.worker.app import create_app
from relayvsr.worker.jobs import Jobs, has_fragment


def test_only_complete_fragments_are_streamable(tmp_path):
    path = tmp_path / "clip.mp4"
    prefix = struct.pack(">I4s", 8, b"ftyp") + struct.pack(">I4s", 8, b"moof")
    path.write_bytes(prefix + struct.pack(">I4s", 16, b"mdat") + b"abc")
    assert not has_fragment(path)
    path.write_bytes(prefix + struct.pack(">I4s", 16, b"mdat") + b"abcdefgh")
    assert has_fragment(path)


def test_foreground_preempts_background_and_reuses_one_job(tmp_path):
    async def scenario():
        started = asyncio.Queue()
        events = {}
        manager = None
        async def runner(job_id, source):
            await started.put(source["file"])
            await events.setdefault(source["file"], asyncio.Event()).wait()
            manager.path(job_id).write_bytes(b"result")
            manager.items[job_id]["state"] = "ready"
        manager = Jobs(tmp_path, 1000, runner)
        background = manager.submit("later", {"file": "later.mp4"}, 1)
        task = asyncio.create_task(manager.serve())
        try:
            assert await asyncio.wait_for(started.get(), 1) == "later.mp4"
            manager.submit("now", {"file": "now.mp4"}, 1)
            live = manager.submit("now", {"file": "now.mp4"}, 0)
            assert await asyncio.wait_for(started.get(), 1) == "now.mp4"
            assert manager.public(background["id"])["state"] == "pending"
            assert manager.submit("now", {"file": "now.mp4"}, 0)["id"] == live["id"]
            assert len(manager.items) == 2
            events["now.mp4"].set()
            assert await asyncio.wait_for(started.get(), 1) == "later.mp4"
            assert manager.public(live["id"])["state"] == "ready"
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
    asyncio.run(scenario())


def test_completed_cache_survives_restart_and_active_reader_is_not_evicted(tmp_path):
    manager = Jobs(tmp_path, 10)
    job = manager.submit("clip", {"file": "clip.mp4"}, 1)
    manager.items[job["id"]]["state"] = "ready"
    path = manager.path(job["id"])
    path.write_bytes(b"a" * 20)
    path.with_suffix(".json").write_text(json.dumps(manager.items[job["id"]]))
    restarted = Jobs(tmp_path, 10)
    assert restarted.public(job["id"])["state"] == "ready"
    restarted.readers[job["id"]] = 1
    restarted.cleanup()
    assert path.exists()
    restarted.readers[job["id"]] = 0
    restarted.cleanup()
    assert not path.exists()


def test_worker_checks_sources_ranges_and_missing_jobs(tmp_path, monkeypatch):
    root = tmp_path / "input"
    root.mkdir()
    (root / "clip.mp4").write_bytes(b"original")
    monkeypatch.setenv("RELAYVSR_INPUT", str(root))
    manager = Jobs(tmp_path / "cache", 1000)
    job = manager.submit("clip", {"file": "clip.mp4"}, 1)
    manager.items[job["id"]]["state"] = "ready"
    manager.path(job["id"]).write_bytes(b"abcdef")
    with TestClient(create_app(manager, lambda: {"available": True})) as client:
        url = f"/jobs/{job['id']}/video.mp4"
        result = client.get(url, headers={"Range": "bytes=2-4"})
        assert result.status_code == 206 and result.content == b"cde"
        assert result.headers["content-range"] == "bytes 2-4/6"
        assert client.head(url).headers["content-length"] == "6"
        assert client.get(url, headers={"Range": "bytes=100-"}).status_code == 416
        assert client.get("/jobs/unknown/video.mp4").status_code == 404
        manager.items[job["id"]]["state"] = "running"
        manager.path(job["id"]).write_bytes(struct.pack(">I4s", 8, b"moof") + struct.pack(">I4s", 8, b"mdat"))
        growing = client.head(url, headers={"Range": "bytes=0-"})
        assert growing.status_code == 200 and growing.headers["accept-ranges"] == "none"
        assert "content-length" not in growing.headers
        manager.items[job["id"]]["state"] = "failed"
        assert client.get(url).status_code == 409
        for source in ({"file": "../../private"}, {"url": "file:///etc/passwd"},
                       {"url": "https://test/video", "headers": {"X": "value\r\nInjected: x"}}):
            assert client.post("/jobs", json={"key": "bad", "source": source}).status_code == 422


def test_removing_queued_work_does_not_cancel_foreground(tmp_path):
    manager = Jobs(tmp_path, 1000)
    background = manager.submit("later", {"file": "later"}, 1)
    live = manager.submit("now", {"file": "now"}, 0)
    manager.cancel_background_except(set())
    assert manager.public(background["id"])["state"] == "cancelled"
    assert manager.public(live["id"])["state"] == "pending"
