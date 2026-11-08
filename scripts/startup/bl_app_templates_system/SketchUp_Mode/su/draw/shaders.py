# SPDX-License-Identifier: GPL-2.0-or-later
"""GPU shaders and small GPU-state helpers (owner: D).

* `builtin(name)` — cached `gpu.shader.from_builtin`.
* `stipple()` — selected-face dot pattern (SketchUp shows selected faces as a blue dot screen):
  fragment kept only on a staggered grid of `spacing` physical px, dots `dot_px` px wide. Works on Metal
  (GLSL is cross-compiled by Blender). Returns None if the shader cannot be built (callers fall back to
  a translucent fill).
* `depth_offset_projection(rv3d)` — the spike's GPU_polygon_offset equivalent: a copy of the window
  matrix that pulls lines 0.25 % towards the camera so edges on faces never z-fight.
* `pixel_space(region)` — context manager: draw in region pixel coordinates from a POST_VIEW callback.
"""

from contextlib import contextmanager

import gpu
from mathutils import Matrix

ORDER = 205

_builtin = {}
_stipple = {}

STIPPLE_VERT = """
void main()
{
  gl_Position = ModelViewProjectionMatrix * vec4(pos, 1.0);
}
"""
STIPPLE_FRAG = """
void main()
{
  ivec2 p = ivec2(gl_FragCoord.xy);
  int row = p.y / spacing;
  int ox = (row - (row / 2) * 2) * (spacing / 2);
  int x = p.x + ox;
  if ((x - (x / spacing) * spacing) >= dot_px || (p.y - row * spacing) >= dot_px) {
    discard;
  }
  FragColor = color;
}
"""


def builtin(name):
    sh = _builtin.get(name)
    if sh is None:
        sh = _builtin[name] = gpu.shader.from_builtin(name)
    return sh


def stipple():
    if "sh" in _stipple:
        return _stipple["sh"]
    sh = None
    try:
        info = gpu.types.GPUShaderCreateInfo()
        info.push_constant('MAT4', "ModelViewProjectionMatrix")
        info.push_constant('VEC4', "color")
        info.push_constant('INT', "spacing")
        info.push_constant('INT', "dot_px")
        info.vertex_in(0, 'VEC3', "pos")
        info.fragment_out(0, 'VEC4', "FragColor")
        info.vertex_source(STIPPLE_VERT)
        info.fragment_source(STIPPLE_FRAG)
        sh = gpu.shader.create_from_info(info)
    except Exception:
        from .. import perf
        perf.exception("shaders: stipple shader (fallback = translucent fill)")
        sh = None
    _stipple["sh"] = sh
    return sh


def mvp():
    return gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()


def depth_offset_projection(rv3d, strength=1.0):
    win = rv3d.window_matrix.copy()
    if rv3d.is_perspective:
        win[2][3] -= win[2][3] * -0.0025 * strength
    else:
        win[2][3] -= 0.00001 * rv3d.view_distance * strength
    return win


@contextmanager
def offset_projection(rv3d, strength=1.0):
    """POST_VIEW: projection pulled towards the camera (lines over faces)."""
    with gpu.matrix.push_pop_projection():
        gpu.matrix.load_projection_matrix(depth_offset_projection(rv3d, strength))
        yield


def ortho(w, h):
    return Matrix(((2.0 / w, 0.0, 0.0, -1.0),
                   (0.0, 2.0 / h, 0.0, -1.0),
                   (0.0, 0.0, -1.0, 0.0),
                   (0.0, 0.0, 0.0, 1.0)))


@contextmanager
def pixel_space(region):
    """Draw in region pixel coordinates (origin bottom-left) from any callback, no depth test."""
    with gpu.matrix.push_pop(), gpu.matrix.push_pop_projection():
        gpu.matrix.load_identity()
        gpu.matrix.load_projection_matrix(ortho(max(1, region.width), max(1, region.height)))
        gpu.state.depth_test_set('NONE')
        yield


def reset_state():
    gpu.state.depth_test_set('NONE')
    gpu.state.depth_mask_set(False)
    gpu.state.blend_set('NONE')
