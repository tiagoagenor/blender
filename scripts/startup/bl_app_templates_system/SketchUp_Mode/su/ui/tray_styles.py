# SPDX-License-Identifier: GPL-2.0-or-later
"""Tray section "Estilos" (owner: D, P1). Ported from the spike (shell_v3): original thumbnail of the
default style, its description, Selecionar/Editar/Misturar tabs and the style folders. The Editar tab
(Arestas, Perfis, Arestas traseiras, Estilo de face) arrives with §9.2-D item 10."""

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
}
FOLDERS = ("misc", "default", "sketch", "colors", "photo", "straight")


def draw(layout, context):
    row = layout.row()
    row.template_icon(icon_value=icons.resolve("png.style_simple"), scale=4.0)
    col = row.column(align=True)
    col.label(text=i18n.t("tray.styles.default_name"))
    col.label(text=i18n.t("tray.styles.default_desc1"))
    col.label(text=i18n.t("tray.styles.default_desc2"))
    tabs = layout.row(align=True)
    for key, on in (("select", True), ("edit", False), ("mix", False)):
        label = i18n.t("tray.styles.tab." + key)
        tabs.operator("su.ui_placeholder", text=label, depress=on).name = label
    grid = layout.grid_flow(columns=3, even_columns=True, align=True)
    for key in FOLDERS:
        label = i18n.t("tray.styles.folder." + key)
        grid.operator("su.ui_placeholder", text=label, icon='FILE_FOLDER').name = label


def register():
    i18n.register_strings(STRINGS)
    tray.register_section(40, "styles", "tray.styles", draw, priority='P1')


def unregister():
    tray.unregister_section("styles")
    i18n.unregister_strings(STRINGS)
