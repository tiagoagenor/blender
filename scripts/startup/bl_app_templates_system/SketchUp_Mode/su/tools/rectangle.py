# SPDX-License-Identifier: GPL-2.0-or-later
"""Retângulo (owner: E). PLANO.md §6.2 (AC-RET-1..5), ROTEIRO_CASA passos 1, 6, 8, B1, B5.

Click the first corner, move, click the opposite corner (or press-drag-release, or type `L;W` Enter).
Plane of the rectangle:
  * an arrow key locks the plane by its NORMAL (↑ blue = horizontal, → red, ← green — leader decision
    AC-CIR-4, same as the SketchUp protractor), before or after the first click;
  * first corner on a face → the face's plane;
  * otherwise the plane follows the second corner: a face under the cursor that contains the first
    corner, or the axis plane through the first corner that contains an inferred point
    ("em pé automático"), else the horizontal plane through the first corner (a cursor above the
    horizon falls back to the vertical axis plane facing the camera).
Measurements: "Dimensões" `L;W` — the first value along the first axis of the plane (red, else green),
the second along the other; the signs follow the mouse quadrant, negative values flip. After the
rectangle is drawn, typing `L;W` re-sizes it (one "Ajustar" undo step).
The edges go through B's add_closed_shape (weld, split, auto faces: a rectangle on a face splits it or
makes a hole); one undo step per rectangle.
"""

import math

from mathutils import Vector
from mathutils import geometry as mgeo

from .. import colors, constants, i18n, registry
from ..core.state import STATE, LastAction, Locks
from .base import BaseTool, Result, ToolMeta, fmt_length, kind_of, make_query, tool, value_of, units

TOOL_ID = "su.rectangle"
LENGTH_KINDS = frozenset({"LENGTH", "DISTANCE", "NUMBER"})
SNAP_KINDS = frozenset({"ENDPOINT", "MIDPOINT", "INTERSECTION", "CENTER", "GUIDE_POINT", "ORIGIN", "ON_EDGE",
                        "ON_GUIDE", "ON_FACE"})
AXES = (Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, 1.0)))
LOCK_AXIS = {"AXIS_X": 0, "AXIS_Y": 1, "AXIS_Z": 2}
PLANE_TOL = 1e-4

STRINGS = {
    "tool.su.rectangle.label": {"pt_BR": "Retângulo", "en": "Rectangle"},
    "tool.su.rectangle.hint_start": {"pt_BR": "Selecione o primeiro canto.", "en": "Select first corner."},
    "tool.su.rectangle.hint_next": {"pt_BR": "Selecione o canto oposto ou digite as dimensões.",
                                    "en": "Select opposite corner or enter dimensions."},
    "tool.su.rectangle.undo": {"pt_BR": "Retângulo", "en": "Rectangle"},
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


def plane_axes(n):
    """(u, v) in-plane axes for normal n: the context axes in X, Y, Z order when n is an axis, else the
    horizontal direction of the plane and the one going up."""
    n = Vector(n).normalized()
    for i, ax in enumerate(AXES):
        if abs(abs(n.dot(ax)) - 1.0) < 1e-6:
            others = [AXES[j] for j in range(3) if j != i]
            return others[0].copy(), others[1].copy()
    u = AXES[2].cross(n)
    if u.length < 1e-9:
        u = AXES[0].copy()
    u.normalize()
    v = n.cross(u).normalized()
    if v.z < 0.0:
        v.negate()
    return u, v


def axis_normal(p1, p):
    """Normal of the axis plane through p1 that contains p (None: p is in general position or on an axis)."""
    d = Vector(p) - Vector(p1)
    comps = [abs(d.dot(ax)) for ax in AXES]
    zero = [i for i, c in enumerate(comps) if c <= PLANE_TOL]
    if len(zero) != 1:
        return None
    return AXES[zero[0]].copy()


def corners(p1, u, v, a, b):
    return [p1.copy(), p1 + u * a, p1 + u * a + v * b, p1 + v * b]


def _sign(x):
    return -1.0 if x < 0.0 else 1.0


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.rectangle.label", icon="ops.gpencil.primitive_box", shortcut="R",
               cursor='PAINT_CROSS', vcb_label_key="vcb.dimensions", vcb_schema="length2"))
