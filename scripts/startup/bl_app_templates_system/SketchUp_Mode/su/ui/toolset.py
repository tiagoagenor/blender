# SPDX-License-Identifier: GPL-2.0-or-later
"""Large Tool Set (owner: D) — the left toolbar in 2 columns. PLANO.md §4.3; ported from the spike.

* `VIEW3D_PT_tools_active._tools['OBJECT']` is replaced by the LTS layout: real tools (registered with
  `bpy.utils.register_tool` by their owners, found by idname) keep their ToolDef (keymap, cursor…) with
  D's icon; ids without a registered tool get a placeholder ToolDef. `None` = separator. An odd number
  of tools in a group leaves the last right cell empty (the empty cell where SketchUp has its tag tool).
* Two columns are forced by patching `_layout_generator_detect_from_region`.
* `_tools[None] = []` and `tool_fallback_id = 'su.select'` (else "builtin.select_box not found").
* Disabled buttons (P2, or `ToolMeta.enabled=False`) use the `_dim` icon.
Layout lists come from A's `tools/catalog.py` when present; otherwise from the spike lists below (same
ids, Apêndice A). Labels: `ToolMeta.label_key` through i18n, else the pt-BR fallback table.
"""

import sys

import bpy

from .. import i18n, perf, registry
from .. import icons

ORDER = 520

# Spike lists (2027 order, CRITICA grouping); A's catalog wins when it exists.
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
    ["su.search"], ["su.select"],
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
# pt-BR labels (Apêndice A) used until the tool's owner registers its ToolMeta.
LABELS = {
    "su.search": "Pesquisar", "su.select": "Selecionar", "su.lasso": "Lasso", "su.paint": "Pintura",
    "su.eraser": "Apagar", "su.make_component": "Criar componente", "su.make_group": "Criar grupo",
    "su.line": "Linha", "su.freehand": "Desenho à mão livre", "su.rectangle": "Retângulo",
    "su.rotated_rectangle": "Retângulo girado", "su.circle": "Círculo", "su.polygon": "Polígono",
    "su.arc": "Arco", "su.arc2": "Arco de dois pontos", "su.arc3": "Arco de três pontos", "su.pie": "Pizza",
    "su.move": "Mover", "su.pushpull": "Empurrar/puxar", "su.rotate": "Girar", "su.followme": "Siga-me",
    "su.scale": "Escala", "su.offset": "Equidistância", "su.axes": "Eixos", "su.flip": "Virar",
    "su.tape": "Fita métrica", "su.dimension": "Dimensões", "su.protractor": "Transferidor",
    "su.text": "Texto", "su.section": "Plano de seção", "su.text3d": "Texto em 3D",
    "su.orbit": "Órbita", "su.pan": "Panorâmica", "su.zoom": "Aplicar zoom",
    "su.zoom_window": "Janela de zoom", "su.zoom_extents": "Extensões de zoom", "su.previous": "Anterior",
    "su.position_camera": "Posição da câmera", "su.walk": "Percorrer", "su.look_around": "Olhar ao redor",
    "su.fov": "Campo de visão",
}
SHORTCUTS = {
    "su.select": "Espaço", "su.paint": "B", "su.eraser": "E", "su.make_component": "G", "su.line": "L",
    "su.rectangle": "R", "su.circle": "C", "su.arc2": "A", "su.move": "M", "su.pushpull": "P",
    "su.rotate": "Q", "su.scale": "S", "su.offset": "F", "su.tape": "T", "su.orbit": "O", "su.pan": "H",
    "su.zoom": "Z", "su.zoom_extents": "Shift+Z",
}
PRIORITY = {
    "su.lasso": "P2", "su.freehand": "P2", "su.rotated_rectangle": "P2", "su.arc3": "P2", "su.pie": "P2",
    "su.axes": "P2", "su.section": "P2", "su.walk": "P2", "su.look_around": "P2", "su.fov": "P2",
    "su.arc": "P1", "su.flip": "P1", "su.text": "P1", "su.text3d": "P1", "su.zoom_window": "P1",
    "su.previous": "P1", "su.position_camera": "P1", "su.search": "P1",
}

_saved = {}


def _sib(name):
    return sys.modules.get(__package__.rsplit(".", 1)[0] + "." + name)


