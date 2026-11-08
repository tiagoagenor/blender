# SPDX-License-Identifier: GPL-2.0-or-later
"""Camera tools (owner: G, P1). PLANO.md §1.2, §4.3 rows 17–19, §6.3.

  Janela de zoom   drag (or click-click) a rectangle: that part of the view fills the region
  Posição da câmera  click a point: the eye goes there at eye height (1,676 m, SketchUp's 5'6"), looking
                   horizontally in the current direction; press-drag-release = eye at the press point
                   looking at the release point. Medidas "Altura dos olhos": typed before (next placement)
                   or after (retype moves the eye up/down, "Ajustar").
"""

import math

from mathutils import Matrix, Vector

from .. import colors, constants, i18n, registry
from ..core import camera
from ..core.state import STATE, LastAction
from .base import BaseTool, Result, ToolMeta, fmt_length, kind_of, tool, value_of

EYE_HEIGHT = 1.676
LENGTH_KINDS = frozenset({"LENGTH", "DISTANCE", "NUMBER"})

STRINGS = {
    "tool.su.zoom_window.label": {"pt_BR": "Janela de zoom", "en": "Zoom Window"},
    "tool.su.zoom_window.hint": {"pt_BR": "Clique e arraste para definir a área de zoom.",
                                 "en": "Click and drag to define the zoom area."},
    "tool.su.zoom_window.hint_next": {"pt_BR": "Selecione o canto oposto.", "en": "Select the opposite corner."},
    "tool.su.position_camera.label": {"pt_BR": "Posição da câmera", "en": "Position Camera"},
    "tool.su.position_camera.hint": {
        "pt_BR": "Clique para posicionar a câmera na altura dos olhos, ou arraste até o ponto para onde olhar.",
        "en": "Click to place the camera at eye height, or drag to the point to look at."},
}


def zoom_window_view(v, x0, y0, x1, y1, target=None):
    """View after Janela de zoom on region rectangle (x0, y0)-(x1, y1): the rectangle centre goes to the
    screen centre and the rectangle fills the region. `target` = 3D point under the rectangle centre."""
    cx, cy = (x0 + x1) * 0.5, (y0 + y1) * 0.5
    w, h = abs(x1 - x0), abs(y1 - y0)
    if w < 2 or h < 2:
        return v
    p = target if target is not None else v.point_at_depth((cx, cy), v.depth(v.loc) if v.persp else 0.0)
    if v.persp:
        camera.pan_to(v, p, v.center_xy())
    else:
        camera.recenter_at(v, p)
    camera.zoom_at(v, p, max(w / v.width, h / v.height))
    return v


@tool(ToolMeta(id="su.zoom_window", label_key="tool.su.zoom_window.label", icon="draw.zoom_window",
               cursor='ZOOM_IN', priority='P1'))
class ZoomWindowTool(BaseTool):
    def __init__(self):
        self.a = None
        self.b = None

    def update_status(self):
        STATE.set_hint("tool.su.zoom_window.hint" if self.a is None else "tool.su.zoom_window.hint_next")

    def activate(self, tc):
        self.a = self.b = None
        self.update_status()

    def cancel(self, tc):
        self.a = self.b = None
        self.update_status()

    def press(self, tc, ev, inf):
        if self.a is None:
            self.a = self.b = (ev.x, ev.y)
            self.update_status()
            return Result.RUNNING
        return self._finish(tc, (ev.x, ev.y))

    def move(self, tc, ev, inf):
        if self.a is not None:
            self.b = (ev.x, ev.y)
        return Result.RUNNING if self.a is not None else Result.IDLE

    def release(self, tc, ev, inf):
        if self.a is None:
            return Result.IDLE
        if ev.is_drag_release:
            return self._finish(tc, (ev.x, ev.y))
        return Result.RUNNING

    def _finish(self, tc, b):
        a = self.a
        self.a = self.b = None
        if tc is not None and tc.region is not None:
            v = camera.View.from_rv3d(tc.region, tc.rv3d)
            camera.push_history(v)
            c = ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5)
            zoom_window_view(v, a[0], a[1], b[0], b[1], camera.hit_point(tc.region, tc.rv3d, c))
            v.apply(tc.rv3d)
            camera.push_history(v)
        self.update_status()
        return Result.IDLE

    def draw_2d(self, dc):
        if self.a is None or self.b is None:
            return
        prims = registry.optional("draw.prims")
        if prims is None:
            return
        (x0, y0), (x1, y1) = self.a, self.b
        c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        black = colors.rgba(colors.EDGE, 1.0)
        for i in range(4):
            prims.line(dc, c[i], c[(i + 1) % 4], black, 1.0, depth=False)


