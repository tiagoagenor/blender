# SPDX-License-Identifier: GPL-2.0-or-later
"""Edit commands (owner: F). PLANO.md §4.5 (Editar menu), §5.3, §6.1 "Comandos"; ROTEIRO_CASA "Apagar uma face".

    su.delete_selected   Excluir (Delete / ⌫ after su.vcb_key): selected faces go alone (their edges stay),
                         selected edges go with the faces they bound (coplanar neighbours merge), selected
                         groups go; 1 undo step; selection empty afterwards (undo restores it)
    su.select_all / su.select_none / su.select_invert     Cmd+A, Shift+Cmd+A, Shift+Cmd+I
    su.escape            Esc when idle: clears the selection; with nothing selected leaves the open group
    su.close_group       Fechar grupo/componente
    su.make_group / su.make_component (G; = Criar grupo until P1)   su.explode   su.reverse_faces
    su.hide / su.unhide_all / su.unhide_last / su.unhide_selected   su.edit_group   su.entity_info
    su.copy / su.cut / su.paste / su.paste_in_place (P1; Cmd+C/X/V; Colar = no local + Mover)
Helper for every multi-document edit: commit(docs, undo_key, select=None) — one undo step whose
pre-operation selection is the selection at the call.
"""

import bpy

from .. import i18n, perf, registry
from ..tools import base
from ..tools.base import BaseTool, ToolMeta, tool
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
    "edit.undo_make_group": {"pt_BR": "Criar grupo", "en": "Make Group"},
    "edit.undo_explode": {"pt_BR": "Explodir", "en": "Explode"},
    "edit.undo_reverse": {"pt_BR": "Inverter faces", "en": "Reverse Faces"},
    "edit.undo_hide": {"pt_BR": "Ocultar", "en": "Hide"},
    "edit.undo_unhide": {"pt_BR": "Reexibir", "en": "Unhide"},
    "edit.component_is_group": {"pt_BR": "Componentes ainda não disponíveis: grupo criado.",
                                "en": "Components are not available yet: group created."},
    "tool.su.make_component.label": {"pt_BR": "Criar componente", "en": "Make Component"},
    "edit.undo_paste": {"pt_BR": "Colar", "en": "Paste"},
    "edit.undo_cut": {"pt_BR": "Recortar", "en": "Cut"},
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


# ---------------------------------------------------------------------------------------------- groups

def _split_selection():
    """(active doc, face idx, edge idx, objects) of the selection in the current context."""
    from ..core import document, selection
    doc = document.active()
    faces = sorted(r.index for r in selection.get() if r.doc_key == doc.key and r.kind == selection.FACE)
    edges = sorted(r.index for r in selection.get() if r.doc_key == doc.key and r.kind == selection.EDGE)
    objs = list(selection.objects())
    return doc, faces, edges, objs


def make_group(undo_key="edit.undo_make_group"):
    """Criar grupo from the selection (geometry of the edited document + selected groups, which nest
    inside). The new group becomes the selection. Returns the group Document or None."""
    from ..core import document, selection
    doc, faces, edges, objs = _split_selection()
    if not faces and not edges and not objs:
        return None
    mws = {o.name: o.matrix_world.copy() for o in objs}
    if faces or edges:
        g = document.group_from(doc, faces, edges)
    else:
        parent = None if document.kind(doc.obj) == document.KIND_MODEL else doc.obj
        g = document.create_group(None, parent)
        g.obj.matrix_world = doc.world()
    for o in objs:
        o.parent = g.obj
        o.matrix_world = mws[o.name]
    docs = [g] + ([doc] if faces or edges else [])
    commit(docs, undo_key, select=[selection.Ref(g.key, selection.OBJECT, 0)])
    return g


