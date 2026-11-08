# SPDX-License-Identifier: GPL-2.0-or-later
"""Menu row (owner: D). PLANO.md §4.5 (names: Apêndice A); ported from the spike.

`TOPBAR_HT_upper_bar.draw_left` draws the app menu + the nine SketchUp menus; `draw_right` is empty
(no Blender logo menu, workspace tabs or scene selectors).

Menus by existence (§2.3-4): an operator item appears only when its operator is registered, so items
owned by F/G (`su.select_all`, `su.make_group`, `su.view_standard`…) show up as their owners land.
Built-in Blender operators are used where they are the real behaviour (files, undo, quit) or as the
fallback of a G camera command until G registers its own. Tool items (`su.*` tools) are always listed;
P2 ones are greyed and run "Em breve".
"""

import bpy

from .. import constants, i18n, registry
from .. import icons
from . import toolset

ORDER = 570

SEP = ("sep",)


def op(label_key, idname, fallback=None, **props):
    """Operator item; `fallback` = (idname, props) used while `idname` does not exist."""
    return ("op", label_key, idname, props, fallback)


def tool(tool_id):
    return ("tool", tool_id)


def sub(label_key, menu_id):
    return ("menu", label_key, menu_id)


def style(label_key, prop):
    return ("style", label_key, prop)


# key -> (label key, items)
MENUS = {
    "app": ("menu.app", [
        op("menu.about", "su.about"),
        op("menu.settings", "su.settings"),
        SEP,
        op("menu.open_full_blender", "su.open_full_blender"),
        SEP,
        op("menu.quit", "wm.quit_blender"),
    ]),
    "file": ("menu.file", [
        op("menu.new", "wm.read_homefile"),
        op("menu.open", "wm.open_mainfile"),
        SEP,
        op("menu.save", "wm.save_mainfile"),
        op("menu.save_as", "wm.save_as_mainfile"),
        op("menu.save_copy", "wm.save_as_mainfile", copy=True),
        op("menu.revert", "wm.revert_mainfile"),
        SEP,
        sub("menu.export", "SU_MT_export"),
    ]),
    "edit": ("menu.edit", [
        op("menu.undo", "ed.undo"),
        op("menu.redo", "ed.redo"),
        SEP,
        op("menu.cut", "su.cut"),
        op("menu.copy", "su.copy"),
        op("menu.paste", "su.paste"),
        op("menu.paste_in_place", "su.paste_in_place"),
        op("menu.delete", "su.delete_selected"),
        op("menu.delete_guides", "su.delete_guides"),
        SEP,
        op("menu.select_all", "su.select_all"),
        op("menu.select_none", "su.select_none"),
        op("menu.select_invert", "su.select_invert"),
        SEP,
        op("menu.hide", "su.hide"),
        sub("menu.unhide", "SU_MT_unhide"),
        SEP,
        op("menu.make_component", "su.make_component"),
        op("menu.make_group", "su.make_group"),
        op("menu.close_group", "su.close_group"),
        sub("menu.intersect", "SU_MT_intersect"),
        op("menu.reverse_faces", "su.reverse_faces"),
        op("menu.explode", "su.explode"),
    ]),
    "view": ("menu.view", [
        style("menu.hidden_geometry", "show_hidden_geometry"),
        style("menu.axes", "show_axes"),
        style("menu.guides", "show_guides"),
        SEP,
        sub("menu.edge_style", "SU_MT_edge_style"),
        sub("menu.face_style", "SU_MT_face_style"),
        op("menu.scene_tabs", "su.toggle_scene_tabs"),
    ]),
    "camera": ("menu.camera", [
        op("menu.previous", "su.view_previous"),
        op("menu.next", "su.view_next"),
        sub("menu.standard_views", "SU_MT_standard_views"),
        SEP,
        op("menu.parallel", "su.set_projection", ("view3d.view_persportho", {}), persp=False),
        op("menu.perspective", "su.set_projection", None, persp=True),
        SEP,
        tool("su.orbit"), tool("su.pan"), tool("su.zoom"),
        op("menu.zoom_window", "su.zoom_window"),
        op("menu.zoom_extents", "su.zoom_extents_cmd", ("view3d.view_all", {"center": False})),
        SEP,
        op("menu.position_camera", "su.position_camera_cmd"),
    ]),
    "draw": ("menu.draw", [
        sub("menu.lines", "SU_MT_draw_lines"),
        sub("menu.arcs", "SU_MT_draw_arcs"),
        sub("menu.shapes", "SU_MT_draw_shapes"),
    ]),
    "tools": ("menu.tools", [
        tool("su.select"), tool("su.eraser"), tool("su.paint"),
        SEP,
        tool("su.move"), tool("su.rotate"), tool("su.scale"),
        tool("su.pushpull"), tool("su.followme"), tool("su.offset"),
        SEP,
        tool("su.tape"), tool("su.protractor"), tool("su.axes"), tool("su.dimension"),
        tool("su.text"), tool("su.text3d"), tool("su.section"),
    ]),
    "window": ("menu.window", [
        sub("menu.default_tray", "SU_MT_tray_sections"),
        SEP,
        op("menu.model_info", "su.model_info"),
    ]),
    "extensions": ("menu.extensions", [
        ("label", "menu.no_extensions"),
    ]),
    "help": ("menu.help", [
        op("menu.shortcuts", "su.shortcuts"),
        SEP,
        op("menu.about", "su.about"),
    ]),
}
ORDER_MENUS = ("app", "file", "edit", "view", "camera", "draw", "tools", "window", "extensions", "help")

