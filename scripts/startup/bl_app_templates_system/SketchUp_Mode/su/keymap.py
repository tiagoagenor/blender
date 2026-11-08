# SPDX-License-Identifier: GPL-2.0-or-later
"""Keymap of the mode (owner: A). PLANO.md §3.5, §5.1, §5.3. The package's only finalizer.

1. Keyconfig "SketchUp_Mode" = blender_default (left select, Mac Cmd mapping) filtered by an ALLOW LIST in
   the keymaps the mode's UI can reach (Window, Screen, Frames, User Interface, 3D View*, Object*): only
   navigation, undo/redo, file, quit and full screen survive there, so no Blender shortcut or popup
   fires over the viewport/tray/toolbar. Modal keymaps, gizmos, View2D (tray scrolling), Screen Editing
   (region resize) and other editors (file browser) stay intact. Activated on a timer (after Blender's
   own keyconfig_init); the previously active keyconfig is restored on unregister.
2. Items of the modules' `KEYMAP_VIEW3D` lists (G: MMB orbit/pan/recenter, wheel, trackpad) go to the add-on
   "3D View" keymap; when there are any, Blender's view3d.rotate/move/zoom/dolly/view_center_pick are dropped
   from the filtered keyconfig, so only the mode's navigation fires.
3. Items in the add-on keyconfig's `Window` keymap, in this order:
   TEXTINPUT, RET, NUMPAD_ENTER, BACK_SPACE, ESC → su.vcb_key (PASS_THROUGH when not for it) →
   tool shortcuts (ToolMeta.shortcut → su.tool_activate) → `KEYMAP` lists of the registered modules
   (e.g. F: Delete/⌫ → Excluir, Esc → sair do grupo). A module KEYMAP is a list of
   (idname, {"type":..., "value":..., "shift":...}, {"properties": [(name, value), ...]} | None).
Every item's operator polls "main window + area VIEW_3D/STATUSBAR/TOPBAR + mode".
"""

import os
import sys

import bpy

from . import perf, registry

ORDER = 8

KC_NAME = "SketchUp_Mode"

VCB_ITEMS = (
    ("su.vcb_key", {"type": 'TEXTINPUT', "value": 'PRESS', "any": True}, None),
    ("su.vcb_key", {"type": 'RET', "value": 'PRESS'}, None),
    ("su.vcb_key", {"type": 'NUMPAD_ENTER', "value": 'PRESS'}, None),
    ("su.vcb_key", {"type": 'BACK_SPACE', "value": 'PRESS'}, None),
    ("su.vcb_key", {"type": 'ESC', "value": 'PRESS'}, None),
)

# Window shortcuts of commands that are not tools (PLANO §5.3), added only when the operator exists.
EXTRA_ITEMS = (
    ("su.style_toggle", {"type": 'K', "value": 'PRESS'}, {"properties": [("prop", "show_back_edges")]}),  # Arestas traseiras
    # Mac mouse (PLANO §5.2): Ctrl+click / idle right click = context menu (F's menu, via A's su.context_menu).
    # (Ctrl+Cmd drag orbit/pan come from G's ops/view_ops.KEYMAP.)
    ("su.context_menu", {"type": 'LEFTMOUSE', "value": 'CLICK', "ctrl": True}, None),
    ("su.context_menu", {"type": 'RIGHTMOUSE', "value": 'PRESS'}, None),
)

# Blender navigation operators replaced by the modules' KEYMAP_VIEW3D items (G's su.view_*): when such
# items exist they are dropped from the filtered keyconfig, so only the mode's navigation fires.
BLENDER_NAV = frozenset({"view3d.rotate", "view3d.move", "view3d.zoom", "view3d.dolly", "view3d.view_center_pick"})
VIEW3D_KEYMAP = ("3D View", 'VIEW_3D', 'WINDOW')


def _op_exists(idname):
    mod, _, name = idname.partition(".")
    try:
        getattr(getattr(bpy.ops, mod), name).get_rna_type()
        return True
    except (AttributeError, KeyError):
        return False


# Keymaps whose non-modal items are filtered by ALLOW (everything else is kept as in blender_default).
FILTERED = frozenset({
    "Window", "Screen", "Frames", "User Interface", "3D View Generic", "3D View", "Object Mode",
    "Object Non-modal", "Screen Region Context Menu", "Region Context Menu", "Header", "Property Editor",
})
ALLOW = frozenset({
    # navigation
    "view3d.rotate", "view3d.move", "view3d.zoom", "view3d.dolly", "view3d.view_center_pick",
    "view3d.ndof_orbit", "view3d.ndof_orbit_zoom", "view3d.ndof_pan", "view3d.ndof_all",
    # undo / redo
    "ed.undo", "ed.redo",
    # file / app
    "wm.open_mainfile", "wm.save_mainfile", "wm.save_as_mainfile", "wm.read_homefile", "wm.quit_blender",
    "wm.window_fullscreen_toggle",
})
ALLOW_PREFIXES = ("view2d.",)

_added = []                 # (keymap, keymap_item) in the add-on keyconfig
_kc_state = {"previous": None, "active": False}


