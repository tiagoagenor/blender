# SPDX-License-Identifier: GPL-2.0-or-later
"""Guides, dimensions and texts in the viewport (owner: G). PLANO.md §2.2, §3.3, §6.3.

Layers (draw/handlers.py):
  guides   POST_VIEW  GUIDES=40    infinite dashed guide lines (clipped to the view frustum) and
                                   guide points (small cross), hidden with Visualizar ▸ Guias
  annot    POST_VIEW  ANNOT_3D=45  dimension lines, extension lines, slash ends; text leaders
  annot2d  POST_PIXEL ANNOT_2D=10  dimension and leader texts in screen space (always legible, AC-DIM-3)
           + the vertical-FOV keeper (core.camera.check_fov) — Blender's lens fits the width, so the
             35° vertical FOV must be re-fitted when the region aspect changes (AC-NAV-7).
"""

import bpy
from mathutils import Vector

from .. import colors, registry
from ..core import camera, guides, viewutil
from . import handlers, prims

ORDER = 240

DASH_PX, GAP_PX = 6, 4
EXT_OVERSHOOT_PX = 6          # extension lines pass the dimension line by this much
SLASH_PX = 6
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


def dimension_geometry(dc, a, b, off):
    """3D segments of a linear dimension: extension lines, dimension line and slash ends."""
    a, b, off = Vector(a), Vector(b), Vector(off)
    A, B = a + off, b + off
    segs = [(A, B)]
    if off.length > 1e-9:
        n = off.normalized()
        for p, P in ((a, A), (b, B)):
            segs.append((p, P + n * _px_world(dc, P, EXT_OVERSHOOT_PX)))
    else:
        n = None
    ab = B - A
    if ab.length > 1e-9:
        t = ab.normalized()
        side = n if n is not None else t.orthogonal().normalized()
        s = (t + side).normalized()
        for P in (A, B):
            h = _px_world(dc, P, SLASH_PX) * 0.5
            segs.append((P - s * h, P + s * h))
    return segs


def draw_annot_3d(dc):
    d = guides.data()
    if d is None:
        return
    black = colors.rgba(colors.EDGE, 1.0)
    segs = []
    for dm in d.dims:
        segs += dimension_geometry(dc, dm.a, dm.b, dm.offset)
    if segs:
        prims.lines(dc, segs, black, 1.0, depth=True)
    lead = [(Vector(t.anchor), Vector(t.leader_end)) for t in d.texts
            if (Vector(t.leader_end) - Vector(t.anchor)).length > 1e-9]
    if lead:
        prims.lines(dc, lead, black, 1.0, depth=False)
        prims.points(dc, [a for a, _b in lead], black, 4, 'CIRCLE', outline=False)
    _last["dims"] = len(d.dims)
    _last["texts"] = len(d.texts)


def draw_annot_2d(dc):
    camera.check_fov(dc)
    d = guides.data()
    if d is None:
        return
    black = colors.rgba(colors.EDGE, 1.0)
    for i, dm in enumerate(d.dims):
        mid = (Vector(dm.a) + Vector(dm.b)) * 0.5 + Vector(dm.offset)
        s = viewutil.project(dc.region, dc.rv3d, mid)
        if s is None:
            continue
        prims.text(dc, (s.x, s.y + viewutil.ui_px(3)), guides.dimension_text(i), TEXT_SIZE, black,
                   bg=(1.0, 1.0, 1.0, 0.75), align='CENTER')
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
