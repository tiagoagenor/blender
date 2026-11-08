# SPDX-License-Identifier: GPL-2.0-or-later
"""Documents = mesh objects edited through a live BMesh (owner: B). Contract: PLANO.md §2.4-B, §3.1.

    doc = document.root()                 # the "Modelo" object (su_doc.kind == 'MODEL')
    geom.add_edge(doc.bm, a, b)
    doc.write(undo_key="undo.line")       # undo.before_change → to_mesh → version++ →
                                          # events "geometry" → undo.push
    doc.begin(); ...; doc.preview_write(); doc.cancel()    # live preview tools only

A Document is keyed by the object NAME and resolves `obj` from bpy.data on every access, so it
survives memfile undo (which re-allocates every ID). `bm` is loaded lazily from the mesh; it is
dropped by invalidate() — on events "undo" and "load" and whenever the object's mesh changed under
us (mesh pointer differs). Meshes without su_doc.kind are groups (PLANO §3.1).
"""

import bmesh
import bpy

from .. import events, registry
from . import geom, undo

ORDER = 120

MODEL_NAME = "Modelo"
KIND_MODEL = 'MODEL'
KIND_GROUP = 'GROUP'
KIND_COMPONENT = 'COMPONENT'


class SU_PG_doc(bpy.types.PropertyGroup):
    kind: bpy.props.StringProperty(name="Kind", default="")          # '' (= group) MODEL GROUP COMPONENT
    curves: bpy.props.StringProperty(name="Curves", default="")      # JSON curve metadata (entities)


_DOCS = {}          # key -> Document


class Document:
    def __init__(self, key):
        self.key = key
        self.version = 0
        self._bm = None
        self._snap = None
        self._mesh_ptr = 0

    def __repr__(self):
        return "<Document {!r} v{:d}>".format(self.key, self.version)

    # -------------------------------------------------------------- data access
    @property
    def obj(self):
        return bpy.data.objects.get(self.key)

    def is_valid(self):
        obj = self.obj
        return obj is not None and obj.type == 'MESH'

    @property
    def bm(self):
        obj = self.obj
        if obj is None or obj.type != 'MESH':
            raise LookupError("document object {!r} does not exist".format(self.key))
        if self._bm is not None and obj.data.as_pointer() != self._mesh_ptr:
            self.invalidate()
        if self._bm is None:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            geom.ensure_layers(bm)
            for f in bm.faces:
                f.normal_update()
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            self._bm = bm
            self._mesh_ptr = obj.data.as_pointer()
        return self._bm

    def world(self):
        return self.obj.matrix_world.copy()

    # ------------------------------------------------------------------ writing
    def _to_mesh(self):
        obj = self.obj
        me = obj.data
        bm = self._bm
        bm.verts.index_update()        # element index == mesh index (selection refs use it)
        bm.edges.index_update()
        bm.faces.index_update()
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.to_mesh(me)
        me.update()
        self._mesh_ptr = me.as_pointer()

    def write(self, *, undo_key, select=None):
        """Commit bm to the mesh: before_change → to_mesh → version++ → "geometry" → undo.push.
        `select` (optional iterable of selection.Ref) becomes the selection after the geometry
        event and BEFORE undo.push, so the undo step stores the pre-operation selection (taken by
        before_change) and this post-operation one (e.g. Excluir: write(undo_key=..., select=()))."""
        bm = self.bm
        undo.before_change()
        self._free_snap()
        bm.normal_update()
        self._to_mesh()
        self.version += 1
        events.emit("geometry", doc_key=self.key)
        if select is not None:
            from . import selection
            selection.set(select)
        if undo_key:
            undo.push(undo_key)

    def begin(self):
        """Snapshot for live-preview tools (cancel() restores it)."""
        self._free_snap()
        self._snap = self.bm.copy()

    def preview_write(self):
        """to_mesh without undo step or event (live preview)."""
        self.bm
        self._to_mesh()

    def cancel(self):
        """Restore the begin() snapshot (bm and mesh)."""
        if self._snap is None:
            return
        if self._bm is not None:
            self._bm.free()
        self._bm = self._snap
        self._snap = None
        geom.ensure_layers(self._bm)
        if self.is_valid():
            self._to_mesh()

    def _free_snap(self):
        if self._snap is not None:
            self._snap.free()
            self._snap = None

    def invalidate(self):
        """Drop the cached BMesh (and any preview snapshot); next `bm` access reloads the mesh."""
        self._free_snap()
        if self._bm is not None:
            self._bm.free()
            self._bm = None
        self._mesh_ptr = 0


