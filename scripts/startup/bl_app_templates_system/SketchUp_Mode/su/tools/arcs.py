# SPDX-License-Identifier: GPL-2.0-or-later
"""Arco de dois pontos (owner: E). PLANO.md §6.2 (AC-ARC-1).

Click the start, click the end (or type the chord length), move to set the bulge ("Curvatura") and click,
or type it; `Nr` gives the radius, `Ns` the segments (default 12). Retyping after the arc rebuilds it
("Ajustar"). Plane: an arrow locks its NORMAL (↑ horizontal, → red, ← green); a face under the first click
gives its plane; else horizontal through the start — when the chord leaves that plane, the axis plane
containing the chord nearest the cursor. The edges are one curve entity (kind "arc", center/radius in the
metadata). One undo step per arc.
"""

import math

from mathutils import Vector

from .. import colors, constants, i18n, registry
from ..core.state import STATE, LastAction, Locks
from .base import BaseTool, Result, ToolMeta, fmt_length, kind_of, make_query, tool, value_of

TOOL_ID = "su.arc2"
AXES = (Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, 1.0)))
LOCK_AXIS = {"AXIS_X": 0, "AXIS_Y": 1, "AXIS_Z": 2}

STRINGS = {
    "tool.su.arc2.label": {"pt_BR": "Arco de dois pontos", "en": "2 Point Arc"},
    "tool.su.arc2.hint_start": {"pt_BR": "Selecione o ponto inicial.", "en": "Select start point."},
    "tool.su.arc2.hint_end": {"pt_BR": "Selecione o ponto final.", "en": "Select end point."},
    "tool.su.arc2.hint_bulge": {"pt_BR": "Selecione a curvatura.", "en": "Select bulge."},
    "tool.su.arc2.undo": {"pt_BR": "Arco", "en": "Arc"},
    "tool.su.arc.label": {"pt_BR": "Arco", "en": "Arc"},
    "tool.su.arc.hint_center": {"pt_BR": "Selecione o ponto central.", "en": "Select center point."},
    "tool.su.arc.hint_start": {"pt_BR": "Selecione o ponto inicial.", "en": "Select start point."},
    "tool.su.arc.hint_end": {"pt_BR": "Selecione o ponto final ou digite o ângulo.", "en": "Select end point or enter angle."},
    "tool.su.arc.undo": {"pt_BR": "Arco", "en": "Arc"},
    "tool.su.pie.label": {"pt_BR": "Pizza", "en": "Pie"},
    "tool.su.pie.hint_center": {"pt_BR": "Selecione o ponto central.", "en": "Select center point."},
    "tool.su.pie.hint_start": {"pt_BR": "Selecione o ponto inicial.", "en": "Select start point."},
    "tool.su.pie.hint_end": {"pt_BR": "Selecione o ponto final ou digite o ângulo.", "en": "Select end point or enter angle."},
    "tool.su.pie.undo": {"pt_BR": "Pizza", "en": "Pie"},
    "tool.su.arc3.label": {"pt_BR": "Arco de três pontos", "en": "3 Point Arc"},
    "tool.su.arc3.hint_start": {"pt_BR": "Selecione o ponto inicial.", "en": "Select start point."},
    "tool.su.arc3.hint_pivot": {"pt_BR": "Selecione o segundo ponto do arco.", "en": "Select second point on arc."},
    "tool.su.arc3.hint_end": {"pt_BR": "Selecione o ponto final.", "en": "Select end point."},
    "tool.su.arc3.undo": {"pt_BR": "Arco de três pontos", "en": "3 Point Arc"},
}


def _document():
    document = registry.optional("core.document")
    if document is None:
        raise RuntimeError("core.document (B) not available")
    return document.active()


def _point(inf):
    if inf is None or inf.kind == "NONE":
        return None
    return Vector(inf.point)


