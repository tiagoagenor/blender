# SPDX-License-Identifier: GPL-2.0-or-later
"""Edit commands (owner: F). PLANO.md §4.5 (Editar menu), §5.3, §6.1 "Comandos"; ROTEIRO_CASA "Apagar uma face".

    su.delete_selected   Excluir (Delete / ⌫ after su.vcb_key): selected faces go alone (their edges stay),
                         selected edges go with the faces they bound (coplanar neighbours merge), selected
                         groups go; 1 undo step; selection empty afterwards (undo restores it)
    su.select_all / su.select_none / su.select_invert     Cmd+A, Shift+Cmd+A, Shift+Cmd+I
    su.escape            Esc when idle: clears the selection; with nothing selected leaves the open group
    su.close_group       Fechar grupo/componente
Helper for every multi-document edit: commit(docs, undo_key, select=None) — one undo step whose
pre-operation selection is the selection at the call.
"""

import bpy

from .. import i18n, perf, registry
from ..tools import base
from .tool_ops import keymap_poll

ORDER = 450

STRINGS = {
    "edit.delete": {"pt_BR": "Excluir", "en": "Erase"},
    "edit.undo_delete": {"pt_BR": "Excluir", "en": "Erase"},
    "edit.select_all": {"pt_BR": "Selecionar tudo", "en": "Select All"},
    "edit.select_none": {"pt_BR": "Selecionar nada", "en": "Select None"},
    "edit.select_invert": {"pt_BR": "Inverter seleção", "en": "Invert Selection"},
    "edit.escape": {"pt_BR": "Cancelar", "en": "Cancel"},
    "edit.close_group": {"pt_BR": "Fechar grupo/componente", "en": "Close Group/Component"},
}


def _core(name):
    return registry.optional("core." + name)


def _poll(context):
    return _core("selection") is not None and _core("document") is not None


def _cancel_running(context):
    if base.DISPATCH.running:
        base.DISPATCH.cancel(base.tool_context(context))


def commit(docs, undo_key, select=None):
    """Write every changed document as ONE undo step. The undo step's pre-operation selection is
    the selection when commit() is called; `select` (iterable of Ref) is the selection after it."""
    from ..core import selection, undo
    pre = selection.get()
    docs = [d for d in docs if d is not None]
    if not docs:
        undo.before_change()
        if select is not None:
            selection.set(select)
        undo.push(undo_key)
        return
    for d in docs[:-1]:
        d.write(undo_key=None)
    selection.set(pre)          # unpruned: the undo state restores the topology these refs belong to
    docs[-1].write(undo_key=undo_key, select=select)


def _remove_object_tree(obj):
    for child in list(obj.children):
        _remove_object_tree(child)
    document = _core("document")
    me = obj.data if obj.type == 'MESH' else None
    if document is not None and hasattr(document, "_DOCS"):
        d = document._DOCS.pop(obj.name, None)
        if d is not None:
            d.invalidate()
    bpy.data.objects.remove(obj)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)


def delete_selection(undo_key="edit.undo_delete"):
    """Excluir the current selection. Returns True when something was deleted."""
    from ..core import document, geom, selection
    refs = selection.get()
    if not refs:
        return False
    by_doc = {}
    objs = []
    for r in refs:
        if r.kind == selection.OBJECT:
            obj = bpy.data.objects.get(r.doc_key)
            if obj is not None:
                objs.append(obj)
        else:
            by_doc.setdefault(r.doc_key, {"EDGE": set(), "FACE": set()})[r.kind].add(r.index)
    changed = []
    for key, sel in by_doc.items():
        doc = document.get_by_key(key)
        if doc is None:
            continue
        bm = doc.bm
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        faces = [bm.faces[i] for i in sel["FACE"] if i < len(bm.faces)]
        edges = [bm.edges[i] for i in sel["EDGE"] if i < len(bm.edges)]
        if faces:
            geom.erase_faces(bm, faces)
        edges = [e for e in edges if e.is_valid]
        if edges:
            geom.erase_edges(bm, edges)
        if faces or edges:
            changed.append(doc)
    # objects: remove (children first); objects that are descendants of others are skipped
    names = {o.name for o in objs}
    for obj in objs:
        p, nested = obj.parent, False
        while p is not None:
            if p.name in names:
                nested = True
                break
            p = p.parent
        if not nested and bpy.data.objects.get(obj.name) is not None:
            _remove_object_tree(obj)
    if not changed and not objs:
        return False
    commit(changed, undo_key, select=())
    return True


