# SPDX-License-Identifier: GPL-2.0-or-later
"""Scene tabs above the viewport (owner: G, P1). PLANO.md §4.1.

While the model has scenes (and Visualizar ▸ Abas de cena is on), the 3D view's HEADER is shown and the
"Primeiros passos" toolbar (D's `header_toolbar.draw_toolbar`) moves there; the TOOL_HEADER, right
above the viewport, shows one tab per scene (SketchUp's layout). Without scenes: as D set it up
(HEADER hidden, toolbar in the TOOL_HEADER).
"""

import bpy

from .. import events, perf, registry

ORDER = 580


def tabs_visible(context=None):
    scene = getattr(context or bpy.context, "scene", None)
    pg = getattr(scene, "su_pages", None)
    return bool(pg is not None and pg.show_tabs and len(pg.pages) > 0)


def _toolbar(self, context):
    ht = registry.optional("ui.header_toolbar")
    if ht is not None:
        ht.draw_toolbar(self, context)


def draw_tabs(layout, context):
    pg = context.scene.su_pages
    row = layout.row(align=True)
    row.alignment = 'LEFT'
    for i, page in enumerate(pg.pages):
        row.operator("su.scene_go", text=page.name, depress=(i == pg.active)).index = i


def draw_header(self, context):
    if tabs_visible(context):
        _toolbar(self, context)


def draw_tool_header(self, context):
    if tabs_visible(context):
        draw_tabs(self.layout, context)
    else:
        _toolbar(self, context)


def sync():
    """Show/hide the HEADER of the main 3D view to match tabs_visible()."""
    if bpy.app.background:
        return
    try:
        from ..tools import base
        _win, area, _r, _rv = base.find_view3d()
        if area is None:
            return
        sp = area.spaces.active
        want = tabs_visible()
        if sp.show_region_header != want:
            sp.show_region_header = want
        area.tag_redraw()
    except Exception:
        perf.exception("scene_tabs: sync")


def _later(**_kw):
    if not bpy.app.background:
        registry.deferred(sync, 0.6)        # after D's start-up steps (they hide the HEADER)


def register():
    registry.override(bpy.types.VIEW3D_HT_header, "draw", draw_header)
    registry.override(bpy.types.VIEW3D_HT_tool_header, "draw", draw_tool_header)
    events.subscribe("load", _later, order=950)
    events.subscribe("undo", _later)


def unregister():
    events.unsubscribe("load", _later)
    events.unsubscribe("undo", _later)