def explode_selection(undo_key="edit.undo_explode"):
    """Explodir the selected groups: their geometry merges into the parent document; the exploded
    geometry (and former child groups) become the selection."""
    from ..core import document, selection
    objs = [o for o in selection.objects() if o.type == 'MESH']
    if not objs:
        return False
    changed, refs = [], []
    for o in objs:
        children = [c.name for c in o.children]
        pdoc, res = document.explode(o)
        refs += [("E", pdoc.key, e) for e in res.new_edges] + [("F", pdoc.key, f) for f in res.new_faces]
        refs += [("O", n, None) for n in children]
        if pdoc not in changed:
            changed.append(pdoc)
    for d in changed:
        d.bm.edges.index_update()
        d.bm.faces.index_update()
    out = []
    for k, key, el in refs:
        if k == "O":
            if bpy.data.objects.get(key) is not None:
                out.append(selection.Ref(key, selection.OBJECT, 0))
        elif el.is_valid:
            out.append(selection.Ref(key, selection.EDGE if k == "E" else selection.FACE, el.index))
    commit(changed, undo_key, select=out)
    return True


def reverse_selected_faces(undo_key="edit.undo_reverse"):
    """Inverter faces: the selected faces flip (front ↔ back, each side keeps its material)."""
    from ..core import document, geom, selection
    by_doc = {}
    for r in selection.get():
        if r.kind == selection.FACE:
            by_doc.setdefault(r.doc_key, set()).add(r.index)
    changed = []
    for key, idx in by_doc.items():
        doc = document.get_by_key(key)
        if doc is None:
            continue
        bm = doc.bm
        bm.faces.ensure_lookup_table()
        geom.reverse_faces(bm, [bm.faces[i] for i in idx if i < len(bm.faces)])
        changed.append(doc)
    if not changed:
        return False
    commit(changed, undo_key, select=selection.get())
    return True


# ---------------------------------------------------------------------------------------------- hide

_last_hidden = []        # [("OBJECT", name) | ("EDGE", doc_key, index)] of the last Ocultar


def hide_selection(undo_key="edit.undo_hide"):
    """Ocultar: selected groups are hidden (view layer), selected edges get su_hidden. Faces stay
    (hidden faces = P1). Selection cleared."""
    from ..core import document, geom, selection
    refs = selection.get()
    if not refs:
        return False
    changed, done = [], []
    by_doc = {}
    for r in refs:
        if r.kind == selection.OBJECT:
            o = bpy.data.objects.get(r.doc_key)
            if o is not None:
                o.hide_set(True)
                done.append(("OBJECT", o.name))
        elif r.kind == selection.EDGE:
            by_doc.setdefault(r.doc_key, set()).add(r.index)
    for key, idx in by_doc.items():
        doc = document.get_by_key(key)
        if doc is None:
            continue
        bm = doc.bm
        lay = geom.ensure_layers(bm)
        bm.edges.ensure_lookup_table()
        for i in idx:
            if i < len(bm.edges):
                bm.edges[i][lay.hidden] = True
                done.append(("EDGE", key, i))
        changed.append(doc)
    if not done:
        return False
    _last_hidden[:] = done
    commit(changed, undo_key, select=())
    return True


def unhide(which="ALL", undo_key="edit.undo_unhide"):
    """Reexibir: 'ALL' (everything in the current context), 'LAST' (the last Ocultar), 'SELECTED'
    (selected refs). Returns True when something changed."""
    from ..core import document, edit_context, geom, selection
    changed, n = [], 0
    if which == 'LAST':
        targets = list(_last_hidden)
    elif which == 'SELECTED':
        targets = [("OBJECT", r.doc_key) if r.kind == selection.OBJECT else ("EDGE", r.doc_key, r.index)
                   for r in selection.get() if r.kind in (selection.OBJECT, selection.EDGE)]
    else:
        doc = document.active()
        lay = geom.ensure_layers(doc.bm)
        doc.bm.edges.index_update()
        targets = [("EDGE", doc.key, e.index) for e in doc.bm.edges if e[lay.hidden]]
        for o in bpy.context.scene.objects:
            if edit_context.is_in_context(o) and o.hide_get():
                targets.append(("OBJECT", o.name))
    for t in targets:
        if t[0] == "OBJECT":
            o = bpy.data.objects.get(t[1])
            if o is not None and o.hide_get():
                o.hide_set(False)
                n += 1
        else:
            doc = document.get_by_key(t[1])
            if doc is None:
                continue
            bm = doc.bm
            lay = geom.ensure_layers(bm)
            bm.edges.ensure_lookup_table()
            if t[2] < len(bm.edges) and bm.edges[t[2]][lay.hidden]:
                bm.edges[t[2]][lay.hidden] = False
                n += 1
                if doc not in changed:
                    changed.append(doc)
    if not n:
        return False
    commit(changed, undo_key)
    return True