class SU_OT_delete_selected(bpy.types.Operator):
    bl_idname = "su.delete_selected"
    bl_label = "Excluir"
    bl_description = "Exclui as entidades selecionadas"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return _poll(context)

    def execute(self, context):
        _cancel_running(context)
        try:
            delete_selection()
        except Exception:
            perf.exception("su.delete_selected")
            return {'CANCELLED'}
        return {'FINISHED'}


class SU_OT_select_all(bpy.types.Operator):
    bl_idname = "su.select_all"
    bl_label = "Selecionar tudo"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return _poll(context)

    def execute(self, context):
        _core("selection").select_all()
        return {'FINISHED'}


class SU_OT_select_none(bpy.types.Operator):
    bl_idname = "su.select_none"
    bl_label = "Selecionar nada"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return _poll(context)

    def execute(self, context):
        _core("selection").clear()
        return {'FINISHED'}


class SU_OT_select_invert(bpy.types.Operator):
    bl_idname = "su.select_invert"
    bl_label = "Inverter seleção"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return _poll(context)

    def execute(self, context):
        _core("selection").invert()
        return {'FINISHED'}


def escape(context=None):
    """Esc with no operation: clear the selection, else leave the open group. False = nothing done."""
    sel, ec = _core("selection"), _core("edit_context")
    if base.DISPATCH.running:
        base.DISPATCH.cancel(base.tool_context(context or bpy.context))
    elif not sel.is_empty():
        sel.clear()
    elif ec is not None and ec.current_object() is not None:
        ec.exit()
    else:
        return False
    from ..core.state import STATE
    STATE.redraw_viewport()
    return True


class SU_OT_escape(bpy.types.Operator):
    """Esc when no operation runs: clear the selection, else leave the open group."""
    bl_idname = "su.escape"
    bl_label = "Cancelar"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return _poll(context) and keymap_poll(context)

    def execute(self, context):
        if not escape(context):
            return {'PASS_THROUGH'}
        return {'FINISHED'}


class SU_OT_close_group(bpy.types.Operator):
    bl_idname = "su.close_group"
    bl_label = "Fechar grupo/componente"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        ec = _core("edit_context")
        return ec is not None and ec.current_object() is not None

    def execute(self, context):
        _cancel_running(context)
        _core("edit_context").exit()
        from ..core.state import STATE
        STATE.redraw_viewport()
        return {'FINISHED'}


_classes = (SU_OT_delete_selected, SU_OT_select_all, SU_OT_select_none, SU_OT_select_invert, SU_OT_escape,
            SU_OT_close_group)

# Window keymap items (keymap.finalize adds them after su.vcb_key and the tool shortcuts).
KEYMAP = [
    ("su.delete_selected", {"type": 'DEL', "value": 'PRESS'}, None),
    ("su.delete_selected", {"type": 'BACK_SPACE', "value": 'PRESS'}, None),
    ("su.escape", {"type": 'ESC', "value": 'PRESS'}, None),
    ("su.select_all", {"type": 'A', "value": 'PRESS', "oskey": True}, None),
    ("su.select_none", {"type": 'A', "value": 'PRESS', "oskey": True, "shift": True}, None),
    ("su.select_invert", {"type": 'I', "value": 'PRESS', "oskey": True, "shift": True}, None),
]


def register():
    i18n.register_strings(STRINGS)
    registry.register_classes(_classes)


def unregister():
    registry.unregister_classes(_classes)
    i18n.unregister_strings(STRINGS)
