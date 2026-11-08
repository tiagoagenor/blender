# SPDX-License-Identifier: GPL-2.0-or-later
"""Spatial queries for inference and selection (owner: C). Contract: PLANO.md §2.4. No cache in v1.

    projection(region, rv3d, exclude=None) -> Projection     numpy, every visible document
    points_near(p, xy, r, exclude=None) -> [PointHit]        inferable vertices within r px (sorted)
    midpoints_near(p, xy, r, exclude=None) -> [PointHit]
    edges_near(p, xy, r, exclude=None) -> [EdgeHit]          closest point of each edge to the view ray
    rect_query(p, x0, y0, x1, y1, mode) -> {doc_key: {'EDGE': set, 'FACE': set}}   'WINDOW' | 'CROSSING'
    ray_cast(tc, origin, direction, *, skip=None) -> Hit

Documents: core.document.visible_documents() (B) when it exists, else every visible mesh object
(doc_key = object name). Geometry comes from `obj.data` (Document.write/preview_write keep it in
sync with the BMesh), so face indices are ORIGINAL indices.
Inferable edges: not su_bridge, not su_hidden, not su_soft (attributes of B; absent = False).
`exclude`: iterable of doc_keys (whole document) and/or (doc_key, vert_index) tuples (moving vertices:
the vertex and its edges are ignored).
Coordinates are region pixels (physical px, origin bottom-left), like event.mouse_region_x/y.
"""

import sys
from dataclasses import dataclass, field
from typing import Optional

import bpy
import numpy as np
from mathutils import Vector

ORDER = 115

HIDDEN_EDGE_ATTRS = ("su_bridge", "su_hidden", "su_soft")
RELAUNCH_MAX = 4


# ---------------------------------------------------------------------------------------------- documents
def _document_module():
    pkg = __name__.rpartition(".")[0]
    return sys.modules.get(pkg + ".document")


def doc_key_of(obj):
    """Document key of an object (B's Document.key when available, else the object name)."""
    doc = _document_module()
    if doc is not None and hasattr(doc, "get"):
        try:
            d = doc.get(obj)
            if d is not None:
                return d.key
        except Exception:
            pass
    return obj.name


def documents():
    """[(doc_key, obj)] of every visible document object."""
    doc = _document_module()
    if doc is not None and hasattr(doc, "visible_documents"):
        try:
            return [(d.key, d.obj) for d in doc.visible_documents()]
        except Exception:
            from .. import perf
            perf.exception("spatial.documents: visible_documents failed")
    out = []
    view_layer = bpy.context.view_layer
    for obj in view_layer.objects:
        if obj.type == 'MESH' and obj.visible_get(view_layer=view_layer):
            out.append((obj.name, obj))
    return out


def _bool_attr(mesh, name, n):
    a = mesh.attributes.get(name)
    if a is None or a.domain != 'EDGE' or a.data_type != 'BOOLEAN' or n == 0:
        return None
    arr = np.zeros(n, dtype=bool)
    a.data.foreach_get("value", arr)
    return arr


def _split_exclude(exclude):
    docs, verts = set(), {}
    for e in exclude or ():
        if isinstance(e, str):
            docs.add(e)
        else:
            verts.setdefault(e[0], set()).add(int(e[1]))
    return docs, verts


# ---------------------------------------------------------------------------------------------- projection
@dataclass
class DocProj:
    key: str
    obj: object
    co: np.ndarray          # (N, 3) world
    scr: np.ndarray         # (N, 2) region px
    front: np.ndarray       # (N,) bool: in front of the camera
    edges: np.ndarray       # (E, 2) vertex indices of inferable edges
    edge_ids: np.ndarray    # (E,) original edge indices
    verts: np.ndarray       # vertex indices used by inferable edges (inferable points)
    faces: list = field(default_factory=list)   # [np.ndarray of vertex indices] per original face


@dataclass
class Projection:
    region: object
    rv3d: object
    docs: list

    def ray(self, xy):
        from .viewutil import mouse_ray
        return mouse_ray(self.region, self.rv3d, xy)

    def doc(self, key):
        for d in self.docs:
            if d.key == key:
                return d
        return None


