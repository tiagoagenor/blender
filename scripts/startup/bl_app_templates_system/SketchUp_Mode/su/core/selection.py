# SPDX-License-Identifier: GPL-2.0-or-later
"""Selection as Python sets (owner: B). Contract: PLANO.md §2.4-B, §3.8.

    Ref(doc_key, kind, index)   kind: 'EDGE' | 'FACE' (bmesh/mesh index in the document) |
                                'OBJECT' (doc_key = object name, index 0)
No mesh flags, no select_set, no active object. Every change bumps version() and emits
"selection". The selection is cleared only by: click on empty space / Excluir (callers), file load
("load" here), and refs that stop existing (pruned on "geometry"). Undo/redo: core/undo (A) stores
snapshot() per undo serial and calls restore(); topology-changing operations call remap().
"""

from dataclasses import dataclass

import bpy
from mathutils import Vector

from .. import events
from . import document, edit_context, entities, geom

ORDER = 123

_pyset = set          # this module defines set() (contract name)

EDGE = 'EDGE'
FACE = 'FACE'
OBJECT = 'OBJECT'


@dataclass(frozen=True)
class Ref:
    doc_key: str
    kind: str
    index: int


_SEL = _pyset()
_VERSION = [0]


def _changed():
    _VERSION[0] += 1
    events.emit("selection")


def _replace(refs):
    refs = _pyset(refs)
    if refs != _SEL:
        _SEL.clear()
        _SEL.update(refs)
        _changed()


# --------------------------------------------------------------------------------- basic API

def get():
    return frozenset(_SEL)


def is_empty():
    return not _SEL


def count():
    return len(_SEL)


def version():
    return _VERSION[0]


def set(refs):        # noqa: A001 — contract name
    _replace(refs)


def add(refs):
    _replace(_SEL | frozenset(refs))


def remove(refs):
    _replace(_SEL - frozenset(refs))


def toggle(refs):
    _replace(_SEL ^ frozenset(refs))


def clear():
    _replace(())


# ------------------------------------------------------------------------------ queries

def edges_of(doc_key):
    return {r.index for r in _SEL if r.doc_key == doc_key and r.kind == EDGE}


def faces_of(doc_key):
    return {r.index for r in _SEL if r.doc_key == doc_key and r.kind == FACE}


def objects():
    out = []
    for r in sorted(_SEL, key=lambda r: r.doc_key):
        if r.kind == OBJECT:
            obj = bpy.data.objects.get(r.doc_key)
            if obj is not None:
                out.append(obj)
    return out


def _tables(bm):
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()


def verts_of(doc):
    """Vertex indices used by the selected edges/faces of `doc`."""
    bm = doc.bm
    _tables(bm)
    out = _pyset()
    for i in edges_of(doc.key):
        if i < len(bm.edges):
            out.update(v.index for v in bm.edges[i].verts)
    for i in faces_of(doc.key):
        if i < len(bm.faces):
            out.update(v.index for v in bm.faces[i].verts)
    return out


