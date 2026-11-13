"""Join RelayVSR job intervals with sampled device/process memory and encoded frames."""
import json
from pathlib import Path
import subprocess

root = Path('/benchmark')
rows = json.loads((root/'logs/relay.timings.json').read_text())
samples = [json.loads(line) for line in (root/'logs/relay_session.samples.jsonl').read_text().splitlines()]
source_duration = json.loads((root/'manifest.json').read_text())['source']['duration_s']
for row in rows:
    output = root/'output'/f"{row['name']}.mp4"
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,avg_frame_rate,nb_read_frames', '-of', 'json', str(output)]))['streams'][0]
    frames = int(probe['nb_read_frames'])
    num, den = map(int, probe['avg_frame_rate'].split('/'))
    seconds = frames*den/num
    row.update(width=probe['width'], height=probe['height'], frames=frames, video_seconds=seconds,
               processing_fps=frames/row['elapsed_with_cleanup_s'],
               episode_estimate_hours=source_duration*row['elapsed_with_cleanup_s']/seconds/3600)
    active = [s for s in samples if row['started_s'] <= s['elapsed_s'] <= row['started_s']+row['elapsed_with_cleanup_s']]
    for source, dest, divisor in [('gpu_used_mib','gpu_total_peak_gib',1024), ('rss_bytes','process_rss_peak_gib',1024**3),
                                  ('cgroup_bytes','container_peak_gib',1024**3), ('swap_bytes','swap_peak_bytes',1)]:
        values = [s[source] for s in active if s.get(source) is not None]
        row[dest] = max(values)/divisor if values else None
(root/'relay.results.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
