# SPDX-License-Identifier: GPL-2.0-or-later
"""Geometry kernel on BMesh (owner: B). Contract: PLANO.md §2.4-B, rules §3.1.

Pure bmesh + mathutils (no bpy context): every function takes the document's `bm` and leaves it
valid; the caller writes it with `Document.write(undo_key=...)`.

Model (SketchUp rules):
  * edges are first-class; a face exists only on a closed planar loop of edges;
  * a "logical face" = bmesh faces joined by `su_bridge` edges (bmesh has no holes: CDT bridges);
  * edge layers: bool su_bridge su_soft su_hidden, int su_curve; face layer int su_back_mat (1);
  * every new face gets `normal_update()` (bmesh faces are born with a zero normal).

Algorithms (simple first, perf deferred — PLANO §7; whole-mesh scans are fine in v1):
  * add_edge: weld endpoints (vertex or edge split), split at crossings / vertices on the segment,
    reuse existing edges (redrawing an edge = "touching" it), then auto_faces.
  * auto_faces: for each plane through a touched edge and a neighbour edge, build the planar
    arrangement of that plane's edges (half-edge face tracing, dangling and graph-bridge edges
    pruned, containment → holes). Logical faces crossed by a touched edge are dissolved and
    their regions recreated with the same material; uncovered regions bounded by a touched
    edge become new faces (healing). Regions are filled by CDT (`_cdt_fill`).
  * rebuild_face: delaunay_2d_cdt(output_type=5, need_ids=True); non-input edges = su_bridge.
  * erase_faces: logical faces removed, edges stay. erase_edges: dependent faces removed; two
    coplanar faces across an erased edge merge; collinear valence-2 vertices left by the erase
    are dissolved (SketchUp heals the split edge).
"""

import math
from dataclasses import dataclass, field

import bmesh
from mathutils import Vector
from mathutils import geometry as mgeo

from ..constants import ARC_SEGMENTS, CIRCLE_SIDES, GEOM_TOL, SLOT_DEFAULT_BACK, SLOT_DEFAULT_FRONT

ORDER = 115

L_BRIDGE = "su_bridge"
L_SOFT = "su_soft"
L_HIDDEN = "su_hidden"
L_CURVE = "su_curve"
L_BACK = "su_back_mat"

_COLLINEAR_SIN = 1e-6     # |sin(angle)| below this = collinear
_PARALLEL_DOT = 1.0 - 1e-9


@dataclass
class EditResult:
    new_verts: list = field(default_factory=list)
    new_edges: list = field(default_factory=list)
    new_faces: list = field(default_factory=list)
    removed_faces: int = 0
    index_map: dict | None = None
    edges: list = field(default_factory=list)     # every edge piece of the operation (new or reused)


# --------------------------------------------------------------------------------------- layers

class _Layers:
    __slots__ = ("bridge", "soft", "hidden", "curve", "back")


def ensure_layers(bm):
    """Create the su_* layers when missing; returns an object with .bridge .soft .hidden .curve .back."""
    el = bm.edges.layers
    for name in (L_BRIDGE, L_SOFT, L_HIDDEN):
        if el.bool.get(name) is None:
            el.bool.new(name)
    if el.int.get(L_CURVE) is None:
        el.int.new(L_CURVE)
    if bm.faces.layers.int.get(L_BACK) is None:
        bm.faces.layers.int.new(L_BACK)
    return layers(bm)


def layers(bm):
    lay = _Layers()
    el = bm.edges.layers
    lay.bridge = el.bool[L_BRIDGE]
    lay.soft = el.bool[L_SOFT]
    lay.hidden = el.bool[L_HIDDEN]
    lay.curve = el.int[L_CURVE]
    lay.back = bm.faces.layers.int[L_BACK]
    return lay


# --------------------------------------------------------------------------------------- planes

def _canon(n):
    """Unit normal with a deterministic sign (first significant component positive)."""
    n = Vector(n).normalized()
    for c in n:
        if abs(c) > 1e-6:
            return -n if c < 0.0 else n
    return n


def _plane(n, co):
    n = _canon(n)
    return (n, n.dot(co))


