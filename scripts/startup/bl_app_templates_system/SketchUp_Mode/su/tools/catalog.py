# SPDX-License-Identifier: GPL-2.0-or-later
"""Tool layout lists (owner: A). PLANO.md §2.3-2, §4.2, §4.3, Apêndice A. Only ids live here: every tool
declares itself with @tool(ToolMeta); an id without a registered tool is shown disabled ("Em breve").

  LARGE_TOOL_SET   Conjunto extenso de ferramentas, 2 columns, None = group separator. An odd group leaves
                   its last right cell empty (the empty ex-"Etiqueta" cell, PLANO §4.3 row 3).
  GETTING_STARTED  Primeiros passos: groups; FLYOUTS maps a button to its flyout ids (first = default).
  label(id), icon(id), is_enabled(id)   for D's toolbar/LTS (fallback names for tools not registered yet).
  lts_tooldefs()   ToolDef list for VIEW3D_PT_tools_active._tools['OBJECT'] (registered tools use the
                   ToolDef Blender built for them — keymap + hover gizmo —, others a disabled placeholder).
register() turns every TOOL/NAV meta into a Blender WorkSpaceTool (after all tool modules registered
their strings: ORDER 390).
"""

from .. import i18n
from . import base

ORDER = 390

LARGE_TOOL_SET = [
    "su.select", "su.lasso", "su.paint", "su.eraser", "su.make_component", None,
    "su.line", "su.freehand", "su.rectangle", "su.rotated_rectangle", "su.circle", "su.polygon",
    "su.arc", "su.arc2", "su.arc3", "su.pie", None,
    "su.move", "su.pushpull", "su.rotate", "su.followme", "su.scale", "su.offset", "su.axes", "su.flip", None,
    "su.tape", "su.dimension", "su.protractor", "su.text", "su.section", "su.text3d", None,
    "su.orbit", "su.pan", "su.zoom", "su.zoom_window", "su.zoom_extents", "su.previous", None,
    "su.position_camera", "su.walk", "su.look_around", "su.fov",
]

GETTING_STARTED = [
    ["su.search"],
    ["su.select"],
    ["su.eraser", "su.line", "su.arc2", "su.rectangle"],
    ["su.pushpull", "su.offset", "su.move", "su.rotate", "su.scale", "su.flip"],
    ["su.tape", "su.paint"],
    ["su.orbit", "su.pan", "su.zoom", "su.zoom_extents"],
]

FLYOUTS = {
    "su.select": ["su.select", "su.lasso"],
    "su.line": ["su.line", "su.freehand"],
    "su.arc2": ["su.arc2", "su.arc", "su.arc3", "su.pie"],
    "su.rectangle": ["su.rectangle", "su.rotated_rectangle", "su.circle", "su.polygon"],
}

