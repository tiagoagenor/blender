#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build the SketchUp Mode icon set (owner: D). Ported from visual_spike/tools/build_icons.py.

    python3 tools/sketchup_mode/build_icons.py <blender datafiles/icons dir> <template icons dir>

1. Recolours the Blender toolbar `.dat` geometry icons referenced in su/icons.py (TOOL_ICONS) into the
   SketchUp palette (white/grey → navy #00426E, Blender green → cyan #0096DC, orange → red), writing
   `su.<handle>.dat` and a 40 % alpha `su.<handle>_dim.dat`. Blender inverts the HSL lightness of
   geometry icons when the toolbar theme is light (interface_icons.cc), so the colours stored are the
   PRE-INVERTED colours of what we want on screen.
2. Draws the original PNG icons (icons/png/*.png, see build_icons_png.py) when Pillow is available.
Only the system python3 is needed (no bpy).
"""

import colorsys
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NAVY, CYAN, RED, PINK, WHITE = (0, 66, 110), (0, 150, 220), (230, 20, 20), (240, 110, 120), (255, 255, 255)
DIM_ALPHA = 0.4


def target(c):
    if c == (117, 255, 175):
        return CYAN       # Blender green "geometry" → SketchUp cyan-blue
    if c == (255, 176, 43):
        return RED        # Blender orange accent → red accent
    if c == (245, 107, 91):
        return PINK       # eraser body
    if c == (217, 175, 245):
        return CYAN
    if c == (0, 0, 0):
        return WHITE      # outline/shadow (shown white in light themes)
    return NAVY           # white/grey glyph bodies → navy


def pre_invert(c):
    h, l, s = colorsys.rgb_to_hls(*(x / 255 for x in c))
    return tuple(int(round(x * 255)) for x in colorsys.hls_to_rgb(h, 1.0 - l, s))


def convert(src_dir, out_dir, handle):
    src = os.path.join(src_dir, handle + ".dat")
    with open(src, "rb") as f:
        b = f.read()
    hdr, data = b[:8], b[8:]
    n = len(data) // 18                         # per triangle: 3×(x, y) u8 coords + 3×RGBA u8 colours
    coords, cols = data[:n * 6], bytearray(data[n * 6:])
    for i in range(0, len(cols), 4):
        r, g, bb = pre_invert(target(tuple(cols[i:i + 3])))
        cols[i:i + 3] = bytes((r, g, bb))
    with open(os.path.join(out_dir, "su." + handle + ".dat"), "wb") as f:
        f.write(hdr + coords + bytes(cols))
    dim = bytearray(cols)
    for i in range(3, len(dim), 4):
        dim[i] = int(round(dim[i] * DIM_ALPHA))
    with open(os.path.join(out_dir, "su." + handle + "_dim.dat"), "wb") as f:
        f.write(hdr + coords + bytes(dim))


def handles_from_icons_py(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    found = set(re.findall(r'"((?:ops|brush)\.[A-Za-z0-9_.]+)"', text))
    return sorted(h for h in found if not h.endswith("_dim"))


def main():
    src_dir, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    icons_py = os.path.join(os.path.dirname(os.path.abspath(out_dir)), "su", "icons.py")
    for f in os.listdir(out_dir):
        if f.startswith("su.") and f.endswith(".dat"):
            os.remove(os.path.join(out_dir, f))
    handles = handles_from_icons_py(icons_py)
    handles = [h for h in handles if os.path.isfile(os.path.join(src_dir, h + ".dat"))]
    for h in handles:
        convert(src_dir, out_dir, h)
    print("build_icons: {:d} recoloured .dat icons (+ _dim)".format(len(handles)))
    try:
        sys.path.insert(0, HERE)
        import build_icons_png
    except ImportError as ex:
        print("build_icons: original PNG icons skipped ({})".format(ex))
        return
    n = build_icons_png.build(os.path.join(out_dir, "png"))
    print("build_icons: {:d} original PNG icons (+ _dim)".format(n))


if __name__ == "__main__":
    main()
