# SPDX-License-Identifier: GPL-2.0-or-later
"""Inference engine (owner: C). Contract: PLANO.md §2.4, behaviour §3.2, acceptance §6.4 (AC-INF-*).

    q = QueryCtx(region, rv3d, xy, anchor=..., ...)
    inf = ENGINE.query(q)            # -> state.Inference
    ENGINE.acquire_tick(inf, t)      # hover ≥ 0.3 s on a point → reference point ("Do ponto")
    lock_from_arrow('UP_ARROW', STATE.locks)
    hover_plane(q) -> (co, normal, axis)   # plane gizmo before the first click ('X'|'Y'|'Z'|'')

Pipeline per query (no cache in v1): view ray → spatial.ray_cast (skip = moving faces) →
spatial.projection → candidates with occlusion → priority
    ENDPOINT > MIDPOINT > INTERSECTION > CENTER > GUIDE_POINT > ORIGIN > ON_EDGE > ON_GUIDE
    > linear constraint (axes / parallel / perpendicular / perpendicular to face / from point) > ON_FACE > FREE.
Linear constraints start at `anchor` (the tool's last click). Constraints: `q.line` (co, dir[, linear])
or a lock (arrow → axis, Shift → the locked inference) turns the result into a point ON that line;
`q.plane` (co, normal) projects the result onto the plane.
Hysteresis: the previous target (q.previous or the engine's last result) is kept while the cursor is
within SNAP_* × SNAP_RELEASE_FACTOR (other targets need SNAP_*).
Group context: points of a document other than the edited one/root → magenta + "no grupo"
(Inference.in_context = 'GROUP' | 'COMPONENT').
Guides (G) register a provider: set_guides_provider(fn) with fn() -> {'points': [Vector], 'lines': [(co, dir)]}.

Flags (BaseTool.inference_flags / QueryCtx.flags): see DEFAULT_FLAGS.
"""

import math
import sys
from dataclasses import dataclass
from typing import Optional

from mathutils import Vector

from .. import constants as K
from . import spatial
from .state import Inference, STATE

ORDER = 130

DEFAULT_FLAGS = frozenset((
    "POINTS", "MIDPOINTS", "INTERSECTIONS", "CENTERS", "GUIDES", "ORIGIN", "EDGES", "FACES",
    "AXES", "PARALLEL", "PERP_FACE", "FROM_POINT",
))
POINT_KINDS = ("ENDPOINT", "MIDPOINT", "INTERSECTION", "CENTER", "GUIDE_POINT", "ORIGIN")
PRIORITY = {"ENDPOINT": 0, "MIDPOINT": 1, "INTERSECTION": 2, "CENTER": 3, "GUIDE_POINT": 4, "ORIGIN": 5,
            "ON_EDGE": 6, "ON_GUIDE": 7, "LINEAR": 8, "ON_FACE": 9, "FREE": 10, "NONE": 11}
AXIS_NAMES = ("AXIS_X", "AXIS_Y", "AXIS_Z")
ARROW_LOCKS = {"RIGHT_ARROW": "AXIS_X", "LEFT_ARROW": "AXIS_Y", "UP_ARROW": "AXIS_Z", "DOWN_ARROW": "PARALLEL"}
ALIGN_COS = math.cos(math.radians(0.05))     # direction "is" an axis
FREE_MAX_FACTOR = 20.0                       # free point on the anchor's horizontal plane: max distance / eye distance
TOOLTIP_KEYS = {
    "ENDPOINT": "inf.endpoint", "MIDPOINT": "inf.midpoint", "ON_EDGE": "inf.on_edge", "ON_FACE": "inf.on_face",
    "INTERSECTION": "inf.intersection", "CENTER": "inf.center", "ORIGIN": "inf.origin",
    "GUIDE_POINT": "inf.guide_point", "ON_GUIDE": "inf.on_guide",
    "AXIS_X": "inf.axis_x", "AXIS_Y": "inf.axis_y", "AXIS_Z": "inf.axis_z", "PARALLEL": "inf.parallel",
    "PERPENDICULAR": "inf.perpendicular", "PERP_FACE": "inf.perp_face", "FROM_POINT": "inf.from_point",
    "TANGENT": "inf.tangent",
}


@dataclass
class QueryCtx:
    region: object
    rv3d: object
    xy: tuple
    depsgraph: object = None
    anchor: Optional[Vector] = None          # last click of the tool (start of linear inferences)
    anchor_normal: Optional[Vector] = None   # normal of the face under the anchor (PERP_FACE)
    plane: Optional[tuple] = None            # (co, normal): result constrained to this plane
    line: Optional[tuple] = None             # (co, dir[, linear]): result constrained to this line
    flags: frozenset = DEFAULT_FLAGS
    exclude: frozenset = frozenset()         # spatial exclude (doc keys / (doc_key, vert))
    skip: Optional[dict] = None              # ray_cast skip {doc_key: {face_idx_orig}}
    locks: object = None                     # state.Locks (default STATE.locks)
    previous: Optional[Inference] = None     # previous result (hysteresis); default = engine's last


