# SPDX-License-Identifier: GPL-2.0-or-later
"""Retângulo girado (owner: E; promoted from P2 by the leader). SketchUp behaviour:

Click the first corner, click the second (the first edge: any direction, inferences from the first corner;
or type its length), then move: the rectangle turns about that edge to follow the cursor (width = the
cursor's distance from the edge line, perpendicular to it) — on a face it lies on the face. Click, or type
`largura;ângulo` ("Largura; Ângulo": the angle in degrees from the horizontal side of the edge, about the
edge; either value may be left empty). One undo step; B's kernel makes the face (split/hole on faces).
"""

import math

from mathutils import Matrix, Vector

from .. import colors, constants, i18n, registry
from ..core.state import STATE, Locks
from .base import BaseTool, Result, ToolMeta, fmt_length, kind_of, make_query, tool, value_of

TOOL_ID = "su.rotated_rectangle"
Z = Vector((0.0, 0.0, 1.0))

STRINGS = {
    "tool.su.rotated_rectangle.label": {"pt_BR": "Retângulo girado", "en": "Rotated Rectangle"},
    "tool.su.rotated_rectangle.hint_start": {"pt_BR": "Selecione o primeiro canto.", "en": "Select first corner."},
    "tool.su.rotated_rectangle.hint_edge": {"pt_BR": "Selecione o segundo canto (primeira aresta).",
                                            "en": "Select second corner (first edge)."},
    "tool.su.rotated_rectangle.hint_width": {"pt_BR": "Selecione a largura e o ângulo, ou digite-os.",
                                             "en": "Select width and angle, or enter them."},
    "tool.su.rotated_rectangle.undo": {"pt_BR": "Retângulo girado", "en": "Rotated Rectangle"},
    "tool.su.rotated_rectangle.vcb": {"pt_BR": "Largura; Ângulo", "en": "Width; Angle"},
}


def _document():
    return registry.optional("core.document").active()


def _point(inf):
    if inf is None or inf.kind == "NONE":
        return None
    return Vector(inf.point)


def ref_dir(e):
    """Angle 0 direction for edge direction e: horizontal, perpendicular to e (X for a vertical edge)."""
    r = e.cross(Z)
    if r.length < 1e-9:
        r = Vector((0.0, 1.0, 0.0)).cross(e)
    return r.normalized()


def _num(v):
    """Plain number of a typed value (the angle): from its text when possible (units-free)."""
    t = getattr(v, "text", "") or ""
    t = t.strip().replace(",", ".").rstrip("°")
    try:
        return float(t)
    except ValueError:
        return value_of(v)


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.rotated_rectangle.label", icon="ops.transform.resize.cage",
               cursor='PAINT_CROSS', vcb_label_key="vcb.length", vcb_schema="length2", priority='P1'))
