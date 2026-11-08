# SPDX-License-Identifier: GPL-2.0-or-later
"""Documents = mesh objects edited through a live BMesh (owner: B). Contract: PLANO.md §2.4-B, §3.1.

    doc = document.root()                 # the "Modelo" object (su_doc.kind == 'MODEL')
    geom.add_edge(doc.bm, a, b)
    doc.write(undo_key="undo.line")       # undo.before_change → to_mesh → version++ →
                                          # events "geometry" → undo.push
    doc.begin(); ...; doc.preview_write(); doc.cancel()    # live preview tools only

A Document is keyed by the object NAME and resolves `obj` from bpy.data on every access, so it
survives memfile undo (which re-allocates every ID). `bm` is loaded lazily from the mesh and is
SHARED by every object using that mesh (component instances): an edit through one instance is
written once to the definition mesh and "geometry" is emitted for every instance. The bmesh is
dropped by invalidate() — on events "undo" and "load" and whenever the mesh changed under us (mesh
pointer differs). Meshes without su_doc.kind are groups (PLANO §3.1).

Components (P1, kernel): definition = a Mesh datablock with the ID property mesh["su_def"] (its
name); instances = objects (su_doc.kind 'COMPONENT') sharing that mesh, each with its own matrix.
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


_DOCS = {}          # key (object name) -> Document
_MESHES = {}        # mesh name -> _MeshState (shared by every instance of a component)


class _MeshState:
    """Live editing state of ONE mesh datablock: shared by all objects using that mesh, so editing
    a component through any instance writes the definition once and every instance follows."""
    __slots__ = ("bm", "ptr", "snap", "version")

    def __init__(self):
        self.bm = None
        self.ptr = 0
        self.snap = None
        self.version = 0

    def free(self):
        if self.snap is not None:
            self.snap.free()
            self.snap = None
        if self.bm is not None:
            self.bm.free()
            self.bm = None
        self.ptr = 0


class Document:
    """Document of one object (key = object name: its matrix is the edit space). The BMesh, the
    version and the preview snapshot belong to the object's MESH (_MeshState), so component
    instances (objects sharing a mesh) share them."""

    def __init__(self, key):
        self.key = key

    def __repr__(self):
        return "<Document {!r} v{:d}>".format(self.key, self.version)

    # -------------------------------------------------------------- data access
    @property
    def obj(self):
        return bpy.data.objects.get(self.key)

    def is_valid(self):
        obj = self.obj
        return obj is not None and obj.type == 'MESH'

    def _state(self):
        obj = self.obj
        if obj is None or obj.type != 'MESH':
            raise LookupError("document object {!r} does not exist".format(self.key))
        me = obj.data
        st = _MESHES.get(me.name)
        if st is None:
            st = _MESHES[me.name] = _MeshState()
        if st.bm is not None and st.ptr != me.as_pointer():
            st.free()
        return st, me

    @property
    def version(self):
        try:
            return self._state()[0].version
        except LookupError:
            return 0

    @property
    def bm(self):
        st, me = self._state()
        if st.bm is None:
            bm = bmesh.new()
            bm.from_mesh(me)
            geom.ensure_layers(bm)
            for f in bm.faces:
                f.normal_update()
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            st.bm = bm
            st.ptr = me.as_pointer()
        return st.bm

    def world(self):
        return self.obj.matrix_world.copy()

    def instance_keys(self):
        """Names of every object sharing this document's mesh (this one first)."""
        obj = self.obj
        if obj is None:
            return [self.key]
        return [self.key] + sorted(o.name for o in instances(obj.data) if o.name != self.key)

    # ------------------------------------------------------------------ writing
    def _to_mesh(self):
        st, me = self._state()
        bm = st.bm
        bm.verts.index_update()        # element index == mesh index (selection refs use it)
        bm.edges.index_update()
        bm.faces.index_update()
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.to_mesh(me)
        me.update()
        st.ptr = me.as_pointer()

    def write(self, *, undo_key, select=None):
        """Commit bm to the mesh: before_change → to_mesh → version++ → "geometry" → undo.push.
        "geometry" is emitted for EVERY object sharing the mesh (component instances), this one
        first. `select` (optional iterable of selection.Ref) becomes the selection after the
        geometry event and BEFORE undo.push, so the undo step stores the pre-operation selection
        (taken by before_change) and this post-operation one (Excluir: write(..., select=()))."""
        bm = self.bm
        st, _me = self._state()
        undo.before_change()
        if st.snap is not None:
            st.snap.free()
            st.snap = None
        bm.normal_update()
        self._to_mesh()
        st.version += 1
        for key in self.instance_keys():
            events.emit("geometry", doc_key=key)
        if select is not None:
            from . import selection
            selection.set(select)
        if undo_key:
            undo.push(undo_key)

    def begin(self):
        """Snapshot for live-preview tools (cancel() restores it)."""
        bm = self.bm
        st, _me = self._state()
        if st.snap is not None:
            st.snap.free()
        st.snap = bm.copy()

    def preview_write(self):
        """to_mesh without undo step or event (live preview)."""
        self.bm
        self._to_mesh()

    def cancel(self):
        """Restore the begin() snapshot (bm and mesh)."""
        st, _me = self._state()
        if st.snap is None:
            return
        if st.bm is not None:
            st.bm.free()
        st.bm = st.snap
        st.snap = None
        geom.ensure_layers(st.bm)
        self._to_mesh()

    def invalidate(self):
        """Drop the cached BMesh (and any preview snapshot) of this document's mesh."""
        obj = self.obj
        if obj is not None and obj.type == 'MESH':
            st = _MESHES.pop(obj.data.name, None)
            if st is not None:
                st.free()


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
    for st in _MESHES.values():
        st.free()
    _MESHES.clear()
    for key in list(_DOCS):
        if bpy.data.objects.get(key) is None:
            del _DOCS[key]