_guides_provider = [None]


def set_guides_provider(fn):
    """G: fn() -> {'points': [Vector], 'lines': [(co, dir)]} (world space)."""
    _guides_provider[0] = fn


def _guides():
    fn = _guides_provider[0]
    if fn is None:
        return [], []
    try:
        g = fn() or {}
    except Exception:
        from .. import perf
        perf.exception("inference: guides provider failed")
        return [], []
    return [Vector(p) for p in g.get("points", ())], [(Vector(c), Vector(d).normalized()) for c, d in g.get("lines", ())
                                                      if Vector(d).length > 1e-12]


# ---------------------------------------------------------------------------------------------- context
def _sibling(name):
    pkg = __name__.rpartition(".")[0]
    return sys.modules.get(pkg + "." + name)


def _context_object():
    ec = _sibling("edit_context")
    if ec is not None and hasattr(ec, "current_object"):
        try:
            return ec.current_object()
        except Exception:
            return None
    return None


def context_axes():
    """(origin, (x, y, z)) unit axes of the edit context (world axes at the root)."""
    obj = _context_object()
    if obj is None:
        return Vector((0.0, 0.0, 0.0)), (Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, 1.0)))
    m = obj.matrix_world
    r = m.to_3x3()
    axes = tuple(Vector(r.col[i]).normalized() for i in range(3))
    return m.translation.copy(), axes


def context_label(obj):
    """'' for geometry of the edited context or the root model; 'GROUP' / 'COMPONENT' otherwise."""
    if obj is None:
        return ""
    ctx = _context_object()
    if ctx is not None and obj == ctx:
        return ""
    sd = getattr(obj, "su_doc", None)
    if sd is None:
        return ""                                   # not a document of ours (no B data)
    kind = getattr(sd, "kind", "")
    if kind == 'MODEL':
        return ""
    return 'COMPONENT' if kind == 'COMPONENT' else 'GROUP'      # B: '' = group


def axis_of(vec, axes=None):
    """'AXIS_X'|'AXIS_Y'|'AXIS_Z' when vec is parallel to an axis, else ''."""
    if vec is None or vec.length < 1e-12:
        return ""
    if axes is None:
        axes = context_axes()[1]
    v = vec.normalized()
    for name, a in zip(AXIS_NAMES, axes):
        if abs(v.dot(a)) >= ALIGN_COS:
            return name
    return ""


# ---------------------------------------------------------------------------------------------- geometry helpers
def _px(v):
    """Logical → physical px (viewutil.ui_px); ui_scale is 0 in background mode → 1:1 there."""
    from .viewutil import ui_px
    r = ui_px(v)
    return r if r > 0.0 else float(v)


def _project(q, co):
    s, front = spatial.project_points(q.region, q.rv3d, [co])
    return (float(s[0][0]), float(s[0][1])) if front[0] else None


def _sdist(q, co):
    s = _project(q, co)
    if s is None:
        return math.inf
    return math.hypot(s[0] - q.xy[0], s[1] - q.xy[1])


def _ray_plane(o, d, c, n):
    den = d.dot(n)
    if abs(den) < 1e-12:
        return None
    t = (c - o).dot(n) / den
    return o + d * t if t > 0.0 else None


def _on_line(x, c, u):
    return c + u * (x - c).dot(u)


def _on_plane(x, c, n):
    return x - n * (x - c).dot(n)


def _view_dir(rv3d):
    return (rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))).normalized()


def _ident(inf):
    if inf is None or inf.kind == "NONE":
        return None
    if inf.kind in POINT_KINDS or inf.kind in ("ON_EDGE", "ON_GUIDE"):
        return (inf.kind, inf.doc_key, inf.elem)
    if inf.linear:
        d = tuple(round(x, 4) for x in inf.direction) if inf.direction is not None else None
        r = tuple(round(x, 4) for x in inf.ref_point) if inf.ref_point is not None else None
        return ("LINEAR", inf.linear, d, r)
    return None


