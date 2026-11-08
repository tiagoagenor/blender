# SPDX-License-Identifier: GPL-2.0-or-later
"""Bandeja ▸ Cenas (owner: G, P1). PLANO.md §4.4.

+ adds a scene with the current view, − deletes the selected one, ⟳ stores the current view in it;
clicking a scene goes to it. Scenes live in Scene.su_pages (core/camera.py; saved, undoable).
"""

from .. import i18n, registry

ORDER = 575

STRINGS = {
    "cam.scenes_empty": {"pt_BR": "Nenhuma cena. Clique em + para adicionar a vista atual.",
                         "en": "No scenes. Click + to add the current view."},
    "cam.scene_name": {"pt_BR": "Nome", "en": "Name"},
    "cam.scene_description": {"pt_BR": "Descrição", "en": "Description"},
}


def draw(layout, context):
    pg = getattr(context.scene, "su_pages", None)
    if pg is None:
        return
    row = layout.row(align=True)
    row.operator("su.scene_add", text="", icon='ADD')
    sub = row.row(align=True)
    sub.enabled = len(pg.pages) > 0
    sub.operator("su.scene_remove", text="", icon='REMOVE').index = -1
    sub.operator("su.scene_update", text="", icon='FILE_REFRESH').index = -1
    row.separator()
    row.operator("su.toggle_scene_tabs", text="", icon='MENU_PANEL', depress=pg.show_tabs)
    if not len(pg.pages):
        layout.label(text=i18n.t("cam.scenes_empty"))
        return
    col = layout.column(align=True)
    for i, page in enumerate(pg.pages):
        col.operator("su.scene_go", text=page.name, depress=(i == pg.active)).index = i
    if 0 <= pg.active < len(pg.pages):
        page = pg.pages[pg.active]
        box = layout.column()
        box.prop(page, "name", text=i18n.t("cam.scene_name"))
        box.prop(page, "description", text=i18n.t("cam.scene_description"))


def register():
    i18n.register_strings(STRINGS)
    tray = registry.optional("ui.tray")
    if tray is not None and hasattr(tray, "register_section"):
        tray.register_section(50, "scenes", "tray.scenes", draw, 'P1')


def unregister():
    tray = registry.optional("ui.tray")
    if tray is not None and hasattr(tray, "unregister_section"):
        tray.unregister_section("scenes")
