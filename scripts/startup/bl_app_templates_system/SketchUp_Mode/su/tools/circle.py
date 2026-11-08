# SPDX-License-Identifier: GPL-2.0-or-later
"""Círculo (owner: E). PLANO.md §6.2 (AC-CIR-1..4). Polígono reuses this controller (tools/polygon.py).

Before the click a plane gizmo follows the cursor (C's hover_plane: arrow lock → the plane whose NORMAL is
that axis — ↑ horizontal, → red normal, ← green normal, leader decision AC-CIR-4 —; a face under the
cursor → its plane; else the ground). Typing a number before the click sets the sides ("Lados"). Click the
center, move (the first vertex points at the cursor), click or type the radius ("Raio"); `Ns` changes the
sides. After drawing, retyping the radius or `Ns` rebuilds it ("Ajustar"). The edges form one curve entity
(su_curve + metadata kind/center/normal/radius/sides: C infers the center); Empurrar/puxar makes the sides of
a circle soft (a polygon keeps hard edges). One undo step per shape.
"""

from mathutils import Vector

from .. import colors, constants, i18n, registry
from ..core.state import STATE, LastAction, Locks
from .base import BaseTool, Result, ToolMeta, fmt_length, kind_of, make_query, tool, value_of

TOOL_ID = "su.circle"
LENGTH_KINDS = frozenset({"LENGTH", "DISTANCE", "NUMBER", "RADIUS"})
COUNT_KINDS = frozenset({"SIDES", "SEGMENTS", "NUMBER"})
AXIS_COLOR = {"X": colors.AXIS_X, "Y": colors.AXIS_Y, "Z": colors.AXIS_Z}

STRINGS = {
    "tool.su.circle.label": {"pt_BR": "Círculo", "en": "Circle"},
    "tool.su.circle.hint_start": {"pt_BR": "Selecione o ponto central.", "en": "Select center point."},
    "tool.su.circle.hint_next": {"pt_BR": "Selecione o raio ou digite-o.", "en": "Select radius or enter it."},
    "tool.su.circle.undo": {"pt_BR": "Círculo", "en": "Circle"},
}


def _document():
    document = registry.optional("core.document")
    if document is None:
        raise RuntimeError("core.document (B) not available")
    return document.active()


def _axis_of(n):
    for name, ax in (("X", Vector((1, 0, 0))), ("Y", Vector((0, 1, 0))), ("Z", Vector((0, 0, 1)))):
        if abs(abs(Vector(n).dot(ax)) - 1.0) < 1e-6:
            return name
    return ""