# ---------------------------------------------------------------------------------------------- engine
class InferenceEngine:
    def __init__(self):
        self.reset()

    def reset(self):
        self._last = None
        self._last_edge = None          # (doc_key, edge_idx, unit direction) of the last hovered edge
        self._curves = []               # [(doc_key, curve_id)] last hovered curves (Centro), newest last
        self._hover_ident = None
        self._hover_t0 = 0.0
        self._hover_done = False

    @property
    def last(self):
        return self._last

    @property
    def last_edge(self):
        return self._last_edge

    # ------------------------------------------------------------------ public
    def query(self, q):
        inf = self._query(q)
        self._finish(q, inf)
        self._last = inf
        return inf

    def acquire_tick(self, inf, t):
        """Call on every hover with the clock time; True when `inf` became a reference point."""
        if inf is None or inf.kind not in POINT_KINDS:
            self._hover_ident = None
            return False
        ident = (inf.kind, inf.doc_key, inf.elem, tuple(round(c, 6) for c in inf.point))
        if ident != self._hover_ident:
            self._hover_ident, self._hover_t0, self._hover_done = ident, t, False
            return False
        if not self._hover_done and t - self._hover_t0 >= K.HOVER_ACQUIRE_S:
            self._hover_done = True
            add_ref_point(inf.point)
            return True
        return False

    # ------------------------------------------------------------------ pipeline
    def _query(self, q):
        locks = q.locks if q.locks is not None else STATE.locks
        prev = _ident(q.previous if q.previous is not None else self._last)
        o, d = spatial.Projection(q.region, q.rv3d, []).ray(q.xy)
        proj = spatial.projection(q.region, q.rv3d, exclude=q.exclude)
        origin, axes = context_axes()
        line, plane, locked = self._constraints(q, locks, axes)

        points = self._points(q, proj, prev, origin) if "POINTS" in q.flags or "ORIGIN" in q.flags else []
        edge = self._edge(q, proj, prev) if "EDGES" in q.flags else None
        guide_line = self._guide_line(q, o, d, prev) if "GUIDES" in q.flags else None
        hit = spatial.ray_cast(q, o, d, skip=q.skip) if "FACES" in q.flags else spatial.Hit.miss()

        # ---- constrained to a line: every candidate becomes a point on the line
        if line is not None:
            c, u, lin = line
            src = points[0] if points else (edge or guide_line)
            if src is not None:
                return self._mk(src.kind, _on_line(src.point, c, u), lin, u, c, src, locked=locked)
            if hit.ok and abs(hit.normal_orig.dot(u)) > 1e-6:
                t = (hit.point - c).dot(hit.normal_orig) / u.dot(hit.normal_orig)
                return self._face(hit, c + u * t, lin, u, c, locked)
            s = spatial.closest_on_line_to_ray(c, u, o, d)
            p = c + u * s if s is not None else c.copy()
            return Inference(kind="FREE", point=p, linear=lin, direction=u.copy(), ref_point=c.copy(), locked=locked)

        # ---- linear inferences from the anchor
        linear = self._linear(q, o, d, prev, axes, plane) if q.anchor is not None else None
        from_pt = self._from_point(q, o, d, prev, axes, linear, plane) if "FROM_POINT" in q.flags else None

        if plane is not None:
            c, n = plane
            src = points[0] if points else (edge or guide_line)
            if src is not None:
                return self._mk(src.kind, _on_plane(src.point, c, n), src.linear, src.direction, src.ref_point,
                                src, locked=locked)
            if from_pt is not None:
                from_pt.locked = locked
                return from_pt
            if linear is not None:
                linear.locked = locked
                return linear
            p = _ray_plane(o, d, c, n)
            if p is None:
                p = _on_plane(o + d * (c - o).dot(d), c, n)
            if hit.ok and abs(abs(hit.normal_orig.dot(n)) - 1.0) < 1e-6 and abs((hit.point - c).dot(n)) < 1e-5:
                return self._face(hit, p, "", None, None, locked)
            return Inference(kind="FREE", point=p, plane=(c.copy(), n.copy()), locked=locked)

        if points:
            return points[0]
        if edge is not None:
            return edge
        if guide_line is not None:
            return guide_line
        if from_pt is not None:
            return from_pt
        if linear is not None:
            return linear
        if hit.ok:
            return self._face(hit, hit.point, "", None, None, False)
        return self._free(q, o, d)

    # ------------------------------------------------------------------ constraints
    def _constraints(self, q, locks, axes):
        """(line (c, u, linear) | None, plane (c, n) | None, locked)."""
        if q.line is not None:
            c, u = Vector(q.line[0]), Vector(q.line[1]).normalized()
            lin = q.line[2] if len(q.line) > 2 else axis_of(u, axes)
            return (c, u, lin), None, False
        plane = (Vector(q.plane[0]), Vector(q.plane[1]).normalized()) if q.plane is not None else None
        if locks is not None and q.anchor is not None:
            a = Vector(q.anchor)
            if locks.axis in AXIS_NAMES:
                u = axes[AXIS_NAMES.index(locks.axis)]
                return (a, u, locks.axis), None, True
            if locks.axis == "PARALLEL" and self._last_edge is not None:
                u = self._last_edge[2]
                return (a, u, "PARALLEL"), None, True
            s = locks.shift
            if s is not None:
                if s.linear and s.linear != "FROM_POINT" and s.direction is not None:
                    return (a, s.direction.normalized(), s.linear), None, True
                if s.kind == "ON_FACE" and s.plane is not None:
                    return None, (Vector(s.plane[0]), Vector(s.plane[1]).normalized()), True
                if s.kind != "NONE" and (s.point - a).length > K.GEOM_TOL:
                    u = (s.point - a).normalized()
                    return (a, u, axis_of(u, axes)), None, True
        if locks is not None and plane is None and locks.plane is not None:
            plane = (Vector(locks.plane[0]), Vector(locks.plane[1]).normalized())
            return None, plane, True
        return None, plane, False

    # ------------------------------------------------------------------ candidates
    def _radius_ok(self, dist, base, ident, prev):
        return dist <= base or (ident is not None and ident == prev and dist <= base * K.SNAP_RELEASE_FACTOR)

    def _visible(self, q, co):
        return spatial.is_visible(q, q.region, q.rv3d, co, skip=q.skip)

    def _points(self, q, proj, prev, origin):
        rp = _px(K.SNAP_PX_POINT)
        rr = rp * K.SNAP_RELEASE_FACTOR
        cands = []
        if "POINTS" in q.flags:
            for h in spatial.points_near(proj, q.xy, rr, q.exclude):
                inf = Inference(kind="ENDPOINT", point=h.co, doc_key=h.doc_key, elem=("VERT", h.index),
                                obj_name=h.obj.name if h.obj else "")
                if self._radius_ok(h.dist, rp, _ident(inf), prev):
                    cands.append((PRIORITY["ENDPOINT"], h.dist, inf, h.obj))
        if "MIDPOINTS" in q.flags:
            for h in spatial.midpoints_near(proj, q.xy, rr, q.exclude):
                inf = Inference(kind="MIDPOINT", point=h.co, doc_key=h.doc_key, elem=("EDGE", h.index),
                                ref_edge=(h.doc_key, h.index), obj_name=h.obj.name if h.obj else "")
                if self._radius_ok(h.dist, rp, _ident(inf), prev):
                    cands.append((PRIORITY["MIDPOINT"], h.dist, inf, h.obj))
        if "CENTERS" in q.flags:
            for key, cid, co, obj in self._curve_centers():
                dist = _sdist(q, co)
                inf = Inference(kind="CENTER", point=co, doc_key=key, elem=("CURVE", cid),
                                obj_name=obj.name)
                if self._radius_ok(dist, rp, _ident(inf), prev):
                    cands.append((PRIORITY["CENTER"], dist, inf, obj))
        if "INTERSECTIONS" in q.flags:
            cands.extend(self._intersections(q, proj, rp, prev))
        g_points, _g_lines = _guides() if "GUIDES" in q.flags else ([], [])
        for i, gp in enumerate(g_points):
            dist = _sdist(q, gp)
            inf = Inference(kind="GUIDE_POINT", point=gp, elem=("GUIDE_POINT", i))
            if self._radius_ok(dist, rp, _ident(inf), prev):
                cands.append((PRIORITY["GUIDE_POINT"], dist, inf, None))
        if "ORIGIN" in q.flags:
            dist = _sdist(q, origin)
            inf = Inference(kind="ORIGIN", point=origin.copy(), elem=("ORIGIN", 0))
            if self._radius_ok(dist, rp, _ident(inf), prev):
                cands.append((PRIORITY["ORIGIN"], dist, inf, None))
        cands.sort(key=lambda c: (c[0], c[1]))
        out = []
        for _p, _d, inf, obj in cands:
            if self._visible(q, inf.point):
                inf.in_context = context_label(obj)
                out.append(inf)
                break
        return out

    def _intersections(self, q, proj, rp, prev):
        """Edge × edge and edge/guide × guide crossings near the cursor (3D, not just on screen)."""
        segs = []
        for h in spatial.edges_near(proj, q.xy, rp * 2.0, q.exclude)[:12]:
            segs.append((h.a, h.b - h.a, True, (h.doc_key, h.index), h.obj))
        if "GUIDES" in q.flags:
            for i, (c, u) in enumerate(_guides()[1]):
                segs.append((c, u, False, ("GUIDE", i), None))
        out = []
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                a, u, ba, ka, oa = segs[i]
                b, v, bb, kb, _ob = segs[j]
                if ka[0] == kb[0] and ka[0] != "GUIDE" and self._share_vertex(proj, ka, kb):
                    continue
                p = _line_line(a, u, ba, b, v, bb)
                if p is None:
                    continue
                dist = _sdist(q, p)
                inf = Inference(kind="INTERSECTION", point=p, doc_key=ka[0] if ka[0] != "GUIDE" else "",
                                elem=("X",) + tuple(sorted((ka, kb), key=repr)))
                if self._radius_ok(dist, rp, _ident(inf), prev):
                    out.append((PRIORITY["INTERSECTION"], dist, inf, oa))
        return out

    @staticmethod
    def _share_vertex(proj, ka, kb):
        d = proj.doc(ka[0])
        if d is None:
            return False
        me = d.obj.data
        va = set(me.edges[ka[1]].vertices)
        vb = set(me.edges[kb[1]].vertices)
        return bool(va & vb)

    def _edge(self, q, proj, prev):
        re = _px(K.SNAP_PX_EDGE)
        for h in spatial.edges_near(proj, q.xy, re * K.SNAP_RELEASE_FACTOR, q.exclude):
            inf = Inference(kind="ON_EDGE", point=h.co, doc_key=h.doc_key, elem=("EDGE", h.index),
                            ref_edge=(h.doc_key, h.index), direction=(h.b - h.a).normalized(),
                            obj_name=h.obj.name if h.obj else "")
            if not self._radius_ok(h.dist, re, _ident(inf), prev):
                continue
            if self._visible(q, h.co):
                inf.in_context = context_label(h.obj)
                return inf
        return None

    def _guide_line(self, q, o, d, prev):
        rg = _px(K.SNAP_PX_GUIDE)
        best = None
        for i, (c, u) in enumerate(_guides()[1]):
            s = spatial.closest_on_line_to_ray(c, u, o, d)
            if s is None:
                continue
            p = c + u * s
            dist = _sdist(q, p)
            inf = Inference(kind="ON_GUIDE", point=p, elem=("GUIDE", i), direction=u.copy())
            if self._radius_ok(dist, rg, _ident(inf), prev) and (best is None or dist < best[0]):
                if self._visible(q, p):
                    best = (dist, inf)
        return best[1] if best else None

    def _linear_dirs(self, q, axes, plane):
        """[(linear, unit dir, ref_edge)] candidate directions from the anchor."""
        dirs = []
        if "AXES" in q.flags:
            dirs.extend((n, a, None) for n, a in zip(AXIS_NAMES, axes))
        if "PARALLEL" in q.flags and self._last_edge is not None:
            key, idx, e = self._last_edge
            if not axis_of(e, axes):
                dirs.append(("PARALLEL", e, (key, idx)))
            for a in axes:
                p = e.cross(a)
                if p.length > 1e-6:
                    p.normalize()
                    if not axis_of(p, axes) and not any(abs(p.dot(x[1])) >= ALIGN_COS for x in dirs):
                        dirs.append(("PERPENDICULAR", p, (key, idx)))
        if "PERP_FACE" in q.flags and q.anchor_normal is not None:
            n = Vector(q.anchor_normal).normalized()
            if not axis_of(n, axes) and not any(abs(n.dot(x[1])) >= ALIGN_COS for x in dirs):
                dirs.append(("PERP_FACE", n, None))
        if plane is not None:
            dirs = [x for x in dirs if abs(x[1].dot(plane[1])) < 1e-6]
        return dirs

    def _linear(self, q, o, d, prev, axes, plane):
        ra = _px(K.SNAP_PX_AXIS)
        a = Vector(q.anchor)
        best = None
        for order, (lin, u, ref_edge) in enumerate(self._linear_dirs(q, axes, plane)):
            s = spatial.closest_on_line_to_ray(a, u, o, d)
            if s is None:
                continue
            p = a + u * s
            sp, sa = _project(q, p), _project(q, a)
            if sp is None:
                continue
            if sa is not None and math.hypot(sp[0] - sa[0], sp[1] - sa[1]) < ra:
                continue                                # at the anchor every axis matches: no inference
            dist = math.hypot(sp[0] - q.xy[0], sp[1] - q.xy[1])
            inf = Inference(kind="FREE", point=p, linear=lin, direction=u.copy(), ref_point=a.copy(),
                            ref_edge=ref_edge)
            if self._radius_ok(dist, ra, _ident(inf), prev) and (best is None or (dist, order) < best[0]):
                best = ((dist, order), inf)
        return best[1] if best else None

    def _from_point(self, q, o, d, prev, axes, linear, plane):
        """'Do ponto': a point aligned (along an axis) with an acquired reference point."""
        refs = [Vector(r) for r in STATE.ref_points]
        if not refs:
            return None
        ra = _px(K.SNAP_PX_AXIS)
        best = None
        for r in refs:
            if linear is not None:
                c, u = linear.ref_point, linear.direction
                p = _on_line(r, c, u)
                v = p - r
                lin_axis = axis_of(v, axes) if v.length > K.GEOM_TOL else ""
                if not lin_axis:
                    continue
                dirv = v.normalized()
            else:
                cand = None
                for name, u in zip(AXIS_NAMES, axes):
                    if plane is not None and abs(u.dot(plane[1])) > 1e-6:
                        continue
                    s = spatial.closest_on_line_to_ray(r, u, o, d)
                    if s is None or abs(s) < K.GEOM_TOL:
                        continue
                    pp = r + u * s
                    dist = _sdist(q, pp)
                    if cand is None or dist < cand[0]:
                        cand = (dist, pp, u)
                if cand is None:
                    continue
                _dist, p, dirv = cand
            dist = _sdist(q, p)
            inf = Inference(kind="FREE", point=p, linear="FROM_POINT", direction=dirv.copy(), ref_point=r.copy())
            if self._radius_ok(dist, ra, _ident(inf), prev) and (best is None or dist < best[0]):
                best = (dist, inf)
        return best[1] if best else None

    # ------------------------------------------------------------------ result builders
    def _mk(self, kind, point, linear, direction, ref_point, src, *, locked):
        return Inference(kind=kind, point=point, linear=linear or "", direction=direction.copy() if direction is not None else None,
                         ref_point=ref_point.copy() if ref_point is not None else None, ref_edge=src.ref_edge,
                         doc_key=src.doc_key, elem=src.elem, obj_name=src.obj_name, in_context=src.in_context,
                         locked=locked)

    def _face(self, hit, point, linear, direction, ref_point, locked):
        return Inference(kind="ON_FACE", point=point, linear=linear or "",
                         direction=direction.copy() if direction is not None else None,
                         ref_point=ref_point.copy() if ref_point is not None else None,
                         normal=hit.normal_orig.copy(), side=hit.side, plane=(hit.point.copy(), hit.normal_orig.copy()),
                         doc_key=hit.doc_key, elem=("FACE", hit.face_idx_orig),
                         obj_name=hit.obj.name if hit.obj else "", in_context=context_label(hit.obj), locked=locked)

    def _free(self, q, o, d):
        origin, axes = context_axes()
        if q.anchor is not None:
            # Free point after a click: on the horizontal plane (of the context) through the anchor, as in
            # SketchUp (drawing on the ground stays on the ground). Only when that plane is not hit (cursor
            # above the horizon) or the hit is absurdly far, use the vertical plane facing the camera.
            a = Vector(q.anchor)
            vd = _view_dir(q.rv3d)
            p = _ray_plane(o, d, a, axes[2])
            if p is not None and (p - a).length <= FREE_MAX_FACTOR * max((o - a).length, 1e-3):
                return Inference(kind="FREE", point=p, plane=(a.copy(), axes[2].copy()))
            n = max(axes[:2], key=lambda x: abs(x.dot(vd)))
            p = _ray_plane(o, d, a, n)
            if p is None:
                p = _ray_plane(o, d, a, vd)
            if p is None:
                p = a.copy()
            return Inference(kind="FREE", point=p, plane=(a.copy(), n.copy()))
        p = _ray_plane(o, d, origin, axes[2])
        if p is not None:
            return Inference(kind="FREE", point=p, plane=(origin.copy(), axes[2].copy()))
        vd = _view_dir(q.rv3d)
        c = Vector(q.rv3d.view_location)
        p = _ray_plane(o, d, c, vd) or c
        return Inference(kind="FREE", point=p, plane=(c, vd))

    # ------------------------------------------------------------------ curves (Centro)
    def _curve_centers(self):
        """World centres of the recently hovered curves (B: su_curve edge layer + su_doc.curves meta,
        meta["center"] = [x, y, z] in the document's local space)."""
        out = []
        ent = _sibling("entities")
        docmod = _sibling("document")
        if ent is None or docmod is None:
            return out
        for key, cid in self._curves:
            try:
                doc = docmod.get_by_key(key)
                meta = ent.get_curve_meta(doc, cid) if doc is not None else None
                c = meta.get("center") if isinstance(meta, dict) else None
                if c is None or len(c) != 3:
                    continue
                obj = doc.obj
                out.append((key, cid, obj.matrix_world @ Vector(c), obj))
            except Exception:
                continue
        return out

    def _remember_curve(self, inf):
        """Hovering a curve edge (or its vertex) makes its centre inferable (SketchUp: hover the arc/circle)."""
        if inf.elem is None or inf.elem[0] not in ("EDGE", "VERT") or not inf.doc_key:
            return
        obj = None
        for key, o in spatial.documents():
            if key == inf.doc_key:
                obj = o
                break
        if obj is None:
            return
        me = obj.data
        a = me.attributes.get("su_curve")
        if a is None or a.domain != 'EDGE':
            return
        idx = inf.elem[1]
        if inf.elem[0] == "EDGE":
            edges = [idx] if 0 <= idx < len(me.edges) else []
        else:
            edges = [e.index for e in me.edges if idx in e.vertices]
        for ei in edges:
            cid = a.data[ei].value
            if cid:
                k = (inf.doc_key, int(cid))
                if k in self._curves:
                    self._curves.remove(k)
                self._curves.append(k)
                del self._curves[:-K.MAX_REF_POINTS]
                return

    def _finish(self, q, inf):
        s = _project(q, inf.point)
        inf.screen = s if s is not None else (float(q.xy[0]), float(q.xy[1]))
        # a point that happens to lie on an axis from the anchor colours the rubber band
        if q.anchor is not None and not inf.linear and inf.kind in POINT_KINDS + ("ON_EDGE", "ON_FACE", "ON_GUIDE"):
            v = inf.point - Vector(q.anchor)
            if v.length > K.GEOM_TOL:
                lin = axis_of(v)
                if lin:
                    inf.linear, inf.direction, inf.ref_point = lin, v.normalized(), Vector(q.anchor)
        if inf.kind in POINT_KINDS or inf.kind in ("ON_EDGE", "ON_GUIDE", "ON_FACE"):
            inf.tooltip_key = TOOLTIP_KEYS[inf.kind]
        if inf.kind not in POINT_KINDS and inf.kind not in ("ON_EDGE", "ON_GUIDE") and inf.linear:
            inf.tooltip_key = TOOLTIP_KEYS.get(inf.linear, inf.tooltip_key)
        if inf.kind in ("ON_EDGE", "MIDPOINT", "ENDPOINT"):
            self._remember_curve(inf)
        if inf.kind == "ON_EDGE" and inf.ref_edge is not None and inf.direction is not None:
            self._last_edge = (inf.ref_edge[0], inf.ref_edge[1], inf.direction.normalized())
        elif inf.kind == "MIDPOINT" and inf.ref_edge is not None:
            try:
                obj = None
                for key, o in spatial.documents():
                    if key == inf.ref_edge[0]:
                        obj = o
                        break
                if obj is not None:
                    e = obj.data.edges[inf.ref_edge[1]]
                    mw = obj.matrix_world
                    v = (mw @ obj.data.vertices[e.vertices[1]].co) - (mw @ obj.data.vertices[e.vertices[0]].co)
                    if v.length > 1e-12:
                        self._last_edge = (inf.ref_edge[0], inf.ref_edge[1], v.normalized())
            except Exception:
                pass


