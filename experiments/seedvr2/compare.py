"""Build same-frame Lanczos comparisons; no generated HR ground truth is assumed."""
import argparse
import av
from PIL import Image, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument('source')
parser.add_argument('enhanced')
parser.add_argument('output')
parser.add_argument('--source-label', default='Lanczos')
parser.add_argument('--enhanced-label', default='SeedVR2-3B FP8')
parser.add_argument('--box', nargs=4, type=int)
parser.add_argument('--frames', nargs='+', type=int, default=[0, 4, 5, 8, 9, 12])
args = parser.parse_args()
source = av.open(args.source)
enhanced = av.open(args.enhanced)
selected = set(args.frames)
pairs = []
for index, (before, after) in enumerate(zip(source.decode(video=0), enhanced.decode(video=0))):
    if index not in selected:
        continue
    a, b = before.to_image(), after.to_image()
    a = a.resize(b.size, Image.Resampling.LANCZOS)
    if args.box:
        a, b = a.crop(tuple(args.box)), b.crop(tuple(args.box))
    pairs.append((index, a, b))
    if len(pairs) == len(selected):
        break
if not pairs:
    raise ValueError('No decoded frames')
w,h = pairs[0][1].size
canvas = Image.new('RGB', (w*2, (h+30)*len(pairs)), 'white')
draw = ImageDraw.Draw(canvas)
for row, (index,a,b) in enumerate(pairs):
    y = row*(h+30)
    draw.text((8,y+8), f'Frame {index}: {args.source_label}', fill='black')
    draw.text((w+8,y+8), args.enhanced_label, fill='black')
    canvas.paste(a, (0,y+30))
    canvas.paste(b, (w,y+30))
canvas.save(args.output)