def project_points(region, rv3d, co):
    """(N,3) world → ((N,2) region px, (N,) in-front mask)."""
    m = np.array(rv3d.perspective_matrix, dtype=np.float64)
    co = np.asarray(co, dtype=np.float64).reshape(-1, 3)
    hom = co @ m[:3, :3].T + m[:3, 3]
    w = co @ m[3, :3] + m[3, 3]
    front = w > 1e-9
    ws = np.where(front, w, 1.0)
    ndc = hom[:, :2] / ws[:, None]
    scr = (ndc + 1.0) * 0.5 * np.array((region.width, region.height), dtype=np.float64)
    return scr, front


def projection(region, rv3d, exclude=None):
    ex_docs, ex_verts = _split_exclude(exclude)
    out = []
    for key, obj in documents():
        if key in ex_docs:
            continue
        me = obj.data
        nv, ne = len(me.vertices), len(me.edges)
        co = np.zeros(nv * 3, dtype=np.float64)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        mw = np.array(obj.matrix_world, dtype=np.float64)
        co = co @ mw[:3, :3].T + mw[:3, 3]
        ev = np.zeros(ne * 2, dtype=np.int64)
        me.edges.foreach_get("vertices", ev)
        ev = ev.reshape(-1, 2)
        keep = np.ones(ne, dtype=bool)
        for name in HIDDEN_EDGE_ATTRS:
            a = _bool_attr(me, name, ne)
            if a is not None:
                keep &= ~a
        if key in ex_verts and ne:
            moving = np.zeros(nv, dtype=bool)
            moving[list(i for i in ex_verts[key] if 0 <= i < nv)] = True
            keep &= ~(moving[ev[:, 0]] | moving[ev[:, 1]])
        edge_ids = np.nonzero(keep)[0]
        edges = ev[edge_ids]
        verts = np.unique(edges.reshape(-1)) if len(edges) else np.zeros(0, dtype=np.int64)
        scr, front = project_points(region, rv3d, co) if nv else (np.zeros((0, 2)), np.zeros(0, bool))
        faces = [np.array(p.vertices, dtype=np.int64) for p in me.polygons]
        out.append(DocProj(key, obj, co, scr, front, edges, edge_ids, verts, faces))
    return Projection(region, rv3d, out)


# ---------------------------------------------------------------------------------------------- point / edge queries
@dataclass
class PointHit:
    dist: float             # px
    doc_key: str
    index: int              # vertex index (MIDPOINT: edge index)
    co: Vector              # world
    obj: object = None


@dataclass
class EdgeHit:
    dist: float             # px from the cursor to the projected closest point
    doc_key: str
    index: int              # original edge index
    co: Vector              # closest point of the edge to the view ray (world)
    a: Vector               # world end points
    b: Vector
    t: float                # co = a + t (b - a)
    obj: object = None


def points_near(p, xy, r, exclude=None):
    ex_docs, ex_verts = _split_exclude(exclude)
    xy = np.array(xy[:2], dtype=np.float64)
    out = []
    for d in p.docs:
        if d.key in ex_docs or not len(d.verts):
            continue
        idx = d.verts
        ok = d.front[idx]
        dist = np.linalg.norm(d.scr[idx] - xy, axis=1)
        sel = np.nonzero(ok & (dist <= r))[0]
        skip = ex_verts.get(d.key, ())
        for i in sel:
            vi = int(idx[i])
            if vi in skip:
                continue
            out.append(PointHit(float(dist[i]), d.key, vi, Vector(d.co[vi]), d.obj))
    out.sort(key=lambda h: h.dist)
    return out


def midpoints_near(p, xy, r, exclude=None):
    ex_docs, _ex_verts = _split_exclude(exclude)
    xy = np.array(xy[:2], dtype=np.float64)
    out = []
    for d in p.docs:
        if d.key in ex_docs or not len(d.edges):
            continue
        mid = (d.co[d.edges[:, 0]] + d.co[d.edges[:, 1]]) * 0.5
        scr, front = project_points(p.region, p.rv3d, mid)
        dist = np.linalg.norm(scr - xy, axis=1)
        for i in np.nonzero(front & (dist <= r))[0]:
            out.append(PointHit(float(dist[i]), d.key, int(d.edge_ids[i]), Vector(mid[i]), d.obj))
    out.sort(key=lambda h: h.dist)
    return out