def _create(name, parent_obj, kind_, mesh=None):
    scene = bpy.context.scene
    coll = parent_obj.users_collection[0] if parent_obj is not None and parent_obj.users_collection \
        else scene.collection
    me = mesh if mesh is not None else bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, me)
    obj.su_doc.kind = kind_
    coll.objects.link(obj)
    if parent_obj is not None:
        obj.parent = parent_obj
    return obj


def create_group(name, parent_obj=None):
    """New empty group document (child of parent_obj, or of the root's collection). Emits "doc"."""
    obj = _create(name or "Grupo", parent_obj, KIND_GROUP)
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
    return _move_into_new(doc, face_ids, edge_ids, name or "Grupo", KIND_GROUP)


def _move_into_new(doc, face_ids, edge_ids, name, kind_):
    src = doc.bm
    sl = geom.ensure_layers(src)
    src.edges.ensure_lookup_table()
    src.faces.ensure_lookup_table()
    faces = [f for cl in geom.clusters(src, [src.faces[i] for i in face_ids]) for f in cl]
    edges = {src.edges[i] for i in edge_ids} | {e for f in faces for e in f.edges}
    parent = None if kind(doc.obj) == KIND_MODEL else doc.obj
    mesh = None
    if kind_ == KIND_COMPONENT:
        mesh = bpy.data.meshes.new(name)
        mesh["su_def"] = mesh.name
    gobj = _create(name, parent, kind_, mesh)
    gobj.matrix_world = doc.world()
    g = get(gobj)
    for mat in doc.obj.data.materials:
        g.obj.data.materials.append(mat)
    g.obj.su_doc.curves = doc.obj.su_doc.curves
    dst = g.bm
    geom.match_face_layers(src, dst)
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
        geom.copy_face_layers(src, f, dst, nf)      # material, smooth, su_back_mat, su_hidden_face…
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
    events.emit("doc", doc_key=g.key)
    return g


# ---------------------------------------------------------------------------- components (P1)

