# SPDX-License-Identifier: GPL-2.0-or-later
"""Drawing kernels of agent E (owner: E). Contract: PLANO.md §2.4 (E/F/G kernels), behaviour §6.2.

    snap = snapshot(doc); ...; restore(doc, snap)      # re-apply of the last action ("Ajustar")
    s = PushPullSession(doc, lface, keep_original)     # Empurrar/puxar (live preview)
    s.update(distance); s.finish() -> EditResult; s.cancel(); s.moving_faces

Pure bmesh + B's kernel (geom/entities); no bpy context except the temporary mesh of restore().
"""

import bmesh
import bpy
from mathutils import Vector

from . import geom

ORDER = 125


# ------------------------------------------------------------------------------------ snapshots

def snapshot(doc):
    """Independent copy of the document's BMesh (free it with release())."""
    return doc.bm.copy()


def release(snap):
    if snap is not None and snap.is_valid:
        snap.free()


def restore(doc, snap):
    """Replace the document's BMesh contents by `snap` (layers included); nothing is written."""
    bm = doc.bm
    me = bpy.data.meshes.new("su_restore_tmp")
    try:
        snap.to_mesh(me)
        bm.clear()
        bm.from_mesh(me)
    finally:
        bpy.data.meshes.remove(me)
    geom.ensure_layers(bm)
    for f in bm.faces:
        f.normal_update()
    bm.verts.index_update()
    bm.edges.index_update()
    bm.faces.index_update()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    return bm


# ------------------------------------------------------------------------------------ point queries

PLANE_TOL = 1e-5


def _frame(n):
    n = Vector(n).normalized()
    u = n.orthogonal().normalized()
    return n, u, n.cross(u)


def point_in_face(face, p, tol=PLANE_TOL):
    """True when world-local point `p` lies on the plane of `face` and inside its polygon."""
    face.normal_update()
    n = face.normal
    if n.length < 0.5:
        return False
    c = face.verts[0].co
    if abs(n.dot(p - c)) > tol * 10:
        return False
    _n, u, w = _frame(n)
    px, py = p.dot(u), p.dot(w)
    pts = [(v.co.dot(u), v.co.dot(w)) for v in face.verts]
    inside = False
    k = len(pts)
    for i in range(k):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        if (y0 > py) != (y1 > py):
            x = x0 + (py - y0) * (x1 - x0) / (y1 - y0)
            if x > px:
                inside = not inside
    return inside


def faces_at(bm, p, normal=None, exclude=()):
    """Faces containing point p (optionally with a normal parallel to `normal`)."""
    out = []
    for f in bm.faces:
        if f in exclude:
            continue
        if normal is not None:
            f.normal_update()
            if abs(abs(f.normal.dot(normal)) - 1.0) > 1e-5:
                continue
        if point_in_face(f, p):
            out.append(f)
    return out


def loop_sample(cos):
    """A point strictly inside the planar polygon `cos` (centroid of its first triangle)."""
    from mathutils.geometry import tessellate_polygon
    cos = [Vector(c) for c in cos]
    tris = tessellate_polygon([cos])
    if not tris:
        return sum(cos, Vector()) / len(cos)
    best = max(tris, key=lambda t: (cos[t[1]] - cos[t[0]]).cross(cos[t[2]] - cos[t[0]]).length)
    return (cos[best[0]] + cos[best[1]] + cos[best[2]]) / 3.0


def _sample_point(face):
    """A point strictly inside `face`."""
    return loop_sample([v.co for v in face.verts])


# ------------------------------------------------------------------------------------ Empurrar/puxar

def _on_plane(co, c, n, tol=PLANE_TOL):
    return abs((co - c).dot(n)) <= tol


def is_lone(bm, cluster):
    """True when the coplanar region around `cluster` has no out-of-plane neighbour (a flat sheet:
    the original face stays as the cap of the new solid)."""
    f0 = cluster[0]
    f0.normal_update()
    n, c = f0.normal.copy(), f0.verts[0].co.copy()
    seen = set(cluster)
    stack = list(cluster)
    while stack:
        f = stack.pop()
        for e in f.edges:
            for g in e.link_faces:
                if g in seen:
                    continue
                if all(_on_plane(v.co, c, n) for v in g.verts):
                    seen.add(g)
                    stack.append(g)
                else:
                    return False
    return True


