# SPDX-License-Identifier: GPL-2.0-or-later
"""Tray section "Estilos" (owner: D, P1). Ported from the spike (shell_v3): original thumbnail of the
default style, its description, Selecionar/Editar/Misturar tabs and the style folders. The Editar tab
shows Arestas / Arestas traseiras / Perfis, the face styles (Raio X, Grade de linhas, Linha oculta,
Sombreado, Sombreado com texturas, Monocromático) and Eixos — all bound to Scene.su_style (§9.2-D 10)."""

from .. import i18n
from .. import icons
from . import tray

ORDER = 560

STRINGS = {
    "tray.styles.default_name": "Estilo simples",
    "tray.styles.default_desc1": "Cores padrão de face. Céu azul",
    "tray.styles.default_desc2": "e fundo cinza.",
    "tray.styles.tab.select": "Selecionar",
    "tray.styles.tab.edit": "Editar",
    "tray.styles.tab.mix": "Misturar",
    "tray.styles.folder.misc": "Diversos",
    "tray.styles.folder.colors": "Cores",
    "tray.styles.folder.default": "Padrão",
    "tray.styles.folder.photo": "Foto",
    "tray.styles.folder.sketch": "Esboço",
    "tray.styles.folder.straight": "Retas",
    "tray.styles.edges": "Configurações de aresta",
    "tray.styles.faces": "Configurações de face",
    "tray.styles.background": "Configurações de modelagem",
    "tray.styles.mix_soon": "Misturar estilos: em breve.",
}
FOLDERS = ("misc", "default", "sketch", "colors", "photo", "straight")


def draw(layout, context):
    row = layout.row()
    row.template_icon(icon_value=icons.resolve("png.style_simple"), scale=4.0)
    col = row.column(align=True)
    col.label(text=i18n.t("tray.styles.default_name"))
    col.label(text=i18n.t("tray.styles.default_desc1"))
    col.label(text=i18n.t("tray.styles.default_desc2"))
    tray_props = context.window_manager.su_tray
    layout.row(align=True).prop(tray_props, "styles_tab", expand=True)
    tab = tray_props.styles_tab
    if tab == 'SELECT':
        grid = layout.grid_flow(columns=3, even_columns=True, align=True)
        for key in FOLDERS:
            label = i18n.t("tray.styles.folder." + key)
            grid.operator("su.ui_placeholder", text=label, icon='FILE_FOLDER').name = label
    elif tab == 'EDIT':
        st = getattr(context.scene, "su_style", None)
        if st is None:
            return
        box = layout.box()
        box.label(text=i18n.t("tray.styles.edges"))
        for prop in ("show_edges", "show_back_edges", "show_profiles"):
            box.prop(st, prop)
        box = layout.box()
        box.label(text=i18n.t("tray.styles.faces"))
        box.prop(st, "face_style", expand=True)
        box = layout.box()
        box.label(text=i18n.t("tray.styles.background"))
        box.prop(st, "show_axes")
    else:
        layout.label(text=i18n.t("tray.styles.mix_soon"))


def register():
    i18n.register_strings(STRINGS)
    tray.register_section(40, "styles", "tray.styles", draw, priority='P1')


def unregister():
    tray.unregister_section("styles")
    i18n.unregister_strings(STRINGS)
