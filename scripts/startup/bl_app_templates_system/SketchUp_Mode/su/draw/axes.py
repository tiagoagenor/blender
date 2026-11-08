# SPDX-License-Identifier: GPL-2.0-or-later
"""Drawing axes (owner: D, layer AXES=10). Ported from visual_spike `draw_axes`. PLANO.md §3.3.

Positive halves: solid 1 pt lines (2 km). Negative halves: dots with an even SCREEN spacing of 4.5 pt —
the half-axis is sampled in front of the camera, projected, stepped in 2D and lifted back to 3D by
intersecting the view ray with the axis, so the dots keep the depth test (hidden behind faces).
Cached per perspective matrix and region size. Visibility follows `style` ("Eixos").
"""

import gpu
from bpy_extras.view3d_utils import location_3d_to_region_2d, region_2d_to_origin_3d, region_2d_to_vector_3d
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from mathutils.geometry import intersect_line_line

from .. import colors
from . import handlers, shaders

ORDER = 221
LENGTH = 2000.0
DOT_STEP_PT = 4.5
AXES = ((Vector((1, 0, 0)), colors.AXIS_X), (Vector((0, 1, 0)), colors.AXIS_Y), (Vector((0, 0, 1)), colors.AXIS_Z))
_cache = {"key": None, "neg": None, "pos": None}
_enabled = [True]


def set_enabled(on):
    _enabled[0] = bool(on)


def is_enabled():
    return _enabled[0]


def _neg_axis_dots(region, rv3d, d, step):
    vm = rv3d.view_matrix
    pts2 = []
    for i in range(400):
        t = 0.0 if i == 0 else 0.01 * (1.06 ** i)
        if t > 5e4:
            break
        p = -d * t
        if rv3d.is_perspective and (vm @ p).z > -0.05:      # behind / too close to the camera
            continue
        q = location_3d_to_region_2d(region, rv3d, p)
        if q is not None:
            pts2.append(q)
    if len(pts2) < 2:
        return []
    a, b = pts2[0], pts2[-1]
    n = int((b - a).length / step)
    out = []
    W, H = region.width, region.height
    for k in range(n + 1):
        s = a.lerp(b, k / max(1, n))
        if s.x < -2 or s.y < -2 or s.x > W + 2 or s.y > H + 2:
            continue
        o = region_2d_to_origin_3d(region, rv3d, s)
        v = region_2d_to_vector_3d(region, rv3d, s)
        r = intersect_line_line(o, o + v, Vector((0, 0, 0)), -d)
        if r:
            out.append(tuple(r[1]))
    return out


def draw(dc):
    rv3d, region = dc.rv3d, dc.region
    if rv3d is None or not _enabled[0]:
        return
    import bpy
    ps = bpy.context.preferences.system.pixel_size
    key = (tuple(round(x, 5) for row in rv3d.perspective_matrix for x in row), region.width, region.height)
    if _cache["key"] != key:
        step = DOT_STEP_PT * ps
        _cache["neg"] = [(_neg_axis_dots(region, rv3d, d, step), col) for d, col in AXES]
        _cache["key"] = key
    line = shaders.builtin('POLYLINE_UNIFORM_COLOR')
    pt = shaders.builtin('POINT_UNIFORM_COLOR')
    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.depth_mask_set(False)
    gpu.state.blend_set('ALPHA')
    line.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
    line.uniform_float("lineWidth", 1.0 * ps)
    for d, col in AXES:
        b = batch_for_shader(line, 'LINES', {"pos": [(0, 0, 0), tuple(d * LENGTH)]})
        line.uniform_float("color", colors.rgba(col))
        b.draw(line)
    gpu.state.point_size_set(1.0 * ps + 0.5)
    for pts, col in _cache["neg"]:
        if not pts:
            continue
        b = batch_for_shader(pt, 'POINTS', {"pos": pts})
        pt.uniform_float("color", colors.rgba(col))
        b.draw(pt)
    gpu.state.point_size_set(1.0)
    gpu.state.depth_test_set('NONE')
    gpu.state.blend_set('NONE')


def register():
    handlers.add_layer("axes", 'POST_VIEW', handlers.POST_VIEW["AXES"], draw)


def unregister():
    handlers.remove_layer("axes")
    _cache.update(key=None, neg=None)