def _same_plane(p, q, tol=GEOM_TOL):
    dot = p[0].dot(q[0])
    if abs(dot) < _PARALLEL_DOT:
        return False
    return abs(p[1] - (q[1] if dot > 0 else -q[1])) <= tol


def _frame(plane):
    """(n, origin, u, v) with u × v = n, deterministic for a canonical plane."""
    n, d = plane
    u = n.orthogonal().normalized()
    v = n.cross(u)
    return n, n * d, u, v


def _on_plane(plane, co, tol=GEOM_TOL):
    return abs(plane[0].dot(co) - plane[1]) <= tol


def _to2(frame, co):
    _n, o, u, v = frame
    w = co - o
    return (w.dot(u), w.dot(v))


def _area2(pts):
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i - 1]
        x2, y2 = pts[i]
        a += x1 * y2 - x2 * y1
    return 0.5 * a


def _inside(p, segs):
    """Even-odd point-in-region test against 2D segments (outer + holes in any orientation)."""
    x, y = p
    c = False
    for (x1, y1), (x2, y2) in segs:
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xi:
                c = not c
    return c


def _loop_segs(pts):
    return [(pts[i - 1], pts[i]) for i in range(len(pts))]


def _sample(loops2):
    """A point strictly inside the region (first loop = outer, others = holes)."""
    polys = [[Vector((x, y, 0.0)) for x, y in loop] for loop in loops2]
    best, best_a = None, -1.0
    try:
        tris = mgeo.tessellate_polygon(polys)
    except Exception:
        tris = []
    flat = [p for poly in polys for p in poly]
    for i, j, k in tris:
        a, b, c = flat[i], flat[j], flat[k]
        area = abs((b - a).cross(c - a).z)
        if area > best_a:
            best_a, best = area, (a + b + c) / 3.0
    if best is None:
        pts = loops2[0]
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    return (best.x, best.y)


def is_planar(face, tol=GEOM_TOL):
    verts = face.verts
    if len(verts) <= 3:
        return True
    n = mgeo.normal([v.co for v in verts])
    if n.length < 0.5:
        return False
    c = verts[0].co
    return all(abs(n.dot(v.co - c)) <= tol for v in verts)


def face_plane(face):
    face.normal_update()
    return _plane(face.normal, face.verts[0].co)


# ---------------------------------------------------------------------------------- face helpers

def orient_face(face, n):
    """Flip `face` so that its normal points along `n` (no-op when already)."""
    face.normal_update()
    if face.normal.dot(n) < 0.0:
        face.normal_flip()
        face.normal_update()


def reverse_faces(bm, faces):
    for f in faces:
        if f.is_valid:
            f.normal_flip()
            f.normal_update()


def new_face(bm, verts, *, material=SLOT_DEFAULT_FRONT, back_material=SLOT_DEFAULT_BACK, normal=None):
    """Create (or return the existing) face on `verts` with the su defaults and a valid normal."""
    lay = ensure_layers(bm)
    f = bm.faces.get(verts)
    if f is None:
        f = bm.faces.new(verts)
        f.material_index = material
        f[lay.back] = back_material
    f.normal_update()
    if normal is not None:
        orient_face(f, normal)
    return f


def clusters(bm, faces):
    """Group `faces` into logical faces (flood fill through su_bridge edges). Returns list of lists."""
    lay = layers(bm)
    seen = set()
    out = []
    for f in faces:
        if f in seen or not f.is_valid:
            continue
        group = []
        stack = [f]
        seen.add(f)
        while stack:
            g = stack.pop()
            group.append(g)
            for e in g.edges:
                if not e[lay.bridge]:
                    continue
                for h in e.link_faces:
                    if h not in seen:
                        seen.add(h)
                        stack.append(h)
        out.append(group)
    return out


def _cluster_boundary(cluster):
    """Edges used by exactly one face of the cluster (bridges are used twice: interior)."""
    count = {}
    for f in cluster:
        for e in f.edges:
            count[e] = count.get(e, 0) + 1
    return [e for e, c in count.items() if c == 1]


def _edge_segs(frame, edges):
    return [(_to2(frame, e.verts[0].co), _to2(frame, e.verts[1].co)) for e in edges]


