# SPDX-License-Identifier: GPL-2.0-or-later
""""Primeiros passos" toolbar (owner: D). PLANO.md §4.1, §4.2; ported from the spike.

Drawn in the 3D view's TOOL_HEADER (the HEADER hidden); while the model has scene tabs (G, P1) the
toolbar moves to the HEADER and the tabs go to the TOOL_HEADER — this module is the ONLY owner of both
header draws and of the HEADER visibility (`draw_header`, `draw_tool_header`, `sync_regions`).
Groups are separated by a LINE separator. A tool button = `wm.tool_set_by_id` (pressed look when
active). A group with a flyout shows its active member (or its head) plus a ▾ menu with the members.
COMMAND tools run `ToolMeta.operator`; disabled tools (P2) run the "Em breve" placeholder.
"""

import sys

import bpy

from .. import registry
from .. import icons
from . import toolset

ORDER = 530

# Commands of the toolbar until their owners declare a ToolMeta(kind='COMMAND').
COMMAND_FALLBACK = {
    "su.search": "",                       # P1 → placeholder
    "su.zoom_extents": "view3d.view_all",
}
_flyout_menus = []


def _active_tool_id(context):
    try:
        t = context.workspace.tools.from_space_view3d_mode('OBJECT', create=False)
        return t.idname if t else ""
    except Exception:
        return ""


def _kind_and_operator(tool_id):
    m = toolset.meta(tool_id)
    if m is not None:
        return m.kind, m.operator
    if tool_id in COMMAND_FALLBACK:
        return 'COMMAND', COMMAND_FALLBACK[tool_id]
    return 'TOOL', ''


def tool_button(layout, tool_id, active_id):
    """One toolbar button (also used by the flyout menus)."""
    enabled = toolset.is_enabled(tool_id)
    icon = icons.tool_icon(tool_id, dim=not enabled)
    kind, operator = _kind_and_operator(tool_id)
    if not enabled or (kind == 'COMMAND' and not operator):
        op = layout.operator("su.ui_placeholder", text="", icon_value=icon, emboss=False)
        op.name = toolset.label(tool_id)
        return
    if kind == 'COMMAND':
        try:
            layout.operator(operator, text="", icon_value=icon, emboss=False)
        except Exception:
            layout.operator("su.ui_placeholder", text="", icon_value=icon, emboss=False).name = toolset.label(tool_id)
        return
    on = tool_id == active_id
    layout.operator("wm.tool_set_by_id", text="", icon_value=icon, depress=on, emboss=on).name = tool_id


def _flyout_menu_class(head):
    key = head.replace(".", "_")

    def draw(self, context):
        lay = self.layout
        act = _active_tool_id(context)
        _lts, _gs, fly = toolset.layout_lists()
        for tid in fly.get(head, [head]):
            enabled = toolset.is_enabled(tid)
            row = lay.row()
            row.active = enabled
            kind, operator = _kind_and_operator(tid)
            icon = icons.tool_icon(tid, dim=not enabled)
            if not enabled:
                row.operator("su.ui_placeholder", text=toolset.label(tid), icon_value=icon).name = toolset.label(tid)
            else:
                row.operator("wm.tool_set_by_id", text=toolset.label(tid), icon_value=icon,
                             depress=(tid == act)).name = tid

    return type("SU_MT_flyout_" + key, (bpy.types.Menu,),
                {"bl_idname": "SU_MT_flyout_" + key, "bl_label": toolset.LABELS.get(head, head), "draw": draw})


def draw_toolbar(self, context):
    layout = self.layout
    act = _active_tool_id(context)
    _lts, groups, fly = toolset.layout_lists()
    row = layout.row(align=False)
    row.scale_x = 1.15
    row.scale_y = 1.1
    for gi, grp in enumerate(groups):
        if gi:
            row.separator(factor=0.6, type='LINE')
        for tid in grp:
            explicit = tid.endswith("*")
            tid = tid.rstrip("*")
            members = fly.get(tid)
            sub = row.row(align=True)
            shown = act if (members and act in members) else tid
            tool_button(sub, shown, act)
            if members or explicit:
                s2 = sub.row(align=True)
                s2.ui_units_x = 0.7
                s2.emboss = 'NONE'
                s2.menu("SU_MT_flyout_" + tid.replace(".", "_"), text="", icon='DOWNARROW_HLT')


# ------------------------------------------------------------------------------------------- header layout
# Single owner of VIEW3D_HT_header.draw / VIEW3D_HT_tool_header.draw (§4.1). The scene tabs (G, P1) plug
# in through `ui/scene_tabs.py`, which only provides `tabs_visible(context)` and `draw_tabs(layout, context)`:
#   no tabs  → HEADER hidden, toolbar in the TOOL_HEADER (right above the viewport)
#   tabs     → HEADER shown with the toolbar, scene tabs in the TOOL_HEADER (SketchUp's layout)
def _tabs_module():
    m = sys.modules.get(__package__ + ".scene_tabs")
    return m if m is not None and hasattr(m, "tabs_visible") and hasattr(m, "draw_tabs") else None


def tabs_visible(context=None):
    m = _tabs_module()
    try:
        return bool(m is not None and m.tabs_visible(context or bpy.context))
    except Exception:
        return False


def draw_header(self, context):
    if tabs_visible(context):
        draw_toolbar(self, context)


def draw_tool_header(self, context):
    m = _tabs_module()
    if m is not None and tabs_visible(context):
        m.draw_tabs(self.layout, context)
    else:
        draw_toolbar(self, context)


def sync_regions(area=None):
    """Show the 3D view's HEADER only while scene tabs are visible (called by ui.startup and G's ops)."""
    if bpy.app.background:
        return
    if area is None:
        wm = bpy.context.window_manager
        areas = [a for w in wm.windows for a in w.screen.areas if a.type == 'VIEW_3D'] if wm else []
        area = max(areas, key=lambda a: a.width * a.height) if areas else None
    if area is None:
        return
    sp = area.spaces.active
    want = tabs_visible()
    if sp.show_region_header != want:
        sp.show_region_header = want
    area.tag_redraw()


def register():
    _lts, _gs, fly = toolset.layout_lists()
    _flyout_menus[:] = [_flyout_menu_class(h) for h in fly]
    registry.register_classes(_flyout_menus)
    registry.override(bpy.types.VIEW3D_HT_tool_header, "draw", draw_tool_header)
    registry.override(bpy.types.VIEW3D_HT_header, "draw", draw_header)


def unregister():
    registry.unregister_classes(_flyout_menus)
    _flyout_menus.clear()
