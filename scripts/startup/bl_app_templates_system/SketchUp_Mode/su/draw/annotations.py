# SPDX-License-Identifier: GPL-2.0-or-later
"""Guides, dimensions and texts in the viewport (owner: G). PLANO.md §2.2, §3.3, §6.3.

Layers (draw/handlers.py):
  guides   POST_VIEW  GUIDES=40    infinite dashed guide lines (clipped to the view frustum) and
                                   guide points (small cross), hidden with Visualizar ▸ Guias
  annot    POST_VIEW  ANNOT_3D=45  text leaders
  annot2d  POST_PIXEL ANNOT_2D=10  dimensions (SketchUp style, drawn ON TOP, never hidden by the geometry
                                   they annotate: extension lines, dimension line, slash ends, text centred
                                   on the line and aligned to the screen — AC-DIM-3) and leader texts
           + the vertical-FOV keeper (core.camera.check_fov) — Blender's lens fits the width, so the
             35° vertical FOV must be re-fitted when the region aspect changes (AC-NAV-7).
"""

import math

import bpy
from mathutils import Vector

from .. import colors, registry
from ..core import camera, guides, viewutil
from . import handlers, prims

ORDER = 240

DASH_PX, GAP_PX = 6, 4
EXT_OVERSHOOT_PX = 6          # extension lines pass the dimension line by this much
SLASH_PX = 12
TEXT_SIZE = 11
_last = {"guides": 0, "dims": 0, "texts": 0}


def clip_line(dc, co, u, margin=1.05):
    """Part of the infinite line co + t·u inside the view frustum → (a, b) world, or None."""
    pm = dc.rv3d.perspective_matrix
    A = pm @ Vector((co[0], co[1], co[2], 1.0))
    D = pm @ Vector((u[0], u[1], u[2], 0.0))
    t0, t1 = -1e7, 1e7
    near = 1e-5

    def limit(f0, f1):          # f0 + t·f1 >= 0
        nonlocal t0, t1
        if abs(f1) < 1e-15:
            return f0 >= 0.0
        t = -f0 / f1
        if f1 > 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        return True

    ok = (limit(margin * A.w + A.x, margin * D.w + D.x) and limit(margin * A.w - A.x, margin * D.w - D.x)
          and limit(margin * A.w + A.y, margin * D.w + D.y) and limit(margin * A.w - A.y, margin * D.w - D.y)
          and limit(A.w - near, D.w))
    if not ok or t0 >= t1:
        return None
    co = Vector(co)
    u = Vector(u)
    return co + u * t0, co + u * t1


def draw_guides(dc):
    d = guides.data()
    _last["guides"] = 0
    if d is None or not guides.guides_visible() or not len(d.guides):
        return
    rgba = colors.rgba(colors.GUIDE, 1.0)
    segs, pts = [], []
    for g in d.guides:
        if g.kind == 'POINT':
            pts.append(Vector(g.co))
            continue
        c = clip_line(dc, g.co, Vector(g.direction))
        if c is not None:
            segs.append(c)
    if segs:
        prims.dashed_many(dc, segs, rgba, 1.0, DASH_PX, GAP_PX, depth=True)
    if pts:
        prims.points(dc, pts, rgba, 7, 'CROSS', outline=False)
    _last["guides"] = len(segs) + len(pts)


def _px_world(dc, co, px):
    k = viewutil.pixel_size_at(dc.region, dc.rv3d, co)
    return k * viewutil.ui_px(px)


def _rot(v, deg):
    c, s_ = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return Vector((v.x * c - v.y * s_, v.x * s_ + v.y * c))


def dimension_screen(dc, a, b, off):
    """Screen-space (POST_PIXEL) parts of a linear dimension, SketchUp style: two extension lines from the
    measured points past the dimension line, the dimension line, slash end marks; plus the text
    position (middle of the dimension line). Returns (lines, slashes, mid) or None when off screen."""
    a, b, off = Vector(a), Vector(b), Vector(off)
    P = [viewutil.project(dc.region, dc.rv3d, p) for p in (a, b, a + off, b + off)]
    if any(p is None for p in P):
        return None
    sa, sb, SA, SB = P
    lines = [(SA, SB)]
    over = viewutil.ui_px(EXT_OVERSHOOT_PX)
    for p, Q in ((sa, SA), (sb, SB)):
        e = Q - p
        if e.length > 0.5:
            lines.append((p, Q + e.normalized() * over))
    slashes = []
    t = SB - SA
    if t.length > 0.5:
        t = t.normalized()
        h = viewutil.ui_px(SLASH_PX) * 0.5
        d = _rot(t, 45.0)
        for Q in (SA, SB):
            slashes.append((Q - d * h, Q + d * h))
    return lines, slashes, (SA + SB) * 0.5


def draw_dimension_2d(dc, a, b, off, text):
    parts = dimension_screen(dc, a, b, off)
    if parts is None:
        return False
    lines, slashes, mid = parts
    black = colors.rgba(colors.EDGE, 1.0)
    prims.lines(dc, [(tuple(p) + (0.0,), tuple(q) + (0.0,)) for p, q in lines], black, 1.0, depth=False)
    prims.lines(dc, [(tuple(p) + (0.0,), tuple(q) + (0.0,)) for p, q in slashes], black, 2.0, depth=False)
    if text:
        prims.text(dc, (mid.x, mid.y - viewutil.ui_px(TEXT_SIZE) * 0.38), text, TEXT_SIZE, black,
                   bg=(1.0, 1.0, 1.0, 0.85), align='CENTER')
    return True


def draw_annot_3d(dc):
    d = guides.data()
    if d is None:
        return
    black = colors.rgba(colors.EDGE, 1.0)
    lead = [(Vector(t.anchor), Vector(t.leader_end)) for t in d.texts
            if (Vector(t.leader_end) - Vector(t.anchor)).length > 1e-9]
    if lead:
        prims.lines(dc, lead, black, 1.0, depth=False)
        prims.points(dc, [a for a, _b in lead], black, 4, 'CIRCLE', outline=False)
    _last["texts"] = len(d.texts)


def draw_annot_2d(dc):
    camera.check_fov(dc)
    d = guides.data()
    if d is None:
        return
    black = colors.rgba(colors.EDGE, 1.0)
    n = 0
    for i, dm in enumerate(d.dims):
        if draw_dimension_2d(dc, dm.a, dm.b, dm.offset, guides.dimension_text(i)):
            n += 1
    _last["dims"] = n
    for t in d.texts:
        s = viewutil.project(dc.region, dc.rv3d, Vector(t.leader_end))
        if s is None or not t.text:
            continue
        prims.text(dc, (s.x, s.y), t.text, TEXT_SIZE, black, bg=(1.0, 1.0, 1.0, 0.9), align='CENTER')


def last_drawn():
    return dict(_last)


def register():
    handlers.add_layer("guides", 'POST_VIEW', handlers.POST_VIEW["GUIDES"], draw_guides)
    handlers.add_layer("annot", 'POST_VIEW', handlers.POST_VIEW["ANNOT_3D"], draw_annot_3d)
    handlers.add_layer("annot2d", 'POST_PIXEL', handlers.POST_PIXEL["ANNOT_2D"], draw_annot_2d)


def unregister():
    for name in ("guides", "annot", "annot2d"):
        handlers.remove_layer(name)