def closest_on_segment_to_ray(a, b, o, d):
    """Parameter t in [0,1] of the point of segment ab closest to the ray (o, d)."""
    u = b - a
    w = a - o
    uu = u.dot(u)
    if uu < 1e-18:
        return 0.0
    ud = u.dot(d)
    dd = d.dot(d)
    denom = uu * dd - ud * ud
    if abs(denom) < 1e-14 * uu * dd:         # parallel
        t = -w.dot(u) / uu
    else:
        t = (ud * w.dot(d) - dd * w.dot(u)) / denom
    return min(1.0, max(0.0, t))


def closest_on_line_to_ray(c, u, o, d):
    """Parameter s of the point c + s u closest to the ray (o, d) (unbounded line). None if parallel."""
    w = c - o
    uu, ud, dd = u.dot(u), u.dot(d), d.dot(d)
    denom = uu * dd - ud * ud
    if uu < 1e-18 or abs(denom) < 1e-12 * uu * dd:
        return None
    return (ud * w.dot(d) - dd * w.dot(u)) / denom


def edges_near(p, xy, r, exclude=None):
    ex_docs, _ = _split_exclude(exclude)
    xy2 = np.array(xy[:2], dtype=np.float64)
    o, dvec = p.ray(xy)
    out = []
    for d in p.docs:
        if d.key in ex_docs or not len(d.edges):
            continue
        ia, ib = d.edges[:, 0], d.edges[:, 1]
        ok = d.front[ia] & d.front[ib]
        sa, sb = d.scr[ia], d.scr[ib]
        seg = sb - sa
        ll = np.einsum("ij,ij->i", seg, seg)
        tt = np.einsum("ij,ij->i", xy2 - sa, seg) / np.where(ll > 1e-12, ll, 1.0)
        tt = np.clip(tt, 0.0, 1.0)
        dist = np.linalg.norm(sa + seg * tt[:, None] - xy2, axis=1)
        for i in np.nonzero(ok & (dist <= r * 1.5 + 1.0))[0]:
            a, b = Vector(d.co[ia[i]]), Vector(d.co[ib[i]])
            t = closest_on_segment_to_ray(a, b, o, dvec)
            co = a.lerp(b, t)
            s, front = project_points(p.region, p.rv3d, [co])
            if not front[0]:
                continue
            dd = float(np.linalg.norm(s[0] - xy2))
            if dd <= r:
                out.append(EdgeHit(dd, d.key, int(d.edge_ids[i]), co, a, b, t, d.obj))
    out.sort(key=lambda h: h.dist)
    return out


# ---------------------------------------------------------------------------------------------- rectangle
def _seg_hits_rect(p0, p1, x0, y0, x1, y1):
    """Liang–Barsky: does segment p0p1 touch the axis-aligned rectangle?"""
    t0, t1 = 0.0, 1.0
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    for pk, qk in ((-dx, p0[0] - x0), (dx, x1 - p0[0]), (-dy, p0[1] - y0), (dy, y1 - p0[1])):
        if pk == 0.0:
            if qk < 0.0:
                return False
        else:
            t = qk / pk
            if pk < 0.0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