SUBMENUS = {
    "unhide": ("menu.unhide", [
        op("menu.unhide_selected", "su.unhide_selected"),
        op("menu.unhide_last", "su.unhide_last"),
        op("menu.unhide_all", "su.unhide_all"),
    ]),
    "export": ("menu.export", [
        op("menu.export_obj", "su.export", fmt='OBJ'),
        op("menu.export_gltf", "su.export", fmt='GLTF'),
        op("menu.export_stl", "su.export", fmt='STL'),
    ]),
    "intersect": ("menu.intersect", [
        op("menu.intersect_model", "su.intersect_faces", mode='MODEL'),
        op("menu.intersect_selection", "su.intersect_faces", mode='SELECTION'),
    ]),
    "edge_style": ("menu.edge_style", [
        style("menu.edges", "show_edges"),
        style("menu.back_edges", "show_back_edges"),
        style("menu.profiles", "show_profiles"),
    ]),
    "face_style": ("menu.face_style", [
        ("face", "menu.xray", 'XRAY'),
        ("face", "menu.wireframe", 'WIREFRAME'),
        ("face", "menu.hidden_line", 'HIDDEN_LINE'),
        ("face", "menu.shaded", 'SHADED'),
        ("face", "menu.textured", 'TEXTURED'),
        ("face", "menu.monochrome", 'MONOCHROME'),
    ]),
    "standard_views": ("menu.standard_views", [
        op("menu.view_iso", "su.view_standard", None, view='ISO'),
        op("menu.view_top", "su.view_standard", ("view3d.view_axis", {"type": 'TOP'}), view='TOP'),
        op("menu.view_bottom", "su.view_standard", ("view3d.view_axis", {"type": 'BOTTOM'}), view='BOTTOM'),
        op("menu.view_front", "su.view_standard", ("view3d.view_axis", {"type": 'FRONT'}), view='FRONT'),
        op("menu.view_back", "su.view_standard", ("view3d.view_axis", {"type": 'BACK'}), view='BACK'),
        op("menu.view_left", "su.view_standard", ("view3d.view_axis", {"type": 'LEFT'}), view='LEFT'),
        op("menu.view_right", "su.view_standard", ("view3d.view_axis", {"type": 'RIGHT'}), view='RIGHT'),
    ]),
    "draw_lines": ("menu.lines", [tool("su.line"), tool("su.freehand")]),
    "draw_arcs": ("menu.arcs", [tool("su.arc"), tool("su.arc2"), tool("su.arc3"), tool("su.pie")]),
    "draw_shapes": ("menu.shapes", [tool("su.rectangle"), tool("su.rotated_rectangle"),
                                     tool("su.circle"), tool("su.polygon")]),
}

