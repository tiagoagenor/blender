# SPDX-License-Identifier: GPL-2.0-or-later
"""Drawing primitives for tools, inference, guides and selection (owner: D). Contract PLANO.md §2.4
(frozen at M-A). Every function takes the `DrawContext` given to draw layers (`draw/handlers.py`).

Coordinates follow the layer phase:
  * POST_VIEW  → 3D world points (Vector or 3-tuples);
  * POST_PIXEL → 2D region points in PHYSICAL px (`(x, y)`; a 3D point is projected).
Widths/sizes are LOGICAL px (`viewutil.line_px` / `ui_px` convert). `depth=True` = depth-tested with a
small offset towards the camera (lines on faces never z-fight); markers, text, tooltips and grips are
always drawn on top in pixel space. `rgba` = sRGB 0–1 (`colors.rgba(c)`), written 1:1 (view transform
Standard).

    line(dc, a, b, rgba, width=1.0, *, depth=True)       lines(dc, segs, rgba, width=1.0, *, depth=True)
    dashed(dc, a, b, rgba, width=1.0, dash_px=6, gap_px=4)
    dashed_many(dc, segs, rgba, width=1.0, dash_px=6, gap_px=4, *, depth=True)
    dotted(dc, a, b, rgba)                               points(dc, pts, rgba, size_px, shape='CIRCLE')
    polygon(dc, pts, rgba, *, stipple=False)             text(dc, xy, s, size=11, rgba=(0,0,0,1), bg=None, align='LEFT')
    tooltip(dc, xy, lines)                               protractor(dc, center, normal, ref_dir, axis_color)
    box(dc, mn, mx, matrix, rgba, *, dashed=False)       grips(dc, pts, rgba, size_px)
"""

import math

import blf
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Vector
from mathutils.geometry import tessellate_polygon

from .. import colors
from ..core import viewutil
from . import shaders

ORDER = 210

SHAPES = ('CIRCLE', 'SQUARE', 'DIAMOND', 'CROSS')
DOTTED_STEP_PX = 4.5          # logical px between dots (same as the negative axes)
TOOLTIP_OFFSET_PX = (14, -26)  # logical px from the cursor
TOOLTIP_PAD_PX = 4
FONT_ID = 0


# ------------------------------------------------------------------------------------------- helpers
def _is_pixel(dc):
    return getattr(dc, "phase", "POST_VIEW") == 'POST_PIXEL'


def _v3(p):
    if len(p) == 2:
        return Vector((p[0], p[1], 0.0))
    return Vector((p[0], p[1], p[2]))


def _to_screen(dc, p):
    """Region px Vector((x, y)) of a 2D/3D point (None when behind the camera)."""
    if len(p) == 2:
        return Vector((p[0], p[1]))
    return viewutil.project(dc.region, dc.rv3d, Vector(p))


def _lw(width):
    return max(1.0, viewutil.line_px(width))


def _polyline(coords, rgba, width, prim='LINES'):
    sh = shaders.builtin('POLYLINE_UNIFORM_COLOR')
    sh.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
    sh.uniform_float("lineWidth", _lw(width))
    try:
        sh.uniform_bool("lineSmooth", True)      # the shader is shared with draw/edges (crisp on 1×)
    except Exception:
        pass
    sh.uniform_float("color", tuple(rgba))
    batch_for_shader(sh, prim, {"pos": coords}).draw(sh)


def _draw_lines(dc, coords, rgba, width, depth):
    if not coords:
        return
    gpu.state.blend_set('ALPHA')
    if _is_pixel(dc):
        _polyline([_v3(c) for c in coords], rgba, width)
    elif depth:
        gpu.state.depth_test_set(depth if isinstance(depth, str) else 'LESS_EQUAL')
        gpu.state.depth_mask_set(False)
        with shaders.offset_projection(dc.rv3d):
            _polyline([_v3(c) for c in coords], rgba, width)
        gpu.state.depth_test_set('NONE')
    else:
        gpu.state.depth_test_set('NONE')
        _polyline([_v3(c) for c in coords], rgba, width)
    gpu.state.blend_set('NONE')


def _clip_w(dc, a, b, eps=1e-4):
    """Clip segment a-b (world) to the part in front of the camera. Returns (a, b, wa, wb) or None."""
    pm = dc.rv3d.perspective_matrix
    wa = (pm @ a.to_4d()).w
    wb = (pm @ b.to_4d()).w
    if not dc.rv3d.is_perspective:
        return a, b, 1.0, 1.0
    near = max(eps, dc.space.clip_start * 0.5 if dc.space else eps)
    if wa < near and wb < near:
        return None
    if wa < near:
        t = (near - wa) / (wb - wa)
        a, wa = a.lerp(b, t), near
    elif wb < near:
        t = (near - wb) / (wa - wb)
        b, wb = b.lerp(a, t), near
    return a, b, wa, wb