def _line_line(a, u, a_bounded, b, v, b_bounded):
    """Intersection of a + s u and b + t v (segments when bounded, s/t in [0, 1]); None if they miss."""
    w = a - b
    uu, uv, vv = u.dot(u), u.dot(v), v.dot(v)
    uw, vw = u.dot(w), v.dot(w)
    den = uu * vv - uv * uv
    if uu < 1e-18 or vv < 1e-18 or abs(den) < 1e-12 * uu * vv:
        return None
    s = (uv * vw - vv * uw) / den
    t = (uu * vw - uv * uw) / den
    eps = 1e-9
    if a_bounded and not (-eps <= s <= 1.0 + eps):
        return None
    if b_bounded and not (-eps <= t <= 1.0 + eps):
        return None
    pa, pb = a + u * s, b + v * t
    scale = max(1.0, pa.length)
    if (pa - pb).length > K.GEOM_TOL * scale:
        return None
    return (pa + pb) * 0.5


# ---------------------------------------------------------------------------------------------- module API
ENGINE = InferenceEngine()


def add_ref_point(p):
    """Add a reference point for "Do ponto" (max MAX_REF_POINTS, oldest dropped, no duplicates)."""
    p = Vector(p)
    refs = [r for r in STATE.ref_points if (Vector(r) - p).length > K.GEOM_TOL]
    refs.append(p.copy())
    STATE.ref_points[:] = refs[-K.MAX_REF_POINTS:]


