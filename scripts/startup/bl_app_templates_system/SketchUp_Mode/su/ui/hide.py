# SPDX-License-Identifier: GPL-2.0-or-later
"""Hide Blender UI the SketchUp shell does not show (owner: D). PLANO.md §4.4, §4.7.

* `hide_ui_panels()` — unregisters every Python panel of the 3D view's UI region whose category is not
  the tray's ("Bandeja"), children first (≈82 panels incl. add-ons such as glTF Variants); they are
  re-registered by `unregister()`. Run once the add-ons are registered (ui.startup step).
* `clean_screen(win)` — one workspace ("SketchUp"), only the largest 3D viewport (others closed).
  Mutating the layout is done one step per timer tick by ui.startup (the spike's area_close crash).
"""

import bpy

from .. import perf

ORDER = 510

TRAY_CATEGORY = "Bandeja"
WORKSPACE_NAME = "SketchUp"
_hidden = []


def _all_subclasses(c):
    for s in c.__subclasses__():
        yield s
        yield from _all_subclasses(s)


def hide_ui_panels():
    victims = [c for c in set(_all_subclasses(bpy.types.Panel))
               if getattr(c, "bl_space_type", "") == 'VIEW_3D' and getattr(c, "bl_region_type", "") == 'UI'
               and getattr(c, "bl_category", "") != TRAY_CATEGORY and getattr(c, "is_registered", False)]
    victims.sort(key=lambda c: 0 if getattr(c, "bl_parent_id", "") else 1)     # children first
    n = 0
    for c in victims:
        try:
            bpy.utils.unregister_class(c)
            _hidden.append(c)
            n += 1
        except Exception:
            pass
    return n


def restore_ui_panels():
    for c in reversed(_hidden):                                                 # parents first
        try:
            bpy.utils.register_class(c)
        except Exception:
            pass
    _hidden.clear()


def hidden_count():
    return len(_hidden)


def main_view3d_area(win):
    areas = [a for a in win.screen.areas if a.type == 'VIEW_3D']
    return max(areas, key=lambda a: a.width * a.height) if areas else None


def keep_one_workspace(win):
    keep = win.workspace
    others = [ws for ws in bpy.data.workspaces if ws != keep]
    if others:
        bpy.data.batch_remove(others)
    if keep.name != WORKSPACE_NAME:
        keep.name = WORKSPACE_NAME
    return keep


def close_other_areas(win):
    """Close every area except the largest 3D viewport. Returns the number closed."""
    scr = win.screen
    main = main_view3d_area(win)
    n = 0
    for a in [a for a in scr.areas if a != main]:
        try:
            with bpy.context.temp_override(window=win, screen=scr, area=a):
                bpy.ops.screen.area_close()
            n += 1
        except Exception:
            perf.exception("hide: area_close {:s}".format(a.type))
    return n


def configure_regions(area):
    sp = area.spaces.active
    sp.show_region_header = False
    sp.show_region_tool_header = True
    sp.show_region_toolbar = True
    sp.show_region_ui = True
    for a in ("show_region_hud", "show_region_asset_shelf"):
        try:
            setattr(sp, a, False)
        except Exception:
            pass


def register():
    pass


def unregister():
    restore_ui_panels()
