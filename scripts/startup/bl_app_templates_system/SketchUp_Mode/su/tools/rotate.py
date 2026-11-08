# SPDX-License-Identifier: GPL-2.0-or-later
"""Girar (owner: F). PLANO.md §6.1 (AC-GIR-1..3).

Hover: the protractor follows the cursor in the plane of the face under it (or the ground), coloured
by its normal (blue/red/green; arrows lock the plane like the Protractor). Click 1 = centre, click 2 =
start of the arm (0°), move = rotation (snaps to 15° near multiples), click 3 = done. Medidas "Ângulo":
degrees or a slope `3:12`; after a copy `5x` / `/5`. Option toggles copy; the selection stays on the
rotated entities (the copy when copying). Without a selection the entity under the first click
rotates (like Mover). Face rotations reject positions that would bend a neighbour face.
"""

import math

import bpy
from mathutils import Matrix, Vector

from .. import colors, constants, i18n, modifiers, registry
from ..core.state import STATE, LastAction, Locks
from . import move as move_tool
from .base import BaseTool, Result, ToolMeta, kind_of, make_query, tool, value_of

TOOL_ID = "su.rotate"

STRINGS = {
    "tool.su.rotate.label": {"pt_BR": "Girar", "en": "Rotate"},
    "tool.su.rotate.hint_center": {"pt_BR": "Clique para definir o centro da rotação. {opt} = Alternar cópia.",
                                   "en": "Click to place the protractor. {opt} = Toggle copy."},
    "tool.su.rotate.hint_start": {"pt_BR": "Clique para definir o início do ângulo.",
                                  "en": "Click to set the start of the angle."},
    "tool.su.rotate.hint_end": {"pt_BR": "Clique para definir o ângulo de rotação. {opt} = Alternar cópia.",
                                "en": "Click to set the rotation angle. {opt} = Toggle copy."},
    "tool.su.rotate.undo": {"pt_BR": "Girar", "en": "Rotate"},
    "tool.su.rotate.undo_copy": {"pt_BR": "Copiar", "en": "Copy"},
}

AXIS_RGB = {"X": colors.AXIS_X, "Y": colors.AXIS_Y, "Z": colors.AXIS_Z, "": colors.EDGE}   # free plane = black
PROTRACTOR_PX = 56          # logical px radius (constant on screen)
SNAP_DEG = constants.ANGLE_SNAP_DEG
SNAP_WITHIN_DEG = 2.0


def _default_ref(n):
    """0° direction of the protractor before the arm exists: red axis (or green) projected on the plane."""
    n = Vector(n).normalized()
    for ax in (Vector((1, 0, 0)), Vector((0, 1, 0))):
        u = ax - n * ax.dot(n)
        if u.length > 1e-3:
            return u.normalized()
    return n.orthogonal().normalized()


def protractor_segments(center, normal, ref_dir, radius):
    """World segments of SketchUp's protractor: outer and inner circles (solid), a tick every 15°
    (longer every 45°, longest every 90°) and the 0° baseline."""
    import math as _m
    c, n = Vector(center), Vector(normal).normalized()
    u = Vector(ref_dir) - n * Vector(ref_dir).dot(n)
    u = u.normalized() if u.length > 1e-9 else n.orthogonal().normalized()
    v = n.cross(u)
    segs = []
    k = 72
    for r in (radius, radius * 0.72):
        for i in range(k):
            a0, a1 = 2 * _m.pi * i / k, 2 * _m.pi * (i + 1) / k
            segs.append((c + (u * _m.cos(a0) + v * _m.sin(a0)) * r, c + (u * _m.cos(a1) + v * _m.sin(a1)) * r))
    for d in range(0, 360, 15):
        a = _m.radians(d)
        e = u * _m.cos(a) + v * _m.sin(a)
        inner = 0.72 if d % 90 == 0 else (0.80 if d % 45 == 0 else 0.88)
        segs.append((c + e * radius * inner, c + e * radius))
    segs.append((c, c + u * radius))
    return segs


def draw_protractor(dc, prims, center, normal, ref_dir, rgba):
    from ..core import viewutil
    k = viewutil.pixel_size_at(dc.region, dc.rv3d, Vector(center))
    if k <= 0:
        return
    radius = viewutil.ui_px(PROTRACTOR_PX) * k
    prims.lines(dc, protractor_segments(center, normal, ref_dir, radius), rgba, 2.0, depth=False)
    prims.points(dc, [Vector(center)], rgba, 5)


def fmt_angle(rad):
    u = registry.optional("core.units")
    if u is not None and hasattr(u, "format_angle"):
        try:
            return u.format_angle(rad, getattr(bpy.context.scene, "su_units", None))
        except Exception:
            pass
    return "{:.1f}°".format(math.degrees(rad)).replace(".", ",")


def rotation_about(center, normal, angle):
    c = Vector(center)
    return Matrix.Translation(c) @ Matrix.Rotation(angle, 4, Vector(normal).normalized()) @ Matrix.Translation(-c)


