"""Measure the unmodified SeedVR2 CLI in one process; save raw samples and peaks."""
import contextlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import threading
import time
import traceback

started = time.monotonic()

import psutil
import torch

name, *cli_args = sys.argv[1:]
if not name.replace('-', '').replace('_', '').isalnum():
    raise ValueError('Invalid run name')
root = Path('/benchmark/logs')
root.mkdir(exist_ok=True)
process = psutil.Process()
stop = threading.Event()
peaks = {'torch_allocated_bytes': 0, 'torch_reserved_bytes': 0}
samples = []
original_reset = torch.cuda.reset_peak_memory_stats

def capture_peaks():
    if torch.cuda.is_initialized():
        peaks['torch_allocated_bytes'] = max(peaks['torch_allocated_bytes'], torch.cuda.max_memory_allocated())
        peaks['torch_reserved_bytes'] = max(peaks['torch_reserved_bytes'], torch.cuda.max_memory_reserved())

def reset_peaks(*args, **kwargs):
    capture_peaks()
    return original_reset(*args, **kwargs)

def read_number(path):
    try:
        return int(Path(path).read_text())
    except (OSError, ValueError):
        return None

def monitor():
    with (root / f'{name}.samples.jsonl').open('w') as output:
        while not stop.is_set():
            row = {'elapsed_s': time.monotonic() - started,
                   'rss_bytes': process.memory_info().rss,
                   'cgroup_bytes': read_number('/sys/fs/cgroup/memory.current'),
                   'swap_bytes': read_number('/sys/fs/cgroup/memory.swap.current')}
            try:
                line = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.used,memory.total,utilization.gpu,power.draw',
                                                '--format=csv,noheader,nounits'], text=True, timeout=3).splitlines()[0]
                values = [float(x.strip()) for x in line.split(',')]
                row.update(gpu_used_mib=values[0], gpu_total_mib=values[1], gpu_utilization=values[2], gpu_power_w=values[3])
            except (subprocess.SubprocessError, ValueError, IndexError):
                pass
            samples.append(row)
            output.write(json.dumps(row) + '\n')
            output.flush()
            stop.wait(0.5)

# Leave headroom for the desktop and enforce a real allocator ceiling rather than relying on WDDM paging.
torch.cuda.set_per_process_memory_fraction(0.85)
torch.set_num_threads(4)
torch.cuda.reset_peak_memory_stats = reset_peaks
thread = threading.Thread(target=monitor, daemon=True)
thread.start()
code = 0
print(f'Benchmark {name} started; logs: /benchmark/logs/{name}.log', flush=True)
try:
    with (root / f'{name}.log').open('w', buffering=1) as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        os.environ['BENCHMARK_STARTED_MONOTONIC'] = str(started)
        sys.argv = ['inference_cli.py', *cli_args]
        try:
            runpy.run_path(os.environ.get('BENCHMARK_ENTRYPOINT', '/opt/seedvr2/inference_cli.py'), run_name='__main__')
        except SystemExit as exc:
            code = int(exc.code or 0)
        except KeyboardInterrupt:
            code = 130
            traceback.print_exc()
        except Exception:
            traceback.print_exc()
            code = 1
finally:
    capture_peaks()
    stop.set()
    thread.join(timeout=4)
    summary = {'name': name, 'exit_code': code, 'elapsed_s': time.monotonic() - started,
               'engine': os.environ.get('BENCHMARK_ENGINE', 'seedvr2'), 'args': cli_args, 'torch': torch.__version__, 'gpu': torch.cuda.get_device_name(),
               'allocator_fraction': 0.85, 'sample_interval_s': 0.5, **peaks}
    for field in ('gpu_used_mib', 'rss_bytes', 'cgroup_bytes', 'swap_bytes'):
        summary['peak_' + field] = max((r[field] for r in samples if r.get(field) is not None), default=None)
    summary['initial_gpu_used_mib'] = next((r['gpu_used_mib'] for r in samples if 'gpu_used_mib' in r), None)
    (root / f'{name}.summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)
sys.exit(code)