class RectangleTool(BaseTool):

    def __init__(self):
        self.reset()
        self.last = None            # (doc_key, p1, u, v, n, a, b, snapshot) of the last rectangle

    def reset(self):
        self.p1 = None              # first corner (world)
        self.face_plane = None      # (co, n) when the first corner is on a face
        self.n = None               # current plane normal
        self.u = self.v = None
        self.a = self.b = 0.0       # signed sizes along u / v
        self.p2 = None

    # -- status --------------------------------------------------------------------------------------
    def _dims_text(self, a, b):
        u = registry.optional("core.units")
        sep = u.list_sep(units()) if u is not None and hasattr(u, "list_sep") else ";"
        return "{:s}{:s} {:s}".format(fmt_length(abs(a)), sep, fmt_length(abs(b)))

    def update_status(self):
        STATE.set_hint("tool.su.rectangle.hint_start" if self.p1 is None else "tool.su.rectangle.hint_next")
        if self.p1 is not None and self.p2 is not None:
            STATE.set_vcb(self.meta.vcb_label_key, self._dims_text(self.a, self.b))
        else:
            STATE.set_vcb(self.meta.vcb_label_key, STATE.vcb_value)

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
            geom_extrude.release(self.last[-1])
            self.last = None

    # -- inference -----------------------------------------------------------------------------------
    def _locked_normal(self):
        i = LOCK_AXIS.get(STATE.locks.axis)
        return AXES[i].copy() if i is not None else None

    def query_ctx(self, tc, xy):
        if self.p1 is None:
            # before the first click an arrow only chooses the plane: no axis line from nothing
            return make_query(tc, xy, locks=Locks())
        n = self._locked_normal()
        if n is not None:
            return make_query(tc, xy, plane=(self.p1.copy(), n), locks=Locks())
        if self.face_plane is not None:
            return make_query(tc, xy, plane=(self.face_plane[0].copy(), self.face_plane[1].copy()), locks=Locks())
        return make_query(tc, xy, locks=Locks())

    @staticmethod
    def _ray(tc, ev):
        if tc is None or tc.region is None or tc.rv3d is None or ev is None:
            return None
        from ..core import viewutil
        return viewutil.mouse_ray(tc.region, tc.rv3d, (ev.x, ev.y))

    @staticmethod
    def _ray_plane(ray, co, n):
        if ray is None:
            return None
        o, d = ray
        if abs(d.dot(n)) < 1e-9:
            return None
        p = mgeo.intersect_line_plane(o, o + d, co, n)
        if p is None or (p - o).dot(d) <= 0.0:
            return None
        return p

    def _resolve(self, tc, ev, inf):
        """Plane normal and second corner (on that plane) for the current inference."""
        p1 = self.p1
        p = _point(inf)
        ray = self._ray(tc, ev)
        n = self._locked_normal()
        if n is None and self.face_plane is not None:
            n = self.face_plane[1].copy()
        if n is not None:
            if p is None or inf.kind == "FREE":
                q = self._ray_plane(ray, p1, n)
                p = q if q is not None else p
            if p is None:
                return None, None
            return n, p - n * (p - p1).dot(n)
        if p is None:
            return None, None
        kind = inf.kind
        if kind == "ON_FACE" and inf.normal is not None and abs((p1 - p).dot(Vector(inf.normal))) <= PLANE_TOL:
            n = Vector(inf.normal).normalized()
            return n, p - n * (p - p1).dot(n)
        if kind in SNAP_KINDS or ray is None:
            n = axis_normal(p1, p)
            if n is not None:
                return n, p - n * (p - p1).dot(n)
            n = AXES[2].copy()
            q = self._ray_plane(ray, p1, n)
            return n, (q if q is not None else p - n * (p - p1).dot(n))
        # FREE: the horizontal plane through the first corner, or (cursor above it, looking up) the
        # vertical axis plane that faces the camera
        n = AXES[2].copy()
        q = self._ray_plane(ray, p1, n)
        if q is not None:
            return n, q
        d = ray[1]
        n = max((AXES[0], AXES[1]), key=lambda ax: abs(ax.dot(d))).copy()
        q = self._ray_plane(ray, p1, n)
        if q is None:
            return None, None
        return n, q

    def _track(self, tc, ev, inf):
        n, p2 = self._resolve(tc, ev, inf)
        if n is None:
            return
        self.n = n
        self.u, self.v = plane_axes(n)
        self.p2 = p2
        d = p2 - self.p1
        self.a, self.b = d.dot(self.u), d.dot(self.v)

    def move(self, tc, ev, inf):
        if self.p1 is not None:
            self._track(tc, ev, inf)
        self.update_status()
        return Result.RUNNING if self.p1 is not None else Result.IDLE

    def key(self, tc, ev):
        if ev.type in {'UP_ARROW', 'LEFT_ARROW', 'RIGHT_ARROW'} and ev.value == 'PRESS':
            if self.p1 is not None and self.p2 is not None:
                n = self._locked_normal()
                if n is not None:
                    self.n = n
                    self.u, self.v = plane_axes(n)
                    p2 = self.p2 - n * (self.p2 - self.p1).dot(n)
                    self.p2 = p2
                    d = p2 - self.p1
                    self.a, self.b = d.dot(self.u), d.dot(self.v)
            self.update_status()
            return Result.RUNNING if self.p1 is not None else Result.IDLE
        return Result.PASS

    # -- clicks --------------------------------------------------------------------------------------
    def press(self, tc, ev, inf):
        p = _point(inf)
        if self.p1 is None:
            if p is None:
                return Result.IDLE
            self.p1 = p
            self.face_plane = None
            if inf.kind == "ON_FACE" and inf.normal is not None:
                self.face_plane = (p.copy(), Vector(inf.normal).normalized())
            self.p2 = None
            self.a = self.b = 0.0
            self.update_status()
            return Result.RUNNING
        self._track(tc, ev, inf)
        if self.p2 is None or abs(self.a) <= constants.GEOM_TOL or abs(self.b) <= constants.GEOM_TOL:
            return Result.RUNNING            # degenerate: keep drawing
        return self._commit(tc, self.a, self.b)

    def release(self, tc, ev, inf):
        if self.p1 is None:
            return Result.IDLE
        if ev.is_drag_release:
            self._track(tc, ev, inf)
            if self.p2 is not None and abs(self.a) > constants.GEOM_TOL and abs(self.b) > constants.GEOM_TOL:
                return self._commit(tc, self.a, self.b)
        return Result.RUNNING

    # -- Measurements --------------------------------------------------------------------------------
    @staticmethod
    def _dims(values, a, b):
        """(a, b) from typed `L;W` (a missing value keeps the current size; signs follow the mouse)."""
        vals = [v for v in values]
        if not vals:
            return None
        out = []
        for i, cur in enumerate((a, b)):
            v = vals[i] if i < len(vals) else None
            if v is None or getattr(v, "value", 0.0) is None:
                out.append(cur)
                continue
            if kind_of(v) not in LENGTH_KINDS:
                return None
            out.append(value_of(v) * _sign(cur))
        return out

    def vcb(self, tc, values):
        if self.p1 is None:
            return Result.PASS
        if self.n is None:
            n = self._locked_normal()
            if n is None:
                n = self.face_plane[1].copy() if self.face_plane is not None else AXES[2].copy()
            self.n = n
            self.u, self.v = plane_axes(n)
        dims = self._dims(values, self.a, self.b)
        if dims is None or abs(dims[0]) <= constants.GEOM_TOL or abs(dims[1]) <= constants.GEOM_TOL:
            STATE.vcb_error = True
            return Result.RUNNING
        return self._commit(tc, dims[0], dims[1])

    def _reapply(self, values):
        """Idle retype: rebuild the last rectangle with new dimensions (geometry restored first)."""
        if self.last is None:
            return False
        key, p1, u, v, n, a, b, snap = self.last
        dims = self._dims(values, a, b)
        if dims is None or abs(dims[0]) <= constants.GEOM_TOL or abs(dims[1]) <= constants.GEOM_TOL:
            return False
        from ..core import geom_extrude
        doc = _document()
        if doc.key != key:
            return False
        geom_extrude.restore(doc, snap)
        self._build(doc, p1, u, v, n, dims[0], dims[1], None)
        doc.write(undo_key=None)
        self.last = (key, p1, u, v, n, dims[0], dims[1], snap)
        STATE.set_vcb(self.meta.vcb_label_key, self._dims_text(dims[0], dims[1]))
        return True

    # -- geometry ------------------------------------------------------------------------------------
    @staticmethod
    def _build(doc, p1, u, v, n, a, b, rv3d):
        from ..core import geom
        inv = doc.world().inverted()
        pts = [inv @ c for c in corners(p1, u, v, a, b)]
        res = geom.add_closed_shape(doc.bm, pts, None)
        faces = [f for f in res.new_faces if f.is_valid]
        # a standalone vertical rectangle faces the camera (horizontal ones: B orients them −Z)
        if rv3d is not None and abs(n.z) < 1.0 - 1e-6:
            alone = all(len(e.link_faces) == 1 for f in faces for e in f.edges)
            if faces and alone:
                view = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))
                nl = (doc.world().to_3x3().inverted().transposed() @ n).normalized()
                target = -nl if nl.dot(view) > 0.0 else nl
                for f in faces:
                    geom.orient_face(f, target)
        return res

    def _commit(self, tc, a, b):
        from ..core import geom_extrude
        doc = _document()
        self._drop_last()
        snap = geom_extrude.snapshot(doc)
        p1, u, v, n = self.p1.copy(), self.u.copy(), self.v.copy(), self.n.copy()
        self._build(doc, p1, u, v, n, a, b, tc.rv3d if tc is not None else None)
        doc.write(undo_key="tool.su.rectangle.undo")
        self.last = (doc.key, p1, u, v, n, a, b, snap)
        STATE.last_action = LastAction(tool_id=TOOL_ID, schema=self.meta.vcb_schema, reapply=self._reapply)
        self.reset()
        STATE.locks.axis = ''
        self.update_status()
        STATE.set_vcb(self.meta.vcb_label_key, self._dims_text(a, b))
        return Result.IDLE

    # -- drawing -------------------------------------------------------------------------------------
    def draw_3d(self, dc):
        if self.p1 is None or self.p2 is None or self.u is None:
            return
        prims = registry.optional("draw.prims")
        if prims is None:
            return
        cs = corners(self.p1, self.u, self.v, self.a, self.b)
        segs = [(cs[i], cs[(i + 1) % 4]) for i in range(4)]
        prims.lines(dc, segs, colors.rgba(colors.EDGE, 1.0), width=1.0)
        if abs(self.a) > constants.GEOM_TOL and abs(abs(self.a) - abs(self.b)) <= 1e-3 * max(abs(self.a), 1e-9):
            prims.dashed(dc, cs[0], cs[2], colors.rgba(colors.SELECTION, 1.0))     # "Quadrado"


def register():
    i18n.register_strings(STRINGS)
