# SPDX-License-Identifier: GPL-2.0-or-later
"""Default Tray — "Bandeja padrão" (owner: D). Contract PLANO.md §2.4, §4.4; ported from the spike.

ONE `HIDE_HEADER` panel in the 3D view's UI region, category "Bandeja" (HIDE_HEADER panels have no
Blender drag grip): a title row ("Bandeja padrão", pin, ✕) and one flat box row per section (chevron +
name + ✕, theme `wcol_box`), the body drawn below an open row. The panel's category is cleared at
its first draw, so the region has no category and no tab strip (the theme also hides `wcol_tab`).

    register_section(order, id, label_key, draw_fn, priority='P0')   # draw_fn(layout, context)

Sections with priority P2 are greyed rows (SHOW_P2_SECTIONS). Registering an existing id replaces it (D registers
placeholder rows for the F/G sections until their owners register the real ones). All rows start
CLOSED (2027 behaviour); the open set lives in `wm.su_tray.open_ids` (not saved: P2 = remember).
"""

import bpy
from bpy.props import EnumProperty, StringProperty

from .. import i18n, registry
from .. import icons

ORDER = 550

CATEGORY = "Bandeja"
# P2 sections (Sombras, Suavizar arestas, Estruturador) are shown as greyed rows in SketchUp's order
# (lead's decision after M-A: "everything except tags equal to SketchUp"; overrides PLANO §4.4). Their
# body says the feature is coming. Tags never appear.
SHOW_P2_SECTIONS = True

STRINGS = {
    "tray.title": "Bandeja padrão",
    "tray.entity": "Informações da entidade",
    "tray.materials": "Materiais",
    "tray.components": "Componentes",
    "tray.styles": "Estilos",
    "tray.scenes": "Cenas",
    "tray.close": "Fechar",
    "tray.placeholder.entity": "Nenhuma seleção",
    "tray.placeholder.materials": "Em uso no modelo",
    "tray.placeholder.soon": "Em breve.",
    "tray.shadows": "Sombras",
    "tray.soften": "Suavizar arestas",
    "tray.outliner": "Estruturador",
}

_sections = {}     # id -> dict(order, label_key, draw, priority, placeholder)


def register_section(order, id, label_key, draw_fn, priority='P0', *, placeholder=False):
    """Add/replace a tray section. P2 sections are dropped (not shown)."""
    if priority == 'P2' and not SHOW_P2_SECTIONS:
        _sections.pop(id, None)
        return
    _sections[id] = dict(order=order, label_key=label_key, draw=draw_fn, priority=priority,
                         placeholder=placeholder)
    _redraw()


def unregister_section(id):
    _sections.pop(id, None)
    _redraw()


def sections():
    """Visible sections in order: [(id, label)]."""
    return [(sid, i18n.t(s["label_key"])) for sid, s in sorted(_sections.items(), key=lambda kv: kv[1]["order"])]


def _open_set(wm):
    tray = getattr(wm, "su_tray", None)
    if tray is None or not tray.open_ids:
        return set()
    return set(tray.open_ids.split(","))


def is_open(section_id, wm=None):
    return section_id in _open_set(wm or bpy.context.window_manager)


def set_open(section_id, on, wm=None):
    wm = wm or bpy.context.window_manager
    s = _open_set(wm)
    (s.add if on else s.discard)(section_id)
    wm.su_tray.open_ids = ",".join(sorted(s))
    _redraw()


def close_all(wm=None):
    wm = wm or bpy.context.window_manager
    if getattr(wm, "su_tray", None) is not None:
        wm.su_tray.open_ids = ""


def _redraw():
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return
    for win in wm.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                for r in area.regions:
                    if r.type == 'UI':
                        r.tag_redraw()


class SU_PG_tray(bpy.types.PropertyGroup):
    open_ids: StringProperty(name="Seções abertas", default="")
    # Measurements field shown by the status bar until A's wm.su_vcb exists.
    vcb_fallback: StringProperty(name="Medidas", default="")
    styles_tab: EnumProperty(name="Aba", items=(('SELECT', "Selecionar", ""), ('EDIT', "Editar", ""),
                                                ('MIX', "Misturar", "")), default='SELECT')


