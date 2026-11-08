# SPDX-License-Identifier: GPL-2.0-or-later
"""Side-by-side comparison image (owner: A). PLANO.md §8.3. Run by compare.sh in Blender headless:

    Blender --background --factory-startup --python compose.py -- <left.png> <right.png> <out.png> [<left label> <right label>]

Both inputs are already scaled to the same height (sips in compare.sh). Output = left | gap | right on a
white canvas with a label band on top (blf drawn into the image buffer).
"""

import sys

import blf
import bpy
import imbuf
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
left, right, out = argv[0], argv[1], argv[2]
labels = (argv[3], argv[4]) if len(argv) >= 5 else ("SketchUp 2027", "SketchUp Mode")
GAP, BAND = 24, 64


def load(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    return px.reshape(h, w, 4)


a, b = load(left), load(right)
h = max(a.shape[0], b.shape[0])
w = a.shape[1] + GAP + b.shape[1]
canvas = np.ones((h + BAND, w, 4), dtype=np.float32)
canvas[h - a.shape[0]:h, :a.shape[1]] = a            # image rows are bottom-up
canvas[h - b.shape[0]:h, a.shape[1] + GAP:] = b

res = bpy.data.images.new("su_compare", w, h + BAND, alpha=False)
res.pixels.foreach_set(canvas.ravel())
res.filepath_raw = out
res.file_format = 'PNG'
res.save()

# labels: draw text into the saved PNG through an ImBuf
ib = imbuf.load(out)
font = 0
with blf.bind_imbuf(font, ib):
    blf.size(font, 36)
    blf.color(font, 0.1, 0.1, 0.12, 1.0)
    for x0, text in ((16, labels[0]), (a.shape[1] + GAP + 16, labels[1])):
        blf.position(font, x0, h + 16, 0)
        blf.draw_buffer(font, text)
imbuf.write(ib, filepath=out)
print("compose.py: wrote", out, w, "x", h + BAND)
