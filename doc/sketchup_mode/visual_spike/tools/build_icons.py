"""Recolour Blender's toolbar .dat geometry icons into a SketchUp-like palette (navy / cyan / red).
Blender inverts HSL lightness of geometry icons when the theme is light (interface_icons.cc,
BKE_icon_geom_invert_lightness), so we store the *pre-inverted* colour of the colour we want on screen.
usage: python3 build_icons.py <blender datafiles/icons dir> <out dir>"""
import sys, os, colorsys
SRC, OUT = sys.argv[1], sys.argv[2]
NAVY, CYAN, RED, PINK, WHITE = (0, 66, 110), (0, 150, 220), (230, 20, 20), (240, 110, 120), (255, 255, 255)
def target(c):
    r, g, b = c
    if (r, g, b) == (117, 255, 175): return CYAN      # Blender green "geometry"   -> SketchUp cyan-blue
    if (r, g, b) == (255, 176, 43):  return RED       # Blender orange accent      -> SketchUp red accent
    if (r, g, b) == (245, 107, 91):  return PINK      # eraser body
    if (r, g, b) == (217, 175, 245): return CYAN
    if (r, g, b) == (0, 0, 0):       return WHITE     # outline/shadow (Blender shows it white in light themes)
    return NAVY                                        # white/grey glyph bodies -> navy
def pre_invert(c):
    h, l, s = colorsys.rgb_to_hls(*(x / 255 for x in c))
    return tuple(int(round(x * 255)) for x in colorsys.hls_to_rgb(h, 1.0 - l, s))
def convert(name):
    b = open(os.path.join(SRC, name + ".dat"), "rb").read()
    hdr, data = b[:8], b[8:]
    n = len(data) // 18
    coords, cols = data[:n * 6], bytearray(data[n * 6:])
    for i in range(0, len(cols), 4):
        r, g, bb = pre_invert(target(tuple(cols[i:i + 3])))
        cols[i:i + 3] = bytes((r, g, bb))
    open(os.path.join(OUT, "su." + name + ".dat"), "wb").write(hdr + coords + bytes(cols))
os.makedirs(OUT, exist_ok=True)
for f in sorted(os.listdir(SRC)):
    if f.endswith(".dat") and (f.startswith("ops.") or f.startswith("brush.gpencil")):
        convert(f[:-4])
print("ok", len(os.listdir(OUT)))