def arc_geometry(a, b, bulge, n, segments):
    """(points, center, radius) of the two-point arc."""
    from ..core import geom
    pts = geom.arc_from_bulge(a, b, bulge, n, segments)
    chord = b - a
    half = chord.length * 0.5
    side = n.cross(chord).normalized()
    apex = (a + b) * 0.5 + side * bulge
    radius = (half * half + bulge * bulge) / (2.0 * abs(bulge))
    center = apex - side * math.copysign(radius, bulge)
    return pts, center, radius


def bulge_for_radius(r, half, sign):
    if r < half - constants.GEOM_TOL:
        return None
    r = max(r, half)
    return sign * (r - math.sqrt(max(r * r - half * half, 0.0)))


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.arc2.label", icon="ops.gpencil.primitive_curve", shortcut="A",
               cursor='PAINT_CROSS', vcb_label_key="vcb.bulge", vcb_schema="arc"))
class Arc2Tool(BaseTool):

    def __init__(self):
        self.segments = constants.ARC_SEGMENTS
        self.last = None
        self.reset()

    def reset(self):
        self.a = None
        self.b = None
        self.n = None              # plane normal
        self.cur = None            # cursor point
        self.bulge = 0.0

    # -- status --------------------------------------------------------------------------------------
    def update_status(self):
        if self.a is None:
            STATE.set_hint("tool.su.arc2.hint_start")
            STATE.set_vcb("vcb.length", STATE.vcb_value)
        elif self.b is None:
            STATE.set_hint("tool.su.arc2.hint_end")
            STATE.set_vcb("vcb.length", fmt_length((self.cur - self.a).length) if self.cur is not None else "")
        else:
            STATE.set_hint("tool.su.arc2.hint_bulge")
            STATE.set_vcb("vcb.bulge", fmt_length(abs(self.bulge)))

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
    def _locked(self):
        i = LOCK_AXIS.get(STATE.locks.axis)
        return AXES[i].copy() if i is not None else None

    def query_ctx(self, tc, xy):
        if self.a is None:
            return make_query(tc, xy, locks=Locks())
        if self.b is None:
            return make_query(tc, xy, anchor=self.a.copy(), locks=Locks())
        return make_query(tc, xy, plane=(self.a.copy(), self.n.copy()), locks=Locks())

    def _bulge_plane(self, p):
        """Plane normal containing the chord (prefers the first-click plane)."""
        chord = self.b - self.a
        lk = self._locked()
        for cand in ([lk] if lk is not None else []) + [self.n]:
            if cand is not None and abs(cand.dot(chord)) <= 1e-6 * max(chord.length, 1.0):
                return cand.normalized()
        axes = [ax for ax in AXES if abs(ax.dot(chord)) <= 1e-6 * max(chord.length, 1.0)]
        if axes:
            if p is not None:
                return min(axes, key=lambda ax: abs((p - self.a).dot(ax))).copy()
            return axes[0].copy()
        n = chord.cross(AXES[2])
        return n.normalized() if n.length > 1e-9 else AXES[1].copy()

    def _track(self, inf):
        p = _point(inf)
        if p is None:
            return
        self.cur = p
        if self.b is not None:
            n = self.n
            p = p - n * (p - self.a).dot(n)
            chord = self.b - self.a
            side = n.cross(chord).normalized()
            self.bulge = (p - (self.a + self.b) * 0.5).dot(side)

    def move(self, tc, ev, inf):
        if self.a is None:
            return Result.IDLE
        self._track(inf)
        self.update_status()
        return Result.RUNNING

    # -- clicks --------------------------------------------------------------------------------------
    def press(self, tc, ev, inf):
        p = _point(inf)
        if self.a is None:
            if p is None:
                return Result.IDLE
            self.a = p
            lk = self._locked()
            if lk is not None:
                self.n = lk
            elif inf.kind == "ON_FACE" and inf.normal is not None:
                self.n = Vector(inf.normal).normalized()
            else:
                self.n = AXES[2].copy()
            self.cur = p
            self.update_status()
            return Result.RUNNING
        if self.b is None:
            if p is None or (p - self.a).length <= constants.GEOM_TOL:
                return Result.RUNNING
            self._set_end(p)
            return Result.RUNNING
        self._track(inf)
        if abs(self.bulge) <= constants.GEOM_TOL:
            return Result.RUNNING
        return self._commit(self.bulge, self.segments)

    def _set_end(self, p):
        self.b = p
        self.n = self._bulge_plane(self.cur)
        self.bulge = 0.0
        self.update_status()

    def release(self, tc, ev, inf):
        if self.a is None:
            return Result.IDLE
        if ev.is_drag_release and self.b is None:
            p = _point(inf)
            if p is not None and (p - self.a).length > constants.GEOM_TOL:
                self._set_end(p)
        return Result.RUNNING

    # -- Measurements --------------------------------------------------------------------------------
    def _values(self, values, half, bulge, segments):
        """(bulge, segments) from typed values, or None."""
        if not values or values[0] is None:
            return None
        v = values[0]
        k = kind_of(v)
        if k in {"SEGMENTS", "SIDES"}:
            s = int(value_of(v))
            return (bulge, s) if s >= 1 else None
        if k == "RADIUS":
            b = bulge_for_radius(value_of(v), half, 1.0 if bulge >= 0 else -1.0)
            return (b, segments) if b is not None else None
        if k in {"LENGTH", "NUMBER", "DISTANCE"}:
            x = value_of(v)
            return (x * (1.0 if bulge >= 0 else -1.0), segments)
        return None

    def vcb(self, tc, values):
        if self.a is None:
            return Result.PASS
        if self.b is None:
            if not values or values[0] is None or kind_of(values[0]) not in {"LENGTH", "NUMBER", "DISTANCE"}:
                STATE.vcb_error = True
                return Result.RUNNING
            d = (self.cur - self.a) if self.cur is not None else Vector()
            if d.length <= constants.GEOM_TOL or value_of(values[0]) <= constants.GEOM_TOL:
                STATE.vcb_error = True
                return Result.RUNNING
            self.cur = self.a + d.normalized() * value_of(values[0])
            self._set_end(self.cur.copy())
            return Result.RUNNING
        half = (self.b - self.a).length * 0.5
        if values and values[0] is not None and kind_of(values[0]) in {"SEGMENTS", "SIDES"}:
            s = int(value_of(values[0]))
            if s < 1:
                STATE.vcb_error = True
            else:
                self.segments = s
            return Result.RUNNING
        r = self._values(values, half, self.bulge, self.segments)
        if r is None or abs(r[0]) <= constants.GEOM_TOL:
            STATE.vcb_error = True
            return Result.RUNNING
        self.segments = r[1]
        return self._commit(r[0], r[1])

    def _reapply(self, values):
        last = self.last
        if last is None:
            return False
        half = (last["b"] - last["a"]).length * 0.5
        r = self._values(values, half, last["bulge"], last["segments"])
        if r is None or abs(r[0]) <= constants.GEOM_TOL:
            return False
        from ..core import geom_extrude
        doc = _document()
        if doc.key != last["doc_key"]:
            return False
        geom_extrude.restore(doc, last["snap"])
        self._build(doc, last["a"], last["b"], r[0], last["n"], r[1], last["cid"])
        doc.write(undo_key=None)
        last["bulge"], last["segments"] = r
        self.segments = r[1]
        STATE.set_vcb("vcb.bulge", fmt_length(abs(r[0])))
        return True

    # -- geometry ------------------------------------------------------------------------------------
    @staticmethod
    def _build(doc, a, b, bulge, n, segments, cid=None):
        from ..core import entities, geom
        mw = doc.world()
        inv = mw.inverted()
        pts, center, radius = arc_geometry(a, b, bulge, n, segments)
        if cid is None:
            cid = entities.new_curve_id(doc)
        geom.add_polyline(doc.bm, [inv @ p for p in pts], False, curve_id=cid)
        sc = mw.to_scale()
        k = ((abs(sc.x) + abs(sc.y) + abs(sc.z)) / 3.0) or 1.0
        c = inv @ center
        nl = (mw.to_3x3().inverted().transposed() @ n).normalized()
        entities.set_curve_meta(doc, cid, {"kind": "arc", "center": [c.x, c.y, c.z], "normal": [nl.x, nl.y, nl.z],
                                           "radius": radius / k, "segments": segments})
        return cid

    def _commit(self, bulge, segments):
        from ..core import geom_extrude
        doc = _document()
        self._drop_last()
        snap = geom_extrude.snapshot(doc)
        a, b, n = self.a.copy(), self.b.copy(), self.n.copy()
        cid = self._build(doc, a, b, bulge, n, segments)
        doc.write(undo_key="tool.su.arc2.undo")
        self.last = {"doc_key": doc.key, "a": a, "b": b, "n": n, "bulge": bulge, "segments": segments,
                     "snap": snap, "cid": cid}
        STATE.last_action = LastAction(tool_id=TOOL_ID, schema="arc", reapply=self._reapply)
        self.reset()
        STATE.locks.axis = ''
        self.update_status()
        STATE.set_vcb("vcb.bulge", fmt_length(abs(bulge)))
        return Result.IDLE

    # -- drawing -------------------------------------------------------------------------------------
    def draw_3d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None or self.a is None:
            return
        rgba = colors.rgba(colors.EDGE, 1.0)
        if self.b is None:
            if self.cur is not None:
                prims.line(dc, self.a, self.cur, rgba)
            return
        if abs(self.bulge) <= constants.GEOM_TOL:
            prims.line(dc, self.a, self.b, rgba)
            return
        pts, _c, _r = arc_geometry(self.a, self.b, self.bulge, self.n, self.segments)
        prims.lines(dc, list(zip(pts, pts[1:])), rgba)


