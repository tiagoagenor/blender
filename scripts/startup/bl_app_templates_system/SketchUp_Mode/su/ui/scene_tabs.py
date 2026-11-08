# SPDX-License-Identifier: GPL-2.0-or-later
"""Scene tabs above the viewport (owner: G, P1). PLANO.md §4.1.

While the model has scenes (and Visualizar ▸ Abas de cena is on), the 3D view's HEADER is shown and the
"Primeiros passos" toolbar moves there; the TOOL_HEADER, right above the viewport, shows one tab per
scene (SketchUp's layout). Without scenes: HEADER hidden, toolbar in the TOOL_HEADER.

The header draws and the HEADER visibility belong to D's `ui/header_toolbar.py` (single owner of both
overrides, fixed at integration 44b13e0 by D): this module only provides the hook
`tabs_visible(context)` + `draw_tabs(layout, context)` and asks D to re-sync the regions.
"""

import bpy

from .. import events, perf, registry

ORDER = 580


def tabs_visible(context=None):
    scene = getattr(context or bpy.context, "scene", None)
    pg = getattr(scene, "su_pages", None)
    return bool(pg is not None and pg.show_tabs and len(pg.pages) > 0)


def draw_tabs(layout, context):
    pg = context.scene.su_pages
    row = layout.row(align=True)
    row.alignment = 'LEFT'
    for i, page in enumerate(pg.pages):
        row.operator("su.scene_go", text=page.name, depress=(i == pg.active)).index = i


def sync():
    """Show/hide the HEADER of the main 3D view to match tabs_visible() (D's header_toolbar decides)."""
    if bpy.app.background:
        return
    try:
        ht = registry.optional("ui.header_toolbar")
        if ht is not None:
            ht.sync_regions()
    except Exception:
        perf.exception("scene_tabs: sync")


def _later(**_kw):
    if not bpy.app.background:
        registry.deferred(sync, 0.6)        # after D's start-up steps


def register():
    events.subscribe("load", _later, order=950)
    events.subscribe("undo", _later)


def unregister():
    events.unsubscribe("load", _later)
    events.unsubscribe("undo", _later)
