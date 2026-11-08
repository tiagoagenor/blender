# SPDX-License-Identifier: GPL-2.0-or-later
"""Sky and ground (owner: D, layer SKY=0). Ported from visual_spike `draw_sky`. PLANO.md §3.3.

Full-viewport quad at NDC z = 0.9999999 (behind everything, depth test LESS_EQUAL, no depth write).
The horizon is the vanishing line of the horizontal view direction; sky = linear gradient from
HORIZON (#BFE5F5) at the horizon to SKY (#1EA6DD) at the top edge; ground = BACKGROUND (#BFBFC6).
"""

import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Vector

from .. import colors
from . import handlers, shaders

ORDER = 220
Z = 0.9999999
_cache = {"key": None, "batch": None}
_enabled = [True]


def horizon_ndc_y(rv3d):
    fwd = -(rv3d.view_matrix.inverted().col[2].xyz)
    if rv3d.is_perspective:
        h = Vector((fwd.x, fwd.y, 0.0))
        if h.length > 1e-6:
            c = rv3d.window_matrix @ rv3d.view_matrix @ Vector((h.x, h.y, 0.0, 0.0))
            if abs(c.w) > 1e-9:
                return c.y / c.w
    return -1.0 if fwd.z > 0 else (1.0 if fwd.z < -0.999 else 0.0)


def set_enabled(on):
    _enabled[0] = bool(on)


def draw(dc):
    rv3d = dc.rv3d
    if rv3d is None or not _enabled[0]:
        return
    sh = shaders.builtin('SMOOTH_COLOR')
    y = max(-1.0, min(1.0, horizon_ndc_y(rv3d)))
    key = round(y, 5)
    if _cache["key"] != key:
        top, hor, gnd = colors.rgba(colors.SKY), colors.rgba(colors.HORIZON), colors.rgba(colors.BACKGROUND)
        pos = [(-1, y, Z), (1, y, Z), (1, 1, Z), (-1, 1, Z),
               (-1, -1, Z), (1, -1, Z), (1, y, Z), (-1, y, Z)]
        col = [hor, hor, top, top, gnd, gnd, gnd, gnd]
        _cache["batch"] = batch_for_shader(sh, 'TRIS', {"pos": pos, "color": col},
                                           indices=[(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)])
        _cache["key"] = key
    with gpu.matrix.push_pop(), gpu.matrix.push_pop_projection():
        gpu.matrix.load_identity()
        gpu.matrix.load_projection_matrix(Matrix.Identity(4))
        gpu.state.depth_test_set('LESS_EQUAL')
        gpu.state.depth_mask_set(False)
        _cache["batch"].draw(sh)
        gpu.state.depth_test_set('NONE')


def register():
    handlers.add_layer("sky", 'POST_VIEW', handlers.POST_VIEW["SKY"], draw)


def unregister():
    handlers.remove_layer("sky")
    _cache.update(key=None, batch=None)
