# SPDX-License-Identifier: GPL-2.0-or-later
"""Entities on top of the BMesh (owner: B). Contract: PLANO.md §2.4-B, §3.1.

The ONE rule of "what is an entity" used by Selecionar / Apagar / Pintura / pre-highlight:
  * edge with su_curve != 0      → CURVE   (every connected edge with the same curve id)
  * other edge                   → EDGE
  * face touching a su_soft edge → SURFACE (flood fill across su_soft edges, whole logical faces)
  * other face                   → FACE    (the logical face: bmesh pieces joined by su_bridge)
Curve metadata (center, radius, sides, kind…) lives in obj.su_doc.curves as JSON {cid: meta}.
"""

import json
from dataclasses import dataclass

from . import geom

ORDER = 122


@dataclass
class LogicalFace:
    faces: list            # BMFaces (pieces joined by su_bridge)
    outer_loop: list       # BMVerts, CCW around the face normal
    inner_loops: list      # [[BMVert]] (holes), CW around the face normal
    plane: tuple           # (normal, d) — normal = the face's normal


def _ensure_tables(bm):
    bm.edges.index_update()
    bm.faces.index_update()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()


def _chain_loops(edges):
    """Boundary edges → closed vertex loops (a vertex used by >2 boundary edges is walked greedily)."""
    remaining = set(edges)
    loops = []
    while remaining:
        e = remaining.pop()
        start, cur = e.verts
        loop = [start]
        while cur is not start:
            loop.append(cur)
            nxt = next((x for x in cur.link_edges if x in remaining), None)
            if nxt is None:
                break
            remaining.discard(nxt)
            cur = nxt.other_vert(cur)
        loops.append(loop)
    return loops


def logical_face(bm, face):
    """The logical face that contains `face` (flood fill through su_bridge)."""
    geom.ensure_layers(bm)
    faces = geom.clusters(bm, [face])[0]
    face.normal_update()
    n = face.normal.copy()
    plane = (n, n.dot(face.verts[0].co))
    u = n.orthogonal().normalized()
    w = n.cross(u)
    loops = _chain_loops(geom._cluster_boundary(faces))
    scored = []
    for loop in loops:
        area = geom._area2([(v.co.dot(u), v.co.dot(w)) for v in loop])
        scored.append((abs(area), area, loop))
    scored.sort(key=lambda s: -s[0])
    outer = scored[0][2] if scored[0][1] > 0 else list(reversed(scored[0][2]))
    inners = [loop if area < 0 else list(reversed(loop)) for _a, area, loop in scored[1:]]
    return LogicalFace(faces=faces, outer_loop=outer, inner_loops=inners, plane=plane)


def surface(bm, face):
    """Smooth surface containing `face`: flood fill across su_soft edges (whole logical faces)."""
    lay = geom.ensure_layers(bm)
    seen = {face}
    stack = [face]
    out = []
    while stack:
        f = stack.pop()
        out.append(f)
        for e in f.edges:
            if not (e[lay.soft] or e[lay.bridge]):
                continue
            for g in e.link_faces:
                if g not in seen:
                    seen.add(g)
                    stack.append(g)
    return out


def is_surface_face(bm, face):
    lay = geom.ensure_layers(bm)
    return any(e[lay.soft] for e in face.edges)


def curve_edges(bm, edge):
    """Every edge connected to `edge` through vertices with the same su_curve id (id 0 → [edge])."""
    lay = geom.ensure_layers(bm)
    cid = edge[lay.curve]
    if cid == 0:
        return [edge]
    seen = {edge}
    stack = [edge]
    while stack:
        e = stack.pop()
        for v in e.verts:
            for x in v.link_edges:
                if x not in seen and x[lay.curve] == cid:
                    seen.add(x)
                    stack.append(x)
    return sorted(seen, key=lambda x: x.index)


def pick_entity(bm, kind, index):
    """('FACE'|'SURFACE'|'EDGE'|'CURVE', sorted indices) for the element clicked."""
    lay = geom.ensure_layers(bm)
    _ensure_tables(bm)
    if kind == 'EDGE':
        e = bm.edges[index]
        if e[lay.curve] != 0:
            return 'CURVE', sorted(x.index for x in curve_edges(bm, e))
        return 'EDGE', [index]
    if kind == 'FACE':
        f = bm.faces[index]
        if is_surface_face(bm, f):
            return 'SURFACE', sorted(g.index for g in surface(bm, f))
        return 'FACE', sorted(g.index for g in geom.clusters(bm, [f])[0])
    raise ValueError("pick_entity: kind must be 'EDGE' or 'FACE', not {!r}".format(kind))


# ----------------------------------------------------------------------------- curve metadata

def _meta_all(doc):
    raw = doc.obj.su_doc.curves
    try:
        data = json.loads(raw) if raw else {}
    except ValueError:
        data = {}
    return data if isinstance(data, dict) else {}


def new_curve_id(doc):
    lay = geom.ensure_layers(doc.bm)
    used = [e[lay.curve] for e in doc.bm.edges]
    used += [int(k) for k in _meta_all(doc)]
    return max(used, default=0) + 1


def get_curve_meta(doc, cid):
    return _meta_all(doc).get(str(cid))


def set_curve_meta(doc, cid, meta):
    data = _meta_all(doc)
    if meta is None:
        data.pop(str(cid), None)
    else:
        data[str(cid)] = meta
    doc.obj.su_doc.curves = json.dumps(data, sort_keys=True)
