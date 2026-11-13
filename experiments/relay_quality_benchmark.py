"""Compare RelayVSR windows 16/64 on a JSON manifest of local clips.

Run in the existing worker image: input clips at /input, outputs at /results.
Only one model pair is loaded. No application settings or user library are changed.
"""
import argparse
import json
from pathlib import Path
import subprocess
import threading
import time

import torch
from worker.inference import InferenceEngine
from refvsr_inference.runtime.streaming import CollaborativeFrameStream

parser = argparse.ArgumentParser()
parser.add_argument("manifest", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--warmup", required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
clips = json.loads(args.manifest.read_text())
original_init = CollaborativeFrameStream.__init__
window = 16


def init(self, **kwargs):
    kwargs["window_size"] = window
    original_init(self, **kwargs)


CollaborativeFrameStream.__init__ = init
started = time.perf_counter()
engine = InferenceEngine()
load_seconds = time.perf_counter() - started
print(json.dumps({"model_loaded_s": load_seconds}), flush=True)
started = time.perf_counter()
engine.run({"source": {"file": args.warmup}, "output": str(args.output / "warmup.mp4")},
           threading.Event(), lambda **_: None)
engine.cleanup()
print(json.dumps({"warmup_s": time.perf_counter() - started}), flush=True)
rows = []
for index, clip in enumerate(clips):
    for window in ([16, 64] if index % 2 == 0 else [64, 16]):
        torch.cuda.reset_peak_memory_stats()
        peak = [0]
        done = threading.Event()
        def poll():
            while not done.is_set():
                raw = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True)
                peak[0] = max(peak[0], int(raw.strip().splitlines()[0]))
                done.wait(0.5)
        sampling = threading.Thread(target=poll, daemon=True)
        sampling.start()
        last = {}
        first_frame = []
        started = time.perf_counter()
        def progress(**values):
            last.update(values)
            if values.get("frames") == 1:
                first_frame.append(time.perf_counter() - started)
        try:
            output = args.output / f"{clip['name']}-w{window}.mp4"
            result = engine.run({"source": {"file": clip["file"]}, "output": str(output)},
                                threading.Event(), progress)
            elapsed = time.perf_counter() - started
            assert result["frames"] == clip["frames"], result
            row = dict(scene=clip["name"], window=window, frames=result["frames"],
                       video_seconds=result["frames"] / last["fps"], elapsed_s=elapsed,
                       fps=result["frames"] / elapsed, first_frame_s=first_frame[0],
                       peak_gpu_mib=peak[0], allocated_mib=torch.cuda.max_memory_allocated()/1024**2,
                       width=last["width"], height=last["height"])
        finally:
            done.set()
            sampling.join()
            engine.cleanup()
        rows.append(row)
        (args.output / "timings.json").write_text(json.dumps(dict(load_seconds=load_seconds, runs=rows), indent=2))
        print(json.dumps(row), flush=True)
