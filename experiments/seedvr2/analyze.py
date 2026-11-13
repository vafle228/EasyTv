"""Summarize measured runs against actual encoded frame counts."""
import json
import re
from pathlib import Path
import subprocess

root=Path('/benchmark')
manifest=json.loads((root/'manifest.json').read_text())
rows=[]
for path in sorted((root/'logs').glob('*.summary.json')):
    run=json.loads(path.read_text())
    if run.get('engine', 'seedvr2') != 'seedvr2':
        continue
    args=run['args']
    output=Path(args[args.index('--output')+1])
    row={'name':run['name'], 'exit_code':run['exit_code'], 'elapsed_s':run['elapsed_s'],
         'gpu_total_peak_gib':run['peak_gpu_used_mib']/1024 if run['peak_gpu_used_mib'] else None,
         'torch_allocated_peak_gib':run['torch_allocated_bytes']/1024**3,
         'torch_reserved_peak_gib':run['torch_reserved_bytes']/1024**3,
         'process_rss_peak_gib':run['peak_rss_bytes']/1024**3,
         'container_peak_gib':run['peak_cgroup_bytes']/1024**3,
         'swap_peak_bytes':run['peak_swap_bytes']}
    if run['exit_code']==0 and output.is_file():
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0',
            '-show_entries','stream=width,height,avg_frame_rate,nb_read_frames,duration','-of','json',str(output)]))['streams'][0]
        frames=int(probe['nb_read_frames'])
        num,den=map(int,probe['avg_frame_rate'].split('/'))
        seconds=frames*den/num
        row.update(width=probe['width'],height=probe['height'],frames=frames,video_seconds=seconds,
                   processing_fps=frames/run['elapsed_s'],realtime_ratio=seconds/run['elapsed_s'],
                   episode_estimate_hours=manifest['source']['duration_s']*run['elapsed_s']/seconds/3600)
    log = (root/'logs'/f"{run['name']}.log").read_text(errors='replace')
    row['phases_s'] = {name: [float(value) for value in re.findall(rf'Phase {number}: [^\n]+?complete: ([\d.]+)s', log)]
                       for number, name in enumerate(('vae_encode', 'dit', 'vae_decode', 'postprocess'), 1)}
    rows.append(row)
(root/'results.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