def pushpull(bm, face_ids, distance, keep_original=False, soft_ids=None, curve_map=None):
    """Empurrar/puxar the logical face containing faces `face_ids` by `distance` along its normal.
    Returns dict(moved=[faces], sides=[faces], perforated=bool, kept=bool) (faces valid until the next
    edit). SketchUp rules: side faces along every boundary edge; a side coplanar with a neighbour face
    extends it (pull) or cuts it (push); the moved face landing on a coplanar face perforates both; the
    original face stays only for a flat sheet (lone) or with Option (keep_original).
    soft_ids: curve ids whose sides become soft/smooth (circles, arcs; not polygons);
    curve_map: {old curve id: new curve id} for the moved copy of boundary curves."""
    soft_ids = set(soft_ids or ())
    curve_map = dict(curve_map or {})
    from . import entities
    lay = geom.ensure_layers(bm)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    out = {"moved": [], "sides": [], "perforated": False, "kept": False}
    if abs(distance) <= geom.GEOM_TOL:
        return out
    f0 = bm.faces[face_ids[0]]
    lf = entities.logical_face(bm, f0)
    cluster = list(lf.faces)
    cset = set(cluster)
    n = lf.plane[0].normalized()
    mv = n * distance
    u = n if distance > 0.0 else -n
    lone = is_lone(bm, cluster)
    keep = bool(keep_original) or lone
    nt = u.copy() if lone and not keep_original else n.copy()
    mat, back = f0.material_index, f0[lay.back]
    samples = [_sample_point(f) for f in cluster]
    # holes of the face that are open (no face inside): the moved copy must stay open too
    open_holes = []
    for loop in lf.inner_loops:
        hs = loop_sample([v.co for v in loop])
        if not faces_at(bm, hs, n, exclude=cset):
            open_holes.append(hs)

    # boundary edges (x→y with the face on the left around n) and their classification
    bnd = []
    for loop in [lf.outer_loop] + lf.inner_loops:
        k = len(loop)
        for i in range(k):
            x, y = loop[i], loop[(i + 1) % k]
            e = bm.edges.get((x, y))
            if e is None:
                continue
            kind, g_normal = "NEW", None
            if not keep:
                for g in e.link_faces:
                    if g in cset:
                        continue
                    g.normal_update()
                    if abs(g.normal.dot(n)) > 1e-6:
                        continue
                    gl = next((l for l in g.loops if l.edge is e), None)
                    if gl is None:
                        continue
                    a, b = (x, y) if gl.vert is x else (y, x)
                    interior = g.normal.cross(b.co - a.co)
                    kind = "IN" if interior.dot(mv) > 0.0 else "OUT"
                    g_normal = g.normal.copy()
                    break
            w_out = (y.co - x.co).cross(n).normalized()
            cid = e[lay.curve]
            bnd.append({"x": x.co.copy(), "y": y.co.copy(), "kind": kind, "w_out": w_out, "curve": cid,
                        "gn": g_normal})
    verts = []
    for loop in [lf.outer_loop] + lf.inner_loops:
        verts += [v.co.copy() for v in loop]
    # vertex → curve ids of its two boundary edges (soft connectors between edges of one curve)
    vcurves = {}
    for b in bnd:
        for key in (b["x"].to_tuple(6), b["y"].to_tuple(6)):
            vcurves.setdefault(key, []).append(b["curve"])

    # perforation target: an existing face where the moved face lands
    moved_samples = [s + mv for s in samples]
    target = [f for f in faces_at(bm, moved_samples[0], n, exclude=cset)] if moved_samples else []
    perforate = bool(target)

    # 1. the original face goes (faces only; its bridges too) unless kept
    if keep:
        out["kept"] = True
    else:
        bridges = {e for f in cluster for e in f.edges if e[lay.bridge]}
        bmesh.ops.delete(bm, geom=cluster, context='FACES_ONLY')
        wire = [e for e in bridges if e.is_valid and not e.link_faces]
        if wire:
            bmesh.ops.delete(bm, geom=wire, context='EDGES')

    # 2. moved loops, then the connectors (B's add_edge welds/splits and makes the faces)
    for b in bnd:
        geom.add_edge(bm, b["x"] + mv, b["y"] + mv, curve_id=curve_map.get(b["curve"], 0))
    seen = set()
    for co in verts:
        key = co.to_tuple(6)
        if key in seen:
            continue
        seen.add(key)
        geom.add_edge(bm, co, co + mv)

    def edge_at(a, c):
        va = _vert_at(bm, a)
        vc = _vert_at(bm, c)
        if va is None or vc is None:
            return None
        return bm.edges.get((va, vc))

    # 3. coplanar sides: pushing in cuts the neighbour, pulling out extends it
    cut_regions, merge_edges = [], []
    for b in bnd:
        if b["kind"] == "IN":
            cut_regions.append(((b["x"] + b["y"]) * 0.5 + mv * 0.5, b["gn"]))
        elif b["kind"] == "OUT":
            e = edge_at(b["x"], b["y"])
            if e is not None:
                merge_edges.append(e)
    for p, gn in cut_regions:
        fs = faces_at(bm, p, gn)
        if fs:
            geom.erase_faces(bm, fs)
    if merge_edges:
        geom.erase_edges(bm, [e for e in merge_edges if e.is_valid])

    # 3b. open holes stay open on the moved face
    for hs in open_holes:
        fs = faces_at(bm, hs + mv, n)
        if fs:
            geom.erase_faces(bm, fs)

    # 4. perforation: the moved face and the face it landed on disappear together
    if perforate:
        for s in moved_samples:
            fs = faces_at(bm, s, n)
            if fs:
                geom.erase_faces(bm, fs)
        out["perforated"] = True

    # 5. wire left by the operation (old boundary under cut sides, connectors without faces)
    cand = []
    for b in bnd:
        cand.append(edge_at(b["x"], b["y"]))
        cand.append(edge_at(b["x"] + mv, b["y"] + mv))
    for co in verts:
        cand.append(edge_at(co, co + mv))
    wire = list({e for e in cand if e is not None and e.is_valid and not e.link_faces})
    if wire:
        vs = {v for e in wire for v in e.verts}
        bmesh.ops.delete(bm, geom=wire, context='EDGES')
        loose = [v for v in vs if v.is_valid and not v.link_edges]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context='VERTS')

    # 6. orientation: moved face along nt, sides consistent with it, a kept sheet faces away
    moved = []
    if not perforate:
        for s in moved_samples:
            for f in faces_at(bm, s, n):
                if f not in moved:
                    moved.append(f)
        for f in moved:
            geom.orient_face(f, nt)
            f.material_index = mat
            f[lay.back] = back
    sgn = 1.0 if nt.dot(u) > 0.0 else -1.0
    sides = []
    for b in bnd:
        if b["kind"] != "NEW":
            continue
        p = (b["x"] + b["y"]) * 0.5 + mv * 0.5
        for f in faces_at(bm, p, b["w_out"]):
            geom.orient_face(f, b["w_out"] * sgn)
            if f not in sides:
                sides.append(f)
            if b["curve"] and b["curve"] in soft_ids:
                f.smooth = True
    if keep and lone and not keep_original:
        for s in samples:
            for f in faces_at(bm, s, n):
                geom.orient_face(f, -u)
    # 7. sides of a curve are soft (connectors between two edges of the same curve)
    if soft_ids:
        for co in verts:
            cids = vcurves.get(co.to_tuple(6), [])
            if len(cids) == 2 and cids[0] in soft_ids and cids[0] == cids[1]:
                e = edge_at(co, co + mv)
                if e is not None:
                    e[lay.soft] = True
                    e.smooth = True
    for f in bm.faces:
        f.normal_update()
    out["moved"], out["sides"] = moved, sides
    return out


