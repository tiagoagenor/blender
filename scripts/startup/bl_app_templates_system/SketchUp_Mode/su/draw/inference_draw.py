# SPDX-License-Identifier: GPL-2.0-or-later
"""Inference feedback (owner: C). PLANO.md §3.2, RESEARCH_SKETCHUP §5 (colours/shapes of the markers).

Draws `STATE.inference` (set by the tool dispatcher / hover) in region pixels, on top of everything:
  * linear indicator from `ref_point` to `point`: axis colour (red/green/blue), magenta for
    parallel / perpendicular / perpendicular-to-face (+ the reference edge in magenta), dotted in the
    axis colour for "Do ponto"; dotted when inferred, solid and thick when locked (Shift / arrow);
  * point marker at the snapped point: Ponto de extremidade = green circle, Ponto central = cyan circle,
    Em aresta = red square, Em face = blue diamond, Interseção = red ×, Centro = blue circle,
    Ponto de orientação = slate circle, Na linha = red square, Ponto de origem = dark circle;
    magenta-purple for geometry in a group/component (Inference.in_context);
  * the ScreenTip (draw/tooltips.py) with the 2nd line "no grupo"/"no componente".
Layers: POST_PIXEL "inference_marker" (order 25, between TOOL_2D and TOOLTIP) and
"inference_tooltip" (TOOLTIP = 30).
"""

import math

import bpy
import gpu
from gpu_extras.batch import batch_for_shader

from .. import colors
from ..core.state import STATE
from . import handlers, tooltips

ORDER = 260

MARKER_ORDER = 25
MARKER_PX = 9            # logical diameter
DOT_STEP_PX = 4.0        # dotted lines: one dot every 4 logical px
LINE_PX = 1.5
LOCKED_LINE_PX = 3.0

MARKERS = {   # kind -> (shape, colour)
    "ENDPOINT": ('CIRCLE', colors.INF_ENDPOINT),
    "MIDPOINT": ('CIRCLE', colors.INF_MIDPOINT),
    "ON_EDGE": ('SQUARE', colors.INF_ON_EDGE),
    "ON_FACE": ('DIAMOND', colors.INF_ON_FACE),
    "INTERSECTION": ('CROSS', colors.INF_INTERSECTION),
    "CENTER": ('CIRCLE', colors.INF_CENTER),
    "GUIDE_POINT": ('CIRCLE', colors.INF_GUIDE_POINT),
    "ON_GUIDE": ('SQUARE', colors.INF_ON_GUIDE),
    "ORIGIN": ('CIRCLE', colors.INF_ORIGIN),
}
LINEAR_COLORS = {
    "AXIS_X": colors.AXIS_X, "AXIS_Y": colors.AXIS_Y, "AXIS_Z": colors.AXIS_Z,
    "PARALLEL": colors.INF_PARALLEL, "PERPENDICULAR": colors.INF_PARALLEL, "PERP_FACE": colors.INF_PARALLEL,
    "TANGENT": colors.INF_TANGENT,
}
# brighter variants for the indicator lines (the axis colours of the viewport are darker, 178)
LINE_BRIGHT = {"AXIS_X": (255, 0, 0), "AXIS_Y": (0, 200, 0), "AXIS_Z": (0, 0, 255)}


def _ui(v):
    return v * bpy.context.preferences.system.ui_scale


def _project(dc, co):
    from bpy_extras import view3d_utils
    if co is None or dc.region is None or dc.rv3d is None:
        return None
    return view3d_utils.location_3d_to_region_2d(dc.region, dc.rv3d, co)


# ---------------------------------------------------------------------------------------------- 2D primitives
def _tris(pts, idx, rgba):
    sh = gpu.shader.from_builtin('UNIFORM_COLOR')
    b = batch_for_shader(sh, 'TRIS', {"pos": [(x, y, 0.0) for x, y in pts]}, indices=idx)
    sh.uniform_float("color", rgba)
    b.draw(sh)


def _polygon(pts, rgba):
    n = len(pts)
    _tris(pts, [(0, i, i + 1) for i in range(1, n - 1)], rgba)


def _segment(a, b, width, rgba):
    sh = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
    bt = batch_for_shader(sh, 'LINES', {"pos": [(a[0], a[1], 0.0), (b[0], b[1], 0.0)]})
    sh.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
    sh.uniform_float("lineWidth", width)
    sh.uniform_float("color", rgba)
    bt.draw(sh)


def _dots(a, b, step, size, rgba):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    n = int(length / step)
    if n < 1:
        return
    pts = [(a[0] + dx * i / n, a[1] + dy * i / n, 0.0) for i in range(n + 1)]
    sh = gpu.shader.from_builtin('POINT_UNIFORM_COLOR')
    bt = batch_for_shader(sh, 'POINTS', {"pos": pts})
    gpu.state.point_size_set(size)
    sh.uniform_float("color", rgba)
    bt.draw(sh)


