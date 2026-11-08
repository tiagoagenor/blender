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
            self._bm = bm
            self._mesh_ptr = obj.data.as_pointer()
        return self._bm

    def world(self):
        return self.obj.matrix_world.copy()

    # ------------------------------------------------------------------ writing
    def _to_mesh(self):
        obj = self.obj
        me = obj.data
        self._bm.to_mesh(me)
        me.update()
        self._mesh_ptr = me.as_pointer()

    def write(self, *, undo_key):
        """Commit bm to the mesh: before_change → to_mesh → version++ → "geometry" → undo.push."""
        bm = self.bm
        undo.before_change()
        self._free_snap()
        bm.normal_update()
        self._to_mesh()
        self.version += 1
        events.emit("geometry", doc_key=self.key)
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