class ShapeTool(BaseTool):
    """Center-radius regular shape (Círculo / Polígono)."""
    DEFAULT_SIDES = constants.CIRCLE_SIDES
    KIND = "circle"
    PREFIX = "tool.su.circle"

    def __init__(self):
        self.sides = self.DEFAULT_SIDES
        self.last = None
        self.reset()

    def reset(self):
        self.center = None
        self.n = None
        self.radius = 0.0
        self.start_dir = None
        self.hover_plane = None       # (co, normal, axis) before the click

    # -- status --------------------------------------------------------------------------------------
    def update_status(self):
        if self.center is None:
            STATE.set_hint(self.PREFIX + ".hint_start")
            STATE.set_vcb("vcb.sides", str(self.sides))
        else:
            STATE.set_hint(self.PREFIX + ".hint_next")
            STATE.set_vcb("vcb.radius", fmt_length(self.radius))

    def activate(self, tc):
        self.reset()
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)
        self._drop_last()

    def cancel(self, tc):
        self.reset()
        STATE.locks.axis = ''
        self.update_status()

    def _drop_last(self):
        if self.last is not None:
            from ..core import geom_extrude
            geom_extrude.release(self.last["snap"])
            self.last = None

    # -- inference -----------------------------------------------------------------------------------
    def query_ctx(self, tc, xy):
        if self.center is None:
            return make_query(tc, xy, locks=Locks())
        return make_query(tc, xy, plane=(self.center.copy(), self.n.copy()), locks=Locks())

    def _plane_before(self, tc, ev, inf):
        """(co, normal, axis) of the gizmo plane at the cursor."""
        lock = {"AXIS_X": Vector((1, 0, 0)), "AXIS_Y": Vector((0, 1, 0)), "AXIS_Z": Vector((0, 0, 1))}.get(STATE.locks.axis)
        p = Vector(inf.point) if inf is not None and inf.kind != "NONE" else None
        if lock is not None and p is not None:
            return p, lock, _axis_of(lock)
        if inf is not None and inf.kind == "ON_FACE" and inf.normal is not None and p is not None:
            n = Vector(inf.normal).normalized()
            if inf.side < 0:
                n.negate()
            return p, n, _axis_of(n)
        if p is None:
            return None
        return p, Vector((0.0, 0.0, 1.0)), "Z"

    def hover(self, tc, inf):
        self.hover_plane = self._plane_before(tc, None, inf)

    def _track(self, inf):
        if inf is None or inf.kind == "NONE":
            return
        p = Vector(inf.point)
        p = p - self.n * (p - self.center).dot(self.n)
        d = p - self.center
        if d.length > constants.GEOM_TOL:
            self.radius = d.length
            self.start_dir = d.normalized()

    def move(self, tc, ev, inf):
        if self.center is None:
            self.hover_plane = self._plane_before(tc, ev, inf)
            self.update_status()
            return Result.IDLE
        self._track(inf)
        self.update_status()
        return Result.RUNNING

    def key(self, tc, ev):
        if ev.type in {'UP_ARROW', 'LEFT_ARROW', 'RIGHT_ARROW'} and self.center is None:
            return Result.IDLE
        return Result.PASS

    # -- clicks --------------------------------------------------------------------------------------
    def press(self, tc, ev, inf):
        if self.center is None:
            pl = self._plane_before(tc, ev, inf)
            if pl is None:
                return Result.IDLE
            self.center, self.n = pl[0].copy(), pl[1].normalized()
            self.radius = 0.0
            self.start_dir = None
            self.update_status()
            return Result.RUNNING
        self._track(inf)
        if self.radius <= constants.GEOM_TOL:
            return Result.RUNNING
        return self._commit(tc, self.radius, self.sides)

    def release(self, tc, ev, inf):
        if self.center is None:
            return Result.IDLE
        if ev.is_drag_release:
            self._track(inf)
            if self.radius > constants.GEOM_TOL:
                return self._commit(tc, self.radius, self.sides)
        return Result.RUNNING

    # -- Measurements --------------------------------------------------------------------------------
    def _parse(self, values):
        """(radius | None, sides | None) from typed values."""
        if not values or values[0] is None:
            return None, None
        v = values[0]
        k = kind_of(v)
        if k == "SIDES" or k == "SEGMENTS":
            return None, int(value_of(v))
        if k in LENGTH_KINDS:
            return value_of(v), None
        return None, None

    def vcb(self, tc, values):
        if self.center is None:
            # before the click: number of sides
            if values and values[0] is not None and kind_of(values[0]) in COUNT_KINDS | {"LENGTH"}:
                n = int(round(value_of(values[0]) if kind_of(values[0]) != "LENGTH" else value_of(values[0])))
                if n >= 3:
                    self.sides = min(n, 999)
                    self.update_status()
                    return Result.IDLE
            STATE.vcb_error = True
            return Result.IDLE
        r, s = self._parse(values)
        if s is not None:
            if s < 3:
                STATE.vcb_error = True
                return Result.RUNNING
            self.sides = s
            self.update_status()
            return Result.RUNNING
        if r is None or r <= constants.GEOM_TOL:
            STATE.vcb_error = True
            return Result.RUNNING
        return self._commit(tc, r, self.sides)

    def _reapply(self, values):
        last = self.last
        if last is None:
            return False
        r, s = self._parse(values)
        r = r if r is not None else last["radius"]
        s = s if s is not None else last["sides"]
        if r <= constants.GEOM_TOL or s < 3:
            return False
        from ..core import geom_extrude
        doc = _document()
        if doc.key != last["doc_key"]:
            return False
        geom_extrude.restore(doc, last["snap"])
        self._build(doc, last["center"], last["n"], r, s, last["start_dir"], last["cid"])
        doc.write(undo_key=None)
        last["radius"], last["sides"] = r, s
        if s != self.sides:
            self.sides = s
        STATE.set_vcb("vcb.radius", fmt_length(r))
        return True

    # -- geometry ------------------------------------------------------------------------------------
    def _build(self, doc, center, n, radius, sides, start_dir, cid=None):
        from ..core import entities, geom
        mw = doc.world()
        sc = mw.to_scale()
        k = ((abs(sc.x) + abs(sc.y) + abs(sc.z)) / 3.0) or 1.0
        inv = mw.inverted()
        pts_w = geom.circle_points(center, n, radius, sides, start_dir)
        pts = [inv @ p for p in pts_w]
        nl = (mw.to_3x3().inverted().transposed() @ n).normalized()
        if cid is None:
            cid = entities.new_curve_id(doc)
        res = geom.add_closed_shape(doc.bm, pts, None, curve_id=cid)
        c_local = inv @ center
        entities.set_curve_meta(doc, cid, {"kind": self.KIND, "center": [c_local.x, c_local.y, c_local.z],
                                           "normal": [nl.x, nl.y, nl.z], "radius": radius / k, "sides": sides})
        return cid

    def _commit(self, tc, radius, sides):
        from ..core import geom_extrude
        doc = _document()
        self._drop_last()
        snap = geom_extrude.snapshot(doc)
        center, n = self.center.copy(), self.n.copy()
        sd = self.start_dir.copy() if self.start_dir is not None else None
        cid = self._build(doc, center, n, radius, sides, sd)
        doc.write(undo_key=self.PREFIX + ".undo")
        self.last = {"doc_key": doc.key, "center": center, "n": n, "radius": radius, "sides": sides,
                     "start_dir": sd, "snap": snap, "cid": cid}
        STATE.last_action = LastAction(tool_id=self.meta.id, schema="radius", reapply=self._reapply)
        self.reset()
        STATE.locks.axis = ''
        self.update_status()
        STATE.set_vcb("vcb.radius", fmt_length(radius))
        return Result.IDLE

    # -- drawing -------------------------------------------------------------------------------------
    def draw_3d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None:
            return
        from ..core import geom
        if self.center is None:
            hp = self.hover_plane
            if hp is None or dc.region is None or dc.rv3d is None:
                return
            from ..core import viewutil
            r = viewutil.pixel_size_at(dc.region, dc.rv3d, hp[0]) * viewutil.ui_px(14)
            if r <= 0.0:
                return
            pts = geom.circle_points(hp[0], hp[1], r, 24)
            rgb = AXIS_COLOR.get(hp[2], colors.INF_PARALLEL)
            prims.lines(dc, [(pts[i], pts[(i + 1) % 24]) for i in range(24)], colors.rgba(rgb, 1.0), width=1.5,
                        depth=False)
            return
        if self.radius <= constants.GEOM_TOL:
            return
        pts = geom.circle_points(self.center, self.n, self.radius, self.sides, self.start_dir)
        k = len(pts)
        prims.lines(dc, [(pts[i], pts[(i + 1) % k]) for i in range(k)], colors.rgba(colors.EDGE, 1.0))
        prims.dotted(dc, self.center, pts[0], colors.rgba(colors.EDGE, 1.0))


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.circle.label", icon="ops.gpencil.primitive_circle", shortcut="C",
               cursor='PAINT_CROSS', vcb_label_key="vcb.radius", vcb_schema="radius"))
class CircleTool(ShapeTool):
    pass


def register():
    i18n.register_strings(STRINGS)