def _circle_pts(c, r, n=16):
    return [(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def marker(xy, shape, rgb, size_px):
    """Filled marker with a 1 px darker outline, centred at region px `xy`."""
    r = size_px * 0.5
    edge = tuple(int(c * 0.55) for c in rgb)
    o = max(1.0, _ui(1.0))
    if shape == 'CIRCLE':
        _polygon(_circle_pts(xy, r + o), colors.rgba(edge))
        _polygon(_circle_pts(xy, r), colors.rgba(rgb))
    elif shape == 'SQUARE':
        for rr, c in ((r + o, edge), (r, rgb)):
            _polygon([(xy[0] - rr, xy[1] - rr), (xy[0] + rr, xy[1] - rr), (xy[0] + rr, xy[1] + rr),
                      (xy[0] - rr, xy[1] + rr)], colors.rgba(c))
    elif shape == 'DIAMOND':
        for rr, c in ((r * 1.25 + o * 1.4, edge), (r * 1.25, rgb)):
            _polygon([(xy[0], xy[1] - rr), (xy[0] + rr, xy[1]), (xy[0], xy[1] + rr), (xy[0] - rr, xy[1])],
                     colors.rgba(c))
    elif shape == 'CROSS':
        w = _ui(2.0)
        _segment((xy[0] - r, xy[1] - r), (xy[0] + r, xy[1] + r), w, colors.rgba(rgb))
        _segment((xy[0] - r, xy[1] + r), (xy[0] + r, xy[1] - r), w, colors.rgba(rgb))


# ---------------------------------------------------------------------------------------------- layers
def _ref_edge_world(inf):
    if inf.ref_edge is None:
        return None
    from ..core import spatial
    key, idx = inf.ref_edge
    for k, obj in spatial.documents():
        if k == key:
            me = obj.data
            if 0 <= idx < len(me.edges):
                v = me.edges[idx].vertices
                mw = obj.matrix_world
                return mw @ me.vertices[v[0]].co, mw @ me.vertices[v[1]].co
    return None


def _linear_rgb(inf):
    if inf.linear == "FROM_POINT":
        from ..core.inference import axis_of
        ax = axis_of(inf.direction)
        return LINE_BRIGHT.get(ax, colors.INF_FROM_POINT)
    return LINE_BRIGHT.get(inf.linear) or LINEAR_COLORS.get(inf.linear, colors.INF_FROM_POINT)


def draw_linear(dc, inf):
    if not inf.linear or inf.ref_point is None:
        return
    a, b = _project(dc, inf.ref_point), _project(dc, inf.point)
    if a is None or b is None:
        return
    rgba = colors.rgba(_linear_rgb(inf))
    if inf.linear in ("PARALLEL", "PERPENDICULAR"):
        e = _ref_edge_world(inf)
        if e is not None:
            ea, eb = _project(dc, e[0]), _project(dc, e[1])
            if ea is not None and eb is not None:
                _segment(ea, eb, _ui(2.0), rgba)
    if inf.locked:
        _segment(a, b, _ui(LOCKED_LINE_PX), rgba)
    else:
        _dots(a, b, _ui(DOT_STEP_PX), max(1.0, _ui(LINE_PX)), rgba)


def draw_marker(dc, inf):
    spec = MARKERS.get(inf.kind)
    if spec is None:
        return
    shape, rgb = spec
    if inf.in_context:
        rgb = colors.INF_IN_CONTEXT
    xy = _project(dc, inf.point) or inf.screen
    marker(xy, shape, rgb, _ui(MARKER_PX))


_drawn = {"marker": None, "tooltip": None}     # last inference drawn by each layer (tests)


def last_drawn():
    return dict(_drawn)


def _layer_marker(dc):
    inf = STATE.inference
    _drawn["marker"] = inf
    if inf is None or inf.kind == "NONE":
        return
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('NONE')
    draw_linear(dc, inf)
    draw_marker(dc, inf)
    gpu.state.blend_set('NONE')


def _layer_tooltip(dc):
    inf = STATE.inference
    if inf is None or inf.kind == "NONE":
        return
    lines = tooltips.lines_for(inf)
    _drawn["tooltip"] = lines
    if lines:
        xy = _project(dc, inf.point) or inf.screen
        tooltips.draw(dc, xy, lines)


def register():
    handlers.add_layer("inference_marker", 'POST_PIXEL', MARKER_ORDER, _layer_marker)
    handlers.add_layer("inference_tooltip", 'POST_PIXEL', handlers.POST_PIXEL["TOOLTIP"], _layer_tooltip)


def unregister():
    handlers.remove_layer("inference_marker")
    handlers.remove_layer("inference_tooltip")