def _point_in_poly(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        xa, ya = poly[i]
        xb, yb = poly[(i + 1) % n]
        if (ya > y) != (yb > y):
            if x < xa + (y - ya) * (xb - xa) / (yb - ya):
                inside = not inside
    return inside


def rect_query(p, x0, y0, x1, y1, mode):
    """Entities inside ('WINDOW': completely) or touching ('CROSSING') the region rectangle."""
    if mode not in ('WINDOW', 'CROSSING'):
        raise ValueError("rect_query mode must be 'WINDOW' or 'CROSSING'")
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    out = {}
    for d in p.docs:
        inside = (d.front & (d.scr[:, 0] >= x0) & (d.scr[:, 0] <= x1)
                  & (d.scr[:, 1] >= y0) & (d.scr[:, 1] <= y1)) if len(d.co) else np.zeros(0, bool)
        edges, faces = set(), set()
        for k, (a, b) in enumerate(d.edges):
            if mode == 'WINDOW':
                hit = inside[a] and inside[b]
            else:
                hit = inside[a] or inside[b] or (
                    d.front[a] and d.front[b] and _seg_hits_rect(d.scr[a], d.scr[b], x0, y0, x1, y1))
            if hit:
                edges.add(int(d.edge_ids[k]))
        for fi, fv in enumerate(d.faces):
            if not len(fv):
                continue
            if mode == 'WINDOW':
                hit = bool(inside[fv].all())
            else:
                hit = bool(inside[fv].any())
                if not hit and d.front[fv].all():
                    poly = d.scr[fv]
                    n = len(fv)
                    hit = any(_seg_hits_rect(poly[i], poly[(i + 1) % n], x0, y0, x1, y1) for i in range(n))
                    if not hit:
                        hit = _point_in_poly(((x0 + x1) * 0.5, (y0 + y1) * 0.5), poly)
            if hit:
                faces.add(fi)
        if edges or faces:
            out[d.key] = {'EDGE': edges, 'FACE': faces}
    return out


# ---------------------------------------------------------------------------------------------- ray cast
@dataclass
class Hit:
    ok: bool
    point: Optional[Vector] = None
    normal_orig: Optional[Vector] = None    # world normal of the ORIGINAL face (never the back copy)
    doc_key: str = ""
    face_idx_orig: int = -1                 # idx % n_orig
    side: int = 0                           # +1 front seen, -1 back seen
    obj: object = None                      # original object
    distance: float = 0.0                   # from the initial origin

    @classmethod
    def miss(cls):
        return cls(ok=False)


def _depsgraph(tc):
    dg = getattr(tc, "depsgraph", None)
    if dg is not None:
        return dg
    if tc is not None and hasattr(tc, "evaluated_depsgraph_get"):
        return tc.evaluated_depsgraph_get()
    return bpy.context.evaluated_depsgraph_get()


def face_normal_world(obj, face_idx):
    n = obj.data.polygons[face_idx].normal
    return (obj.matrix_world.to_3x3().inverted_safe().transposed() @ n).normalized()


def ray_cast(tc, origin, direction, *, skip=None):
    """First face hit along the ray. Face index/normal of the ORIGINAL mesh (the evaluated mesh may hold
    D's GN back copy after the originals: idx % n_orig). `skip` = {doc_key: {face_idx_orig}} faces to
    pass through (moving faces): the ray is relaunched from hit + ε (max 4×)."""
    dg = _depsgraph(tc)
    scene = getattr(tc, "scene", None) or bpy.context.scene
    origin = Vector(origin)
    direction = Vector(direction).normalized()
    o = origin.copy()
    for _ in range(RELAUNCH_MAX + 1):
        ok, loc, _normal, idx, obj, _mat = scene.ray_cast(dg, o, direction)
        if not ok or obj is None:
            return Hit.miss()
        orig = obj.original if obj.original is not None else obj
        me = orig.data
        n_orig = len(me.polygons) if me is not None and hasattr(me, "polygons") else 0
        idx_o = idx % n_orig if n_orig else idx
        key = doc_key_of(orig)
        if skip and idx_o in skip.get(key, ()):
            o = loc + direction * (1e-4 * max(1.0, (loc - origin).length * 1e-2))
            continue
        nrm = face_normal_world(orig, idx_o) if n_orig else Vector(_normal)
        side = 1 if direction.dot(nrm) < 0.0 else -1
        return Hit(True, Vector(loc), nrm, key, idx_o, side, orig, (Vector(loc) - origin).length)
    return Hit.miss()


def is_visible(tc, region, rv3d, co, *, skip=None):
    """True when nothing hides world point `co` from the camera (point on the hit face counts)."""
    from bpy_extras import view3d_utils
    s = view3d_utils.location_3d_to_region_2d(region, rv3d, co)
    if s is None:
        return False
    o = view3d_utils.region_2d_to_origin_3d(region, rv3d, s)
    v = Vector(co) - o
    dist = v.length
    if dist < 1e-9:
        return True
    hit = ray_cast(tc, o, v / dist, skip=skip)
    if not hit.ok:
        return True
    return hit.distance >= dist - max(1e-4, 2e-4 * dist)