def lock_from_arrow(event_type, locks):
    """Arrow keys: → red, ← green, ↑ blue, ↓ parallel/perpendicular. Same arrow again unlocks.
    Returns True when the key was an arrow (handled)."""
    axis = ARROW_LOCKS.get(event_type)
    if axis is None:
        return False
    locks.axis = "" if locks.axis == axis else axis
    return True


# ---------------------------------------------------------------------------------------------- shape inferences (P1)
GOLDEN = (1.0 + math.sqrt(5.0)) / 2.0


def rect_shape(q, corner, p, u, v):
    """Retângulo: snap the opposite corner `p` (on the plane spanned by unit u, v through `corner`) to a
    Quadrado / Seção áurea diagonal when the cursor is within SNAP_PX_AXIS of it.
    Returns an Inference (kind FREE, tooltip 'inf.square' | 'inf.golden', ref_point = corner,
    direction = unit diagonal) or None. Shift-lock = keep passing the returned direction as q.line."""
    corner, p, u, v = Vector(corner), Vector(p), Vector(u).normalized(), Vector(v).normalized()
    d = p - corner
    a, b = d.dot(u), d.dot(v)
    if abs(a) < K.GEOM_TOL or abs(b) < K.GEOM_TOL:
        return None
    sa, sb = math.copysign(1.0, a), math.copysign(1.0, b)
    ra = _px(K.SNAP_PX_AXIS)
    best = None
    for key, ru, rv in (("inf.square", 1.0, 1.0), ("inf.golden", GOLDEN, 1.0), ("inf.golden", 1.0, GOLDEN)):
        diag = (u * (sa * ru) + v * (sb * rv)).normalized()
        o, dr = spatial.Projection(q.region, q.rv3d, []).ray(q.xy)
        s = spatial.closest_on_line_to_ray(corner, diag, o, dr)
        if s is None or s <= 0.0:
            continue
        pt = corner + diag * s
        dist = _sdist(q, pt)
        if dist <= ra and (best is None or dist < best[0]):
            best = (dist, Inference(kind="FREE", point=pt, ref_point=corner.copy(), direction=diag,
                                    tooltip_key=key))
    if best is None:
        return None
    inf = best[1]
    s = _project(q, inf.point)
    inf.screen = s if s is not None else (float(q.xy[0]), float(q.xy[1]))
    return inf