STRINGS = {
    "menu.app": constants.PRODUCT_NAME,
    "menu.about": "Sobre o " + constants.PRODUCT_NAME,
    "menu.settings": "Configurações…",
    "menu.open_full_blender": "Abrir no Blender completo",
    "menu.quit": "Sair",
    "menu.file": "Arquivo", "menu.new": "Novo", "menu.open": "Abrir…", "menu.save": "Salvar",
    "menu.save_as": "Salvar como…", "menu.save_copy": "Salvar uma cópia como…", "menu.revert": "Reverter",
    "menu.export": "Exportar", "menu.export_obj": "OBJ…", "menu.export_gltf": "glTF…", "menu.export_stl": "STL…",
    "menu.edit": "Editar", "menu.undo": "Desfazer", "menu.redo": "Refazer", "menu.cut": "Recortar",
    "menu.copy": "Copiar", "menu.paste": "Colar", "menu.paste_in_place": "Colar no local",
    "menu.delete": "Excluir", "menu.delete_guides": "Excluir guias", "menu.select_all": "Selecionar tudo",
    "menu.select_none": "Selecionar nada", "menu.select_invert": "Inverter seleção", "menu.hide": "Ocultar",
    "menu.unhide": "Reexibir", "menu.unhide_selected": "Selecionados", "menu.unhide_last": "Último",
    "menu.unhide_all": "Tudo", "menu.make_component": "Criar componente…", "menu.make_group": "Criar grupo",
    "menu.close_group": "Fechar grupo/componente", "menu.intersect": "Interseccionar faces",
    "menu.intersect_model": "Com o modelo", "menu.intersect_selection": "Com a seleção",
    "menu.reverse_faces": "Inverter faces", "menu.explode": "Explodir",
    "menu.view": "Visualizar", "menu.hidden_geometry": "Geometria oculta", "menu.axes": "Eixos",
    "menu.guides": "Guias", "menu.edge_style": "Estilo de aresta", "menu.face_style": "Estilo de face",
    "menu.scene_tabs": "Abas de cena", "menu.edges": "Arestas", "menu.back_edges": "Arestas traseiras",
    "menu.profiles": "Perfis", "menu.xray": "Raio X", "menu.wireframe": "Grade de linhas",
    "menu.hidden_line": "Linha oculta", "menu.shaded": "Sombreado", "menu.textured": "Sombreado com texturas",
    "menu.monochrome": "Monocromático",
    "menu.camera": "Câmera", "menu.previous": "Anterior", "menu.next": "Próxima",
    "menu.standard_views": "Exibições padrão", "menu.view_iso": "Iso", "menu.view_top": "Superior",
    "menu.view_bottom": "Inferior", "menu.view_front": "Frontal", "menu.view_back": "Traseira",
    "menu.view_left": "Esquerda", "menu.view_right": "Direita", "menu.parallel": "Projeção paralela",
    "menu.perspective": "Perspectiva", "menu.zoom_window": "Janela de zoom",
    "menu.zoom_extents": "Extensões de zoom", "menu.position_camera": "Posição da câmera",
    "menu.draw": "Desenho", "menu.lines": "Linhas", "menu.arcs": "Arcos", "menu.shapes": "Formas",
    "menu.tools": "Ferramentas", "menu.window": "Janela", "menu.default_tray": "Bandeja padrão",
    "menu.model_info": "Informações do modelo", "menu.extensions": "Extensões",
    "menu.no_extensions": "Nenhuma extensão instalada", "menu.help": "Ajuda", "menu.shortcuts": "Atalhos",
}


# ------------------------------------------------------------------------------------------- helpers
def op_exists(idname):
    try:
        mod, name = idname.split(".", 1)
        getattr(getattr(bpy.ops, mod), name).get_rna_type()
        return True
    except Exception:
        return False


def _set_props(o, props):
    for k, v in props.items():
        try:
            setattr(o, k, v)
        except Exception:
            pass