def _vert_at(bm, co, tol=geom.GEOM_TOL * 10):
    for v in bm.verts:
        if (v.co - co).length <= tol:
            return v
    return None


class PushPullSession:
    """Live Empurrar/puxar on a document: doc.begin() once; update() rebuilds from the snapshot."""

    def __init__(self, doc, lface, keep_original=False):
        self.doc = doc
        bm = doc.bm
        bm.faces.index_update()
        faces = lface.faces if hasattr(lface, "faces") else [bm.faces[i] for i in lface]
        self.face_ids = sorted(f.index for f in faces)
        faces[0].normal_update()
        self._normal = faces[0].normal.copy()
        self.keep_original = keep_original
        self.distance = 0.0
        self.moving_faces = set()
        self.result = None
        self.soft_ids, self.curve_map, self._metas = self._curve_plan(doc, faces)
        doc.begin()

    @staticmethod
    def _curve_plan(doc, faces):
        """Soft curve ids (circle/arc) and new ids for the moved copy of the boundary curves."""
        from . import entities
        lay = geom.ensure_layers(doc.bm)
        cids = sorted({e[lay.curve] for f in faces for e in f.edges if e[lay.curve]})
        soft, cmap, metas = set(), {}, {}
        nxt = entities.new_curve_id(doc) if cids else 0
        for cid in cids:
            meta = entities.get_curve_meta(doc, cid)
            if not (isinstance(meta, dict) and meta.get("kind") == "polygon"):
                soft.add(cid)
            cmap[cid] = nxt
            metas[nxt] = meta
            nxt += 1
        return soft, cmap, metas

    def _apply(self, distance):
        doc = self.doc
        doc.cancel()
        doc.begin()
        bm = doc.bm
        bm.faces.index_update()
        bm.faces.ensure_lookup_table()
        self.distance = distance
        self.result = pushpull(bm, self.face_ids, distance, self.keep_original, self.soft_ids, self.curve_map)
        return bm

    def update(self, distance):
        self._apply(distance)
        r = self.result
        self.doc.preview_write()
        self.moving_faces = {f.index for f in r["moved"] + r["sides"] if f.is_valid}

    def finish(self):
        """Final geometry in doc.bm (not written: the caller writes it with its undo step)."""
        self._apply(self.distance)
        self._write_curve_meta()
        res = geom.EditResult(new_faces=[f for f in self.result["moved"] + self.result["sides"] if f.is_valid])
        return res

    def _write_curve_meta(self):
        """Metadata of the moved curves (center moved with the face)."""
        from . import entities
        if not self.curve_map:
            return
        bm = self.doc.bm
        bm.faces.ensure_lookup_table()
        n = self._normal
        for new, meta in self._metas.items():
            if not isinstance(meta, dict):
                continue
            m = dict(meta)
            c = m.get("center")
            if c is not None and n is not None:
                m["center"] = list(Vector(c) + n * self.distance)
            entities.set_curve_meta(self.doc, new, m)

    def cancel(self):
        self.doc.cancel()
        self.moving_faces = set()