def _delete_faces(bm, faces):
    """Delete faces only, then the bridge edges they leave as wire. Returns the count deleted."""
    lay = layers(bm)
    faces = [f for f in set(faces) if f.is_valid]
    if not faces:
        return 0
    bridges = {e for f in faces for e in f.edges if e[lay.bridge]}
    bmesh.ops.delete(bm, geom=faces, context='FACES_ONLY')
    wire = [e for e in bridges if e.is_valid and not e.link_faces]
    if wire:
        bmesh.ops.delete(bm, geom=wire, context='EDGES')
    return len(faces)


# ---------------------------------------------------------------------------------------- welds

def _closest_on_edge(e, co):
    a, b = e.verts[0].co, e.verts[1].co
    d = b - a
    l2 = d.length_squared
    if l2 == 0.0:
        return 0.0, a.copy()
    t = (co - a).dot(d) / l2
    return t, a + d * t


def _weld(bm, co, tol, res):
    co = Vector(co)
    best, best_d = None, tol
    for v in bm.verts:
        dist = (v.co - co).length
        if dist <= best_d:
            best, best_d = v, dist
    if best is not None:
        return best
    for e in bm.edges:
        t, p = _closest_on_edge(e, co)
        if (p - co).length > tol:
            continue
        length = e.calc_length()
        if t * length <= tol or (1.0 - t) * length <= tol:
            continue
        _ne, nv = bmesh.utils.edge_split(e, e.verts[0], t)
        nv.co = p
        res.new_verts.append(nv)
        return nv
    v = bm.verts.new(co)
    res.new_verts.append(v)
    return v


def weld_point(bm, co, tol=GEOM_TOL):
    """Existing vertex within tol, else split the edge passing through co, else a new vertex."""
    return _weld(bm, co, tol, EditResult())


# --------------------------------------------------------------------------------------- add_edge

def add_edge(bm, a, b, *, curve_id=0):
    """Add segment a→b with SketchUp semantics; returns EditResult (new_faces = faces created)."""
    lay = ensure_layers(bm)
    res = EditResult()
    a, b = Vector(a), Vector(b)
    if (b - a).length <= GEOM_TOL:
        return res
    va = _weld(bm, a, GEOM_TOL, res)
    vb = _weld(bm, b, GEOM_TOL, res)
    if va is vb:
        return res
    pa, pb = va.co.copy(), vb.co.copy()
    d = pb - pa
    l2 = d.length_squared
    seg_len = math.sqrt(l2)

    # 1. split existing edges that cross the open segment
    crossings = []
    for e in bm.edges:
        if va in e.verts or vb in e.verts:
            continue
        c0, c1 = e.verts[0].co, e.verts[1].co
        r = mgeo.intersect_line_line(pa, pb, c0, c1)
        if r is None:
            continue
        p, q = r
        if (p - q).length > GEOM_TOL:
            continue
        t = (p - pa).dot(d) / l2
        if t * seg_len <= GEOM_TOL or (1.0 - t) * seg_len <= GEOM_TOL:
            continue
        s, _q = _closest_on_edge(e, q)
        el = e.calc_length()
        if s * el <= GEOM_TOL or (1.0 - s) * el <= GEOM_TOL or s < 0.0 or s > 1.0 or t < 0.0 or t > 1.0:
            continue
        crossings.append((e, s, q.copy()))
    for e, s, q in crossings:
        if not e.is_valid:
            continue
        _ne, nv = bmesh.utils.edge_split(e, e.verts[0], s)
        nv.co = q
        res.new_verts.append(nv)

    # 2. every vertex on the open segment, in order
    on = []
    for v in bm.verts:
        if v is va or v is vb:
            continue
        t = (v.co - pa).dot(d) / l2
        if 0.0 < t < 1.0 and (v.co - (pa + d * t)).length <= GEOM_TOL:
            on.append((t, v))
    on.sort(key=lambda tv: tv[0])
    chain = [va] + [v for _t, v in on] + [vb]

    # 3. edge pieces (existing pieces are reused: redrawing an edge "touches" it)
    for v0, v1 in zip(chain, chain[1:]):
        e = bm.edges.get((v0, v1))
        if e is None:
            e = bm.edges.new((v0, v1))
            e[lay.curve] = curve_id
            res.new_edges.append(e)
        elif e[lay.bridge]:
            e[lay.bridge] = False          # drawn over a CDT bridge: now a user edge
        res.edges.append(e)

    res.new_faces = auto_faces(bm, res.edges)
    return res


