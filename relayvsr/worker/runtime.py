"""A resident inference process, with cooperative per-video cancellation."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import signal
import sys
import uuid


class InferenceProcess:
    def __init__(self, command=None, cancel_timeout=90):
        self.command = command or [sys.executable, "-m", "worker.inference"]
        self.cancel_timeout = cancel_timeout
        self.process = None

    async def _send(self, message):
        self.process.stdin.write((json.dumps(message) + "\n").encode())
        await self.process.stdin.drain()

    async def run(self, request, update):
        # Jobs serializes calls, including the acknowledgement of a cancelled job.
        if self.process is None or self.process.returncode is not None:
            await self.close()
            self.process = await asyncio.create_subprocess_exec(
                *self.command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL, start_new_session=True,
            )
        token = uuid.uuid4().hex
        accepting_updates = True

        async def receive():
            while line := await self.process.stdout.readline():
                try:
                    message = json.loads(line)
                except ValueError:
                    continue  # Upstream may print diagnostics to stdout.
                if not isinstance(message, dict) or message.get("id") != token:
                    continue
                if accepting_updates:
                    update(message["update"])
                if message.get("event") == "finished":
                    return
            raise RuntimeError("Процесс RelayVSR завершился до окончания задания")

        response = None
        try:
            await self._send({"op": "run", "id": token, "request": request})
            response = asyncio.create_task(receive())
            await asyncio.shield(response)
        except (asyncio.CancelledError, Exception):
            accepting_updates = False
            if response is not None and not response.done():
                try:
                    await self._send({"op": "cancel", "id": token})
                    await asyncio.wait_for(asyncio.shield(response), self.cancel_timeout)
                except (asyncio.CancelledError, Exception):
                    await self.close()
            elif response is None or response.cancelled() or response.exception() is not None:
                # A protocol/read failure or a rejected progress update: restart safely.
                await self.close()
            if response is not None:
                response.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await response
            raise

    async def close(self):
        process, self.process = self.process, None
        if process is None:
            return
        if process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGTERM)
                else:
                    process.terminate()
            try:
                await asyncio.wait_for(process.wait(), 10)
            except TimeoutError:
                with contextlib.suppress(ProcessLookupError):
                    if os.name == "posix":
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                await process.wait()
        else:
            await process.wait()
