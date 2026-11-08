# SPDX-License-Identifier: GPL-2.0-or-later
"""Transferidor (owner: G). PLANO.md §6.3 AC-TRA-1..2; RESEARCH_SKETCHUP §6 (Protractor).

  hover    the protractor gizmo follows the cursor in the plane under it (C's `hover_plane`: face plane,
           arrow-locked axis plane, else the ground), coloured by the plane (blue = horizontal,
           red = YZ, green = XZ) — drawn by the tool's draw_3d (the tool keymap's MOUSEMOVE gives hover)
  click 1  vertex (centre); the plane is locked
  click 2  baseline point (0°)
  move     angle from the baseline, snapping to 15° steps while the cursor is near the protractor
  click 3  (or a typed angle / slope `3:12` + Enter) → angled guide line through the centre
Option toggles guide creation (measure only: Medidas shows the angle). 1 undo step per guide.
"""

import math

from mathutils import Vector, geometry

from .. import colors, constants, i18n, registry
from ..core import guides, undo, viewutil
from ..core.state import STATE
from .base import BaseTool, Result, ToolMeta, kind_of, make_query, tool, value_of

TOOL_ID = "su.protractor"
OPTION_KEYS = frozenset({'LEFT_ALT', 'RIGHT_ALT'})
GIZMO_RADIUS_PX = 48
SNAP_RADIUS_FACTOR = 1.6       # snapping to 15° while the cursor is within this × the gizmo radius

AXIS_COLORS = {"X": colors.AXIS_X, "Y": colors.AXIS_Y, "Z": colors.AXIS_Z}

STRINGS = {
    "tool.su.protractor.label": {"pt_BR": "Transferidor", "en": "Protractor"},
    "tool.su.protractor.hint_center": {"pt_BR": "Posicione o centro do transferidor. Option = alternar criação de guia.",
                                       "en": "Place the protractor center. Option = toggle guide creation."},
    "tool.su.protractor.hint_base": {"pt_BR": "Selecione o ponto da linha de base do ângulo.",
                                     "en": "Select the baseline point of the angle."},
    "tool.su.protractor.hint_angle": {"pt_BR": "Selecione o ângulo ou digite um valor.",
                                      "en": "Select the angle or type a value."},
    "tool.su.protractor.undo": {"pt_BR": "Guia angular", "en": "Angle Guide"},
}


def signed_angle(ref, v, normal):
    """Angle from `ref` to `v` (radians, −π..π) counter-clockwise around `normal`."""
    n = Vector(normal).normalized()
    a = Vector(ref) - n * Vector(ref).dot(n)
    b = Vector(v) - n * Vector(v).dot(n)
    if a.length < 1e-12 or b.length < 1e-12:
        return 0.0
    a.normalize()
    b.normalize()
    return math.atan2(n.dot(a.cross(b)), max(-1.0, min(1.0, a.dot(b))))


def direction_at(ref, normal, angle):
    """Unit vector at `angle` from `ref` around `normal` (in the plane)."""
    n = Vector(normal).normalized()
    a = Vector(ref) - n * Vector(ref).dot(n)
    a.normalize()
    b = n.cross(a)
    return (a * math.cos(angle) + b * math.sin(angle)).normalized()


def snap15(angle):
    step = math.radians(constants.ANGLE_SNAP_DEG)
    return round(angle / step) * step


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.protractor.label", icon="draw.protractor", cursor='CROSSHAIR',
               vcb_label_key="vcb.angle", vcb_schema="angle"))