def place_eye(v, eye, target=None):
    """Camera at `eye`, looking at `target` (or horizontally along the current direction); no roll."""
    eye = Vector(eye)
    if target is not None and (Vector(target) - eye).length > 1e-6:
        f = (Vector(target) - eye).normalized()
    else:
        f = v.fwd.copy()
        f.z = 0.0
        if f.length < 1e-6:
            f = v.up.copy()
            f.z = 0.0
        f.normalize()
    if abs(f.z) > 0.999:
        right = Vector((1.0, 0.0, 0.0))
    else:
        right = f.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = right.cross(f).normalized()
    v.rot = Matrix((right, up, -f)).transposed().to_quaternion()
    d = (Vector(target) - eye).length if target is not None else 5.0
    v.dist = max(0.5, d)
    v.persp = True
    v.loc = eye + f * v.dist
    return v


@tool(ToolMeta(id="su.position_camera", label_key="tool.su.position_camera.label", icon="draw.position_camera",
               cursor='CROSSHAIR', vcb_label_key="vcb.eye_height", vcb_schema="length", priority='P1'))
class PositionCameraTool(BaseTool):
    def __init__(self):
        self.height = EYE_HEIGHT
        self.press_point = None
        self.last = None             # (ground point, target) of the last placement

    def update_status(self):
        STATE.set_hint("tool.su.position_camera.hint")
        STATE.set_vcb(self.meta.vcb_label_key, fmt_length(self.height))

    def activate(self, tc):
        self.press_point = None
        self.update_status()

    def cancel(self, tc):
        self.press_point = None

    def press(self, tc, ev, inf):
        if inf is None or inf.kind == "NONE":
            return Result.IDLE
        self.press_point = Vector(inf.point)
        return Result.RUNNING

    def move(self, tc, ev, inf):
        return Result.RUNNING if self.press_point is not None else Result.IDLE

    def release(self, tc, ev, inf):
        if self.press_point is None:
            return Result.IDLE
        target = None
        if ev.is_drag_release and inf is not None and inf.kind != "NONE":
            target = Vector(inf.point)
        self._place(tc, self.press_point, target)
        self.press_point = None
        return Result.IDLE

    def _place(self, tc, ground, target):
        self.last = (Vector(ground), None if target is None else Vector(target))
        STATE.last_action = LastAction(tool_id=self.meta.id, schema=self.meta.vcb_schema, reapply=self._reapply)
        if tc is None or tc.region is None:
            return
        v = camera.View.from_rv3d(tc.region, tc.rv3d)
        camera.push_history(v)
        place_eye(v, Vector(ground) + Vector((0.0, 0.0, self.height)), target)
        v.apply(tc.rv3d)
        camera.push_history(v)
        registry.deferred(lambda: camera.keep_fov(tc.area, tc.region, tc.rv3d, force=True), 0.05)

    def _reapply(self, values):
        if not values or kind_of(values[0]) not in LENGTH_KINDS or self.last is None:
            return False
        self.height = value_of(values[0])
        from .base import tool_context
        self._place(tool_context(), self.last[0], self.last[1])
        self.update_status()
        return False            # camera only: no undo step (A pushes "undo.adjust" on True)

    def vcb(self, tc, values):
        if not values or kind_of(values[0]) not in LENGTH_KINDS:
            return Result.PASS
        self.height = value_of(values[0])           # before placing: the next eye height
        self.update_status()
        return Result.IDLE


def register():
    i18n.register_strings(STRINGS)