class SU_OT_tray_toggle(bpy.types.Operator):
    bl_idname = "su.tray_toggle"
    bl_label = "Abrir/fechar seção"
    bl_options = {'INTERNAL'}
    section: StringProperty()

    @classmethod
    def description(cls, context, props):
        s = _sections.get(props.section)
        return i18n.t(s["label_key"]) if s else ""

    def execute(self, context):
        set_open(self.section, not is_open(self.section, context.window_manager), context.window_manager)
        return {'FINISHED'}


class SU_PT_tray(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_label = "Bandeja padrão"
    bl_options = {'HIDE_HEADER'}
    bl_order = 0

    def draw(self, context):
        if self.bl_category:
            # §9.2-D 9.4: a panel type WITHOUT category adds no category to the region, so Blender
            # reserves no tab strip (≈20 pt). Python registration forces a category ("Misc"), but
            # PanelType.category is writable from an instance: clear it once (CATEGORY is kept on
            # the class for hide.py / active_panel_category).
            self.bl_category = ""
            context.region.tag_redraw()
        wm = context.window_manager
        opened = _open_set(wm)
        lay = self.layout
        row = lay.row()
        row.label(text=i18n.t("tray.title"))
        r = row.row(align=False)
        r.alignment = 'RIGHT'
        r.label(text="", icon_value=icons.ui_icon("pin"))
        r.label(text="", icon_value=icons.ui_icon("close"))
        col = lay.column(align=True)
        for sid, s in sorted(_sections.items(), key=lambda kv: kv[1]["order"]):
            is_open_ = sid in opened
            box = col.box()
            box.active = s["priority"] != 'P2'
            hr = box.row(align=True)
            left = hr.row(align=True)
            left.alignment = 'LEFT'
            left.operator("su.tray_toggle", text="", emboss=False,
                          icon='DOWNARROW_HLT' if is_open_ else 'RIGHTARROW').section = sid
            left.operator("su.tray_toggle", text=i18n.t(s["label_key"]), emboss=False).section = sid
            x = hr.row()
            x.alignment = 'RIGHT'
            x.operator("su.ui_placeholder", text="", icon_value=icons.ui_icon("close"),
                       emboss=False).name = i18n.t("tray.close") + " " + i18n.t(s["label_key"])
            if is_open_:
                body = col.column()
                body.separator(factor=0.4)
                try:
                    s["draw"](body, context)
                except Exception:
                    from .. import perf
                    perf.exception("tray section {!r}".format(sid))
                body.separator(factor=0.6)


def _placeholder(text_key):
    def draw(layout, context):
        layout.label(text=i18n.t(text_key))
    return draw


_classes = (SU_PG_tray, SU_OT_tray_toggle, SU_PT_tray)


def register():
    i18n.register_strings(STRINGS)
    registry.register_classes(_classes)
    bpy.types.WindowManager.su_tray = bpy.props.PointerProperty(type=SU_PG_tray)
    # Placeholder rows for the F/G sections (replaced when the owners register theirs).
    for order, sid, prio, key in ((10, "entity", 'P0', "tray.placeholder.entity"),
                                  (20, "materials", 'P0', "tray.placeholder.materials"),
                                  (30, "components", 'P1', "tray.placeholder.soon"),
                                  (50, "scenes", 'P1', "tray.placeholder.soon"),
                                  (45, "shadows", 'P2', "tray.placeholder.soon"),
                                  (60, "soften", 'P2', "tray.placeholder.soon"),
                                  (70, "outliner", 'P2', "tray.placeholder.soon")):
        if sid not in _sections:
            register_section(order, sid, "tray." + sid, _placeholder(key), prio, placeholder=True)


def unregister():
    del bpy.types.WindowManager.su_tray
    registry.unregister_classes(_classes)
    for sid in [k for k, s in _sections.items() if s["placeholder"]]:
        _sections.pop(sid)
    i18n.unregister_strings(STRINGS)