# ------------------------------------------------------------------------- module API

def get(obj):
    """Document of a mesh object (cached by name)."""
    if obj is None:
        return None
    key = obj.name
    doc = _DOCS.get(key)
    if doc is None:
        doc = _DOCS[key] = Document(key)
    return doc


def get_by_key(key):
    obj = bpy.data.objects.get(key)
    return get(obj) if obj is not None and obj.type == 'MESH' else None


def _new_doc_object(name, kind, collection, parent=None):
    me = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, me)
    obj.su_doc.kind = kind
    collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def root(scene=None):
    """The "Modelo" document of the scene, created when missing (emits "doc")."""
    scene = scene or bpy.context.scene
    for obj in scene.objects:
        if obj.type == 'MESH' and obj.su_doc.kind == KIND_MODEL:
            return get(obj)
    obj = _new_doc_object(MODEL_NAME, KIND_MODEL, scene.collection)
    events.emit("doc", doc_key=obj.name)
    return get(obj)


def active():
    """Document being edited: the innermost open group, else the root."""
    from . import edit_context
    obj = edit_context.current_object()
    if obj is not None and obj.type == 'MESH':
        return get(obj)
    return root()


def visible_documents():
    vl = bpy.context.view_layer
    return [get(o) for o in vl.objects if o.type == 'MESH' and o.visible_get()]


def invalidate_all():
    for key, doc in list(_DOCS.items()):
        doc.invalidate()
        if bpy.data.objects.get(key) is None:
            del _DOCS[key]


def create_group(name, parent_obj=None):
    """New empty group document (child of parent_obj, or of the root's collection). Emits "doc"."""
    scene = bpy.context.scene
    coll = parent_obj.users_collection[0] if parent_obj is not None and parent_obj.users_collection \
        else scene.collection
    obj = _new_doc_object(name or "Grupo", KIND_GROUP, coll, parent_obj)
    events.emit("doc", doc_key=obj.name)
    return get(obj)


def _copy_edge_layers(src_lay, e, dst_lay, ne):
    ne[dst_lay.bridge] = e[src_lay.bridge]
    ne[dst_lay.soft] = e[src_lay.soft]
    ne[dst_lay.hidden] = e[src_lay.hidden]
    ne[dst_lay.curve] = e[src_lay.curve]


def group_from(doc, face_ids, edge_ids, name=None):
    """Criar grupo (kernel): MOVE the given faces (whole logical faces) and edges of `doc` into a
    new group document created in the current context (child of doc.obj unless doc is the root).
    Edges still used by faces left outside stay in `doc` too (SketchUp keeps the outside intact).
    The group gets doc's world matrix and material slots. Both bmeshes are left unwritten: the
    caller writes the group (undo_key=None) and then doc (with the undo step). Emits "doc"."""
    src = doc.bm
    sl = geom.ensure_layers(src)
    src.edges.ensure_lookup_table()
    src.faces.ensure_lookup_table()
    faces = [f for cl in geom.clusters(src, [src.faces[i] for i in face_ids]) for f in cl]
    edges = {src.edges[i] for i in edge_ids} | {e for f in faces for e in f.edges}
    parent = None if kind(doc.obj) == KIND_MODEL else doc.obj
    g = create_group(name, parent)
    g.obj.matrix_world = doc.world()
    for mat in doc.obj.data.materials:
        g.obj.data.materials.append(mat)
    g.obj.su_doc.curves = doc.obj.su_doc.curves
    dst = g.bm
    dl = geom.ensure_layers(dst)
    vmap = {}
    for e in edges:
        for v in e.verts:
            if v not in vmap:
                vmap[v] = dst.verts.new(v.co)
    for e in edges:
        ne = dst.edges.new((vmap[e.verts[0]], vmap[e.verts[1]]))
        _copy_edge_layers(sl, e, dl, ne)
    for f in faces:
        nf = dst.faces.new([vmap[v] for v in f.verts])
        nf.material_index = f.material_index
        nf.smooth = f.smooth
        nf[dl.back] = f[sl.back]
        nf.normal_update()
    verts = {v for e in edges for v in e.verts}
    if faces:
        bmesh.ops.delete(src, geom=faces, context='FACES_ONLY')
    wire = [e for e in edges if e.is_valid and not e.link_faces]
    if wire:
        bmesh.ops.delete(src, geom=wire, context='EDGES')
    loose = [v for v in verts if v.is_valid and not v.link_edges]
    if loose:
        bmesh.ops.delete(src, geom=loose, context='VERTS')
    return g