def _screen_params(dc, a, b, step_px):
    """For a 3D segment: (a, b, wa, wb, screen length, n steps) or None."""
    c = _clip_w(dc, _v3(a), _v3(b))
    if c is None:
        return None
    a, b, wa, wb = c
    sa, sb = _to_screen(dc, a), _to_screen(dc, b)
    if sa is None or sb is None:
        return None
    L = (sb - sa).length
    return a, b, wa, wb, L


def _lift(a, b, wa, wb, s):
    """Perspective-correct 3D point at screen-space fraction s of segment a-b."""
    den = (1.0 - s) * wb + s * wa
    t = s * wa / den if abs(den) > 1e-12 else s
    return a.lerp(b, t)


# ------------------------------------------------------------------------------------------- lines
def line(dc, a, b, rgba, width=1.0, *, depth=True):
    _draw_lines(dc, [a, b], rgba, width, depth)


def lines(dc, segs, rgba, width=1.0, *, depth=True):
    """`segs` = iterable of (a, b) pairs, or a flat list of points taken two by two."""
    coords = []
    for s in segs:
        if len(s) == 2 and hasattr(s[0], "__len__"):
            coords.extend(s)
        else:
            coords.append(s)
    _draw_lines(dc, coords, rgba, width, depth)


def _dash_coords(dc, a, b, dash, gap):
    if _is_pixel(dc):
        sa, sb = Vector(a[:2]), Vector(b[:2])
        L = (sb - sa).length
        coords, d = [], 0.0
        while d < L:
            coords += [sa.lerp(sb, d / L), sa.lerp(sb, min(L, d + dash) / L)]
            d += dash + gap
        return coords
    p = _screen_params(dc, a, b, dash + gap)
    if p is None:
        return []
    a, b, wa, wb, L = p
    if L < 1e-6:
        return []
    coords, d = [], 0.0
    while d < L and len(coords) < 20000:
        coords += [_lift(a, b, wa, wb, d / L), _lift(a, b, wa, wb, min(L, d + dash) / L)]
        d += dash + gap
    return coords


def dashed(dc, a, b, rgba, width=1.0, dash_px=6, gap_px=4):
    """Dashes of constant SCREEN length (perspective-correct, depth-tested)."""
    dash, gap = viewutil.ui_px(dash_px), viewutil.ui_px(gap_px)
    _draw_lines(dc, _dash_coords(dc, a, b, dash, gap), rgba, width, not _is_pixel(dc))


def dashed_many(dc, segs, rgba, width=1.0, dash_px=6, gap_px=4, *, depth=True):
    """Many dashed segments in one batch. `depth` = True / False / a depth test name ('GREATER' = only
    the parts hidden behind faces, used for back edges)."""
    dash, gap = viewutil.ui_px(dash_px), viewutil.ui_px(gap_px)
    coords = []
    for a, b in segs:
        coords += _dash_coords(dc, a, b, dash, gap)
    _draw_lines(dc, coords, rgba, width, depth if not _is_pixel(dc) else False)


def _dot_points(dc, a, b, step):
    if _is_pixel(dc):
        sa, sb = Vector(a[:2]), Vector(b[:2])
        n = int((sb - sa).length / step)
        return [_v3(sa.lerp(sb, k / max(1, n))) for k in range(n + 1)]
    p = _screen_params(dc, a, b, step)
    if p is None:
        return []
    a, b, wa, wb, L = p
    n = min(20000, int(L / step))
    return [_lift(a, b, wa, wb, k / max(1, n)) for k in range(n + 1)]


def dotted(dc, a, b, rgba):
    """Evenly spaced round dots (1 pt) along a-b, depth-tested in POST_VIEW."""
    pts = _dot_points(dc, a, b, DOTTED_STEP_PX * bpy.context.preferences.system.pixel_size)
    if not pts:
        return
    sh = shaders.builtin('POINT_UNIFORM_COLOR')
    gpu.state.blend_set('ALPHA')
    gpu.state.point_size_set(_lw(1.0) + 0.5)
    sh.uniform_float("color", tuple(rgba))
    if _is_pixel(dc):
        batch_for_shader(sh, 'POINTS', {"pos": pts}).draw(sh)
    else:
        gpu.state.depth_test_set('LESS_EQUAL')
        with shaders.offset_projection(dc.rv3d):
            batch_for_shader(sh, 'POINTS', {"pos": [tuple(p) for p in pts]}).draw(sh)
        gpu.state.depth_test_set('NONE')
    gpu.state.point_size_set(1.0)
    gpu.state.blend_set('NONE')