def add_polyline(bm, pts, closed, *, curve_id=0):
    res = EditResult()
    pts = [Vector(p) for p in pts]
    pairs = list(zip(pts, pts[1:]))
    if closed and len(pts) > 2:
        pairs.append((pts[-1], pts[0]))
    for a, b in pairs:
        r = add_edge(bm, a, b, curve_id=curve_id)
        res.new_verts += r.new_verts
        res.new_edges += r.new_edges
        res.new_faces += r.new_faces
        res.edges += r.edges
    res.new_faces = [f for f in res.new_faces if f.is_valid]
    return res


def add_closed_shape(bm, pts, normal, *, curve_id=0):
    """Closed planar loop (rectangle, circle, polygon); faces it creates are oriented along `normal`."""
    res = add_polyline(bm, pts, True, curve_id=curve_id)
    if normal is not None:
        for f in res.new_faces:
            orient_face(f, Vector(normal))
    return res


# ------------------------------------------------------------------------------------ auto_faces

def _planes_of_edges(edges):
    planes = []

    def add(p):
        if not any(_same_plane(p, q) for q in planes):
            planes.append(p)

    for e in edges:
        if not e.is_valid:
            continue
        for f in e.link_faces:
            add(face_plane(f))
        d = e.verts[1].co - e.verts[0].co
        for w in e.verts:
            for n in w.link_edges:
                if n is e:
                    continue
                nd = n.other_vert(w).co - w.co
                c = d.cross(nd)
                if c.length <= _COLLINEAR_SIN * d.length * nd.length:
                    continue
                add(_plane(c, w.co))
    return planes


def auto_faces(bm, edges):
    """Create/split faces around the touched `edges` (see module doc). Returns the new faces."""
    ensure_layers(bm)
    edges = [e for e in edges if e.is_valid]
    created = []
    for plane in _planes_of_edges(edges):
        touched = [e for e in edges if e.is_valid
                   and _on_plane(plane, e.verts[0].co) and _on_plane(plane, e.verts[1].co)]
        created += _process_plane(bm, plane, touched, [])
    return [f for f in created if f.is_valid]


def _arrangement(pos, edge_pairs):
    """Planar faces of a graph. pos: vert -> (x, y); edge_pairs: iterable of (va, vb).
    Returns [(outer_cycle, [hole_cycle, ...])], outer CCW, holes as traced (CW)."""
    adj = {}
    for a, b in edge_pairs:
        if a is b:
            continue
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)

    def prune():
        stack = [v for v, s in adj.items() if len(s) <= 1]
        while stack:
            v = stack.pop()
            s = adj.pop(v, None)
            if s is None:
                continue
            for w in s:
                ws = adj.get(w)
                if ws is not None:
                    ws.discard(v)
                    if len(ws) <= 1:
                        stack.append(w)

    while True:
        prune()
        order = {}
        for v, s in adj.items():
            x0, y0 = pos[v]
            order[v] = sorted(s, key=lambda w: math.atan2(pos[w][1] - y0, pos[w][0] - x0))
        index = {v: {w: i for i, w in enumerate(lst)} for v, lst in order.items()}
        seen = set()
        cycles = []
        for a in adj:
            for b in adj[a]:
                if (a, b) in seen:
                    continue
                cyc = []
                h = (a, b)
                while h not in seen:
                    seen.add(h)
                    cyc.append(h)
                    x, y = h
                    lst = order[y]
                    h = (y, lst[(index[y][x] - 1) % len(lst)])
                cycles.append(cyc)
        bridges = set()
        for cyc in cycles:
            hs = set(cyc)
            for x, y in cyc:
                if (y, x) in hs:
                    bridges.add(frozenset((x, y)))
        if not bridges:
            break
        for br in bridges:
            x, y = tuple(br)
            adj[x].discard(y)
            adj[y].discard(x)

    bounded, outers = [], []
    for cyc in cycles:
        verts = [h[0] for h in cyc]
        area = _area2([pos[v] for v in verts])
        if area > 0.0:
            bounded.append((verts, area))
        elif area < 0.0:
            outers.append(verts)
    regions = [(verts, []) for verts, _a in bounded]
    comp = {}
    for i, (verts, _a) in enumerate(bounded):
        for v in verts:
            comp.setdefault(v, set()).add(i)
    for hole in outers:
        p = pos[hole[0]]
        own = comp.get(hole[0], set())
        best, best_a = None, None
        for i, (verts, area) in enumerate(bounded):
            if i in own or hole[0] in verts:
                continue
            if _inside(p, _loop_segs([pos[v] for v in verts])):
                if best is None or area < best_a:
                    best, best_a = i, area
        if best is not None:
            regions[best][1].append(hole)
    # a component's own bounded faces must not take its vertices as holes; remove holes of the
    # same component as the face (cannot happen in a crossing-free graph, kept as a guard)
    return regions