class ProtractorTool(BaseTool):

    def __init__(self):
        self.guide_mode = True
        self.reset()

    def reset(self):
        self.stage = 0               # 0 hover, 1 centre placed, 2 baseline placed
        self.center = None
        self.normal = Vector((0.0, 0.0, 1.0))
        self.axis = "Z"
        self.ref = None              # baseline unit vector (in the plane)
        self.cursor = None           # cursor point projected on the plane
        self.angle = 0.0
        self.snapped = False

    # -- status ----------------------------------------------------------------------------------
    def update_status(self):
        STATE.set_hint(("tool.su.protractor.hint_center", "tool.su.protractor.hint_base",
                        "tool.su.protractor.hint_angle")[self.stage])
        if self.stage == 2:
            STATE.set_vcb(self.meta.vcb_label_key, _fmt_angle(self.angle))
        else:
            STATE.set_vcb(self.meta.vcb_label_key, STATE.vcb_value)

    def activate(self, tc):
        self.reset()
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)

    def cancel(self, tc):
        self.reset()
        self.update_status()

    # -- plane / cursor ----------------------------------------------------------------------------
    def query_ctx(self, tc, xy):
        return make_query(tc, xy, anchor=self.center)

    def _hover_plane(self, tc, inf):
        """(centre, normal, axis) of the gizmo under the cursor."""
        inference = registry.optional("core.inference")
        if tc is not None and tc.region is not None and inference is not None and hasattr(inference, "hover_plane"):
            try:
                co, n, ax = inference.hover_plane(make_query(tc, tc.xy if tc.xy != (0, 0) else inf.screen))
                return Vector(co), Vector(n).normalized(), ax
            except Exception:
                pass
        if inf is not None and inf.kind == "ON_FACE" and inf.normal is not None:
            n = Vector(inf.normal) * (1 if inf.side >= 0 else -1)
            return Vector(inf.point), n.normalized(), _axis_of(n)
        lk = getattr(STATE.locks, "axis", "")
        if lk in ("AXIS_X", "AXIS_Y", "AXIS_Z"):
            i = ("AXIS_X", "AXIS_Y", "AXIS_Z").index(lk)
            n = Vector([1.0 if k == i else 0.0 for k in range(3)])
            return Vector(inf.point) if inf is not None else Vector(), n, "XYZ"[i]
        return (Vector(inf.point) if inf is not None else Vector()), Vector((0.0, 0.0, 1.0)), "Z"

    def _on_plane(self, tc, ev, inf):
        """Cursor point on the locked plane: mouse ray ∩ plane (GUI) or the inference point projected."""
        p = None
        if tc is not None and tc.region is not None and ev is not None:
            o, d = viewutil.mouse_ray(tc.region, tc.rv3d, (ev.x, ev.y))
            if inf is not None and inf.kind not in ("NONE", "FREE", "ON_FACE"):
                q = Vector(inf.point)          # snapped point: keep it (projected on the plane)
                p = q - self.normal * (q - self.center).dot(self.normal)
            else:
                p = geometry.intersect_line_plane(o, o + d, self.center, self.normal)
        if p is None and inf is not None and inf.kind != "NONE":
            q = Vector(inf.point)
            p = q - self.normal * (q - self.center).dot(self.normal)
        return p

    def _near_gizmo(self, tc, p):
        if tc is None or tc.region is None:
            return True
        k = viewutil.pixel_size_at(tc.region, tc.rv3d, self.center)
        if k <= 0:
            return False
        return (p - self.center).length <= viewutil.ui_px(GIZMO_RADIUS_PX) * k * SNAP_RADIUS_FACTOR

    def hover(self, tc, inf):
        if self.stage == 0 and inf is not None and inf.kind != "NONE":
            self.center, self.normal, self.axis = self._hover_plane(tc, inf)

    def move(self, tc, ev, inf):
        if self.stage == 0:
            return Result.IDLE
        p = self._on_plane(tc, ev, inf)
        if p is None:
            return Result.RUNNING
        self.cursor = p
        v = p - self.center
        if self.stage == 2 and v.length > 1e-9:
            a = signed_angle(self.ref, v, self.normal)
            self.snapped = self._near_gizmo(tc, p)
            self.angle = snap15(a) if self.snapped else a
        self.update_status()
        return Result.RUNNING

    def key(self, tc, ev):
        if ev.type in OPTION_KEYS and ev.value == 'PRESS':
            self.guide_mode = not self.guide_mode
            return Result.RUNNING if self.stage else Result.IDLE
        return Result.PASS

    # -- clicks ------------------------------------------------------------------------------------
    def press(self, tc, ev, inf):
        if inf is None or inf.kind == "NONE":
            return Result.RUNNING if self.stage else Result.IDLE
        if self.stage == 0:
            if ev.copy:
                self.guide_mode = not self.guide_mode
            self.center, self.normal, self.axis = self._hover_plane(tc, inf)
            self.center = Vector(inf.point)
            self.stage = 1
            self.update_status()
            return Result.RUNNING
        p = self._on_plane(tc, ev, inf)
        if p is None or (p - self.center).length <= constants.GEOM_TOL:
            return Result.RUNNING
        if self.stage == 1:
            self.ref = (p - self.center).normalized()
            self.cursor = p
            self.angle = 0.0
            self.stage = 2
            self.update_status()
            return Result.RUNNING
        self.cursor = p
        a = signed_angle(self.ref, p - self.center, self.normal)
        self.angle = snap15(a) if self._near_gizmo(tc, p) else a
        return self._commit(self.angle)

    def release(self, tc, ev, inf):
        return Result.RUNNING if self.stage else Result.IDLE

    def vcb(self, tc, values):
        if self.stage != 2 or not values or kind_of(values[0]) != "ANGLE":
            return Result.PASS
        a = abs(value_of(values[0]))
        side = 1.0
        if self.cursor is not None:
            s = signed_angle(self.ref, self.cursor - self.center, self.normal)
            side = -1.0 if s < -1e-9 else 1.0
        return self._commit(a * side)

    def _commit(self, angle):
        self.angle = angle
        STATE.set_vcb(self.meta.vcb_label_key, _fmt_angle(angle))
        if self.guide_mode:
            guides.add_guide_line(self.center, direction_at(self.ref, self.normal, angle))
            undo.push("tool.su.protractor.undo")
        text = _fmt_angle(angle)
        self.reset()
        self.update_status()
        STATE.set_vcb(self.meta.vcb_label_key, text)
        return Result.IDLE

    # -- drawing -----------------------------------------------------------------------------------
    def draw_3d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None or self.center is None:
            return
        rgb = AXIS_COLORS.get(self.axis, colors.AXIS_Z)
        ref = self.ref if self.ref is not None else _default_ref(self.normal)
        prims.protractor(dc, self.center, self.normal, ref, colors.rgba(rgb, 1.0), radius_px=GIZMO_RADIUS_PX)
        black = colors.rgba(colors.GUIDE, 1.0)
        ann = registry.optional("draw.annotations")
        if self.stage == 1 and self.cursor is not None:
            prims.dashed(dc, self.center, self.cursor, black, 1.0, 6, 4)
        if self.stage == 2:
            for d in (ref, direction_at(ref, self.normal, self.angle)):
                seg = ann.clip_line(dc, self.center, d) if ann is not None else None
                if seg is not None:
                    prims.dashed(dc, seg[0], seg[1], black, 1.0, 6, 4)


def _default_ref(normal):
    n = Vector(normal).normalized()
    for axis in (Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0))):
        a = axis - n * axis.dot(n)
        if a.length > 1e-6:
            return a.normalized()
    return n.orthogonal().normalized()


def _axis_of(n):
    a = [abs(c) for c in n]
    i = a.index(max(a))
    return "XYZ"[i] if a[i] > 0.999 else ""


def _fmt_angle(rad):
    units = registry.optional("core.units")
    if units is not None and hasattr(units, "format_angle"):
        return units.format_angle(rad)
    return "{:.1f}°".format(math.degrees(rad)).replace(".", ",")


def register():
    i18n.register_strings(STRINGS)