class RotatedRectangleTool(BaseTool):

    def __init__(self):
        self.reset()

    def reset(self):
        self.p1 = self.p2 = None
        self.cur = None
        self.w = None             # width vector (perpendicular to the edge)

    # -- status --------------------------------------------------------------------------------------
    def _angle(self):
        if self.w is None or self.w.length <= constants.GEOM_TOL:
            return 0.0
        e = (self.p2 - self.p1).normalized()
        r = ref_dir(e)
        return math.atan2(e.cross(r).dot(self.w), r.dot(self.w))

    def update_status(self):
        if self.p1 is None:
            STATE.set_hint("tool.su.rotated_rectangle.hint_start")
            STATE.set_vcb("vcb.length", STATE.vcb_value)
        elif self.p2 is None:
            STATE.set_hint("tool.su.rotated_rectangle.hint_edge")
            STATE.set_vcb("vcb.length", fmt_length((self.cur - self.p1).length) if self.cur is not None else "")
        else:
            STATE.set_hint("tool.su.rotated_rectangle.hint_width")
            w = self.w.length if self.w is not None else 0.0
            ang = ("%.1f" % math.degrees(self._angle())).replace(".", ",")
            STATE.set_vcb("tool.su.rotated_rectangle.vcb", "{:s}; {:s}°".format(fmt_length(w), ang))

    def activate(self, tc):
        self.reset()
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)

    def cancel(self, tc):
        self.reset()
        self.update_status()

    def query_ctx(self, tc, xy):
        anchor = self.p2 if self.p2 is not None else self.p1
        return make_query(tc, xy, anchor=anchor.copy() if anchor is not None else None,
                          locks=STATE.locks if self.p2 is None else Locks())

    # -- tracking ------------------------------------------------------------------------------------
    def _width_from(self, q):
        e = (self.p2 - self.p1).normalized()
        v = q - self.p2
        return v - e * v.dot(e)

    def move(self, tc, ev, inf):
        if self.p1 is None:
            return Result.IDLE
        p = _point(inf)
        if p is not None:
            self.cur = p
            if self.p2 is not None:
                self.w = self._width_from(p)
        self.update_status()
        return Result.RUNNING

    def press(self, tc, ev, inf):
        p = _point(inf)
        if self.p1 is None:
            if p is None:
                return Result.IDLE
            self.p1, self.cur = p, p
            self.update_status()
            return Result.RUNNING
        if self.p2 is None:
            if p is None or (p - self.p1).length <= constants.GEOM_TOL:
                return Result.RUNNING
            self.p2, self.w = p, None
            self.update_status()
            return Result.RUNNING
        if p is not None:
            self.w = self._width_from(p)
        if self.w is None or self.w.length <= constants.GEOM_TOL:
            return Result.RUNNING
        return self._commit(self.w)

    def release(self, tc, ev, inf):
        return Result.RUNNING if self.p1 is not None else Result.IDLE

    # -- Measurements --------------------------------------------------------------------------------
    def vcb(self, tc, values):
        if self.p1 is None or not values:
            return Result.PASS
        if self.p2 is None:
            v = values[0]
            if v is None or value_of(v) is None or value_of(v) <= constants.GEOM_TOL or self.cur is None \
                    or (self.cur - self.p1).length <= constants.GEOM_TOL:
                STATE.vcb_error = True
                return Result.RUNNING
            self.p2 = self.p1 + (self.cur - self.p1).normalized() * value_of(v)
            self.w = None
            self.update_status()
            return Result.RUNNING
        e = (self.p2 - self.p1).normalized()
        cur_w = self.w.length if self.w is not None else 0.0
        width = value_of(values[0]) if values[0] is not None and getattr(values[0], "value", 0) is not None else cur_w
        ang = self._angle()
        if len(values) > 1 and values[1] is not None and getattr(values[1], "value", None) is not None:
            ang = math.radians(_num(values[1]))
        if width is None or abs(width) <= constants.GEOM_TOL:
            STATE.vcb_error = True
            return Result.RUNNING
        w = Matrix.Rotation(ang, 3, e) @ ref_dir(e) * width
        return self._commit(w)

    # -- geometry ------------------------------------------------------------------------------------
    def _commit(self, w):
        from ..core import geom
        doc = _document()
        inv = doc.world().inverted()
        pts = [self.p1, self.p2, self.p2 + w, self.p1 + w]
        geom.add_closed_shape(doc.bm, [inv @ p for p in pts], None)
        doc.write(undo_key="tool.su.rotated_rectangle.undo")
        self.w = w
        ang = ("%.1f" % math.degrees(self._angle())).replace(".", ",")
        text = "{:s}; {:s}°".format(fmt_length(w.length), ang)
        self.reset()
        self.update_status()
        STATE.set_vcb("tool.su.rotated_rectangle.vcb", text)     # the last values stay visible
        return Result.IDLE

    def draw_3d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None or self.p1 is None:
            return
        rgba = colors.rgba(colors.EDGE, 1.0)
        if self.p2 is None:
            if self.cur is not None:
                prims.line(dc, self.p1, self.cur, rgba)
            return
        w = self.w if self.w is not None else Vector()
        pts = [self.p1, self.p2, self.p2 + w, self.p1 + w]
        prims.lines(dc, [(pts[i], pts[(i + 1) % 4]) for i in range(4)], rgba)
        e = (self.p2 - self.p1).normalized()
        prims.protractor(dc, self.p2, e, ref_dir(e), colors.rgba(colors.INF_PARALLEL, 1.0))


def register():
    i18n.register_strings(STRINGS)
