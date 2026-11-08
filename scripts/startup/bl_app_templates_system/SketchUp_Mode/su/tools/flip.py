# SPDX-License-Identifier: GPL-2.0-or-later
"""Virar (owner: F, P1). PLANO.md §4.3 (LTS row 12), §6.1 "Comandos" P1.

With a selection (or the entity under the cursor), three planes through the centre of its bounding
box are shown (red = YZ, green = XZ, blue = XY). Hover highlights the plane under the cursor; a click
mirrors the selection in that plane (Option = mirrored copy). Faces are reversed so normals stay
outward. The selection is kept (the copy when copying). 1 undo step.
"""

import bpy
from mathutils import Vector, geometry

from .. import colors, i18n, modifiers, registry
from ..core.state import STATE
from . import move as move_tool
from .base import BaseTool, Result, ToolMeta, tool

TOOL_ID = "su.flip"
AXES = (("X", Vector((1, 0, 0)), colors.AXIS_X), ("Y", Vector((0, 1, 0)), colors.AXIS_Y),
        ("Z", Vector((0, 0, 1)), colors.AXIS_Z))

STRINGS = {
    "tool.su.flip.label": {"pt_BR": "Virar", "en": "Flip"},
    "tool.su.flip.hint": {"pt_BR": "Clique num plano para virar a seleção. {opt} = Alternar cópia.",
                          "en": "Click a plane to flip the selection. {opt} = Toggle copy."},
    "tool.su.flip.undo": {"pt_BR": "Virar", "en": "Flip"},
}


def _targets(tc, xy, inf):
    from ..core import selection
    if not selection.is_empty():
        return list(selection.get()), {}
    return move_tool.hover_target(tc, xy, inf)


def _box(refs, verts):
    from . import scale
    b = scale.Box(refs, verts)
    return b if b.ok() else None


def _planes(b):
    """[(axis name, normal, rgb, quad world corners)] through the box centre."""
    c = (b.mn + b.mx) * 0.5
    size = b.mx - b.mn
    pad = max(size.length * 0.05, 0.05)
    out = []
    for i, (name, n, rgb) in enumerate(AXES):
        j, k = [a for a in range(3) if a != i]
        quad = []
        for sj, sk in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            p = c.copy()
            p[j] = c[j] + sj * (size[j] * 0.5 + pad)
            p[k] = c[k] + sk * (size[k] * 0.5 + pad)
            quad.append(b.matrix @ p)
        out.append((name, (b.matrix.to_3x3() @ n).normalized(), rgb, quad, b.matrix @ c))
    return out


def plane_under(tc, xy, b, inf=None):
    """Axis name of the plane hit first by the view ray (headless: the plane containing inf.point)."""
    planes = _planes(b)
    if tc.region is None or tc.rv3d is None:
        if inf is None or inf.kind == "NONE":
            return None
        for name, n, _rgb, quad, c in planes:
            if abs((Vector(inf.point) - c).dot(n)) < 1e-6:
                return name
        return None
    from ..core import viewutil
    o, d = viewutil.mouse_ray(tc.region, tc.rv3d, xy)
    best, bd = None, None
    for name, n, _rgb, quad, _c in planes:
        for tri in ((quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])):
            p = geometry.intersect_ray_tri(tri[0], tri[1], tri[2], d, o, False)
            if p is not None:
                t = (p - o).dot(d)
                if t > 0 and (bd is None or t < bd):
                    best, bd = name, t
    return best


def flip(refs, verts, axis, copy, box):
    from ..core import geom_transform
    for name, n, _rgb, _quad, c in _planes(box):
        if name == axis:
            return geom_transform.mirror(refs, c, n, copy, verts=verts)
    return None


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.flip.label", icon="ops.gpencil.edit_mirror", cursor='CROSSHAIR',
               priority='P1'))
class FlipTool(BaseTool):

    def __init__(self):
        self.box = None
        self.hot = None
        self.targets = ([], {})

    def update_status(self):
        STATE.set_hint("tool.su.flip.hint", opt=modifiers.label("copy"))
        STATE.set_vcb("", "")

    def activate(self, tc):
        self.box = None
        self.hot = None
        self.update_status()

    def hover(self, tc, inf):
        self.targets = _targets(tc, tc.xy, inf)
        self.box = _box(*self.targets) if (self.targets[0] or self.targets[1]) else None
        self.hot = plane_under(tc, tc.xy, self.box, inf) if self.box is not None else None

    def press(self, tc, ev, inf):
        refs, verts = _targets(tc, (ev.x, ev.y), inf)
        box = _box(refs, verts) if (refs or verts) else None
        if box is None:
            return Result.IDLE
        axis = plane_under(tc, (ev.x, ev.y), box, inf)
        if axis is None:
            return Result.IDLE
        flip(refs, verts, axis, ev.copy, box)
        self.box = None
        self.hot = None
        return Result.IDLE

    def draw_3d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None or self.box is None:
            return
        for name, _n, rgb, quad, _c in _planes(self.box):
            a = 0.35 if name == self.hot else 0.12
            prims.polygon(dc, quad, colors.rgba(rgb, a))
            prims.lines(dc, [(quad[i], quad[(i + 1) % 4]) for i in range(4)], colors.rgba(rgb), 1.0, depth=False)


def register():
    i18n.register_strings(STRINGS)