ARC_TOOL_ID = "su.arc"
_ARC_META = ToolMeta(id=ARC_TOOL_ID, label_key="tool.su.arc.label", icon="ops.gpencil.primitive_arc",
                     cursor='PAINT_CROSS', vcb_label_key="vcb.radius", vcb_schema="arc", priority='P1')


@tool(_ARC_META)
class ArcCenterTool(BaseTool):
    """Arco (centro), P1: center (plane gizmo like Círculo: arrow = normal lock, face, ground), start point
    (radius; typed length), end point (angle; 15° snap; typed angle in degrees). `Ns` = segments, typed
    before the start point (the angle step parses angles only)."""

    BASE_META = _ARC_META
    PREFIX = "tool.su.arc"
    PIE = False

    def __init__(self):
        self.segments = constants.ARC_SEGMENTS
        self.reset()

    def reset(self):
        self.c = None
        self.n = None
        self.s = None             # start point
        self.cur = None
        self.angle = 0.0
        self._schema("arc", "vcb.radius")

    def _schema(self, schema, label):
        from dataclasses import replace
        self.meta = replace(self.BASE_META, vcb_schema=schema, vcb_label_key=label)   # instance override

    def update_status(self):
        if self.c is None:
            STATE.set_hint(self.PREFIX + ".hint_center")
            STATE.set_vcb("vcb.radius", STATE.vcb_value)
        elif self.s is None:
            STATE.set_hint(self.PREFIX + ".hint_start")
            r = (self.cur - self.c).length if self.cur is not None else 0.0
            STATE.set_vcb("vcb.radius", fmt_length(r))
        else:
            STATE.set_hint(self.PREFIX + ".hint_end")
            from .base import units
            u = registry.optional("core.units")
            txt = u.format_angle(abs(self.angle), units()) if u is not None else "{:.1f}".format(math.degrees(abs(self.angle)))
            STATE.set_vcb("vcb.angle", txt)

    def activate(self, tc):
        self.reset()
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)

    def cancel(self, tc):
        self.reset()
        STATE.locks.axis = ''
        self.update_status()

    def query_ctx(self, tc, xy):
        if self.c is None:
            return make_query(tc, xy, locks=Locks())
        return make_query(tc, xy, plane=(self.c.copy(), self.n.copy()), locks=Locks())

    def _plane_at(self, inf):
        lk = {"AXIS_X": 0, "AXIS_Y": 1, "AXIS_Z": 2}.get(STATE.locks.axis)
        if lk is not None:
            return AXES[lk].copy()
        if inf is not None and inf.kind == "ON_FACE" and inf.normal is not None:
            return Vector(inf.normal).normalized()
        return AXES[2].copy()

    def _on_plane(self, inf):
        p = _point(inf)
        if p is None:
            return None
        return p - self.n * (p - self.c).dot(self.n)

    def _angle_to(self, p):
        r0 = (self.s - self.c).normalized()
        v = p - self.c
        if v.length <= constants.GEOM_TOL:
            return self.angle
        a = math.atan2(self.n.cross(r0).dot(v), r0.dot(v))
        # continuous sweep: keep the previous turn direction past ±180°
        if self.angle > math.pi / 2 and a < 0:
            a += 2 * math.pi
        elif self.angle < -math.pi / 2 and a > 0:
            a -= 2 * math.pi
        from .base import units
        u = units()
        if getattr(u, "angle_snap", True):
            step = math.radians(getattr(u, "angle_snap_deg", 15.0) or 15.0)
            k = round(a / step)
            if abs(a - k * step) <= math.radians(1.5):
                a = k * step
        return a

    def move(self, tc, ev, inf):
        if self.c is None:
            return Result.IDLE
        p = self._on_plane(inf)
        if p is not None:
            self.cur = p
            if self.s is not None:
                self.angle = self._angle_to(p)
        self.update_status()
        return Result.RUNNING

    def press(self, tc, ev, inf):
        p = _point(inf)
        if self.c is None:
            if p is None:
                return Result.IDLE
            self.c, self.n = p, self._plane_at(inf)
            self.cur = p
            self.update_status()
            return Result.RUNNING
        q = self._on_plane(inf)
        if self.s is None:
            if q is None or (q - self.c).length <= constants.GEOM_TOL:
                return Result.RUNNING
            self._set_start(q)
            return Result.RUNNING
        if q is not None:
            self.angle = self._angle_to(q)
        if abs(self.angle) <= 1e-6:
            return Result.RUNNING
        return self._commit(self.angle)

    def _set_start(self, q):
        self.s = q
        self.angle = 0.0
        self._schema("angle", "vcb.angle")
        self.update_status()

    def release(self, tc, ev, inf):
        return Result.RUNNING if self.c is not None else Result.IDLE

    def vcb(self, tc, values):
        if self.c is None or not values or values[0] is None:
            return Result.PASS
        v = values[0]
        k = kind_of(v)
        if k in {"SEGMENTS", "SIDES"}:
            n = int(value_of(v))
            if n >= 1:
                self.segments = n
            return Result.RUNNING
        if self.s is None:
            if k not in {"LENGTH", "RADIUS", "NUMBER"} or value_of(v) <= constants.GEOM_TOL:
                STATE.vcb_error = True
                return Result.RUNNING
            d = (self.cur - self.c) if self.cur is not None else Vector()
            if d.length <= constants.GEOM_TOL:
                d = self.n.orthogonal()
            self._set_start(self.c + d.normalized() * value_of(v))
            return Result.RUNNING
        if k not in {"ANGLE", "NUMBER"}:
            STATE.vcb_error = True
            return Result.RUNNING
        a = value_of(v) if k == "ANGLE" else math.radians(value_of(v))
        if self.angle < 0:
            a = -abs(a)
        if abs(a) <= 1e-6:
            STATE.vcb_error = True
            return Result.RUNNING
        return self._commit(a)

    def _commit(self, angle):
        from ..core import entities, geom
        doc = _document()
        mw = doc.world()
        inv = mw.inverted()
        n = self.n if angle > 0 else -self.n
        pts = geom.arc_points(self.c, n, self.s, abs(angle), self.segments)
        cid = entities.new_curve_id(doc)
        geom.add_polyline(doc.bm, [inv @ p for p in pts], False, curve_id=cid)
        if self.PIE:                                  # Pizza: the two radii close the face
            geom.add_edge(doc.bm, inv @ self.c, inv @ pts[0])
            geom.add_edge(doc.bm, inv @ pts[-1], inv @ self.c)
        sc = mw.to_scale()
        k = ((abs(sc.x) + abs(sc.y) + abs(sc.z)) / 3.0) or 1.0
        c = inv @ self.c
        nl = (mw.to_3x3().inverted().transposed() @ self.n).normalized()
        entities.set_curve_meta(doc, cid, {"kind": "arc", "center": [c.x, c.y, c.z], "normal": [nl.x, nl.y, nl.z],
                                           "radius": (self.s - self.c).length / k, "segments": self.segments})
        doc.write(undo_key=self.PREFIX + ".undo")
        self.reset()
        STATE.locks.axis = ''
        self.update_status()
        u = registry.optional("core.units")
        from .base import units
        STATE.set_vcb("vcb.angle", u.format_angle(abs(angle), units()) if u is not None
                      else "{:.1f}".format(math.degrees(abs(angle))))      # the last value stays visible
        return Result.IDLE

    def draw_3d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None or self.c is None:
            return
        rgba = colors.rgba(colors.EDGE, 1.0)
        if self.s is None:
            if self.cur is not None:
                prims.dotted(dc, self.c, self.cur, rgba)
            return
        prims.dotted(dc, self.c, self.s, rgba)
        if abs(self.angle) > 1e-6:
            from ..core import geom
            n = self.n if self.angle > 0 else -self.n
            pts = geom.arc_points(self.c, n, self.s, abs(self.angle), self.segments)
            prims.lines(dc, list(zip(pts, pts[1:])), rgba)
            if self.PIE:
                prims.line(dc, self.c, pts[-1], rgba)