def arc_semicircle(q, a, b, bulge_point, normal):
    """Arco de dois pontos: when the bulge is within SNAP_PX_AXIS (screen) of half the chord, snap it
    ("Semicírculo"). Returns (bulge, tooltip_key) — bulge signed along the in-plane perpendicular of ab;
    tooltip_key '' when not snapped."""
    a, b, bp, n = Vector(a), Vector(b), Vector(bulge_point), Vector(normal).normalized()
    chord = b - a
    if chord.length < K.GEOM_TOL:
        return 0.0, ""
    perp = n.cross(chord).normalized()
    mid = (a + b) * 0.5
    bulge = (bp - mid).dot(perp)
    half = chord.length * 0.5
    target = mid + perp * math.copysign(half, bulge if bulge != 0.0 else 1.0)
    if _sdist(q, target) <= _px(K.SNAP_PX_AXIS):
        return math.copysign(half, bulge if bulge != 0.0 else 1.0), "inf.half_circle"
    return bulge, ""


def hover_plane(q):
    """Plane for gizmos before the first click (Círculo, Girar, Transferidor, Retângulo):
    arrow lock → the plane whose normal is that axis; face under the cursor → its plane;
    otherwise the ground plane of the context. Returns (co, normal, axis) with axis 'X'|'Y'|'Z'|''
    = gizmo colour (normal parallel to red/green/blue)."""
    locks = q.locks if q.locks is not None else STATE.locks
    origin, axes = context_axes()
    if locks is not None and locks.axis in AXIS_NAMES:
        inf = ENGINE.query(QueryCtx(q.region, q.rv3d, q.xy, q.depsgraph, flags=q.flags, exclude=q.exclude,
                                    skip=q.skip, locks=_NO_LOCKS, previous=q.previous))
        i = AXIS_NAMES.index(locks.axis)
        return inf.point.copy(), axes[i].copy(), "XYZ"[i]
    inf = ENGINE.query(QueryCtx(q.region, q.rv3d, q.xy, q.depsgraph, flags=q.flags, exclude=q.exclude,
                                skip=q.skip, locks=_NO_LOCKS, previous=q.previous))
    if inf.kind == "ON_FACE" and inf.normal is not None:
        n = inf.normal.copy()
        if inf.side < 0:
            n.negate()
        ax = axis_of(n, axes)
        return inf.point.copy(), n, ax[-1] if ax else ""
    return inf.point.copy(), axes[2].copy(), "Z"