def signed_angle(u, v, n):
    """Angle from u to v around n (both projected on the plane of n)."""
    n = Vector(n).normalized()
    a = u - n * u.dot(n)
    b = v - n * v.dot(n)
    if a.length < 1e-9 or b.length < 1e-9:
        return 0.0
    return math.atan2(n.dot(a.cross(b)), a.dot(b))


def snap(angle):
    d = math.degrees(angle)
    k = round(d / SNAP_DEG) * SNAP_DEG
    return math.radians(k) if abs(d - k) <= SNAP_WITHIN_DEG else angle


def _axis_of(n):
    for name, ax in (("X", (1, 0, 0)), ("Y", (0, 1, 0)), ("Z", (0, 0, 1))):
        if abs(abs(Vector(n).normalized().dot(Vector(ax))) - 1.0) < 1e-6:
            return name
    return ""


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.rotate.label", icon="ops.transform.rotate", shortcut="Q",
               cursor='CROSSHAIR', vcb_label_key="vcb.angle", vcb_schema="angle"))
class RotateTool(BaseTool):

    def __init__(self):
        self.reset()
        self.last = None
        self.last_angle = None
        self.last_axis = None

    def reset(self):
        self.stage = 0               # 0 hover, 1 centre placed, 2 rotating
        self.center = None
        self.normal = Vector((0, 0, 1))
        self.axis = "Z"
        self.ref = None              # start of the arm (world)
        self.angle = 0.0
        self.session = None
        self.copy = False
        self.targets = ([], {})
        self.cursor = None
        self.hover_refs = ([], {})

    def update_status(self):
        opt = modifiers.label("copy")
        key = ("tool.su.rotate.hint_center", "tool.su.rotate.hint_start", "tool.su.rotate.hint_end")[self.stage]
        STATE.set_hint(key, opt=opt)
        if self.stage == 2:
            STATE.set_vcb(self.meta.vcb_label_key, fmt_angle(self.angle))
        else:
            STATE.set_vcb(self.meta.vcb_label_key, STATE.vcb_value)

    def activate(self, tc):
        self.reset()
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)

    def cancel(self, tc):
        if self.session is not None:
            self.session.cancel()
        self.reset()
        self.update_status()

    # -- planes / inference --------------------------------------------------------------------------
    def _hover_plane(self, tc, xy, inf):
        locks = STATE.locks
        axes = {"AXIS_X": ("X", Vector((1, 0, 0))), "AXIS_Y": ("Y", Vector((0, 1, 0))),
                "AXIS_Z": ("Z", Vector((0, 0, 1)))}
        inference = registry.optional("core.inference")
        if tc.region is not None and inference is not None and hasattr(inference, "hover_plane"):
            co, n, ax = inference.hover_plane(make_query(tc, xy))
            return Vector(co), Vector(n), ax
        if locks.axis in axes:
            ax, n = axes[locks.axis]
            return Vector(inf.point), n, ax
        if inf is not None and inf.kind == "ON_FACE" and inf.normal is not None:
            n = Vector(inf.normal) * (-1 if inf.side < 0 else 1)
            return Vector(inf.point), n, _axis_of(n)
        return Vector(inf.point) if inf is not None else Vector(), Vector((0, 0, 1)), "Z"

    def query_ctx(self, tc, xy):
        if self.stage == 0:
            return make_query(tc, xy)
        kw = dict(anchor=self.center, plane=(self.center, self.normal))
        if self.session is not None:
            kw.update(exclude=self.session.exclude, skip=self.session.moving_faces)
        return make_query(tc, xy, **kw)

    def hover(self, tc, inf):
        if inf is None or inf.kind == "NONE":
            self.cursor = None
            return
        co, n, ax = self._hover_plane(tc, tc.xy, inf)
        self.cursor, self.normal, self.axis = co, n, ax
        from ..core import selection
        self.hover_refs = move_tool.hover_target(tc, tc.xy, inf) if selection.is_empty() else ([], {})

    def _on_plane(self, p):
        return p - self.normal * (p - self.center).dot(self.normal)

    # -- clicks --------------------------------------------------------------------------------------
    def press(self, tc, ev, inf):
        if inf is None or inf.kind == "NONE":
            return Result.RUNNING if self.stage else Result.IDLE
        p = Vector(inf.point)
        if self.stage == 0:
            from ..core import selection
            co, n, ax = self._hover_plane(tc, (ev.x, ev.y), inf)
            refs, verts = (list(selection.get()), {}) if not selection.is_empty() else \
                move_tool.hover_target(tc, (ev.x, ev.y), inf)
            if not refs and not verts:
                return Result.IDLE
            self.targets = (refs, verts)
            self.center, self.normal, self.axis = p, n.normalized(), ax
            self.copy = ev.copy
            self.stage = 1
            self.update_status()
            return Result.RUNNING
        if self.stage == 1:
            q = self._on_plane(p)
            if (q - self.center).length <= constants.GEOM_TOL:
                return Result.RUNNING
            self.ref = q
            self._start_session()
            self.stage = 2
            self.update_status()
            return Result.RUNNING
        return self._finish(self.angle)

    def release(self, tc, ev, inf):
        if self.stage == 2 and ev.is_drag_release:
            return self._finish(self.angle)
        if self.stage == 1 and ev.is_drag_release and inf is not None and inf.kind != "NONE":
            q = self._on_plane(Vector(inf.point))
            if (q - self.center).length > constants.GEOM_TOL:
                self.ref = q
                self._start_session()
                self.stage = 2
                self.update_status()
        return Result.RUNNING if self.stage else Result.IDLE

    def _start_session(self):
        from ..core import geom_transform, selection
        refs, verts = self.targets
        fold = 'AUTO' if verts or not any(r.kind == selection.FACE for r in refs) else 'RESTRICT'
        self.session = geom_transform.TransformSession(refs, copy=self.copy, fold=fold, verts=verts)

    def move(self, tc, ev, inf):
        if inf is not None and inf.kind != "NONE":
            self.cursor = Vector(inf.point)
        if self.stage == 2 and self.cursor is not None:
            a = signed_angle(self.ref - self.center, self._on_plane(self.cursor) - self.center, self.normal)
            self.angle = snap(a)
            self.session.set_matrix(rotation_about(self.center, self.normal, self.angle))   # RESTRICT may keep the last valid one
        self.update_status()
        return Result.RUNNING if self.stage else Result.IDLE

    def key(self, tc, ev):
        if ev.type in {'LEFT_ALT', 'RIGHT_ALT'} and ev.value == 'PRESS' and self.stage:
            self.copy = not self.copy
            if self.session is not None:
                m = self.session.matrix.copy()
                self.session.cancel()
                self._start_session()
                self.session.set_matrix(m)
            STATE.redraw_viewport(tc.region)
            return Result.RUNNING
        return Result.PASS

    def vcb(self, tc, values):
        if self.stage != 2 or not values:
            return Result.PASS
        v = values[0]
        if kind_of(v) not in {"ANGLE", "NUMBER"}:
            return Result.PASS
        a = value_of(v) if kind_of(v) == "ANGLE" else math.radians(value_of(v))
        if self.angle < 0:
            a = -abs(a) if a > 0 else a
        return self._finish(a)

    def _finish(self, angle):
        s = self.session
        m = rotation_about(self.center, self.normal, angle)
        got = s.set_matrix(m)
        if got != m:
            angle = self.angle
        s.finish("tool.su.rotate.undo_copy" if self.copy else "tool.su.rotate.undo")
        self.last, self.last_angle, self.last_axis = s, angle, (self.center.copy(), self.normal.copy())
        STATE.last_action = LastAction(tool_id=TOOL_ID, schema=self.meta.vcb_schema, reapply=self._reapply)
        STATE.locks = Locks()                 # arrow/Shift locks end with the operation
        STATE.set_vcb(self.meta.vcb_label_key, fmt_angle(angle))
        self.session = None
        self.reset()
        self.update_status()
        return Result.IDLE

    def _reapply(self, values):
        s, a = self.last, self.last_angle
        if s is None or a is None or not values:
            return False
        c, n = self.last_axis
        v = values[0]
        k = kind_of(v)
        if k in {"MULTIPLY", "DIVIDE"} and s.copy:
            cnt = v.count
            if not cnt or cnt < 1:
                return False
            return s.array(cnt, k == "DIVIDE", lambda t: rotation_about(c, n, a * t))
        if k in {"ANGLE", "NUMBER"}:
            new = value_of(v) if k == "ANGLE" else math.radians(value_of(v))
            if a < 0:
                new = -abs(new)
            if s.copy:
                ok = s.array(1, False, lambda t: rotation_about(c, n, new * t))
            else:
                s.reapply_matrix(rotation_about(c, n, new))
                ok = True
            if ok:
                self.last_angle = new
                STATE.set_vcb(self.meta.vcb_label_key, fmt_angle(new))
            return ok
        return False

    # -- drawing -------------------------------------------------------------------------------------
    def draw_3d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None:
            return
        center = self.center if self.stage else self.cursor
        if center is None:
            return
        rgba = colors.rgba(AXIS_RGB.get(self.axis, AXIS_RGB[""]))
        ref_dir = (self.ref - self.center) if self.ref is not None else _default_ref(self.normal)
        draw_protractor(dc, prims, center, self.normal, ref_dir, rgba)
        black = colors.rgba(colors.EDGE)
        if self.stage == 2 and self.ref is not None:
            prims.line(dc, self.center, self.ref, black, 1.0, depth=False)
        if self.stage >= 1 and self.cursor is not None:
            prims.dashed(dc, self.center, self._on_plane(self.cursor), black, 1.0)


def register():
    i18n.register_strings(STRINGS)
