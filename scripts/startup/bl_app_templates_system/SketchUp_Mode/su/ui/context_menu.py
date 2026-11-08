# SPDX-License-Identifier: GPL-2.0-or-later
"""Context menu of the 3D view (owner: F). PLANO.md §4.5 (Menu de contexto), §5.2.

Right click (or Ctrl+click, Mac) over the viewport → A's su.context_menu opens SU_MT_context. Before
that, `select_under(context, xy)` makes the entity under the cursor the selection when it is not
selected yet (SketchUp) — A's operator calls it when this module is loaded. Menu:
    Informações da entidade · Excluir · Ocultar · Selecionar ▸ · Criar grupo · Inverter faces ·
    Explodir · Editar grupo · Zoom na seleção
Items exist only when their operator is registered (menus by existence); polls grey them out.
"""

import bpy
from mathutils import Vector

from .. import i18n, perf, registry

ORDER = 565

STRINGS = {
    "edit.ctx.entity_info": {"pt_BR": "Informações da entidade", "en": "Entity Info"},
    "edit.ctx.delete": {"pt_BR": "Excluir", "en": "Erase"},
    "edit.ctx.hide": {"pt_BR": "Ocultar", "en": "Hide"},
    "edit.ctx.select": {"pt_BR": "Selecionar", "en": "Select"},
    "edit.ctx.select_all": {"pt_BR": "Tudo", "en": "All"},
    "edit.ctx.select_none": {"pt_BR": "Nada", "en": "None"},
    "edit.ctx.select_invert": {"pt_BR": "Inverter seleção", "en": "Invert Selection"},
    "edit.ctx.select_connected": {"pt_BR": "Tudo conectado", "en": "All Connected"},
    "edit.ctx.make_group": {"pt_BR": "Criar grupo", "en": "Make Group"},
    "edit.ctx.reverse_faces": {"pt_BR": "Inverter faces", "en": "Reverse Faces"},
    "edit.ctx.explode": {"pt_BR": "Explodir", "en": "Explode"},
    "edit.ctx.edit_group": {"pt_BR": "Editar grupo", "en": "Edit Group"},
    "edit.ctx.close_group": {"pt_BR": "Fechar grupo", "en": "Close Group"},
    "edit.ctx.zoom_selection": {"pt_BR": "Zoom na seleção", "en": "Zoom Selection"},
    "edit.ctx.unhide_all": {"pt_BR": "Reexibir tudo", "en": "Unhide All"},
}

ITEMS = (
    ("edit.ctx.entity_info", "su.entity_info"),
    None,
    ("edit.ctx.delete", "su.delete_selected"),
    ("edit.ctx.hide", "su.hide"),
    ("edit.ctx.unhide_all", "su.unhide_all"),
    ("menu", "edit.ctx.select", "SU_MT_context_select"),
    None,
    ("edit.ctx.make_group", "su.make_group"),
    ("edit.ctx.reverse_faces", "su.reverse_faces"),
    ("edit.ctx.explode", "su.explode"),
    ("edit.ctx.edit_group", "su.edit_group"),
    ("edit.ctx.close_group", "su.close_group"),
    None,
    ("edit.ctx.zoom_selection", "su.zoom_selection"),
)

SELECT_ITEMS = (
    ("edit.ctx.select_all", "su.select_all"),
    ("edit.ctx.select_none", "su.select_none"),
    ("edit.ctx.select_invert", "su.select_invert"),
    ("edit.ctx.select_connected", "su.select_connected"),
)


def _op_exists(idname):
    mod, _, name = idname.partition(".")
    try:
        getattr(getattr(bpy.ops, mod), name).get_rna_type()
        return True
    except (AttributeError, KeyError):
        return False


def _draw_items(layout, items):
    for it in items:
        if it is None:
            layout.separator()
        elif it[0] == "menu":
            layout.menu(it[2], text=i18n.t(it[1]))
        elif _op_exists(it[1]):
            layout.operator(it[1], text=i18n.t(it[0]))


class SU_MT_context(bpy.types.Menu):
    bl_idname = "SU_MT_context"
    bl_label = ""

    def draw(self, context):
        _draw_items(self.layout, ITEMS)


class SU_MT_context_select(bpy.types.Menu):
    bl_idname = "SU_MT_context_select"
    bl_label = "Selecionar"

    def draw(self, context):
        _draw_items(self.layout, SELECT_ITEMS)


def _view3d_window(context):
    area, region = getattr(context, "area", None), getattr(context, "region", None)
    return area is not None and area.type == 'VIEW_3D' and region is not None and region.type == 'WINDOW'


def select_under(context, xy):
    """SketchUp: right click on an entity that is not selected selects it; on empty space keeps the
    selection. Returns the Ref picked (or None)."""
    from ..core import selection
    from ..tools import base, select as sel_tool
    tc = base.tool_context(context, xy=xy)
    p = sel_tool.pick(tc, xy, None)
    ref = sel_tool.resolve(*p) if p is not None else None
    if ref is not None and ref not in selection.get():
        selection.set(sel_tool.entity_refs(ref))
    return ref


class SU_OT_select_connected(bpy.types.Operator):
    """Selecionar tudo o que está conectado à seleção"""
    bl_idname = "su.select_connected"
    bl_label = "Tudo conectado"

    @classmethod
    def poll(cls, context):
        sel = registry.optional("core.selection")
        return sel is not None and any(r.kind in ('EDGE', 'FACE') for r in sel.get())

    def execute(self, context):
        from ..core import selection
        refs = set()
        for r in list(selection.get()):
            if r.kind in (selection.EDGE, selection.FACE) and r not in refs:
                refs.update(selection.connected(r))
        selection.add(refs)
        return {'FINISHED'}


class SU_OT_zoom_selection(bpy.types.Operator):
    """Enquadrar a seleção na vista"""
    bl_idname = "su.zoom_selection"
    bl_label = "Zoom na seleção"

    @classmethod
    def poll(cls, context):
        sel = registry.optional("core.selection")
        return sel is not None and not sel.is_empty()

    def execute(self, context):
        from ..core import selection
        camera = registry.optional("core.camera")
        if camera is not None and hasattr(camera, "zoom_extents"):
            try:
                camera.zoom_extents(selection_only=True)
                return {'FINISHED'}
            except Exception:
                perf.exception("camera.zoom_extents(selection_only)")
        b = selection.bounds_world()
        if b is None:
            return {'CANCELLED'}
        mn, mx = b
        center = (mn + mx) * 0.5
        radius = max((mx - mn).length * 0.5, 0.5)
        screen = getattr(context, "screen", None)
        for area in (screen.areas if screen is not None else ()):
            if area.type == 'VIEW_3D':
                rv3d = area.spaces.active.region_3d
                rv3d.view_location = center
                rv3d.view_distance = radius * 3.0
                area.tag_redraw()
        return {'FINISHED'}


_classes = (SU_MT_context, SU_MT_context_select, SU_OT_select_connected, SU_OT_zoom_selection)


def register():
    i18n.register_strings(STRINGS)
    registry.register_classes(_classes)


def unregister():
    registry.unregister_classes(_classes)
    i18n.unregister_strings(STRINGS)