PIE_TOOL_ID = "su.pie"
_PIE_META = ToolMeta(id=PIE_TOOL_ID, label_key="tool.su.pie.label", icon="ops.gpencil.edit_bend",
                     cursor='PAINT_CROSS', vcb_label_key="vcb.radius", vcb_schema="arc", priority='P1')


@tool(_PIE_META)
class PieTool(ArcCenterTool):
    """Pizza (promoted from P2): Arco (centro) closed by the two radii → a face (sector)."""
    BASE_META = _PIE_META
    PREFIX = "tool.su.pie"
    PIE = True


ARC3_TOOL_ID = "su.arc3"


def circle_through(a, b, c):
    """(center, normal) of the circle through three points, or None when they are collinear."""
    ab, ac = b - a, c - a
    n = ab.cross(ac)
    if n.length <= 1e-9 * max(ab.length * ac.length, 1e-12):
        return None
    center = a + (n.cross(ab) * ac.length_squared + ac.cross(n) * ab.length_squared) / (2.0 * n.length_squared)
    return center, n.normalized()


def arc3_points(a, b, c, segments):
    """Points of the arc from a through b to c (and its center/radius), or None."""
    r = circle_through(a, b, c)
    if r is None:
        return None
    center, n = r                     # a → b → c runs counter-clockwise about n
    u = (a - center).normalized()
    v = n.cross(u)
    w = c - center
    sweep = math.atan2(w.dot(v), w.dot(u))
    if sweep <= 0.0:
        sweep += 2.0 * math.pi
    from ..core import geom
    return geom.arc_points(center, n, a, sweep, segments), center, (a - center).length, n


