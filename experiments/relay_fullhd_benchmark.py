"""Run in the RelayVSR image with this repository and input/output directories mounted.

Example: python /experiment/relay_fullhd_benchmark.py /input/clip.mp4 /results
Loads one model pair. First run warms kernels; subsequent runs compare window spacing.
The yield-to-encoder timer includes waiting for GPU results; it is not additive to GPU spans.
Experimental windows never modify the application's default of 16 frames.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import subprocess
import threading
import time

import torch
from worker.inference import InferenceEngine
from refvsr_inference.runtime.streaming import CollaborativeFrameStream

parser = argparse.ArgumentParser()
parser.add_argument("input")
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
original_init = CollaborativeFrameStream.__init__
original_frames = CollaborativeFrameStream.frames
window = 16
spans = defaultdict(float)
postprocess_s = 0


def init(self, **kwargs):
    kwargs["window_size"] = window
    original_init(self, **kwargs)


def frames(self, source):
    global postprocess_s
    iterator = original_frames(self, source)
    try:
        for result in iterator:
            started = time.perf_counter()
            yield result
            postprocess_s += time.perf_counter() - started
            for name, span in result.timings:
                spans[name] += span.milliseconds() / 1000
    finally:
        iterator.close()


CollaborativeFrameStream.__init__ = init
CollaborativeFrameStream.frames = frames
started = time.perf_counter()
engine = InferenceEngine()
load_seconds = time.perf_counter() - started
rows = []
for label, window, autotune in [("warmup", 16, False), ("baseline", 16, False),
                                ("cudnn", 16, True), ("window32", 32, True), ("window64", 64, True)]:
    torch.backends.cudnn.benchmark = autotune
    spans.clear()
    postprocess_s = 0
    torch.cuda.reset_peak_memory_stats()
    last = {}
    peak = [0]
    done = threading.Event()
    def poll():
        while not done.is_set():
            value = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True)
            peak[0] = max(peak[0], int(value.strip().splitlines()[0]))
            done.wait(0.5)
    sampling = threading.Thread(target=poll, daemon=True)
    sampling.start()
    started = time.perf_counter()
    try:
        result = engine.run({"source": {"file": args.input}, "output": str(args.output / f"{label}.mp4")},
                            threading.Event(), lambda **values: last.update(values))
        elapsed = time.perf_counter() - started
        row = dict(label=label, window=window, elapsed_s=elapsed, frames=result["frames"],
                   fps=result["frames"]/elapsed, video_seconds=result["frames"]/last["fps"],
                   stage_s=dict(spans), yield_to_encoder_s=postprocess_s,
                   gpu_peak_mib=peak[0], allocated_mib=torch.cuda.max_memory_allocated()/1024**2,
                   reserved_mib=torch.cuda.max_memory_reserved()/1024**2)
    finally:
        done.set()
        sampling.join()
        engine.cleanup()
    rows.append(row)
    (args.output / "results.json").write_text(json.dumps(dict(load_seconds=load_seconds, runs=rows), indent=2))
    print(json.dumps(row), flush=True)