# ------------------------------------------------------------------------------------------- 2D shapes
def _shape_tris(shape, c, r):
    x, y = c
    if shape == 'SQUARE':
        q = [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r)]
        return [q[0], q[1], q[2], q[0], q[2], q[3]], q
    if shape == 'DIAMOND':
        q = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
        return [q[0], q[1], q[2], q[0], q[2], q[3]], q
    n = 16
    ring = [(x + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    tris = []
    for i in range(n):
        tris += [(x, y), ring[i], ring[(i + 1) % n]]
    return tris, ring


def _darker(rgba, k=0.55):
    return (rgba[0] * k, rgba[1] * k, rgba[2] * k, rgba[3])


def points(dc, pts, rgba, size_px, shape='CIRCLE', *, outline=True):
    """Markers of `size_px` logical px, always on top. CROSS = two strokes (no fill)."""
    scr = [s for s in (_to_screen(dc, p) for p in pts) if s is not None]
    if not scr:
        return
    r = viewutil.ui_px(size_px) * 0.5
    fill, outl, cross = [], [], []
    for s in scr:
        if shape == 'CROSS':
            cross += [(s.x - r, s.y - r), (s.x + r, s.y + r), (s.x - r, s.y + r), (s.x + r, s.y - r)]
            continue
        tris, ring = _shape_tris(shape, s, r)
        fill += tris
        for i in range(len(ring)):
            outl += [ring[i], ring[(i + 1) % len(ring)]]
    with shaders.pixel_space(dc.region):
        gpu.state.blend_set('ALPHA')
        if fill:
            sh = shaders.builtin('UNIFORM_COLOR')
            sh.uniform_float("color", tuple(rgba))
            batch_for_shader(sh, 'TRIS', {"pos": fill}).draw(sh)
        if outl and outline:
            _polyline([_v3(p) for p in outl], _darker(rgba), 1.0)
        if cross:
            _polyline([_v3(p) for p in cross], rgba, 2.0)
        gpu.state.blend_set('NONE')


def polygon(dc, pts, rgba, *, stipple=False):
    """Filled polygon (concave OK, no holes). `stipple` = SketchUp selected-face dot screen."""
    if len(pts) < 3:
        return
    P = [_v3(p) for p in pts]
    tris = tessellate_polygon([P])
    coords = [P[i] for t in tris for i in t]
    if not coords:
        return
    gpu.state.blend_set('ALPHA')
    sh = shaders.stipple() if stipple else None
    ctx = shaders.offset_projection(dc.rv3d, 0.5) if not _is_pixel(dc) else _null()
    if not _is_pixel(dc):
        gpu.state.depth_test_set('LESS_EQUAL')
        gpu.state.depth_mask_set(False)
    with ctx:
        if sh is not None:
            ps = bpy.context.preferences.system.pixel_size
            sh.bind()
            sh.uniform_float("ModelViewProjectionMatrix", shaders.mvp())
            # custom shader output is taken as linear (the built-ins convert sRGB themselves)
            lin = tuple(colors._to_linear(c) for c in rgba[:3]) + (rgba[3],)
            sh.uniform_float("color", lin)
            sh.uniform_int("spacing", int(round(3 * ps)))
            sh.uniform_int("dot_px", max(1, int(round(ps))))
            batch_for_shader(sh, 'TRIS', {"pos": coords}).draw(sh)
        else:
            u = shaders.builtin('UNIFORM_COLOR')
            c = tuple(rgba) if not stipple else (rgba[0], rgba[1], rgba[2], rgba[3] * 0.25)
            u.uniform_float("color", c)
            batch_for_shader(u, 'TRIS', {"pos": coords}).draw(u)
    gpu.state.depth_test_set('NONE')
    gpu.state.blend_set('NONE')


class _null:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


# ------------------------------------------------------------------------------------------- text
def _text_size(s, size):
    blf.size(FONT_ID, viewutil.ui_px(size))
    return blf.dimensions(FONT_ID, s)


def _rect(x0, y0, x1, y1, rgba):
    sh = shaders.builtin('UNIFORM_COLOR')
    sh.uniform_float("color", tuple(rgba))
    batch_for_shader(sh, 'TRIS', {"pos": [(x0, y0), (x1, y0), (x1, y1), (x0, y0), (x1, y1), (x0, y1)]}).draw(sh)


def _frame(x0, y0, x1, y1, rgba):
    _polyline([(x0, y0, 0), (x1, y0, 0), (x1, y0, 0), (x1, y1, 0), (x1, y1, 0), (x0, y1, 0),
               (x0, y1, 0), (x0, y0, 0)], rgba, 1.0)


def text(dc, xy, s, size=11, rgba=(0, 0, 0, 1), bg=None, align='LEFT'):
    p = _to_screen(dc, xy)
    if p is None or not s:
        return
    w, h = _text_size(s, size)
    x = p.x - (w if align == 'RIGHT' else w * 0.5 if align == 'CENTER' else 0.0)
    y = p.y
    with shaders.pixel_space(dc.region):
        gpu.state.blend_set('ALPHA')
        if bg is not None:
            pad = viewutil.ui_px(2)
            _rect(x - pad, y - pad, x + w + pad, y + h + pad, bg)
        blf.position(FONT_ID, x, y, 0)
        blf.color(FONT_ID, *rgba)
        blf.draw(FONT_ID, s)
        gpu.state.blend_set('NONE')


def tooltip(dc, xy, lines):
    """SketchUp screen tip: pale-yellow box, thin black border, black text, below-right of `xy`."""
    p = _to_screen(dc, xy)
    lines = [l for l in (lines or []) if l]
    if p is None or not lines:
        return
    size = 11
    pad = viewutil.ui_px(TOOLTIP_PAD_PX)
    dims = [_text_size(l, size) for l in lines]
    lh = max(d[1] for d in dims) if dims else 0
    lh = max(lh, viewutil.ui_px(size) * 0.8)
    gap = viewutil.ui_px(3)
    w = max(d[0] for d in dims) + 2 * pad
    h = len(lines) * lh + (len(lines) - 1) * gap + 2 * pad
    x0 = p.x + viewutil.ui_px(TOOLTIP_OFFSET_PX[0])
    y1 = p.y + viewutil.ui_px(TOOLTIP_OFFSET_PX[1]) + viewutil.ui_px(12)
    y0 = y1 - h
    reg = dc.region
    if x0 + w > reg.width:
        x0 = max(0, p.x - w - viewutil.ui_px(8))
    if y0 < 0:
        y0, y1 = p.y + viewutil.ui_px(16), p.y + viewutil.ui_px(16) + h
    with shaders.pixel_space(reg):
        gpu.state.blend_set('ALPHA')
        _rect(x0, y0, x0 + w, y1, colors.rgba(colors.TOOLTIP_BG))
        _frame(x0, y0, x0 + w, y1, colors.rgba(colors.TOOLTIP_BORDER))
        blf.size(FONT_ID, viewutil.ui_px(size))
        blf.color(FONT_ID, *colors.rgba(colors.TOOLTIP_TEXT))
        y = y1 - pad - lh
        for l in lines:
            blf.position(FONT_ID, x0 + pad, y + lh * 0.15, 0)
            blf.draw(FONT_ID, l)
            y -= lh + gap
        gpu.state.blend_set('NONE')


# ------------------------------------------------------------------------------------------- gizmos
def _basis(normal, ref_dir):
    n = Vector(normal).normalized()
    u = Vector(ref_dir) - n * Vector(ref_dir).dot(n)
    if u.length < 1e-9:
        u = n.orthogonal()
    u.normalize()
    return n, u, n.cross(u)


def protractor(dc, center, normal, ref_dir, axis_color, radius_px=48):
    """Protractor gizmo (screen-constant radius) in the plane of `normal`, 0° along `ref_dir`.
    Ticks every 15°, longer every 45°, coloured `axis_color` (rgba)."""
    c = Vector(center)
    k = viewutil.pixel_size_at(dc.region, dc.rv3d, c) if not _is_pixel(dc) else 1.0
    if k <= 0:
        return
    R = viewutil.ui_px(radius_px) * k
    n, u, v = _basis(normal, ref_dir)
    ring = []
    m = 48
    for i in range(m):
        a0, a1 = 2 * math.pi * i / m, 2 * math.pi * (i + 1) / m
        ring += [c + (u * math.cos(a0) + v * math.sin(a0)) * R, c + (u * math.cos(a1) + v * math.sin(a1)) * R]
    ticks = []
    for d in range(0, 360, 15):
        a = math.radians(d)
        e = u * math.cos(a) + v * math.sin(a)
        r0 = R * (0.78 if d % 45 == 0 else 0.88)
        ticks += [c + e * r0, c + e * R]
    _draw_lines(dc, ring + ticks, axis_color, 1.5, False)
    _draw_lines(dc, [c, c + u * R * 1.15], axis_color, 1.0, False)


def box(dc, mn, mx, matrix, rgba, *, dashed=False):
    """Oriented bounding box: 12 edges of [mn, mx] transformed by `matrix`."""
    M = matrix if matrix is not None else Matrix.Identity(4)
    x0, y0, z0 = mn
    x1, y1, z1 = mx
    c = [M @ Vector(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    E = ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7))
    if dashed:
        for i, j in E:
            globals()["dashed"](dc, c[i], c[j], rgba)
    else:
        _draw_lines(dc, [c[i] for e in E for i in e], rgba, 1.0, False)


def grips(dc, pts, rgba, size_px):
    """Handles (Scale tool): filled squares with a dark outline, on top."""
    points(dc, pts, rgba, size_px, 'SQUARE')