# ------------------------------------------------------------------------------------ Equidistância

def _area2(pts, n):
    _n, u, w = _frame(n)
    a = 0.0
    k = len(pts)
    for i in range(k):
        p, q = pts[i - 1], pts[i]
        a += p.dot(u) * q.dot(w) - q.dot(u) * p.dot(w)
    return a * 0.5


def offset_loop(pts, n, d):
    """Mitred offset of a closed loop whose material lies on the LEFT (n × direction) by d (+ = into the
    material). Collinear vertices stay. Returns the new points (None when the loop collapses/inverts)."""
    pts = [Vector(p) for p in pts]
    n = Vector(n).normalized()
    k = len(pts)
    out = []
    for i in range(k):
        e0 = (pts[i] - pts[i - 1]).normalized()
        e1 = (pts[(i + 1) % k] - pts[i]).normalized()
        l0, l1 = n.cross(e0), n.cross(e1)
        den = 1.0 + l0.dot(l1)
        if den < 1e-6:
            return None
        out.append(pts[i] + (l0 + l1) * (d / den))
    a0, a1 = _area2(pts, n), _area2(out, n)
    if a0 * a1 <= 0.0 or abs(a1) <= geom.GEOM_TOL:
        return None
    # an edge that flipped direction = the offset went past a corner
    for i in range(k):
        if (out[(i + 1) % k] - out[i]).dot(pts[(i + 1) % k] - pts[i]) <= 0.0:
            return None
    return out