def _unique_def_name(base):
    used = {me.name for me in bpy.data.meshes}
    if base and base not in used:
        return base
    stem = base or "Componente"
    n = 1
    while "{:s}#{:d}".format(stem, n) in used:
        n += 1
    return "{:s}#{:d}".format(stem, n)


def component_from(doc, face_ids, edge_ids, name=None):
    """Criar componente (kernel): like group_from, but the new mesh is a component DEFINITION
    (mesh["su_def"] = its name) and the new object its first instance (su_doc.kind 'COMPONENT'),
    created in place. Unwritten bmeshes as in group_from. Emits "doc". Returns the instance doc."""
    return _move_into_new(doc, face_ids, edge_ids, _unique_def_name(name), KIND_COMPONENT)


def is_component(obj):
    return obj is not None and obj.type == 'MESH' and "su_def" in obj.data


def definition_name(obj):
    return obj.data["su_def"] if is_component(obj) else None


def definitions():
    """Component definition meshes that still have instances, sorted by name."""
    return sorted((me for me in bpy.data.meshes if "su_def" in me and me.users > 0), key=lambda m: m.name)


def instances(definition):
    """Objects using `definition` (a Mesh or its name), sorted by name."""
    me = bpy.data.meshes.get(definition) if isinstance(definition, str) else definition
    if me is None:
        return []
    return sorted((o for o in bpy.data.objects if o.type == 'MESH' and o.data == me), key=lambda o: o.name)


def duplicate(obj, parent=None):
    """Copy of a document object for Mover/Girar copies and Colar: a component instance SHARES
    its definition mesh (new instance); a group gets its own mesh copy. Children are duplicated
    too; links the same collections; emits "doc" for every new object. Returns the new object."""
    new = obj.copy()
    if obj.type == 'MESH' and not is_component(obj):
        new.data = obj.data.copy()
    for coll in obj.users_collection:
        coll.objects.link(new)
    if parent is not None:
        new.parent = parent
        new.matrix_parent_inverse = obj.matrix_parent_inverse.copy()
    events.emit("doc", doc_key=new.name)
    for child in list(obj.children):
        duplicate(child, new)
    return new


def make_unique(obj):
    """Tornar exclusivo: give instance `obj` its own copy of the definition (new definition name).
    No-op for an object that is the only user of its mesh. Returns its Document."""
    if not is_component(obj) or obj.data.users <= 1:
        return get(obj)
    src = obj.data                 # the mesh is the truth (edits are written before this is called)
    new = src.copy()
    new.name = _unique_def_name(src["su_def"])
    new["su_def"] = new.name
    obj.data = new
    events.emit("geometry", doc_key=obj.name)
    return get(obj)


def explode(obj):
    """Explodir (kernel): merge group or component instance `obj` into its parent document (root
    when top level); for an instance a COPY of the definition's geometry is welded in and the
    definition (shared mesh) stays for the other instances.
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
    geom.match_face_layers(src, dst)
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
        geom.copy_face_layers(src, f, dst, nf)
        nf.material_index = slot.get(f.material_index, f.material_index)
        geom.orient_face(nf, nm @ f.normal)
        res.new_faces.append(nf)
    for child in list(obj.children):
        mw = child.matrix_world.copy()
        child.parent = parent_obj
        child.matrix_world = mw
    me = obj.data
    if me.users <= 1:
        gdoc.invalidate()            # other instances of a component keep the shared bmesh
    _DOCS.pop(obj.name, None)
    bpy.data.objects.remove(obj)
    if me.users == 0:
        _MESHES.pop(me.name, None)
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
    for st in _MESHES.values():
        st.free()
    _MESHES.clear()
    _DOCS.clear()
    events.unsubscribe("load", _on_load)
    events.unsubscribe("undo", _on_undo)
    if hasattr(bpy.types.Object, "su_doc"):
        del bpy.types.Object.su_doc
    registry.unregister_classes([SU_PG_doc])
