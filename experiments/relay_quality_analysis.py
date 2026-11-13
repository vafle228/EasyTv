"""Frame-aligned comparisons to the baseline, not quality scores against ground truth.

Uses only PyAV, NumPy and ffmpeg already installed in the RelayVSR image.
Run after inference finishes to avoid contaminating performance measurements.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

import av
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("manifest", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
clips = json.loads(args.manifest.read_text())
results = []


def gray_frames(path, width=956, height=540):
    with av.open(str(path)) as media:
        stream = media.streams.video[0]
        stream.thread_type = "AUTO"
        for frame in media.decode(stream):
            yield frame.reformat(width=width, height=height, format="gray").to_ndarray().astype(np.float32)


for clip in clips:
    name = clip["name"]
    base, fast = (args.output / f"{name}-w{w}.mp4" for w in (16, 64))
    stats = args.output / f"{name}-ssim.log"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(base), "-i", str(fast),
                    "-lavfi", f"ssim=stats_file={stats}", "-an", "-f", "null", "-"], check=True)
    ssim = [float(re.search(r"All:([0-9.]+)", line)[1]) for line in stats.read_text().splitlines()]
    source = list(gray_frames(args.manifest.parent / clip["file"], 160, 90))
    cut_indices = [i for i in range(1, len(source)) if np.abs(source[i] - source[i-1]).mean() > 22]
    rows = []
    prev_a = prev_b = None
    for i, (a, b) in enumerate(zip(gray_frames(base), gray_frames(fast), strict=True)):
        diff = np.abs(a-b)
        row = dict(frame=i, ssim=ssim[i], mae=float(diff.mean()), p99=float(np.percentile(diff, 99)),
                   changed_pct=float((diff>12).mean()*100))
        if prev_a is not None:
            da, db = a-prev_a, b-prev_b
            row.update(temporal_difference=float(np.abs(da-db).mean()),
                       baseline_motion=float(np.abs(da).mean()), fast_motion=float(np.abs(db).mean()))
        rows.append(row)
        prev_a, prev_b = a, b
    assert len(rows) == clip["frames"]
    stable = [r for r in rows[1:] if not any(abs(r["frame"]-c)<=2 for c in cut_indices)]
    mean = lambda key: float(np.mean([r[key] for r in rows]))
    item = dict(scene=name, frames=len(rows), cuts=cut_indices, mean_ssim=mean("ssim"), min_ssim=min(ssim),
                mean_mae=mean("mae"), mean_changed_pct=mean("changed_pct"),
                temporal_difference_no_cuts=float(np.mean([r["temporal_difference"] for r in stable])),
                motion_ratio_no_cuts=float(np.mean([r["fast_motion"] for r in stable])/np.mean([r["baseline_motion"] for r in stable])),
                worst_frames=[r["frame"] for r in sorted(rows,key=lambda r:r["ssim"])[:8]], per_frame=rows)
    results.append(item)
    print(json.dumps({k:v for k,v in item.items() if k!='per_frame'}), flush=True)
(args.output / "comparison.json").write_text(json.dumps(results,indent=2))
