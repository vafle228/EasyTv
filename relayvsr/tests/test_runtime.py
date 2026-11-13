import asyncio
import contextlib
import json
import os
import sys
import textwrap
from pathlib import Path

import pytest

from relayvsr.worker.runtime import InferenceProcess


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    root = str(Path(__file__).resolve().parents[2])
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(filter(None, [root, os.environ.get("PYTHONPATH")])))
    trace = tmp_path / "events.jsonl"
    script = tmp_path / "fake_engine.py"
    script.write_text(textwrap.dedent('''
        import json, os, sys, time
        from pathlib import Path
        from relayvsr.worker.inference import serve, check_cancelled

        def trace(event):
            with Path(sys.argv[1]).open('a') as log:
                log.write(json.dumps({'event': event, 'pid': os.getpid()}) + '\\n')

        class Engine:
            def __init__(self):
                trace('load')

            def run(self, request, cancelled, report):
                trace('run')
                report(state='running', pid=os.getpid())
                if request.get('mode') == 'fail':
                    raise ValueError('secret source URL')
                if request.get('mode') == 'crash':
                    os._exit(7)
                if request.get('mode') == 'block':
                    cancelled.wait(10)
                    check_cancelled(cancelled)
                if request.get('mode') == 'hang':
                    time.sleep(10)
                return {'state': 'ready'}

            def cleanup(self):
                trace('cleanup')

        serve(Engine)
    '''), encoding="utf-8")
    return InferenceProcess([sys.executable, "-u", str(script), str(trace)], cancel_timeout=2), trace


def test_weights_survive_success_failure_and_preemption(runtime):
    worker, trace = runtime

    async def scenario():
        try:
            first = []
            await worker.run({}, first.append)
            process = worker.process
            assert first[-1]["state"] == "ready"
            failed = []
            await worker.run({"mode": "fail"}, failed.append)
            assert failed[-1]["state"] == "failed"
            assert "secret" not in failed[-1]["error"]

            started = asyncio.Event()
            cancelled_updates = []
            def update(value):
                cancelled_updates.append(value)
                if value["state"] == "running":
                    started.set()
            task = asyncio.create_task(worker.run({"mode": "block"}, update))
            await asyncio.wait_for(started.wait(), 5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert all(value["state"] != "cancelled" for value in cancelled_updates)

            next_video = []
            await worker.run({}, next_video.append)
            assert next_video[-1]["state"] == "ready"
            assert worker.process is process and process.returncode is None
            assert not any(value["state"] == "loading" for value in next_video)
        finally:
            await worker.close()
        assert process.returncode is not None

    asyncio.run(scenario())
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    assert [value["event"] for value in events] == ["load"] + ["run", "cleanup"] * 4
    assert len({value["pid"] for value in events}) == 1


@pytest.mark.parametrize("mode", ["crash", "hang"])
def test_dead_or_unresponsive_process_is_replaced(runtime, mode):
    worker, _ = runtime

    async def scenario():
        worker.cancel_timeout = 0.05
        started = asyncio.Event()
        task = asyncio.create_task(worker.run(
            {"mode": mode}, lambda value: started.set() if value["state"] == "running" else None,
        ))
        try:
            await asyncio.wait_for(started.wait(), 5)
            old = worker.process
            if mode == "hang":
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            else:
                with pytest.raises(RuntimeError, match="Процесс RelayVSR"):
                    await task
            result = []
            await worker.run({}, result.append)
            assert result[-1]["state"] == "ready"
            assert old.returncode is not None and worker.process.pid != old.pid
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, RuntimeError):
                await task
            await worker.close()

    asyncio.run(scenario())
