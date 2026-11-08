# SPDX-License-Identifier: GPL-2.0-or-later
"""Original icon artwork of SketchUp Mode (owner: D) — no third-party art. §9.2-D item 9.1.

Our own drawings of the usual SketchUp METAPHORS (metaphors are not protected; nothing is copied or
traced): pencil (Linha), eraser (Apagar), paint bucket (Pintura), tape measure (Fita métrica), box + red
up arrow (Empurrar/puxar), four red arrows (Mover), red circular arrows (Girar), box + diagonal arrow
(Escala), protractor (Transferidor), magnifier (Aplicar zoom), hand (Panorâmica), red orbit arrows around
a globe (Órbita), arrow cursor (Selecionar), and the status-bar pin (light grey) and ⓘ (thin black).
Flat style: navy #00426E strokes, light-cyan fills, red #DC1E1E accents.

The icons are VECTOR: drawn on a 100-unit grid (y down) into triangles and written as Blender toolbar
geometry icons (`.dat`, "VCO" format, 255×255 range, y up) — crisp at any toolbar size, unlike preview
images which Blender draws at 16 px. Blender inverts the HSL lightness of geometry icons when the
toolbar theme is light, so the stored colours are pre-inverted (build_icons.pre_invert).
Output: icons/su.draw.<name>.dat and su.draw.<name>_dim.dat (40 % alpha) → icon handle "draw.<name>".

Also draws the PNG thumbnail of the default style for the tray (icons/png/style_simple.png) and, on
request, a review contact sheet (PNG, Pillow).
"""

import colorsys
import math
import os
import struct
import sys

sys.dont_write_bytecode = True

NAVY = (0, 66, 110, 255)
CYAN = (0, 150, 220, 255)
CYAN_L = (196, 230, 248, 255)
RED = (220, 30, 30, 255)
WHITE = (255, 255, 255, 255)
PINK = (245, 140, 150, 255)
WOOD = (250, 226, 190, 255)
YELLOW = (250, 214, 70, 255)
GREY_L = (170, 172, 180, 255)
BLACK = (20, 20, 24, 255)
W = 6.0           # default stroke (units of the 100 grid)
# The 100 grid maps to 13 %…87 % of the .dat range, the extent of Blender's own toolbar icons
# (ops.transform.translate spans 34…221 of 255), so ours sit at the same visual size.
MARGIN = 0.13
SPAN = 1.0 - 2 * MARGIN
# Label icons (status bar, tray title) are drawn in a 20 pt box next to 11 pt text: keep them smaller.
MARGIN_UI = 0.25


# ------------------------------------------------------------------------------------------- vector canvas
def _area(pts):
    return sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts))) / 2.0