def make_component():
    """Criar componente = Criar grupo until components (P1), with the hint."""
    if make_group("edit.undo_make_group") is not None:
        from ..core.state import STATE
        STATE.set_hint("edit.component_is_group")
        return True
    return False


def _redraw():
    from ..core.state import STATE
    STATE.redraw_viewport()


def _has_sel():
    sel = _core("selection")
    return sel is not None and not sel.is_empty()


def _has_objects():
    sel = _core("selection")
    return sel is not None and bool(sel.objects())


def _has_faces():
    sel = _core("selection")
    return sel is not None and any(r.kind == 'FACE' for r in sel.get())


def _simple_op(idname, label, fn, poll=None, desc=""):
    """Operator class running fn() as one edit command (any running tool operation is cancelled)."""
    def execute(self, context):
        _cancel_running(context)
        try:
            fn()
        except Exception:
            perf.exception(idname)
            return {'CANCELLED'}
        _redraw()
        return {'FINISHED'}

    def _poll_fn(cls, context):
        return _poll(context) and (poll is None or poll())
    return type("SU_OT_" + idname.split(".", 1)[1], (bpy.types.Operator,), {
        "bl_idname": idname, "bl_label": label, "bl_description": desc or label,
        "poll": classmethod(_poll_fn), "execute": execute})


SU_OT_make_group = _simple_op("su.make_group", "Criar grupo", make_group, _has_sel)
SU_OT_make_component = _simple_op("su.make_component", "Criar componente", make_component, _has_sel,
                                  "Criar componente (por enquanto cria um grupo)")
SU_OT_explode = _simple_op("su.explode", "Explodir", explode_selection, _has_objects)
SU_OT_reverse_faces = _simple_op("su.reverse_faces", "Inverter faces", reverse_selected_faces, _has_faces)
SU_OT_hide = _simple_op("su.hide", "Ocultar", hide_selection, _has_sel)
SU_OT_unhide_all = _simple_op("su.unhide_all", "Reexibir tudo", lambda: unhide('ALL'))
SU_OT_unhide_last = _simple_op("su.unhide_last", "Reexibir último", lambda: unhide('LAST'),
                               lambda: bool(_last_hidden))
SU_OT_unhide_selected = _simple_op("su.unhide_selected", "Reexibir selecionados", lambda: unhide('SELECTED'),
                                   _has_sel)


class SU_OT_edit_group(bpy.types.Operator):
    """Abrir o grupo selecionado para edição"""
    bl_idname = "su.edit_group"
    bl_label = "Editar grupo"

    @classmethod
    def poll(cls, context):
        return _has_objects() and len(_core("selection").objects()) == 1

    def execute(self, context):
        _cancel_running(context)
        obj = _core("selection").objects()[0]
        _core("edit_context").enter(obj)
        _redraw()
        return {'FINISHED'}


class SU_OT_entity_info(bpy.types.Operator):
    """Mostrar a seção Informações da entidade na Bandeja"""
    bl_idname = "su.entity_info"
    bl_label = "Informações da entidade"

    def execute(self, context):
        tray = registry.optional("ui.tray")
        if tray is None:
            return {'CANCELLED'}
        screen = getattr(context, "screen", None)
        for area in (screen.areas if screen is not None else ()):
            if area.type == 'VIEW_3D' and not area.spaces.active.show_region_ui:
                area.spaces.active.show_region_ui = True
        tray.set_open("entity", True, context.window_manager)
        return {'FINISHED'}


# Criar componente (LTS button + G): a COMMAND tool. A click on it in the Large Tool Set makes it the
# workspace tool for a moment: activate() runs the command and goes back to the previous tool.
_prev_tool = [""]


def _on_tool(old="", new="", **_kw):
    if new and new != "su.make_component":
        _prev_tool[0] = new


@tool(ToolMeta(id="su.make_component", label_key="tool.su.make_component.label",
               icon="ops.mesh.primitive_cube_add_gizmo", kind='COMMAND', operator="su.make_component",
               shortcut="G"))
class MakeComponentCommand(BaseTool):
    def activate(self, tc):
        back = _prev_tool[0] or "su.select"
        try:
            make_component()
        finally:
            if not bpy.app.background:
                registry.deferred(lambda: base.set_workspace_tool(back), 0.0)


