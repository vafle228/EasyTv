from fractions import Fraction

import pytest
from fastapi.testclient import TestClient

from relayvsr.worker.app import create_app
from relayvsr.worker.jobs import Jobs
from relayvsr.worker.resolution import AlreadyFullHD, model_size


@pytest.mark.parametrize("source,expected", [
    ((256, 144), (1920, 1080)), ((320, 240), (1440, 1080)),
    ((640, 360), (1920, 1080)), ((852, 480), (1916, 1080)),
    ((1280, 720), (1920, 1080)), ((1600, 900), (1920, 1080)),
    ((1280, 540), (1920, 808)), ((480, 720), (720, 1080)),
])
def test_all_small_sources_fit_full_hd_and_preserve_aspect(source, expected):
    assert model_size(*source).output == expected


def test_anamorphic_source_uses_display_aspect():
    assert model_size(720, 576, Fraction(64, 45)).output == (1920, 1080)
    with pytest.raises(AlreadyFullHD):
        model_size(1440, 800, Fraction(4, 3))


@pytest.mark.parametrize("width,height", [(0, 720), (1280, -1)])
def test_invalid_geometry_fails(width, height):
    with pytest.raises(ValueError):
        model_size(width, height)


@pytest.mark.parametrize("source", [(1920, 1080), (2560, 1440), (3840, 2160), (1920, 800), (720, 1280)])
def test_full_hd_is_rejected_before_gpu_queue(tmp_path, source):
    manager = Jobs(tmp_path, 1000)
    with TestClient(create_app(manager, probe=lambda _: model_size(*source))) as client:
        result = client.post("/jobs", json={"key": "fullhd", "source": {"url": "https://example.test/video.mp4"}})
        assert result.status_code == 409
        assert result.json()["detail"] == {"code": "already_full_hd", "width": source[0], "height": source[1]}
        assert not manager.items and manager.runtime.process is None


def test_probe_failure_never_queues_or_exposes_source(tmp_path):
    def probe(_):
        raise OSError("https://private.test/video?secret=123")
    manager = Jobs(tmp_path, 1000)
    with TestClient(create_app(manager, probe=probe)) as client:
        result = client.post("/jobs", json={"key": "broken", "source": {"url": "https://example.test/video"}})
        assert result.status_code == 503 and "secret" not in result.text
        assert not manager.items and manager.runtime.process is None


def test_output_version_never_reuses_native_x4_cache(tmp_path):
    import hashlib
    import json
    key = "clip"
    old_id = hashlib.sha256(f"e856773350f53036d825404c9ea9228e6dffadca-v1:{key}".encode()).hexdigest()
    (tmp_path / f"{old_id}.mp4").write_bytes(b"old-x4")
    (tmp_path / f"{old_id}.json").write_text(json.dumps({"id": old_id, "key": key, "state": "ready", "priority": 1, "accessed": 0}))
    manager = Jobs(tmp_path, 1000)
    job = manager.submit(key, {"file": "clip.mp4"}, 0)
    assert job["id"] != old_id and job["state"] == "pending"
    assert (tmp_path / f"{old_id}.mp4").read_bytes() == b"old-x4"
