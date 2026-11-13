"""Resident RelayVSR weights with a fresh streaming session for each video."""

from __future__ import annotations

import json
import gc
import contextlib
import math
import os
import queue
import subprocess
import sys
import threading
import time
from fractions import Fraction
from pathlib import Path

from .resolution import model_size, source_address, source_options


class Cancelled(Exception):
    pass


def check_cancelled(cancelled):
    if cancelled.is_set():
        raise Cancelled()


class InferenceEngine:
    def __init__(self):
        import torch
        from refvsr_inference.checkpoints import load_checkpoints

        torch.set_num_threads(4)
        torch.set_grad_enabled(False)
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA недоступна в контейнере RelayVSR")
        torch.cuda.set_per_process_memory_fraction(0.85)
        weights = Path(os.environ.get("RELAYVSR_WEIGHTS", "/weights"))
        self.models = load_checkpoints(weights / "wan.safetensors", weights / "flash.safetensors")

    def run(self, request, cancelled, report):
        return run(request, self.models, cancelled, report)

    def cleanup(self):
        import torch
        # Frames, per-video KV history and failed-operation tracebacks have been released.
        # Return unused allocations to CUDA, keeping the two model instances resident.
        gc.collect()
        torch.cuda.empty_cache()


def run(request, models, cancelled, report):
    import av
    import numpy as np
    import torch

    from refvsr_inference.models.wan.sampling import WanVSRPipeline
    from refvsr_inference.runtime.streaming import CollaborativeFrameStream, InputFrame

    check_cancelled(cancelled)
    wan, flash = models
    source, output = request["source"], Path(request["output"])
    headers = "".join(f"{k}: {v}\r\n" for k, v in source.get("headers", {}).items())
    options = source_options(source)
    address = source_address(source)

    with av.open(address, options=options, timeout=(30, 60)) as media:
        video = media.streams.video[0]
        video.thread_type = "AUTO"
        fps = video.average_rate
        if fps is None or not 0 < fps <= 120:
            raise RuntimeError("Не удалось определить частоту кадров видео (1–120 FPS)")
        duration = float(video.duration * video.time_base) if video.duration else None
        if duration is None and media.duration:
            duration = media.duration / av.time_base
        size = model_size(video.width, video.height, video.sample_aspect_ratio)
        width, height = size.output
        report(state="running", fps=float(fps), duration=duration, width=width, height=height)
        check_cancelled(cancelled)
        sampler = WanVSRPipeline(
            scheduler_config={"num_train_timesteps": 1000, "shift": 5.0},
            sampling={"execution_mode": "streaming", "num_inference_steps": 1,
                      "timesteps": [1000], "guidance_scale": 1.0, "seed": 42,
                      "kv_cache_window_size": wan.temporal_context_frames},
        )
        sampler.prepare_streaming(model=wan, prompt_embeds=wan.prompt_embeds,
                                  device=torch.device("cuda"), compute_dtype=torch.bfloat16)
        stream = CollaborativeFrameStream(
            wan_model=wan, flash_model=flash, wan_pipeline=sampler, prompt_embeds=wan.prompt_embeds,
            device=torch.device("cuda"), compute_dtype=torch.bfloat16, window_size=16, seed=42,
        )

        def packets():
            # Convert variable timestamps to the declared CFR without accumulating audio drift.
            first_time = None
            previous = None
            index = 0
            for frame in media.decode(video):
                check_cancelled(cancelled)
                stamp = frame.time
                if first_time is None:
                    first_time = stamp or 0
                target = round((stamp - first_time) * float(fps)) if stamp is not None else index
                if (frame.width, frame.height) != (size.width, size.height):
                    frame = frame.reformat(width=size.width, height=size.height, interpolation="LANCZOS")
                rgb = torch.from_numpy(np.ascontiguousarray(frame.to_ndarray(format="rgb24"))).permute(2, 0, 1).contiguous()
                if target < index:
                    continue
                while index < target and previous is not None:
                    yield InputFrame(index, previous, source_time=index / float(fps))
                    index += 1
                yield InputFrame(index, rgb, source_time=index / float(fps))
                index += 1
                previous = rgb

        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
                   "-r", str(Fraction(fps)), "-i", "pipe:0"]
        if source.get("url"):
            command += ["-rw_timeout", "60000000"]
        if headers:
            command += ["-headers", headers]
        command += ["-i", address, "-map", "0:v:0", "-map", "1:a:0?",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-g", str(math.ceil(float(fps))), "-keyint_min", str(math.ceil(float(fps))),
                    "-sc_threshold", "0", "-bf", "0", "-c:a", "aac", "-b:a", "160k",
                    "-af", "asetpts=PTS-STARTPTS", "-shortest", "-movflags",
                    "+frag_keyframe+empty_moov+default_base_moof", "-flush_packets", "1", str(output)]
        # The file is tailed by HTTP while it is being produced; never rewrite its existing bytes.
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        started = time.monotonic()
        frames = 0
        results = stream.frames(packets())
        try:
            for result in results:
                check_cancelled(cancelled)
                rgb = result.rgb[0].add(1).mul_(127.5).clamp_(0, 255).to(torch.uint8)
                encoder.stdin.write(rgb.permute(1, 2, 0).contiguous().cpu().numpy().tobytes())
                frames += 1
                elapsed = time.monotonic() - started
                report(state="running", frames=frames, processed_seconds=frames / float(fps),
                       speed=frames / float(fps) / elapsed,
                       progress=min(0.999, frames / float(fps) / duration) if duration else None)
            encoder.stdin.close()
            if encoder.wait(timeout=120) != 0 or frames == 0:
                raise RuntimeError("Не удалось закодировать улучшенное видео со звуком")
        finally:
            results.close()  # Release frame buffers and KV state even on preemption/OOM.
            if not encoder.stdin.closed:
                with contextlib.suppress(OSError):
                    encoder.stdin.close()
            if encoder.poll() is None:
                encoder.kill()
                encoder.wait()
        return {"state": "ready", "progress": 1.0, "frames": frames}