# ---------------------------------------------------------------------------------------------- clipboard (P1)

_CLIP = {"geo": None, "objects": []}     # geometry in WORLD space + detached object copies


def _store_object(obj):
    """Detached deep copy of a group (not linked to any scene; children too)."""
    new = obj.copy()
    if obj.data is not None:
        new.data = obj.data.copy()
    new.use_fake_user = True
    kids = [_store_object(c) for c in obj.children]
    for k in kids:
        k.parent = new
    return new


def _clip_objects():
    """Stored clipboard objects that still exist (stored by name: undo/load re-allocate IDs)."""
    return [o for o in (bpy.data.objects.get(n) for n in _CLIP["objects"]) if o is not None]


def _free_clip_objects():
    try:
        for o in _clip_objects():
            for x in list(o.children_recursive) + [o]:
                me = x.data if x.type == 'MESH' else None
                bpy.data.objects.remove(x)
                if me is not None and me.users == 0:
                    bpy.data.meshes.remove(me)
    except (ReferenceError, AttributeError):
        pass
    _CLIP["objects"] = []


def copy_selection():
    """Copiar: selected faces (+ their edges), edges and groups of the context go to the clipboard."""
    from ..core import document, geom, selection
    refs = selection.get()
    if not refs:
        return False
    geo = {"verts": [], "edges": [], "faces": []}
    vid = {}

    def v_of(doc, v):
        k = (doc.key, v.index)
        if k not in vid:
            vid[k] = len(geo["verts"])
            geo["verts"].append(tuple(doc.world() @ v.co))
        return vid[k]
    by_doc = {}
    for r in refs:
        if r.kind in (selection.EDGE, selection.FACE):
            by_doc.setdefault(r.doc_key, {selection.EDGE: set(), selection.FACE: set()})[r.kind].add(r.index)
    for key, sel in by_doc.items():
        doc = document.get_by_key(key)
        if doc is None:
            continue
        bm = doc.bm
        lay = geom.ensure_layers(bm)
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        faces = [bm.faces[i] for i in sel[selection.FACE] if i < len(bm.faces)]
        edges = {bm.edges[i] for i in sel[selection.EDGE] if i < len(bm.edges)} | {e for f in faces for e in f.edges}
        mats = doc.obj.data.materials
        for e in edges:
            geo["edges"].append((v_of(doc, e.verts[0]), v_of(doc, e.verts[1]),
                                 bool(e[lay.bridge]), bool(e[lay.soft]), bool(e[lay.hidden]), int(e[lay.curve])))
        for f in faces:
            fm = mats[f.material_index] if f.material_index < len(mats) else None
            bmat = mats[f[lay.back]] if f[lay.back] < len(mats) else None
            geo["faces"].append(([v_of(doc, v) for v in f.verts], fm, bmat, bool(f.smooth)))
    _free_clip_objects()
    _CLIP["geo"] = geo if geo["verts"] else None
    _CLIP["objects"] = [_store_object(o).name for o in selection.objects()]
    return bool(_CLIP["geo"] or _CLIP["objects"])


def has_clipboard():
    return bool(_CLIP["geo"] or _clip_objects())