@tool(ToolMeta(id=ARC3_TOOL_ID, label_key="tool.su.arc3.label", icon="ops.mesh.spin", cursor='PAINT_CROSS',
               vcb_label_key="vcb.segments", vcb_schema="arc", priority='P1'))
class Arc3Tool(BaseTool):
    """Arco de três pontos (promoted from P2): start, a point the arc passes through, end. `Ns` = segments
    (any time before the last click)."""

    def __init__(self):
        self.segments = constants.ARC_SEGMENTS
        self.reset()

    def reset(self):
        self.a = self.b = None
        self.cur = None

    def update_status(self):
        key = "hint_start" if self.a is None else ("hint_pivot" if self.b is None else "hint_end")
        STATE.set_hint("tool.su.arc3." + key)
        STATE.set_vcb("vcb.segments", str(self.segments))

    def activate(self, tc):
        self.reset()
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)

    def cancel(self, tc):
        self.reset()
        self.update_status()

    def query_ctx(self, tc, xy):
        anchor = self.b if self.b is not None else self.a
        return make_query(tc, xy, anchor=anchor.copy() if anchor is not None else None)

    def move(self, tc, ev, inf):
        if self.a is None:
            return Result.IDLE
        p = _point(inf)
        if p is not None:
            self.cur = p
        self.update_status()
        return Result.RUNNING

    def press(self, tc, ev, inf):
        p = _point(inf)
        if p is None:
            return Result.RUNNING if self.a is not None else Result.IDLE
        self.cur = p
        if self.a is None:
            self.a = p
            self.update_status()
            return Result.RUNNING
        if self.b is None:
            if (p - self.a).length > constants.GEOM_TOL:
                self.b = p
            self.update_status()
            return Result.RUNNING
        if arc3_points(self.a, self.b, p, self.segments) is None:
            return Result.RUNNING
        return self._commit(p)

    def release(self, tc, ev, inf):
        return Result.RUNNING if self.a is not None else Result.IDLE

    def vcb(self, tc, values):
        if not values or values[0] is None:
            return Result.PASS
        v = values[0]
        if kind_of(v) in {"SEGMENTS", "SIDES", "NUMBER"} or (kind_of(v) == "LENGTH" and self.a is None):
            n = int(round(value_of(v)))
            if n >= 1:
                self.segments = n
                self.update_status()
                return Result.RUNNING if self.a is not None else Result.IDLE
        STATE.vcb_error = True
        return Result.RUNNING if self.a is not None else Result.IDLE

    def _commit(self, c):
        from ..core import entities, geom
        doc = _document()
        mw = doc.world()
        inv = mw.inverted()
        pts, center, radius, n = arc3_points(self.a, self.b, c, self.segments)
        cid = entities.new_curve_id(doc)
        geom.add_polyline(doc.bm, [inv @ p for p in pts], False, curve_id=cid)
        sc = mw.to_scale()
        k = ((abs(sc.x) + abs(sc.y) + abs(sc.z)) / 3.0) or 1.0
        cl = inv @ center
        nl = (mw.to_3x3().inverted().transposed() @ n).normalized()
        entities.set_curve_meta(doc, cid, {"kind": "arc", "center": [cl.x, cl.y, cl.z], "normal": [nl.x, nl.y, nl.z],
                                           "radius": radius / k, "segments": self.segments})
        doc.write(undo_key="tool.su.arc3.undo")
        self.reset()
        self.update_status()
        return Result.IDLE

    def draw_3d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None or self.a is None or self.cur is None:
            return
        rgba = colors.rgba(colors.EDGE, 1.0)
        if self.b is None:
            prims.line(dc, self.a, self.cur, rgba)
            return
        r = arc3_points(self.a, self.b, self.cur, self.segments)
        if r is None:
            prims.lines(dc, [(self.a, self.b), (self.b, self.cur)], rgba)
            return
        prims.lines(dc, list(zip(r[0], r[0][1:])), rgba)


def register():
    i18n.register_strings(STRINGS)