def _orient_new(bm, faces, n_plane):
    """Orientation of a new logical face: consistent with neighbour faces, else floor → −Z."""
    fs = set(faces)
    flip_votes = keep_votes = 0
    for f in faces:
        for loop in f.loops:
            e = loop.edge
            for g in e.link_faces:
                if g in fs:
                    continue
                for gl in g.loops:
                    if gl.edge is e:
                        same = gl.vert is loop.vert
                        if same:
                            flip_votes += 1
                        else:
                            keep_votes += 1
    if flip_votes or keep_votes:
        if flip_votes > keep_votes:
            reverse_faces(bm, faces)
        return
    if abs(n_plane.z) > 1.0 - 1e-6:
        target = Vector((0.0, 0.0, -1.0))
        for f in faces:
            orient_face(f, target)


def _process_plane(bm, plane, touched, hints):
    """Re-derive the faces of one plane. hints: [(segs2d_list, material, back, normal)] = regions
    that were faces just before (dissolved or erased-to-merge) and must be recreated."""
    lay = layers(bm)
    frame = _frame(plane)
    hints = list(hints)
    touched_set = set(touched)

    def onp(v):
        return _on_plane(plane, v.co)

    pfaces = [f for f in bm.faces if all(onp(v) for v in f.verts)]
    for cl in clusters(bm, pfaces):
        bnd = _cluster_boundary(cl)
        bset = set(bnd)
        segs = _edge_segs(frame, bnd)
        hit = False
        for e in touched:
            if e in bset or not e.is_valid:
                continue
            m = _to2(frame, (e.verts[0].co + e.verts[1].co) * 0.5)
            if _inside(m, segs):
                hit = True
                break
        if hit:
            f0 = cl[0]
            f0.normal_update()
            hints.append((segs, f0.material_index, f0[lay.back], f0.normal.copy()))
            _delete_faces(bm, cl)

    pos = {}
    pairs = []
    for e in bm.edges:
        if e[lay.bridge]:
            continue
        a, b = e.verts
        if onp(a) and onp(b):
            for v in (a, b):
                if v not in pos:
                    pos[v] = _to2(frame, v.co)
            pairs.append((a, b))
    regions = _arrangement(pos, pairs)
    if not regions:
        return []

    live = [f for f in pfaces if f.is_valid]
    face_segs = [(f, _loop_segs([_to2(frame, v.co) for v in f.verts])) for f in live]
    created = []
    for outer, holes in regions:
        loops2 = [[pos[v] for v in outer]] + [[pos[v] for v in h] for h in holes]
        sp = _sample(loops2)
        if any(_inside(sp, segs) for _f, segs in face_segs):
            continue
        hint = next((h for h in hints if _inside(sp, h[0])), None)
        if hint is not None:
            _segs, mat, back, normal = hint
        else:
            outer_edges = {bm.edges.get((outer[i - 1], outer[i])) for i in range(len(outer))}
            if not (outer_edges & touched_set):
                continue
            mat, back, normal = SLOT_DEFAULT_FRONT, SLOT_DEFAULT_BACK, None
        faces = _cdt_fill(bm, frame, [outer] + holes, mat, back)
        if not faces:
            continue
        if normal is not None:
            for f in faces:
                orient_face(f, normal)
        else:
            for f in faces:
                orient_face(f, frame[0])
            _orient_new(bm, faces, frame[0])
        created += faces
    return created


