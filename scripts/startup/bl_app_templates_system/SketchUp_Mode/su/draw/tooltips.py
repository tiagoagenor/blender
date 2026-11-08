# SPDX-License-Identifier: GPL-2.0-or-later
"""Inference ScreenTips (owner: C). PLANO.md §2.4: used by inference_draw; `prims.tooltip` (D) is the
primitive when it exists, otherwise a local fallback with the same look (RESEARCH_SKETCHUP §5:
black text on #FFFFDC with a 1 px black border, to the lower right of the cursor).

    lines_for(inf) -> [str]        1st line = inference name, 2nd = "no grupo"/"no componente"
    draw(dc, xy, lines)            xy = cursor / snapped point (region px)
"""

import sys

import blf
import gpu
from gpu_extras.batch import batch_for_shader

from .. import colors, i18n

ORDER = 255

FONT_PX = 12            # logical px
PAD_PX = 3
OFFSET_PX = (14, 16)    # from the point: right, down


def lines_for(inf):
    if inf is None or not inf.tooltip_key:
        return []
    out = [i18n.t(inf.tooltip_key)]
    if inf.in_context == 'GROUP':
        out.append(i18n.t("inf.in_group"))
    elif inf.in_context == 'COMPONENT':
        out.append(i18n.t("inf.in_component"))
    return out


def _ui(v):
    import bpy
    return v * bpy.context.preferences.system.ui_scale


def _prims():
    pkg = __name__.rpartition(".")[0]
    return sys.modules.get(pkg + ".prims")


def _rect(x0, y0, x1, y1, rgba):
    sh = gpu.shader.from_builtin('UNIFORM_COLOR')
    b = batch_for_shader(sh, 'TRIS', {"pos": ((x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0))}, indices=((0, 1, 2), (0, 2, 3)))
    sh.uniform_float("color", rgba)
    b.draw(sh)


def box_size(lines):
    """(width, height, line_height) of the tooltip box in region px."""
    fid = 0
    size = _ui(FONT_PX)
    blf.size(fid, size)
    pad = _ui(PAD_PX)
    lh = size * 1.3
    w = max(blf.dimensions(fid, s)[0] for s in lines) + 2 * pad
    return w, lh * len(lines) + 2 * pad, lh


def draw(dc, xy, lines):
    if not lines:
        return
    pr = _prims()
    if pr is not None and hasattr(pr, "tooltip"):
        pr.tooltip(dc, xy, lines)
        return
    _draw_fallback(dc, xy, lines)


def _draw_fallback(dc, xy, lines):
    fid = 0
    w, h, lh = box_size(lines)
    pad = _ui(PAD_PX)
    x0 = xy[0] + _ui(OFFSET_PX[0])
    y1 = xy[1] - _ui(OFFSET_PX[1])
    region = dc.region
    if region is not None:
        x0 = min(x0, region.width - w - 2)
        y1 = max(y1, h + 2)
    x0, y1 = round(x0), round(y1)
    x1, y0 = x0 + round(w), y1 - round(h)
    bw = max(1, round(_ui(1)))
    gpu.state.blend_set('ALPHA')
    _rect(x0 - bw, y0 - bw, x1 + bw, y1 + bw, colors.rgba(colors.TOOLTIP_BORDER))
    _rect(x0, y0, x1, y1, colors.rgba(colors.TOOLTIP_BG))
    blf.size(fid, _ui(FONT_PX))
    blf.color(fid, *colors.rgba(colors.TOOLTIP_TEXT))
    for i, s in enumerate(lines):
        blf.position(fid, x0 + pad, y1 - pad - lh * (i + 1) + lh * 0.25, 0)
        blf.draw(fid, s)
    gpu.state.blend_set('NONE')