def draw_items(layout, items, context):
    """Draw a menu item list; returns the number of visible entries."""
    n, pending_sep = 0, False
    for it in items:
        kind = it[0]
        if kind == "sep":
            pending_sep = n > 0
            continue
        row = None
        if kind == "op":
            _k, label_key, idname, props, fallback = it
            if op_exists(idname):
                target, tprops = idname, props
            elif fallback and op_exists(fallback[0]):
                target, tprops = fallback
            else:
                continue
            if pending_sep:
                layout.separator()
                pending_sep = False
            _set_props(layout.operator(target, text=i18n.t(label_key)), tprops)
        elif kind == "tool":
            tid = it[1]
            if pending_sep:
                layout.separator()
                pending_sep = False
            enabled = toolset.is_enabled(tid)
            row = layout.row()
            row.active = enabled
            icon = icons.tool_icon(tid, dim=not enabled)
            if enabled:
                row.operator("wm.tool_set_by_id", text=toolset.label(tid), icon_value=icon).name = tid
            else:
                row.operator("su.ui_placeholder", text=toolset.label(tid), icon_value=icon).name = toolset.label(tid)
        elif kind == "menu":
            sm = SUBMENUS.get(it[2][len("SU_MT_"):])
            if sm is not None and not _has_visible(sm[1], context):
                continue
            if pending_sep:
                layout.separator()
                pending_sep = False
            layout.menu(it[2], text=i18n.t(it[1]))
        elif kind == "style":
            st = getattr(context.scene, "su_style", None)
            if st is None or not op_exists("su.style_toggle"):
                continue
            if pending_sep:
                layout.separator()
                pending_sep = False
            on = getattr(st, it[2])
            layout.operator("su.style_toggle", text=i18n.t(it[1]),
                            icon='CHECKBOX_HLT' if on else 'CHECKBOX_DEHLT').prop = it[2]
        elif kind == "face":
            st = getattr(context.scene, "su_style", None)
            if st is None or not op_exists("su.face_style"):
                continue
            on = st.face_style == it[2]
            layout.operator("su.face_style", text=i18n.t(it[1]),
                            icon='RADIOBUT_ON' if on else 'RADIOBUT_OFF').style = it[2]
        elif kind == "label":
            r = layout.row()
            r.active = False
            r.label(text=i18n.t(it[1]))
        n += 1
    return n


def _has_visible(items, context):
    for it in items:
        if it[0] == "op" and (op_exists(it[2]) or (it[4] and op_exists(it[4][0]))):
            return True
        if it[0] == "tool":
            return True
        if it[0] == "style" and op_exists("su.style_toggle"):
            return True
        if it[0] == "face" and op_exists("su.face_style"):
            return True
    return False


def _menu_class(idname, label_key, items):
    def draw(self, context):
        draw_items(self.layout, items, context)
    return type(idname, (bpy.types.Menu,), {"bl_idname": idname, "bl_label": i18n.t(label_key), "draw": draw})


class SU_MT_tray_sections(bpy.types.Menu):
    bl_idname = "SU_MT_tray_sections"
    bl_label = "Bandeja padrão"

    def draw(self, context):
        from . import tray
        for sid, label in tray.sections():
            on = tray.is_open(sid, context.window_manager)
            self.layout.operator("su.tray_toggle", text=label,
                                 icon='CHECKBOX_HLT' if on else 'CHECKBOX_DEHLT').section = sid


def topbar_left(self, context):
    layout = self.layout
    layout.separator(factor=0.5)
    for key in ORDER_MENUS:
        layout.menu("SU_MT_" + key, text=i18n.t(MENUS[key][0]))


def topbar_right(self, context):
    pass


_classes = []


def register():
    i18n.register_strings(STRINGS)
    _classes[:] = [_menu_class("SU_MT_" + k, MENUS[k][0], MENUS[k][1]) for k in ORDER_MENUS]
    _classes.extend(_menu_class("SU_MT_" + k, v[0], v[1]) for k, v in SUBMENUS.items())
    _classes.append(SU_MT_tray_sections)
    registry.register_classes(_classes)
    registry.override(bpy.types.TOPBAR_HT_upper_bar, "draw_left", topbar_left)
    registry.override(bpy.types.TOPBAR_HT_upper_bar, "draw_right", topbar_right)


def unregister():
    registry.unregister_classes(_classes)
    _classes.clear()
    i18n.unregister_strings(STRINGS)