# ------------------------------------------------------------------------------------------- CDT

def _cdt_fill(bm, frame, loops, material, back_material, *, keep_inner=()):
    """Fill loops (BMVert lists; [0] = outer, others = holes) with faces by
    delaunay_2d_cdt(output_type=5). Faces inside hole i are created only when i in keep_inner.
    Non-input edges created here are marked su_bridge. Returns the faces (normals along frame n)."""
    lay = layers(bm)
    coords, ids, edges_in, faces_in = [], [], [], []
    for loop in loops:
        pts = [_to2(frame, v.co) for v in loop]
        if _area2(pts) < 0.0:
            loop = list(reversed(loop))
            pts.reverse()
        base = len(coords)
        coords.extend(Vector(p) for p in pts)
        ids.extend(loop)
        k = len(loop)
        edges_in.extend((base + i, base + (i + 1) % k) for i in range(k))
        faces_in.append(list(range(base, base + k)))
    try:
        vc, ve, vf, ov, oe, of = mgeo.delaunay_2d_cdt(coords, edges_in, faces_in, 5, GEOM_TOL * 0.1, True)
    except Exception:
        return []
    n, o, u, v = frame
    omap = []
    for i, orig in enumerate(ov):
        if orig:
            omap.append(ids[orig[0]])
        else:
            x, y = vc[i]
            omap.append(bm.verts.new(o + u * x + v * y))
    bridge_pairs = []
    for k, orig in enumerate(oe):
        if not orig:
            a, b = omap[ve[k][0]], omap[ve[k][1]]
            bridge_pairs.append((a, b, bm.edges.get((a, b)) is not None))
    out = []
    keep = {0} | {i for i in keep_inner}
    for j, face in enumerate(vf):
        org = set(of[j])
        inner = org - {0}
        if 0 not in org:
            continue
        if inner and not (len(inner) == 1 and next(iter(inner)) in keep):
            continue
        verts = [omap[i] for i in face]
        if len(set(verts)) < 3:
            continue
        f = new_face(bm, verts, material=material, back_material=back_material, normal=n)
        out.append(f)
    for a, b, existed in bridge_pairs:
        e = bm.edges.get((a, b))
        if e is not None and not existed:
            e[lay.bridge] = True
    return out


def rebuild_face(bm, outer, inners, normal, material, back_material, *, through_holes=frozenset()):
    """Rebuild the planar face bounded by `outer` with holes `inners` (lists of coordinates).
    Existing faces of the plane inside the region are deleted ("the cluster"); the CDT pieces are
    created with `material`/`back_material` and normals along `normal`; non-input edges become
    su_bridge. A hole in `through_holes` stays open; any other hole gets an inner face (same
    material) unless a face already covers it. Returns the new faces."""
    ensure_layers(bm)
    res = EditResult()
    n = Vector(normal).normalized()
    outer_v = [_weld(bm, p, GEOM_TOL, res) for p in outer]
    inner_v = [[_weld(bm, p, GEOM_TOL, res) for p in loop] for loop in inners]
    plane = _plane(n, outer_v[0].co)
    frame = _frame(plane)
    for loop in [outer_v] + inner_v:
        for i in range(len(loop)):
            a, b = loop[i - 1], loop[i]
            e = bm.edges.get((a, b))
            if e is None:
                bm.edges.new((a, b))
            else:
                e[layers(bm).bridge] = False
    region_segs = []
    for loop in [outer_v] + inner_v:
        region_segs += _loop_segs([_to2(frame, v.co) for v in loop])
    old = []
    for f in bm.faces:
        if all(_on_plane(plane, v.co) for v in f.verts):
            sp = _sample([[_to2(frame, v.co) for v in f.verts]])
            if _inside(sp, region_segs):
                old.append(f)
    _delete_faces(bm, old)
    keep_inner = []
    for i, loop in enumerate(inner_v):
        if i in through_holes:
            continue
        sp = _sample([[_to2(frame, v.co) for v in loop]])
        covered = any(all(_on_plane(plane, v.co) for v in f.verts)
                      and _inside(sp, _loop_segs([_to2(frame, v.co) for v in f.verts]))
                      for f in bm.faces)
        if not covered:
            keep_inner.append(i + 1)
    faces = _cdt_fill(bm, frame, [outer_v] + inner_v, material, back_material, keep_inner=keep_inner)
    for f in faces:
        orient_face(f, n)
    return faces