def face_loops(bm, face_idx):
    """(normal, [loops of coordinates with the material on the left]) of the logical face of a face."""
    from . import entities
    bm.faces.ensure_lookup_table()
    lf = entities.logical_face(bm, bm.faces[face_idx])
    n = lf.plane[0].normalized()
    return n, [[v.co.copy() for v in lf.outer_loop]] + [[v.co.copy() for v in loop] for loop in lf.inner_loops]


def offset_face_loops(bm, face_idx, distance):
    """Offset loops of a logical face (outer shrinks / holes grow for distance > 0), or None."""
    n, loops = face_loops(bm, face_idx)
    out = []
    for loop in loops:
        o = offset_loop(loop, n, distance)
        if o is None:
            return None
        out.append(o)
    return out


def offset_faces(bm, lface, distance, allow_overlap=False):
    """Equidistância on a logical face (face index or LogicalFace): new edge loops at `distance` inside
    (+) or outside (−) every boundary loop. The regions are rebuilt with B's rebuild_face (CDT) after the
    original face is erased — adding the loops with add_edge would split the face's CDT bridges and leave
    extra vertices on the new edges. Returns EditResult or None."""
    from . import entities
    idx = lface if isinstance(lface, int) else lface.faces[0].index
    bm.faces.ensure_lookup_table()
    f0 = bm.faces[idx]
    lay = geom.ensure_layers(bm)
    mat, back = f0.material_index, f0[lay.back]
    n, loops = face_loops(bm, idx)
    new = offset_face_loops(bm, idx, distance)
    if new is None:
        return None
    outer, holes = loops[0], loops[1:]
    o2, h2 = new[0], new[1:]
    lf = entities.logical_face(bm, f0)
    faces = []
    if distance > 0.0:
        geom.erase_faces(bm, lf.faces)
        faces += geom.rebuild_face(bm, outer, [o2], n, mat, back, through_holes=frozenset({0}))
        faces += geom.rebuild_face(bm, o2, h2, n, mat, back, through_holes=frozenset(range(len(h2))))
        for h, hh in zip(holes, h2):
            faces += geom.rebuild_face(bm, hh, [h], n, mat, back, through_holes=frozenset({0}))
    else:
        faces += geom.rebuild_face(bm, o2, [outer], n, mat, back, through_holes=frozenset({0}))
        for h, hh in zip(holes, h2):
            faces += geom.rebuild_face(bm, h, [hh], n, mat, back, through_holes=frozenset({0}))
    res = geom.EditResult()
    res.new_faces = [f for f in faces if f.is_valid]
    return res


def boundary_distance(loops, n, p):
    """Signed distance from p (on the plane) to the loops: + inside the material, − outside."""
    best = None
    for loop in loops:
        k = len(loop)
        for i in range(k):
            a, b = loop[i], loop[(i + 1) % k]
            ab = b - a
            t = 0.0 if ab.length_squared == 0.0 else max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
            d = (p - (a + ab * t)).length
            if best is None or d < best:
                best = d
    if best is None:
        return 0.0
    inside = _inside_loops(loops, n, p)
    return best if inside else -best


def _inside_loops(loops, n, p):
    _n, u, w = _frame(n)
    px, py = p.dot(u), p.dot(w)
    inside = False
    for loop in loops:
        pts = [(v.dot(u), v.dot(w)) for v in loop]
        k = len(pts)
        for i in range(k):
            x0, y0 = pts[i - 1]
            x1, y1 = pts[i]
            if (y0 > py) != (y1 > py):
                x = x0 + (py - y0) * (x1 - x0) / (y1 - y0)
                if x > px:
                    inside = not inside
    return inside


# ------------------------------------------------------------------------------------ Siga-me

def _newell(pts):
    n = Vector()
    k = len(pts)
    for i in range(k):
        a, b = pts[i], pts[(i + 1) % k]
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    return n.normalized() if n.length > 1e-12 else n