# Fallback name/icon of ids not registered (yet). Names = Apêndice A (QRC 2026 pt-BR Mac); icons from the
# spike ("bi.NAME" = Blender built-in icon, else a toolbar .dat icon name).
FALLBACK = {
    "su.search": ("Pesquisar", "bi.VIEWZOOM"),
    "su.select": ("Selecionar", "ops.generic.select"),
    "su.lasso": ("Lasso", "ops.generic.select_lasso"),
    "su.paint": ("Pintura", "brush.gpencil_draw.fill"),
    "su.eraser": ("Apagar", "brush.gpencil_draw.erase"),
    "su.make_component": ("Criar componente", "ops.mesh.primitive_cube_add_gizmo"),
    "su.line": ("Linha", "ops.gpencil.primitive_line"),
    "su.freehand": ("Desenho à mão livre", "ops.gpencil.draw"),
    "su.rectangle": ("Retângulo", "ops.gpencil.primitive_box"),
    "su.rotated_rectangle": ("Retângulo girado", "ops.transform.resize.cage"),
    "su.circle": ("Círculo", "ops.gpencil.primitive_circle"),
    "su.polygon": ("Polígono", "ops.gpencil.primitive_polyline"),
    "su.arc": ("Arco", "ops.gpencil.primitive_arc"),
    "su.arc2": ("Arco de dois pontos", "ops.gpencil.primitive_curve"),
    "su.arc3": ("Arco de três pontos", "ops.mesh.spin"),
    "su.pie": ("Pizza", "ops.gpencil.edit_bend"),
    "su.move": ("Mover", "ops.transform.translate"),
    "su.pushpull": ("Empurrar/puxar", "ops.mesh.extrude_region_move"),
    "su.rotate": ("Girar", "ops.transform.rotate"),
    "su.followme": ("Siga-me", "ops.mesh.extrude_faces_move"),
    "su.scale": ("Escala", "ops.transform.resize"),
    "su.offset": ("Equidistância", "ops.mesh.inset"),
    "su.axes": ("Eixos", "bi.EMPTY_AXIS"),
    "su.flip": ("Virar", "ops.gpencil.edit_mirror"),
    "su.tape": ("Fita métrica", "ops.view3d.ruler"),
    "su.dimension": ("Dimensões", "bi.DRIVER_DISTANCE"),
    "su.protractor": ("Transferidor", "bi.DRIVER_ROTATIONAL_DIFFERENCE"),
    "su.text": ("Texto", "bi.FILE_TEXT"),
    "su.section": ("Plano de seção", "ops.mesh.bisect"),
    "su.text3d": ("Texto em 3D", "bi.OUTLINER_OB_FONT"),
    "su.orbit": ("Órbita", "bi.ORIENTATION_GIMBAL"),
    "su.pan": ("Panorâmica", "bi.VIEW_PAN"),
    "su.zoom": ("Aplicar zoom", "bi.ZOOM_IN"),
    "su.zoom_window": ("Janela de zoom", "bi.ZOOM_SELECTED"),
    "su.zoom_extents": ("Extensões de zoom", "bi.ZOOM_ALL"),
    "su.previous": ("Anterior", "bi.ZOOM_PREVIOUS"),
    "su.position_camera": ("Posição da câmera", "bi.VIEW_CAMERA"),
    "su.walk": ("Percorrer", "bi.ARMATURE_DATA"),
    "su.look_around": ("Olhar ao redor", "bi.HIDE_OFF"),
    "su.fov": ("Campo de visão", "bi.VIEW_PERSPECTIVE"),
}


def all_ids():
    ids = [t for t in LARGE_TOOL_SET if t]
    for grp in GETTING_STARTED:
        for t in grp:
            if t not in ids:
                ids.append(t)
    return ids


def is_enabled(tool_id):
    cls = base.TOOLS.get(tool_id)
    return cls is not None and cls.meta.enabled


def label(tool_id):
    cls = base.TOOLS.get(tool_id)
    if cls is not None:
        return i18n.t(cls.meta.label_key)
    fb = FALLBACK.get(tool_id)
    return fb[0] if fb else tool_id


def icon(tool_id):
    cls = base.TOOLS.get(tool_id)
    if cls is not None and cls.meta.icon:
        return cls.meta.icon
    fb = FALLBACK.get(tool_id)
    return fb[1] if fb else "ops.generic.select"


def placeholder_tooldef(tool_id):
    from bl_ui.space_toolsystem_common import ToolDef
    name = label(tool_id)
    return ToolDef.from_dict(dict(idname=tool_id, label=name, description=i18n.t("app.coming_soon", name=name),
                                  icon=icon(tool_id), cursor='DEFAULT', keymap=None))


def lts_tooldefs():
    """[ToolDef | None] in LARGE_TOOL_SET order (for D's toolset)."""
    out = []
    for tid in LARGE_TOOL_SET:
        if tid is None:
            out.append(None)
            continue
        td = base.bl_tool(tid)
        out.append(td if td is not None else placeholder_tooldef(tid))
    return out


def register():
    base.register_workspace_tools()


def unregister():
    pass   # base.unregister() removes the WorkSpaceTools