def paste_in_place(undo_key="edit.undo_paste"):
    """Colar no local: the clipboard is added to the edited document at the same world position
    (groups are duplicated as children of the open group). The pasted entities become the selection."""
    from mathutils import Vector
    from ..core import document, geom, materials, selection
    if not has_clipboard():
        return False
    doc = document.active()
    refs, changed = [], []
    geo = _CLIP["geo"]
    if geo:
        bm = doc.bm
        lay = geom.ensure_layers(bm)
        inv = doc.world().inverted()
        vs = [bm.verts.new(inv @ Vector(co)) for co in geo["verts"]]
        new_edges, new_faces = [], []
        for a, b, bridge, soft, hidden, curve in geo["edges"]:
            e = bm.edges.get((vs[a], vs[b])) or bm.edges.new((vs[a], vs[b]))
            e[lay.bridge], e[lay.soft], e[lay.hidden], e[lay.curve] = bridge, soft, hidden, curve
            new_edges.append(e)
        for idx, fm, bmat, smooth in geo["faces"]:
            f = bm.faces.new([vs[i] for i in idx])
            f.material_index = materials.slot_for(doc.obj, fm, 1)
            f[lay.back] = materials.slot_for(doc.obj, bmat, -1)
            f.smooth = smooth
            f.normal_update()
            new_faces.append(f)
        bm.edges.index_update()
        bm.faces.index_update()
        refs += [selection.Ref(doc.key, selection.EDGE, e.index) for e in new_edges if not e[lay.bridge]]
        refs += [selection.Ref(doc.key, selection.FACE, f.index) for f in new_faces]
        changed.append(doc)
    parent = None if document.kind(doc.obj) == document.KIND_MODEL else doc.obj
    coll = doc.obj.users_collection[0] if doc.obj.users_collection else bpy.context.scene.collection
    for o in _clip_objects():
        mw = o.matrix_world.copy()
        tmp = _link_copy(o, coll)
        tmp.parent = parent
        tmp.matrix_world = mw
        refs.append(selection.Ref(tmp.name, selection.OBJECT, 0))
    commit(changed, undo_key, select=refs)
    return True


def _link_copy(obj, coll):
    from .. import events
    new = obj.copy()
    if obj.data is not None:
        new.data = obj.data.copy()
    new.use_fake_user = False
    coll.objects.link(new)
    events.emit("doc", doc_key=new.name)
    for ch in obj.children:
        c = _link_copy(ch, coll)
        c.parent = new
        c.matrix_parent_inverse = ch.matrix_parent_inverse.copy()
    return new


def cut_selection():
    if copy_selection():
        return delete_selection("edit.undo_cut")
    return False


def paste():
    """Colar: paste in place, then Mover picks it up (click the start point, then the destination)."""
    if not paste_in_place():
        return False
    if not bpy.app.background and "su.move" in base.TOOLS:
        base.set_workspace_tool("su.move")
    return True


SU_OT_copy = _simple_op("su.copy", "Copiar", copy_selection, _has_sel)
SU_OT_cut = _simple_op("su.cut", "Recortar", cut_selection, _has_sel)
SU_OT_paste = _simple_op("su.paste", "Colar", paste, has_clipboard)
SU_OT_paste_in_place = _simple_op("su.paste_in_place", "Colar no local", paste_in_place, has_clipboard)


_classes = (SU_OT_delete_selected, SU_OT_select_all, SU_OT_select_none, SU_OT_select_invert, SU_OT_escape,
            SU_OT_close_group, SU_OT_make_group, SU_OT_make_component, SU_OT_explode, SU_OT_reverse_faces,
            SU_OT_hide, SU_OT_unhide_all, SU_OT_unhide_last, SU_OT_unhide_selected, SU_OT_edit_group,
            SU_OT_entity_info, SU_OT_copy, SU_OT_cut, SU_OT_paste, SU_OT_paste_in_place)

# Window keymap items (keymap.finalize adds them after su.vcb_key and the tool shortcuts).
KEYMAP = [
    ("su.delete_selected", {"type": 'DEL', "value": 'PRESS'}, None),
    ("su.delete_selected", {"type": 'BACK_SPACE', "value": 'PRESS'}, None),
    ("su.escape", {"type": 'ESC', "value": 'PRESS'}, None),
    ("su.select_all", {"type": 'A', "value": 'PRESS', "oskey": True}, None),
    ("su.select_none", {"type": 'A', "value": 'PRESS', "oskey": True, "shift": True}, None),
    ("su.select_invert", {"type": 'I', "value": 'PRESS', "oskey": True, "shift": True}, None),
    ("su.copy", {"type": 'C', "value": 'PRESS', "oskey": True}, None),
    ("su.cut", {"type": 'X', "value": 'PRESS', "oskey": True}, None),
    ("su.paste", {"type": 'V', "value": 'PRESS', "oskey": True}, None),
]


def register():
    i18n.register_strings(STRINGS)
    registry.register_classes(_classes)
    from .. import events
    events.subscribe("tool", _on_tool)


def unregister():
    _free_clip_objects()
    from .. import events
    events.unsubscribe("tool", _on_tool)
    registry.unregister_classes(_classes)
    i18n.unregister_strings(STRINGS)