def _inside(p, a, b, c):
    def s(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
    d1, d2, d3 = s(p, a, b), s(p, b, c), s(p, c, a)
    neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (neg and pos)


def triangulate(pts):
    """Ear clipping of a simple polygon → list of triangles."""
    pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 3:
        return []
    idx = list(range(len(pts)))
    if _area(pts) < 0:
        idx.reverse()
    tris, guard = [], 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) <= 0:
                continue
            if any(_inside(pts[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((a, b, c))
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        tris.append(tuple(pts[i] for i in idx))
    return tris


class Canvas:
    def __init__(self):
        self.tris = []      # [((x, y)×3, rgba)]

    def fill(self, pts, col):
        for t in triangulate(list(pts)):
            self.tris.append((t, col))

    def disc(self, cx, cy, r, col, n=28, ry=None):
        ry = r if ry is None else ry
        ring = [(cx + r * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]
        for i in range(n):
            self.tris.append((((cx, cy), ring[i], ring[(i + 1) % n]), col))

    def ring(self, cx, cy, r, w, col, n=36, ry=None):
        ry = r if ry is None else ry
        ro, ri = (r + w / 2, ry + w / 2), (r - w / 2, ry - w / 2)
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            o0 = (cx + ro[0] * math.cos(a0), cy + ro[1] * math.sin(a0))
            o1 = (cx + ro[0] * math.cos(a1), cy + ro[1] * math.sin(a1))
            i0 = (cx + ri[0] * math.cos(a0), cy + ri[1] * math.sin(a0))
            i1 = (cx + ri[0] * math.cos(a1), cy + ri[1] * math.sin(a1))
            self.tris.append(((o0, o1, i1), col))
            self.tris.append(((o0, i1, i0), col))

    def stroke(self, pts, col, w, closed=False, caps=True):
        pts = list(pts)
        segs = list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if closed else [])
        h = w / 2
        for a, b in segs:
            dx, dy = b[0] - a[0], b[1] - a[1]
            n = math.hypot(dx, dy)
            if n < 1e-9:
                continue
            px, py = -dy / n * h, dx / n * h
            q = [(a[0] + px, a[1] + py), (b[0] + px, b[1] + py), (b[0] - px, b[1] - py), (a[0] - px, a[1] - py)]
            self.tris.append(((q[0], q[1], q[2]), col))
            self.tris.append(((q[0], q[2], q[3]), col))
        joints = pts if (closed or caps) else pts[1:-1]
        for p in joints:
            self.disc(p[0], p[1], h, col, 12)

    # ---- output
    def dat_bytes(self, alpha=1.0, margin=None):
        m = MARGIN if margin is None else margin
        span = 1.0 - 2 * m
        coords, cols = bytearray(), bytearray()
        for tri, col in self.tris:
            r, g, b = pre_invert(col[:3])
            a = int(round(col[3] * alpha))
            for x, y in tri:
                coords += bytes((_q(255 * (m + span * x / 100.0)), _q(255 * (1.0 - m - span * y / 100.0))))
                cols += bytes((r, g, b, a))
        return b"VCO\x00" + struct.pack("BBBB", 255, 255, 0, 0) + bytes(coords) + bytes(cols)

    def raster(self, size=128, ss=4):
        from PIL import Image, ImageDraw
        S = size * ss
        im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        k = S / 100.0
        for tri, col in self.tris:
            d.polygon([(x * k, y * k) for x, y in tri], fill=col)
        return im.resize((size, size), Image.LANCZOS)


def _q(v):
    return max(0, min(255, int(round(v))))


def pre_invert(c):
    h, l, s = colorsys.rgb_to_hls(*(x / 255 for x in c))
    return tuple(int(round(x * 255)) for x in colorsys.hls_to_rgb(h, 1.0 - l, s))


# ------------------------------------------------------------------------------------------- helpers
def rot(pts, ang_deg, cx, cy):
    a = math.radians(ang_deg)
    c, s = math.cos(a), math.sin(a)
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]


def poly(d, pts, fill=None, outline=NAVY, w=W):
    if fill is not None:
        d.fill(pts, fill)
    if outline is not None and w > 0:
        d.stroke(pts, outline, w, closed=True)


def line(d, pts, col=NAVY, w=W, caps=True):
    d.stroke(pts, col, w, closed=False, caps=caps)


def circle(d, cx, cy, r, fill=None, outline=NAVY, w=W):
    if fill is not None:
        d.disc(cx, cy, r, fill)
    if outline is not None and w > 0:
        d.ring(cx, cy, r, w, outline)


def arrow_head(d, tip, direction, size=16, col=RED):
    dx, dy = direction
    n = math.hypot(dx, dy) or 1.0
    dx, dy = dx / n, dy / n
    px, py = -dy, dx
    bx, by = tip[0] - dx * size, tip[1] - dy * size
    d.fill([tip, (bx + px * size * 0.6, by + py * size * 0.6), (bx - px * size * 0.6, by - py * size * 0.6)], col)


def arrow(d, a, b, col=RED, w=7, head=17):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    ux, uy = dx / n, dy / n
    line(d, [a, (b[0] - ux * head * 0.8, b[1] - uy * head * 0.8)], col, w, caps=False)
    arrow_head(d, b, (dx, dy), head, col)


def arc_pts(cx, cy, rx, ry, a0, a1, tilt=0.0):
    n = max(8, int(abs(a1 - a0) / 4))
    pts = [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
            cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
    return rot(pts, tilt, cx, cy) if tilt else pts


def arc_arrow(d, cx, cy, rx, ry, a0, a1, col=RED, w=7, head=16, tilt=0.0):
    pts = arc_pts(cx, cy, rx, ry, a0, a1, tilt)
    tip = pts[-1]
    L, cut = 0.0, 0
    while cut < len(pts) - 2 and L < head * 0.7:
        L += math.hypot(pts[-1 - cut][0] - pts[-2 - cut][0], pts[-1 - cut][1] - pts[-2 - cut][1])
        cut += 1
    prev = pts[-2]
    line(d, pts[:len(pts) - cut], col, w, caps=False)
    arrow_head(d, tip, (tip[0] - prev[0], tip[1] - prev[1]), head, col)


def iso_box(d, x, y, w, h, depth, top=CYAN_L, front=WHITE, side=CYAN_L, stroke=NAVY, sw=5):
    dx, dy = depth * 0.9, -depth * 0.55
    f = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    t = [(x, y), (x + dx, y + dy), (x + w + dx, y + dy), (x + w, y)]
    s = [(x + w, y), (x + w + dx, y + dy), (x + w + dx, y + h + dy), (x + w, y + h)]
    poly(d, t, top, stroke, sw)
    poly(d, s, side, stroke, sw)
    poly(d, f, front, stroke, sw)


# ------------------------------------------------------------------------------------------- tools
def icon_line(d):
    poly(d, [(30, 58), (72, 16), (86, 30), (44, 72)], RED, NAVY, 5)
    poly(d, [(72, 16), (78, 10), (92, 24), (86, 30)], CYAN_L, NAVY, 5)          # eraser cap
    poly(d, [(30, 58), (44, 72), (14, 88)], WOOD, NAVY, 5)                       # wood tip
    poly(d, [(20, 75), (27, 82), (14, 88)], NAVY, NAVY, 3)                       # graphite


def icon_eraser(d):
    c = (50, 44)
    poly(d, rot([(10, 30), (90, 30), (90, 60), (10, 60)], -38, *c), CYAN_L, NAVY, 5)
    poly(d, rot([(10, 30), (38, 30), (38, 60), (10, 60)], -38, *c), PINK, NAVY, 5)
    line(d, [(40, 90), (92, 90)], NAVY, 5)


def icon_paint(d):
    c = (44, 54)
    poly(d, rot([(20, 34), (68, 34), (62, 86), (26, 86)], -30, *c), CYAN_L, NAVY, 5)
    lip = rot([(20, 34), (68, 34)], -30, *c)
    line(d, lip, NAVY, 7)
    line(d, rot([(24, 34), (24, 14), (64, 14), (64, 34)], -30, *c), NAVY, 4.5)
    x, y = lip[1]
    d.fill([(x - 7, y + 2), (x + 7, y + 2), (x + 9, y + 30), (x - 1, y + 30)], RED)
    circle(d, x + 4, y + 33, 9, RED, None, 0)


def icon_tape(d):
    circle(d, 40, 44, 30, CYAN_L, NAVY, 5)
    circle(d, 40, 44, 11, WHITE, NAVY, 5)
    circle(d, 40, 44, 3, NAVY, None, 0)
    poly(d, [(40, 74), (92, 74), (92, 88), (40, 88)], YELLOW, NAVY, 4)
    for x in range(48, 92, 8):
        line(d, [(x, 74), (x, 80 if (x // 8) % 2 else 83)], NAVY, 2.5, caps=False)
    circle(d, 18, 20, 6, RED, None, 0)


def icon_pushpull(d):
    iso_box(d, 12, 56, 52, 30, 26, top=CYAN, front=WHITE, side=CYAN_L)
    arrow(d, (50, 52), (50, 6), RED, 8, 20)


def icon_move(d):
    for (bx, by) in ((50, 6), (50, 94), (6, 50), (94, 50)):
        arrow(d, (50, 50), (bx, by), RED, 7, 18)
    circle(d, 50, 50, 6, RED, None, 0)


def icon_rotate(d):
    arc_arrow(d, 50, 50, 34, 34, 200, 340, RED, 8, 18)
    arc_arrow(d, 50, 50, 34, 34, 20, 160, RED, 8, 18)


def icon_scale(d):
    poly(d, [(10, 30), (70, 30), (70, 90), (10, 90)], WHITE, NAVY, 5)
    poly(d, [(10, 62), (38, 62), (38, 90), (10, 90)], CYAN_L, NAVY, 5)
    arrow(d, (36, 64), (88, 12), RED, 8, 20)


def icon_protractor(d):
    cx, cy, r = 50, 78, 42
    pts = [(cx + r * math.cos(math.radians(180 + a)), cy + r * math.sin(math.radians(180 + a)))
           for a in range(0, 181, 6)]
    poly(d, pts, CYAN_L, NAVY, 5)
    for a in range(15, 180, 15):
        u = (math.cos(math.radians(180 + a)), math.sin(math.radians(180 + a)))
        r0 = r * (0.72 if a % 45 == 0 else 0.82)
        line(d, [(cx + u[0] * r0, cy + u[1] * r0), (cx + u[0] * r * 0.97, cy + u[1] * r * 0.97)], NAVY, 3, caps=False)
    circle(d, cx, cy, 12, WHITE, NAVY, 4)
    line(d, [(cx, cy), (cx + 40 * math.cos(math.radians(-50)), cy + 40 * math.sin(math.radians(-50)))], RED, 6)


def icon_zoom(d):
    line(d, [(60, 60), (88, 88)], NAVY, 13)
    circle(d, 40, 40, 28, CYAN_L, NAVY, 7)
    line(d, arc_pts(40, 40, 17, 17, 200, 260), WHITE, 5)


def icon_pan(d):
    for x, top in ((30, 18), (42, 10), (54, 12), (66, 20)):                     # fingers
        poly(d, [(x - 5.5, 44), (x - 5.5, top + 5), (x, top), (x + 5.5, top + 5), (x + 5.5, 44)], WHITE, NAVY, 4.5)
    poly(d, rot([(14, 52), (14, 40), (20, 35), (26, 40), (26, 60)], -35, 20, 58), WHITE, NAVY, 4.5)   # thumb
    poly(d, [(24, 40), (72, 40), (72, 66), (62, 88), (34, 88), (24, 70)], WHITE, NAVY, 4.5)          # palm
    d.fill([(25.5, 37.5), (70.5, 37.5), (70.5, 46), (25.5, 46)], WHITE)                               # finger bases
    line(d, [(24, 40), (24, 70)], NAVY, 4.5)
    line(d, [(72, 40), (72, 66)], NAVY, 4.5)


def icon_orbit(d):
    circle(d, 50, 50, 20, CYAN_L, NAVY, 5)                                      # globe
    d.ring(50, 50, 9, 3.5, NAVY, ry=20)
    line(d, [(30, 50), (70, 50)], NAVY, 3.5, caps=False)
    arc_arrow(d, 50, 50, 44, 20, 195, 335, RED, 7, 16, tilt=-25)
    arc_arrow(d, 50, 50, 44, 20, 15, 155, RED, 7, 16, tilt=-25)


def icon_select(d):
    poly(d, [(28, 10), (28, 78), (44, 63), (56, 90), (68, 84), (56, 58), (78, 58)], NAVY, NAVY, 4)


TOOLS = {
    "line": icon_line, "eraser": icon_eraser, "paint": icon_paint, "tape": icon_tape,
    "pushpull": icon_pushpull, "move": icon_move, "rotate": icon_rotate, "scale": icon_scale,
    "protractor": icon_protractor, "zoom": icon_zoom, "pan": icon_pan, "orbit": icon_orbit,
    "select": icon_select,
}


# ------------------------------------------------------------------------------------------- status bar
def ui_pin(d):
    c = (50, 50)
    line(d, rot([(50, 58), (50, 90)], 40, *c), GREY_L, 5)
    poly(d, rot([(40, 14), (60, 14), (58, 46), (70, 58), (30, 58), (42, 46)], 40, *c), GREY_L, None, 0)


def ui_info(d):
    circle(d, 50, 50, 40, None, BLACK, 4)
    circle(d, 50, 29, 5, BLACK, None, 0)
    line(d, [(50, 44), (50, 73)], BLACK, 6)


UI = {"ui_pin": ui_pin, "ui_info": ui_info}


# ------------------------------------------------------------------------------------------- PNG
def style_simple(path, S=128):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (S, S))
    d = ImageDraw.Draw(im)
    hz = 52
    for y in range(hz):
        t = y / hz
        d.line([(0, y), (S, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip((30, 166, 221), (191, 229, 245))))
    d.rectangle([0, hz, S, S], fill=(191, 191, 198))
    k = (0, 0, 0)
    d.polygon([(22, 62), (56, 54), (96, 60), (62, 70)], fill=(160, 160, 160), outline=k)
    d.polygon([(22, 62), (62, 70), (62, 110), (22, 100)], fill=(252, 252, 252), outline=k)
    d.polygon([(62, 70), (96, 60), (96, 98), (62, 110)], fill=(210, 210, 210), outline=k)
    d.rectangle([84, 40, 112, 84], fill=(236, 236, 236))
    d.line([(84, 40), (84, 84)], fill=k)
    d.line([(112, 40), (112, 84)], fill=k)
    d.ellipse([84, 35, 112, 45], fill=(176, 176, 176), outline=k)
    d.arc([84, 79, 112, 89], 0, 180, fill=k)
    d.rectangle([0, 0, S - 1, S - 1], outline=(170, 170, 180))
    im.save(path)


# ------------------------------------------------------------------------------------------- build
def canvases():
    out = {}
    for name, fn in list(TOOLS.items()) + list(UI.items()):
        c = Canvas()
        fn(c)
        out[name] = c
    return out


def build(icons_dir):
    """Write su.draw.<name>.dat (+ _dim for tools) into `icons_dir`, png/style_simple.png. Returns count."""
    n = 0
    for name, c in canvases().items():
        with open(os.path.join(icons_dir, "su.draw.{:s}.dat".format(name)), "wb") as f:
            f.write(c.dat_bytes(margin=MARGIN_UI if name in UI else None))
        if name in TOOLS:
            with open(os.path.join(icons_dir, "su.draw.{:s}_dim.dat".format(name)), "wb") as f:
                f.write(c.dat_bytes(0.4))
        n += 1
    png = os.path.join(icons_dir, "png")
    os.makedirs(png, exist_ok=True)
    for f in os.listdir(png):
        if f.endswith(".png"):
            os.remove(os.path.join(png, f))
    try:
        style_simple(os.path.join(png, "style_simple.png"))
    except ImportError as ex:
        print("build_icons_draw: style thumbnail skipped ({})".format(ex))
    return n


def contact_sheet(path):
    from PIL import Image
    cs = canvases()
    sheet = Image.new("RGBA", (len(cs) * 72 + 8, 120), (241, 241, 246, 255))
    for i, (name, c) in enumerate(cs.items()):
        sheet.alpha_composite(c.raster(64), (8 + i * 72, 4))
        sheet.alpha_composite(c.raster(32), (24 + i * 72, 78))
    sheet.save(path)


if __name__ == "__main__":
    if sys.argv[1] == "--sheet":
        contact_sheet(sys.argv[2])
    else:
        print(build(sys.argv[1]))
