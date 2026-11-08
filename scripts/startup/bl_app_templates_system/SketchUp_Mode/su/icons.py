# SPDX-License-Identifier: GPL-2.0-or-later
"""Tool and UI icons (owner: D). PLANO.md §4.6.

Icon handles are strings, the same ones stored in `ToolDef.icon`:
  "bi.NAME"          Blender built-in SVG icon (drawn in the theme's wcol_*.text colour, navy)
  "ops.x.y" etc.     Blender toolbar geometry icon, RECOLOURED copy `icons/su.<handle>.dat`
                     (tools/sketchup_mode/build_icons.py: navy/cyan/red, pre-inverted for light themes)
  "draw.NAME"        ORIGINAL vector icon `icons/su.draw.NAME.dat` (tools/sketchup_mode/build_icons_draw.py)
  "png.NAME"         PNG image `icons/png/NAME.png` (bpy.utils.previews; drawn at 16 px, so only for
                     thumbnails such as the tray's style preview)
A "_dim" suffix (e.g. "ops.mesh.bisect_dim") gives the 40 % variant used by disabled buttons.

`ToolSelectPanelHelper._icon_value_from_icon_handle` is patched (registry.override) so the toolbar,
the Large Tool Set and `tool_icon()` all resolve handles the same way.
"""

import os

import bpy

from . import perf, registry

ORDER = 70

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")
PNG_DIR = os.path.join(ICON_DIR, "png")
DIM_SUFFIX = "_dim"

# tool id -> icon handle: all "draw." = original drawings (tools/sketchup_mode/build_icons_draw.py, §9.2-D 9.1).
# (The recoloured Blender .dat pipeline of the spike stays in build_icons.py for any "ops.*" handle.)
TOOL_ICONS = {
    "su.search": "draw.search",
    "su.select": "draw.select",
    "su.lasso": "draw.lasso",
    "su.paint": "draw.paint",
    "su.eraser": "draw.eraser",
    "su.make_component": "draw.make_component",
    "su.make_group": "draw.make_component",
    "su.line": "draw.line",
    "su.freehand": "draw.freehand",
    "su.rectangle": "draw.rectangle",
    "su.rotated_rectangle": "draw.rotated_rectangle",
    "su.circle": "draw.circle",
    "su.polygon": "draw.polygon",
    "su.arc": "draw.arc",
    "su.arc2": "draw.arc2",
    "su.arc3": "draw.arc3",
    "su.pie": "draw.pie",
    "su.move": "draw.move",
    "su.pushpull": "draw.pushpull",
    "su.rotate": "draw.rotate",
    "su.followme": "draw.followme",
    "su.scale": "draw.scale",
    "su.offset": "draw.offset",
    "su.axes": "draw.axes",
    "su.flip": "draw.flip",
    "su.tape": "draw.tape",
    "su.dimension": "draw.dimension",
    "su.protractor": "draw.protractor",
    "su.text": "draw.text",
    "su.section": "draw.section",
    "su.text3d": "draw.text3d",
    "su.orbit": "draw.orbit",
    "su.pan": "draw.pan",
    "su.zoom": "draw.zoom",
    "su.zoom_window": "draw.zoom_window",
    "su.zoom_extents": "draw.zoom_extents",
    "su.previous": "draw.previous",
    "su.position_camera": "draw.position_camera",
    "su.walk": "draw.walk",
    "su.look_around": "draw.look_around",
    "su.fov": "draw.fov",
}
# UI icons that are not tools (status bar, tray title)
UI_ICONS = {
    "pin": "draw.ui_pin",
    "info": "draw.ui_info",
    "close": "bi.X",
}

_builtin = {}
_cache = {}           # handle -> icon value
_previews = [None]
_orig_resolver = [None]


def builtin_icon_value(name):
    if not _builtin:
        for it in bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items:
            _builtin[it.identifier] = it.value
    return _builtin.get(name, _builtin.get("QUESTION", 0))


def _png_collection():
    if _previews[0] is None:
        import bpy.utils.previews
        _previews[0] = bpy.utils.previews.new()
    return _previews[0]


def png_path(name):
    return os.path.join(PNG_DIR, name + ".png")


def dat_path(handle):
    """Absolute path WITHOUT extension of the recoloured .dat of `handle` (may not exist)."""
    return os.path.join(ICON_DIR, "su." + handle)


def resolve(handle):
    """Icon handle → icon value (0 when nothing can be found)."""
    if not handle:
        return 0
    v = _cache.get(handle)
    if v is not None:
        return v
    base, dim = (handle[:-len(DIM_SUFFIX)], True) if handle.endswith(DIM_SUFFIX) else (handle, False)
    v = 0
    try:
        if base.startswith("bi."):
            v = builtin_icon_value(base[3:])             # built-ins have no dim variant (layout.active dims)
        elif base.startswith("png."):
            name = base[4:] + (DIM_SUFFIX if dim else "")
            path = png_path(name)
            if os.path.isfile(path):
                pc = _png_collection()
                if name not in pc:
                    pc.load(name, path, 'IMAGE')
                v = pc[name].icon_id
        elif os.path.isabs(base):
            v = _orig_resolver[0](base) if _orig_resolver[0] else 0
        else:
            alt = dat_path(handle)
            if not os.path.isfile(alt + ".dat"):
                alt = dat_path(base)
            if os.path.isfile(alt + ".dat"):
                v = bpy.app.icons.new_triangles_from_file(alt + ".dat")
            elif _orig_resolver[0]:
                v = _orig_resolver[0](base)              # Blender's own (not recoloured) icon
    except Exception:
        perf.exception("icons: resolve {!r}".format(handle))
        v = 0
    _cache[handle] = v
    return v


def tool_handle(tool_id, dim=False):
    h = TOOL_ICONS.get(tool_id, "bi.QUESTION")
    return h + DIM_SUFFIX if dim else h


def tool_icon(tool_id, dim=False):
    """Icon value of a tool (for `icon_value=` in layouts)."""
    return resolve(tool_handle(tool_id, dim))


def ui_icon(name):
    return resolve(UI_ICONS.get(name, "bi.QUESTION"))


def _resolver(icon_name):
    if icon_name is None:
        return 0
    return resolve(icon_name)


def register():
    from bl_ui.space_toolsystem_common import ToolSelectPanelHelper as TSP
    _orig_resolver[0] = TSP._icon_value_from_icon_handle
    registry.override(TSP, "_icon_value_from_icon_handle", staticmethod(_resolver))


def unregister():
    _cache.clear()
    if _previews[0] is not None:
        import bpy.utils.previews
        bpy.utils.previews.remove(_previews[0])
        _previews[0] = None