# ---------------------------------------------------------------------------------------------- filtered keyconfig

def _allowed(idname, blocked=frozenset()):
    return idname not in blocked and (idname in ALLOW or idname.startswith(ALLOW_PREFIXES))


def view3d_items():
    """Items of the modules' KEYMAP_VIEW3D lists whose operators exist, in module order."""
    pkg = sys.modules[__package__]
    out = []
    for mod in getattr(pkg, "_active", []):
        for it in getattr(mod, "KEYMAP_VIEW3D", ()) or ():
            if _op_exists(it[0]):
                out.append(it)
    return out


def keyconfig_data():
    """blender_default data (left select, macOS Cmd mapping) with the allow list applied."""
    preset = bpy.utils.preset_find("Blender", "keyconfig")
    blender_default = bpy.utils.execfile(os.path.join(os.path.dirname(preset), "keymap_data", "blender_default.py"))
    params = blender_default.Params(select_mouse='LEFT', spacebar_action='PLAY', use_fallback_tool=True,
                                    use_alt_navigation=False)
    data = blender_default.generate_keymaps(params)
    if sys.platform == "darwin":
        from bl_keymap_utils.platform_helpers import keyconfig_data_oskey_from_ctrl_for_macos
        data = keyconfig_data_oskey_from_ctrl_for_macos(data)
    blocked = BLENDER_NAV if view3d_items() else frozenset()
    out = []
    for km_name, km_args, km_content in data:
        if km_name in FILTERED and not km_args.get("modal", False):
            items = [it for it in km_content["items"] if _allowed(it[0], blocked)]
            km_content = dict(km_content, items=items)
        out.append((km_name, km_args, km_content))
    return out


def activate_keyconfig():
    """Create (once) and activate the filtered keyconfig; remembers the previous active one."""
    wm = bpy.context.window_manager
    kcs = wm.keyconfigs
    if kcs.active is not None and kcs.active.name == KC_NAME:
        return
    from bl_keymap_utils.io import keyconfig_init_from_data
    kc = kcs.get(KC_NAME)
    if kc is None:
        kc = kcs.new(KC_NAME)
        keyconfig_init_from_data(kc, keyconfig_data())
    if _kc_state["previous"] is None and kcs.active is not None:
        _kc_state["previous"] = kcs.active.name
    kcs.active = kc
    _kc_state["active"] = True


def deactivate_keyconfig():
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None or not _kc_state["active"]:
        return
    kcs = wm.keyconfigs
    prev = kcs.get(_kc_state["previous"] or "Blender") or kcs.default
    if kcs.active is not None and kcs.active.name == KC_NAME and prev is not None:
        kcs.active = prev
    kc = kcs.get(KC_NAME)
    if kc is not None:
        kcs.remove(kc)
    _kc_state.update(previous=None, active=False)


# ---------------------------------------------------------------------------------------------- Window items

def window_items():
    """The ordered Window keymap item list (data form), as finalize() adds it."""
    from .tools import base
    items = list(VCB_ITEMS)
    for tid in sorted(base.TOOLS):
        meta = base.TOOLS[tid].meta
        if not meta.shortcut:
            continue
        key, mods = base.parse_shortcut(meta.shortcut)
        args = {"type": key, "value": 'PRESS'}
        for m in mods:
            args[m] = True
        items.append(("su.tool_activate", args, {"properties": [("tool_id", tid)]}))
    for idname, args, data in EXTRA_ITEMS:
        if _op_exists(idname):
            items.append((idname, args, data))
    pkg = sys.modules[__package__]
    for mod in getattr(pkg, "_active", []):
        for it in getattr(mod, "KEYMAP", ()) or ():
            items.append(it)
    return items


def finalize():
    """Called once by su.register() after every module registered."""
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon if wm is not None else None
    if kc is None:
        return                       # background without key configurations
    km = kc.keymaps.new("Window", space_type='EMPTY', region_type='WINDOW')
    for idname, args, data in window_items():
        try:
            kmi = km.keymap_items.new(idname, **args)
        except Exception:
            perf.exception("keymap item {!r} {!r}".format(idname, args))
            continue
        for name, value in (data or {}).get("properties", ()):
            setattr(kmi.properties, name, value)
        _added.append((km, kmi))
    name, space, region = VIEW3D_KEYMAP
    km3 = kc.keymaps.new(name, space_type=space, region_type=region)
    for idname, args, data in view3d_items():
        try:
            kmi = km3.keymap_items.new(idname, **args)
        except Exception:
            perf.exception("3D View keymap item {!r} {!r}".format(idname, args))
            continue
        for pname, value in (data or {}).get("properties", ()):
            setattr(kmi.properties, pname, value)
        _added.append((km3, kmi))
    if not bpy.app.background:
        registry.deferred(activate_keyconfig, 0.0)


def register():
    pass                             # items are added by finalize(); register() only puts us in su._active


def unregister():
    for km, kmi in reversed(_added):
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _added.clear()
    try:
        deactivate_keyconfig()
    except Exception:
        perf.exception("keymap: restore keyconfig")