def explode(obj):
    """Explodir (kernel): merge group `obj` into its parent document (root when top level).
    Vertices are welded into the parent geometry; materials are mapped by identity (missing ones
    are appended to the parent mesh); child groups are re-parented keeping their world matrix;
    the group object (and its mesh, when unused) is deleted. The parent bmesh is left unwritten.
    Returns (parent_doc, geom.EditResult with new_edges/new_faces)."""
    gdoc = get(obj)
    parent_obj = obj.parent
    pdoc = get(parent_obj) if parent_obj is not None and parent_obj.type == 'MESH' else root()
    m = pdoc.world().inverted() @ obj.matrix_world
    nm = m.to_3x3().inverted().transposed()
    pmats = pdoc.obj.data.materials
    slot = {}
    for i, mat in enumerate(obj.data.materials):
        idx = next((j for j, pm in enumerate(pmats) if pm == mat), None)
        if idx is None:
            pmats.append(mat)
            idx = len(pmats) - 1
        slot[i] = idx
    src, dst = gdoc.bm, pdoc.bm
    sl, dl = geom.ensure_layers(src), geom.ensure_layers(dst)
    res = geom.EditResult()
    vmap = {v: geom.weld_point(dst, m @ v.co) for v in src.verts}
    for e in src.edges:
        a, b = vmap[e.verts[0]], vmap[e.verts[1]]
        if a is b:
            continue
        ne = dst.edges.get((a, b))
        if ne is None:
            ne = dst.edges.new((a, b))
            _copy_edge_layers(sl, e, dl, ne)
            res.new_edges.append(ne)
        res.edges.append(ne)
    for f in src.faces:
        verts = [vmap[v] for v in f.verts]
        if len(set(verts)) < 3 or dst.faces.get(verts) is not None:
            continue
        nf = dst.faces.new(verts)
        nf.material_index = slot.get(f.material_index, f.material_index)
        nf.smooth = f.smooth
        nf[dl.back] = f[sl.back]
        geom.orient_face(nf, nm @ f.normal)
        res.new_faces.append(nf)
    for child in list(obj.children):
        mw = child.matrix_world.copy()
        child.parent = parent_obj
        child.matrix_world = mw
    gdoc.invalidate()
    _DOCS.pop(obj.name, None)
    me = obj.data
    bpy.data.objects.remove(obj)
    if me.users == 0:
        bpy.data.meshes.remove(me)
    return pdoc, res


def kind(obj):
    k = obj.su_doc.kind if obj is not None else ''
    return k or KIND_GROUP


# ------------------------------------------------------------------------------- events

def _on_load(**_kw):
    invalidate_all()
    if bpy.context.scene is not None:
        root()


def _on_undo(**_kw):
    invalidate_all()


def register():
    registry.register_classes([SU_PG_doc])
    bpy.types.Object.su_doc = bpy.props.PointerProperty(type=SU_PG_doc)
    events.subscribe("load", _on_load, order=100)
    events.subscribe("undo", _on_undo, order=100)


def unregister():
    for doc in _DOCS.values():
        doc.invalidate()
    _DOCS.clear()
    events.unsubscribe("load", _on_load)
    events.unsubscribe("undo", _on_undo)
    if hasattr(bpy.types.Object, "su_doc"):
        del bpy.types.Object.su_doc
    registry.unregister_classes([SU_PG_doc])
