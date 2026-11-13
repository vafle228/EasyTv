"""Run the original EasyTv RelayVSR engine, preserving resident weights between jobs."""
import json
import os
from pathlib import Path
import threading
import time
import torch
from worker.inference import InferenceEngine

root = Path('/benchmark')
started = time.monotonic()
engine = InferenceEngine()
load_s = time.monotonic() - started
rows = []
try:
    for name, source in [('relay_faces_cold', 'faces270.mkv'),
                         ('relay_faces1080', 'faces270.mkv'),
                         ('relay_details1080', 'details270.mkv'),
                         ('relay_motion1080', 'motion270.mkv')]:
        torch.cuda.reset_peak_memory_stats()
        begun = time.monotonic()
        print(json.dumps({'job': name, 'started_s': begun - started}), flush=True)
        def report(**values):
            if values.get('frames', 0) % 16 == 0:
                print(json.dumps({'job': name, **values}), flush=True)
        result = engine.run({'source': {'file': source},
                             'output': str(root/'output'/f'{name}.mp4')},
                            threading.Event(), report)
        elapsed = time.monotonic() - begun
        row = {'name': name, 'model_load_s': load_s, 'started_s': begun - float(os.environ['BENCHMARK_STARTED_MONOTONIC']), 'elapsed_s': elapsed, **result,
               'torch_allocated_peak_gib': torch.cuda.max_memory_allocated()/1024**3,
               'torch_reserved_peak_gib': torch.cuda.max_memory_reserved()/1024**3}
        engine.cleanup()
        row['elapsed_with_cleanup_s'] = time.monotonic() - begun
        rows.append(row)
        (root/'logs'/'relay.timings.json').write_text(json.dumps(rows, indent=2))
        print(json.dumps(row), flush=True)
finally:
    engine.cleanup()
