# SPDX-License-Identifier: GPL-2.0-or-later
"""Original PNG artwork of SketchUp Mode (owner: D), drawn with Pillow — no third-party art.

`build(out_dir)` writes icons/png/<name>.png (+ <name>_dim.png at 40 % alpha for tool icons) and returns
how many images were written. Called by build_icons.py (system python3 with Pillow).

* style_simple — tray thumbnail of the default style (sky, grey ground, white box + cylinder, black
  edges); ported from visual_spike/tools/build_style_thumb.py.
"""

import os
import sys

sys.dont_write_bytecode = True

from PIL import Image, ImageDraw     # noqa: E402  (Pillow is required for this module)


def style_simple(path, S=128):
    im = Image.new("RGB", (S, S))
    d = ImageDraw.Draw(im)
    hz = 52
    for y in range(hz):
        t = y / hz
        d.line([(0, y), (S, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip((30, 166, 221), (191, 229, 245))))
    d.rectangle([0, hz, S, S], fill=(191, 191, 198))
    k = (0, 0, 0)
    front = [(22, 62), (62, 70), (62, 110), (22, 100)]
    side = [(62, 70), (96, 60), (96, 98), (62, 110)]
    top = [(22, 62), (56, 54), (96, 60), (62, 70)]
    d.polygon(top, fill=(160, 160, 160), outline=k)
    d.polygon(front, fill=(252, 252, 252), outline=k)
    d.polygon(side, fill=(210, 210, 210), outline=k)
    d.rectangle([84, 40, 112, 84], fill=(236, 236, 236))
    d.line([(84, 40), (84, 84)], fill=k)
    d.line([(112, 40), (112, 84)], fill=k)
    d.ellipse([84, 35, 112, 45], fill=(176, 176, 176), outline=k)
    d.arc([84, 79, 112, 89], 0, 180, fill=k)
    d.rectangle([0, 0, S - 1, S - 1], outline=(170, 170, 180))
    im.save(path)


def build(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    n = 0
    style_simple(os.path.join(out_dir, "style_simple.png"))
    n += 1
    return n


if __name__ == "__main__":
    print(build(sys.argv[1]))