# ------------------------------------------------------------------------------------------- catalogue
def layout_lists():
    """(large_tool_set, getting_started, flyouts) — A's catalog when present, else the spike lists."""
    cat = _sib("tools.catalog")
    lts = getattr(cat, "LARGE_TOOL_SET", None) or LARGE_TOOL_SET
    gs = getattr(cat, "GETTING_STARTED", None) or GETTING_STARTED
    fly = getattr(cat, "FLYOUTS", None) or FLYOUTS
    return lts, gs, fly


def meta(tool_id):
    base = _sib("tools.base")
    cls = base.TOOLS.get(tool_id) if base is not None else None
    return getattr(cls, "meta", None)


def label(tool_id):
    m = meta(tool_id)
    if m is not None and m.label_key and i18n.has(m.label_key):
        return i18n.t(m.label_key)
    return LABELS.get(tool_id, tool_id)


def priority(tool_id):
    m = meta(tool_id)
    if m is not None:
        return m.priority
    return PRIORITY.get(tool_id, "P0")


def is_enabled(tool_id):
    m = meta(tool_id)
    if m is not None:
        return bool(m.enabled) and m.priority != "P2"
    return PRIORITY.get(tool_id, "P0") != "P2"


def tooltip(tool_id):
    sc = SHORTCUTS.get(tool_id)
    m = meta(tool_id)
    if m is not None and m.shortcut:
        sc = m.shortcut
    text = label(tool_id)
    if not is_enabled(tool_id):
        text += " — " + i18n.t("ui.coming_soon")
    return text + (" ({:s})".format(sc) if sc else "")


# ------------------------------------------------------------------------------------------- LTS
def _flatten(items):
    for it in items:
        if it is None:
            continue
        if isinstance(it, tuple) and not hasattr(it, "idname"):
            yield from _flatten(it)
        elif hasattr(it, "idname"):
            yield it


def registered_tooldefs():
    from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active as TA
    out = {}
    for td in _flatten(_saved.get("tools_object", TA._tools.get('OBJECT', []))):
        if td.idname.startswith("su."):
            out[td.idname] = td
    return out


def tooldef(tool_id, existing=None):
    from bl_ui.space_toolsystem_common import ToolDef
    enabled = is_enabled(tool_id)
    icon = icons.tool_handle(tool_id, dim=not enabled)
    if existing is not None:
        return existing._replace(icon=icon, label=label(tool_id), description=tooltip(tool_id))
    return ToolDef.from_dict(dict(idname=tool_id, label=label(tool_id), description=tooltip(tool_id),
                                  icon=icon, cursor='DEFAULT', keymap=None))


def build_tools():
    lts, _gs, _fly = layout_lists()
    reg = registered_tooldefs()
    return [None if t is None else tooldef(t, reg.get(t)) for t in lts]


def rebuild():
    """Re-create the LTS (call after tools are (un)registered or labels change)."""
    from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active as TA
    TA._tools['OBJECT'] = build_tools()
    TA._tools[None] = []


def _force_two_columns(layout, region, scale_y):
    from bl_ui.space_toolsystem_common import ToolSelectPanelHelper as TSP
    return TSP._layout_generator_multi_columns(layout, column_count=2, scale_y=scale_y), False


def lts_ids():
    """Order of the LTS as drawn (None = separator), for tests/state_dump."""
    from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active as TA
    return [None if t is None else getattr(t, "idname", None) for t in TA._tools.get('OBJECT', [])]


def register():
    from bl_ui.space_toolsystem_common import ToolSelectPanelHelper as TSP
    from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active as TA
    _saved["tools_object"] = list(TA._tools.get('OBJECT', []))
    _saved["tools_none"] = list(TA._tools.get(None, []))
    registry.override(TA, "tool_fallback_id", "su.select")
    registry.override(TSP, "_layout_generator_detect_from_region", staticmethod(_force_two_columns))
    try:
        rebuild()
    except Exception:
        perf.exception("toolset: LTS build")


def unregister():
    from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active as TA
    if "tools_object" in _saved:
        TA._tools['OBJECT'] = _saved.pop("tools_object")
        TA._tools[None] = _saved.pop("tools_none")