# ----------------------------------------------------------------------------------------- erase

def erase_faces(bm, faces):
    """Delete faces the SketchUp way: whole logical faces go, every non-bridge edge stays."""
    ensure_layers(bm)
    fs = [f for cl in clusters(bm, [f for f in faces if f.is_valid]) for f in cl]
    return EditResult(removed_faces=_delete_faces(bm, fs))


def _coplanar_clusters(c1, c2):
    p1 = face_plane(c1[0])
    return all(_on_plane(p1, v.co) for f in c2 for v in f.verts)


def erase_edges(bm, edges):
    """Delete edges: faces bounded by them go too, except that two coplanar logical faces separated
    by an erased edge merge into one. Vertices left alone are removed; a vertex left with exactly
    two collinear edges is dissolved (the split edge becomes whole again)."""
    lay = ensure_layers(bm)
    edges = [e for e in set(edges) if e.is_valid and not e[lay.bridge]]
    if not edges:
        return EditResult()
    adj_faces = {f for e in edges for f in e.link_faces}
    cls = clusters(bm, list(adj_faces))
    cid = {f: i for i, cl in enumerate(cls) for f in cl}
    parent = list(range(len(cls)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    doomed_cl = set()
    for e in edges:
        ids = sorted({cid[f] for f in e.link_faces})
        if len(ids) == 2 and _coplanar_clusters(cls[ids[0]], cls[ids[1]]):
            parent[find(ids[0])] = find(ids[1])
        else:
            doomed_cl.update(ids)
    groups = {}
    for i in range(len(cls)):
        groups.setdefault(find(i), []).append(i)
    doomed_roots = {find(i) for i in doomed_cl}

    merges = []      # (plane, hint)
    for root, members in groups.items():
        if root in doomed_roots or len(members) < 2:
            continue
        f0 = cls[members[0]][0]
        f0.normal_update()
        plane = face_plane(f0)
        frame = _frame(plane)
        segs = []
        for i in members:
            segs.append(_edge_segs(frame, _cluster_boundary(cls[i])))
        merges.append((plane, segs, f0.material_index, f0[lay.back], f0.normal.copy()))

    removed = _delete_faces(bm, [f for cl in cls for f in cl])
    verts = {v for e in edges for v in e.verts}
    bmesh.ops.delete(bm, geom=edges, context='EDGES')
    verts = [v for v in verts if v.is_valid]
    loose = [v for v in verts if not v.link_edges]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    _dissolve_collinear(bm, [v for v in verts if v.is_valid])

    created = []
    for plane, segs_list, mat, back, normal in merges:
        hints = [(segs, mat, back, normal) for segs in segs_list]
        created += _process_plane(bm, plane, [], hints)
    return EditResult(new_faces=[f for f in created if f.is_valid], removed_faces=removed)


def _dissolve_collinear(bm, verts):
    lay = layers(bm)
    for v in verts:
        if not v.is_valid or len(v.link_edges) != 2:
            continue
        e1, e2 = v.link_edges
        if any(e[lay.bridge] for e in (e1, e2)):
            continue
        if (e1[lay.soft], e1[lay.hidden], e1[lay.curve]) != (e2[lay.soft], e2[lay.hidden], e2[lay.curve]):
            continue
        d1 = e1.other_vert(v).co - v.co
        d2 = e2.other_vert(v).co - v.co
        if d1.cross(d2).length > _COLLINEAR_SIN * d1.length * d2.length or d1.dot(d2) >= 0.0:
            continue
        bmesh.ops.dissolve_verts(bm, verts=[v])


def merge_coplanar(bm, edges):
    """Erase those `edges` that only separate two coplanar logical faces (they merge)."""
    lay = ensure_layers(bm)
    pick = []
    for e in edges:
        if not e.is_valid or e[lay.bridge]:
            continue
        cl = clusters(bm, list(e.link_faces))
        if len(cl) == 2 and _coplanar_clusters(cl[0], cl[1]):
            pick.append(e)
    return erase_edges(bm, pick) if pick else EditResult()


# -------------------------------------------------------------------------------------- validate

def validate(bm, tol=GEOM_TOL):
    """Invariants of a document mesh; returns a list of problems (empty = valid)."""
    lay = ensure_layers(bm)
    out = []
    from mathutils.kdtree import KDTree
    kd = KDTree(len(bm.verts))
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()
    bm.verts.ensure_lookup_table()
    for i, v in enumerate(bm.verts):
        for _co, j, _d in kd.find_range(v.co, tol):
            if j > i:
                out.append("duplicate vertices {:d} {:d}".format(i, j))
    for e in bm.edges:
        if e.calc_length() <= tol:
            out.append("zero-length edge {:d}".format(e.index))
        if e[lay.bridge] and not e.link_faces:
            out.append("wire bridge edge {:d}".format(e.index))
    for f in bm.faces:
        if len(set(f.verts)) != len(f.verts):
            out.append("face {:d} repeats a vertex".format(f.index))
        if f.calc_area() <= tol * tol:
            out.append("zero-area face {:d}".format(f.index))
        if not is_planar(f, tol * 10):
            out.append("non-planar face {:d}".format(f.index))
        if f.normal.length < 0.5:
            out.append("face {:d} without normal".format(f.index))
        if f[lay.back] < 0:
            out.append("face {:d} su_back_mat < 0".format(f.index))
    return out


# --------------------------------------------------------------------------------- point helpers

def circle_points(center, normal, radius, sides=CIRCLE_SIDES, start_dir=None):
    n = Vector(normal).normalized()
    u = (Vector(start_dir) - n * n.dot(start_dir)).normalized() if start_dir is not None else n.orthogonal().normalized()
    v = n.cross(u)
    c = Vector(center)
    return [c + (u * math.cos(2 * math.pi * i / sides) + v * math.sin(2 * math.pi * i / sides)) * radius
            for i in range(sides)]


def arc_points(center, normal, start, angle, segments=ARC_SEGMENTS):
    """Points from `start` around `center` (right hand about `normal`) through `angle` radians."""
    n = Vector(normal).normalized()
    c = Vector(center)
    r = Vector(start) - c
    u = r.normalized()
    v = n.cross(u)
    rad = r.length
    return [c + (u * math.cos(angle * i / segments) + v * math.sin(angle * i / segments)) * rad
            for i in range(segments + 1)]


def arc_from_bulge(a, b, bulge, normal, segments=ARC_SEGMENTS):
    """Two-point arc: chord a→b, sagitta `bulge` (signed: + = towards normal × (b − a))."""
    a, b, n = Vector(a), Vector(b), Vector(normal).normalized()
    chord = b - a
    half = chord.length * 0.5
    if abs(bulge) <= GEOM_TOL or half <= GEOM_TOL:
        return [a, b]
    side = n.cross(chord).normalized()
    apex = (a + b) * 0.5 + side * bulge
    radius = (half * half + bulge * bulge) / (2.0 * abs(bulge))
    center = apex - side * math.copysign(radius, bulge)
    u = (a - center).normalized()
    v = n.cross(u)

    def ang(p):
        w = p - center
        t = math.atan2(w.dot(v), w.dot(u))
        return t + 2.0 * math.pi if t < 0.0 else t

    ang_b, ang_apex = ang(b), ang(apex)
    sweep = ang_b if ang_apex < ang_b else ang_b - 2.0 * math.pi
    return [center + (u * math.cos(sweep * i / segments) + v * math.sin(sweep * i / segments)) * radius
            for i in range(segments + 1)]