class _NoLocks:
    axis = ""
    shift = None
    plane = None


_NO_LOCKS = _NoLocks()


STRINGS = {
    "inf.endpoint": {"pt_BR": "Ponto de extremidade", "en": "Endpoint"},
    "inf.midpoint": {"pt_BR": "Ponto central", "en": "Midpoint"},
    "inf.on_edge": {"pt_BR": "Em aresta", "en": "On Edge"},
    "inf.on_face": {"pt_BR": "Em face", "en": "On Face"},
    "inf.intersection": {"pt_BR": "Interseção", "en": "Intersection"},
    "inf.center": {"pt_BR": "Centro", "en": "Center"},
    "inf.origin": {"pt_BR": "Ponto de origem", "en": "Origin"},
    "inf.guide_point": {"pt_BR": "Ponto de orientação", "en": "Guide Point"},
    "inf.on_guide": {"pt_BR": "Na linha", "en": "On Line"},
    "inf.axis_x": {"pt_BR": "No eixo vermelho", "en": "On Red Axis"},
    "inf.axis_y": {"pt_BR": "No eixo verde", "en": "On Green Axis"},
    "inf.axis_z": {"pt_BR": "No eixo azul", "en": "On Blue Axis"},
    "inf.parallel": {"pt_BR": "Paralela à aresta", "en": "Parallel to Edge"},
    "inf.perpendicular": {"pt_BR": "Perpendicular à aresta", "en": "Perpendicular to Edge"},
    "inf.perp_face": {"pt_BR": "Perpendicular à face", "en": "Perpendicular to Face"},
    "inf.from_point": {"pt_BR": "Do ponto", "en": "From Point"},
    "inf.tangent": {"pt_BR": "Tangente no vértice", "en": "Tangent at Vertex"},
    "inf.in_group": {"pt_BR": "no grupo", "en": "in Group"},
    "inf.in_component": {"pt_BR": "no componente", "en": "in Component"},
    "inf.square": {"pt_BR": "Quadrado", "en": "Square"},
    "inf.golden": {"pt_BR": "Seção áurea", "en": "Golden Section"},
    "inf.half_circle": {"pt_BR": "Semicírculo", "en": "Half Circle"},
}


def register():
    from .. import i18n
    i18n.register_strings(STRINGS)
    ENGINE.reset()


def unregister():
    from .. import i18n
    i18n.unregister_strings(STRINGS)
    ENGINE.reset()
    _guides_provider[0] = None