def order_path(edges_pts):
    """[(a, b)] segments (coordinates) → (ordered points, closed) of one connected chain, or None."""
    segs = [(Vector(a), Vector(b)) for a, b in edges_pts]
    if not segs:
        return None

    def key(p):
        return p.to_tuple(5)

    adj = {}
    for a, b in segs:
        adj.setdefault(key(a), []).append(b)
        adj.setdefault(key(b), []).append(a)
        if len(adj[key(a)]) > 2 or len(adj[key(b)]) > 2:
            return None
    ends = [k for k, v in adj.items() if len(v) == 1]
    closed = not ends
    start = segs[0][0] if closed else Vector(next(k for k in ends))
    pts = [start]
    prev = None
    cur = start
    while True:
        nxt = [p for p in adj[key(cur)] if prev is None or key(p) != key(prev)]
        if not nxt:
            break
        p = nxt[0]
        if closed and key(p) == key(start):
            break
        pts.append(p)
        prev, cur = cur, p
        if len(pts) > len(segs) + 1:
            return None
    if len(pts) - (0 if closed else 1) != len(segs):
        return None
    return pts, closed


def follow_me(bm, profile, path, closed, smooth_from_curve=False):
    """Siga-me: sweep the logical face `profile` (face index) along `path` (points in the document's
    space, ordered; `closed` = loop) with mitred joints. Open path: the profile is the start cap (it is
    kept) and a new end cap closes the solid; the path end nearest the profile is the start. Closed path:
    the sweep starts at the path vertex nearest the profile and the profile face is removed. Returns dict
    (faces=[...], ok=bool)."""
    from . import entities
    lay = geom.ensure_layers(bm)
    bm.faces.ensure_lookup_table()
    f0 = bm.faces[profile]
    lf = entities.logical_face(bm, f0)
    n_p = lf.plane[0].normalized()
    mat, back = f0.material_index, f0[lay.back]
    loops = [[v.co.copy() for v in lf.outer_loop]] + [[v.co.copy() for v in l] for l in lf.inner_loops]
    curve_profile = [[v for v in loop] for loop in [lf.outer_loop] + lf.inner_loops]
    pcurves = []
    for loop in curve_profile:
        k = len(loop)
        cids = []
        for i in range(k):
            e = bm.edges.get((loop[i], loop[(i + 1) % k]))
            cids.append(e[lay.curve] if e is not None else 0)
        pcurves.append(cids)
    centroid = sum(loops[0], Vector()) / len(loops[0])
    P = [Vector(p) for p in path]
    if closed and len(P) > 2 and (P[0] - P[-1]).length <= geom.GEOM_TOL:
        P = P[:-1]
    if len(P) < 2 or (closed and len(P) < 3):
        return {"ok": False, "faces": []}
    if closed:
        i0 = min(range(len(P)), key=lambda i: (P[i] - centroid).length)
        P = P[i0:] + P[:i0]
    elif (P[-1] - centroid).length < (P[0] - centroid).length:
        P.reverse()
    m = len(P)
    nseg = m if closed else m - 1
    D = [(P[(k + 1) % m] - P[k]).normalized() for k in range(nseg)]
    M = []
    for i in range(m if closed else m):
        if closed:
            M.append((D[i - 1] + D[i % nseg]).normalized())
        elif i == 0:
            M.append(D[0].copy())
        elif i == m - 1:
            M.append(D[-1].copy())
        else:
            M.append((D[i - 1] + D[i]).normalized())

    def project(pts, d, co, nrm):
        out = []
        for p in pts:
            den = d.dot(nrm)
            if abs(den) < 1e-9:
                return None
            t = (co - p).dot(nrm) / den
            out.append(p + d * t)
        return out

    stations = m + 1 if closed else m
    rings = []
    first = []
    for loop in loops:
        r = project(loop, D[0], P[0], M[0]) if closed else [p.copy() for p in loop]
        if r is None:
            return {"ok": False, "faces": []}
        first.append(r)
    rings.append(first)
    for i in range(1, stations):
        si = i % m
        d = D[i - 1]
        nxt = []
        for r in rings[-1]:
            q = project(r, d, P[si], M[si])
            if q is None:
                return {"ok": False, "faces": []}
            nxt.append(q)
        rings.append(nxt)
    if closed:
        rings[-1] = rings[0]
    flip = n_p.dot(D[0]) > 0.0          # the profile front looks into the sweep: build inside-out, then flip

    # faces that exist before the sweep (a face B's kernel recreates in their place is not "new")
    old = []
    for f in bm.faces:
        if f in lf.faces and closed:
            continue
        f.normal_update()
        old.append((f.normal.copy(), [v.co.copy() for v in f.verts]))
    if closed:
        geom.erase_faces(bm, lf.faces)
    # edges: rings (except the profile itself) and longitudinal edges
    for i in range(1, stations if not closed else stations - 1):
        for r in rings[i]:
            k = len(r)
            for j in range(k):
                geom.add_edge(bm, r[j], r[(j + 1) % k])
    if closed:
        for r in rings[0]:
            k = len(r)
            for j in range(k):
                geom.add_edge(bm, r[j], r[(j + 1) % k])
    for i in range(stations - 1):
        for li, r in enumerate(rings[i]):
            for j in range(len(r)):
                geom.add_edge(bm, r[j], rings[i + 1][li][j])
    # no faces in the mitre planes (inside the solid)
    inner_stations = range(0, stations - 1) if closed else range(1, stations - 1)
    for i in inner_stations:
        s = loop_sample(rings[i][0])
        fs = [f for f in faces_at(bm, s, M[i % m])]
        if fs:
            geom.erase_faces(bm, fs)
    # orientation: sides consistent with the profile (x→y around n_p ⇒ side (y, x, x', y'))
    faces = []
    sgn = -1.0 if flip else 1.0
    for i in range(stations - 1):
        for li, r in enumerate(rings[i]):
            k = len(r)
            for j in range(k):
                a, b = r[j], r[(j + 1) % k]
                a2, b2 = rings[i + 1][li][j], rings[i + 1][li][(j + 1) % k]
                want = _newell([b, a, a2, b2]) * sgn
                c = (a + b + a2 + b2) / 4.0
                for f in faces_at(bm, c, want):
                    geom.orient_face(f, want)
                    f.material_index, f[lay.back] = mat, back
                    if f not in faces:
                        faces.append(f)
                    if pcurves[li][j] or smooth_from_curve:
                        f.smooth = True
    if not closed:
        s = loop_sample(rings[-1][0])
        for f in faces_at(bm, s, M[-1]):
            geom.orient_face(f, D[-1] * (1.0 if not flip else 1.0))
            f.material_index, f[lay.back] = mat, back
            faces.append(f)
        s0 = loop_sample(rings[0][0])
        for f in faces_at(bm, s0, n_p):
            geom.orient_face(f, -D[0])
    # soft edges: along a curved path (mitre ring edges) and along a curved profile (longitudinal edges)
    if smooth_from_curve:
        for i in (range(1, stations - 1) if not closed else range(0, stations - 1)):
            for r in rings[i]:
                k = len(r)
                for j in range(k):
                    e = _edge_between(bm, r[j], r[(j + 1) % k])
                    if e is not None:
                        e[lay.soft] = True
                        e.smooth = False
    for li, r in enumerate(rings[0]):
        k = len(r)
        cids = pcurves[li]
        for j in range(k):
            if cids[j] and cids[j] == cids[j - 1]:
                for i in range(stations - 1):
                    e = _edge_between(bm, rings[i][li][j], rings[i + 1][li][j])
                    if e is not None:
                        e[lay.soft] = True
    # loops of the new edges can close planar regions that are not part of the sweep (e.g. the inner rim
    # of a moulding): remove every face that is neither swept nor where a face was before
    keep = set(faces)
    extra = []
    for f in bm.faces:
        if f in keep:
            continue
        f.normal_update()
        s = _sample_point(f)
        if not any(abs(abs(n.dot(f.normal)) - 1.0) < 1e-5 and abs(n.dot(s - pts[0])) <= PLANE_TOL * 10
                   and _inside_loops([pts], n, s) for n, pts in old):
            extra.append(f)
    if extra:
        bridges = {e for f in extra for e in f.edges if e[lay.bridge]}
        bmesh.ops.delete(bm, geom=extra, context='FACES_ONLY')
        wire = [e for e in bridges if e.is_valid and not e.link_faces]
        if wire:
            bmesh.ops.delete(bm, geom=wire, context='EDGES')
    for f in bm.faces:
        f.normal_update()
    return {"ok": True, "faces": [f for f in faces if f.is_valid]}


def _edge_between(bm, a, b):
    va, vb = _vert_at(bm, a), _vert_at(bm, b)
    if va is None or vb is None:
        return None
    return bm.edges.get((va, vb))


def register():
    pass


def unregister():
    pass