def failure(exc):
    if os.environ.get("RELAYVSR_DEBUG") == "1":
        import traceback
        traceback.print_exc()
    # CDN URLs/headers may contain credentials: do not expose arbitrary exception messages.
    kind = type(exc).__name__
    if "OutOfMemory" in kind:
        detail = "Недостаточно видеопамяти. Закройте другие приложения, использующие GPU, или выключите ИИ."
    elif isinstance(exc, FileNotFoundError):
        detail = "Не найден исходник, ffmpeg или файл весов RelayVSR"
    else:
        detail = f"RelayVSR не смог обработать видео ({kind}). Проверьте исходник и доступность GPU."
    return {"state": "failed", "error": detail}


def serve(engine_factory=InferenceEngine, incoming=None, emit=None):
    incoming = incoming if incoming is not None else sys.stdin
    emit = emit or (lambda message: print(json.dumps(message), flush=True))
    pending = queue.Queue()
    cancellations = {}

    def read_commands():
        try:
            for line in incoming:
                message = json.loads(line)
                token = message["id"]
                if message["op"] == "cancel":
                    if event := cancellations.get(token):
                        event.set()
                elif message["op"] == "run":
                    event = threading.Event()
                    cancellations[token] = event
                    pending.put((token, message["request"], event))
        finally:
            for event in list(cancellations.values()):
                event.set()
            pending.put(None)

    threading.Thread(target=read_commands, daemon=True).start()
    engine = None
    while item := pending.get():
        token, request, cancelled = item

        def report(**values):
            emit({"id": token, "event": "progress", "update": values})

        try:
            check_cancelled(cancelled)
            if engine is None:
                report(state="loading")
                engine = engine_factory()
            check_cancelled(cancelled)
            result = engine.run(request, cancelled, report)
        except Cancelled:
            result = {"state": "cancelled"}
        except Exception as exc:
            result = failure(exc)
        # Cleanup precedes the acknowledgement: the next job must not see old video state.
        if engine is not None:
            engine.cleanup()
        cancellations.pop(token, None)
        emit({"id": token, "event": "finished", "update": result})


if __name__ == "__main__":
    serve()