def bounds_world():
    """(min, max) world-space corners of everything selected, or None."""
    pts = []
    keys = {r.doc_key for r in _SEL if r.kind in (EDGE, FACE)}
    for key in keys:
        doc = document.get_by_key(key)
        if doc is None:
            continue
        m = doc.world()
        bm = doc.bm
        _tables(bm)
        pts += [m @ bm.verts[i].co for i in verts_of(doc)]
    for obj in objects():
        pts += [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    if not pts:
        return None
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


# ------------------------------------------------------------------------ entity expansion

def _entity_refs(doc, kind, index):
    """Refs of the entity (pick_entity rule) that contains element (kind, index)."""
    ek, idx = entities.pick_entity(doc.bm, kind, index)
    k = EDGE if ek in ('EDGE', 'CURVE') else FACE
    return [Ref(doc.key, k, i) for i in idx]


def entity(ref):
    """The refs a single click on `ref` selects (curve / surface / logical face)."""
    if ref.kind == OBJECT:
        return [ref]
    doc = document.get_by_key(ref.doc_key)
    return _entity_refs(doc, ref.kind, ref.index)


def _visible_edge(lay, e):
    return not e[lay.bridge] and not e[lay.hidden]


def expand_face(ref):
    """Double click on a face: the face entity + its bounding (visible) edges."""
    doc = document.get_by_key(ref.doc_key)
    bm = doc.bm
    lay = geom.ensure_layers(bm)
    refs = _entity_refs(doc, FACE, ref.index)
    _tables(bm)
    for r in list(refs):
        for e in bm.faces[r.index].edges:
            if _visible_edge(lay, e) and not e[lay.soft]:
                refs.append(Ref(doc.key, EDGE, e.index))
    return sorted(_pyset(refs), key=lambda r: (r.kind, r.index))


def expand_edge(ref):
    """Double click on an edge: the edge entity + the faces (entities) it bounds."""
    doc = document.get_by_key(ref.doc_key)
    bm = doc.bm
    refs = _entity_refs(doc, EDGE, ref.index)
    _tables(bm)
    for r in list(refs):
        for f in bm.edges[r.index].link_faces:
            refs += _entity_refs(doc, FACE, f.index)
    return sorted(_pyset(refs), key=lambda r: (r.kind, r.index))


def connected(ref):
    """Triple click: every edge and face connected to the element (through shared vertices)."""
    doc = document.get_by_key(ref.doc_key)
    bm = doc.bm
    lay = geom.ensure_layers(bm)
    _tables(bm)
    start = bm.edges[ref.index].verts[0] if ref.kind == EDGE else bm.faces[ref.index].verts[0]
    seen = {start}
    stack = [start]
    while stack:
        v = stack.pop()
        for e in v.link_edges:
            w = e.other_vert(v)
            if w not in seen:
                seen.add(w)
                stack.append(w)
    refs = _pyset()
    for v in seen:
        for e in v.link_edges:
            if _visible_edge(lay, e):
                refs.add(Ref(doc.key, EDGE, e.index))
        for f in v.link_faces:
            refs.add(Ref(doc.key, FACE, f.index))
    return sorted(refs, key=lambda r: (r.kind, r.index))


def _context_refs():
    """Everything selectable in the current edit context: its geometry + its child objects."""
    doc = document.active()
    bm = doc.bm
    lay = geom.ensure_layers(bm)
    bm.edges.index_update()
    bm.faces.index_update()
    refs = {Ref(doc.key, EDGE, e.index) for e in bm.edges if _visible_edge(lay, e)}
    refs |= {Ref(doc.key, FACE, f.index) for f in bm.faces}
    for obj in bpy.context.scene.objects:
        if obj.name == doc.key or document.kind(obj) == document.KIND_MODEL:
            continue
        if (obj.type == 'MESH' or obj.su_doc.kind) and edit_context.is_in_context(obj) \
                and obj.visible_get():
            refs.add(Ref(obj.name, OBJECT, 0))
    return refs


def select_all():
    _replace(_context_refs())


def invert():
    _replace(_context_refs() - _SEL)


# ------------------------------------------------------------------------- undo / remap

def snapshot():
    return {"refs": frozenset(_SEL)}


def restore(snap):
    """Selection of an undo state (None → empty); refs that no longer exist are dropped."""
    refs = snap.get("refs", ()) if snap else ()
    _replace(_valid(refs))


def remap(doc_key, index_map):
    """index_map: {'EDGE': {old: new|None}, 'FACE': {old: new|None}} for document `doc_key`.
    Refs of a mapped kind follow the map (missing / None → dropped); other refs are kept."""
    out = _pyset()
    for r in _SEL:
        if r.doc_key == doc_key and r.kind in index_map:
            new = index_map[r.kind].get(r.index)
            if new is not None:
                out.add(Ref(doc_key, r.kind, new))
        else:
            out.add(r)
    _replace(out)


def _valid(refs):
    out = _pyset()
    sizes = {}
    for r in refs:
        if r.kind == OBJECT:
            if bpy.data.objects.get(r.doc_key) is not None:
                out.add(r)
            continue
        if r.doc_key not in sizes:
            # count from the MESH (the truth after write and after undo; undo restores the
            # selection before the "undo" event invalidates the cached bmesh)
            obj = bpy.data.objects.get(r.doc_key)
            me = obj.data if obj is not None and obj.type == 'MESH' else None
            sizes[r.doc_key] = (len(me.edges), len(me.polygons)) if me is not None else (0, 0)
        ne, nf = sizes[r.doc_key]
        if (r.kind == EDGE and r.index < ne) or (r.kind == FACE and r.index < nf):
            out.add(r)
    return out


# ------------------------------------------------------------------------------ events

def _on_geometry(doc_key=None, **_kw):
    pruned = _valid(_SEL)
    if pruned != _SEL:
        _replace(pruned)


def _on_load(**_kw):
    _SEL.clear()
    _changed()


def register():
    events.subscribe("geometry", _on_geometry, order=100)
    events.subscribe("load", _on_load, order=95)


def unregister():
    _SEL.clear()
    events.unsubscribe("geometry", _on_geometry)
    events.unsubscribe("load", _on_load)
