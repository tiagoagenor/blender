# SPDX-License-Identifier: GPL-2.0-or-later
"""Backup/restore of the user's preferences that the mode changes (owner: A). PLANO.md §5.2, §9.2-A item 11.

An app template only swaps some preferences with its own userpref.blend (themes, keymaps/keyconfig,
add-ons, UI fonts/scale, gizmo/app flags, splash/navigate flags — BKE_blender_userdef_app_template_data_swap).
Everything else the mode changes (navigation inputs, region overlap, smooth view, studio light ambient,
status bar fields, mini axis) would leak into the user's normal Blender prefs when they are auto-saved.

So: register() (ORDER 10, before any owner touches prefs) stores the original values of KEYS — in memory
and in `<user config>/sketchup_mode_prefs_backup.json` —, and they are written back on unregister (template
switch) and on exit_pre (which runs BEFORE Blender's automatic prefs save on quit). If a backup file is
found at register time, a previous session ended without restoring (crash): its values are the originals.
Owners that change other preferences add them first with `track(section, attr)`.
"""

import json
import os

import bpy

from . import perf, registry

ORDER = 10

KEYS = [
    ("inputs", "use_zoom_to_mouse"), ("inputs", "use_mouse_depth_navigate"),
    ("inputs", "use_rotate_around_active"), ("inputs", "use_auto_perspective"),
    ("inputs", "view_rotate_method"), ("inputs", "view_zoom_method"), ("inputs", "invert_zoom_wheel"),
    ("inputs", "use_mouse_emulate_3_button"), ("inputs", "invert_mouse_zoom"),
    ("system", "use_region_overlap"), ("system", "light_ambient"),
    ("view", "smooth_view"), ("view", "mini_axis_type"),
    ("view", "show_statusbar_stats"), ("view", "show_statusbar_memory"), ("view", "show_statusbar_vram"),
    ("view", "show_statusbar_scene_duration"), ("view", "show_statusbar_version"),
    ("view", "show_statusbar_extensions_updates"),
]
FILE_NAME = "sketchup_mode_prefs_backup.json"

_orig = {}          # "section.attr" -> original value (JSON-able)


def path():
    return os.path.join(bpy.utils.user_resource('CONFIG'), FILE_NAME)


def _get(section, attr):
    v = getattr(getattr(bpy.context.preferences, section), attr)
    if hasattr(v, "__len__") and not isinstance(v, str):
        v = list(v)
    return v


def _set(section, attr, value):
    obj = getattr(bpy.context.preferences, section)
    try:
        if getattr(obj, attr) != value and not (isinstance(value, list) and list(getattr(obj, attr)) == value):
            setattr(obj, attr, value)
    except (AttributeError, TypeError, ValueError):
        pass            # read-only in this build (e.g. show_statusbar_vram) or removed


def _save_file():
    try:
        os.makedirs(os.path.dirname(path()), exist_ok=True)
        with open(path(), "w", encoding="utf-8") as f:
            json.dump(_orig, f, indent=1)
    except Exception:
        perf.exception("prefs: cannot write backup " + path())


def track(section, attr):
    """Back up one more preference (call BEFORE changing it). Returns False if it does not exist."""
    key = section + "." + attr
    if key in _orig:
        return True
    try:
        _orig[key] = _get(section, attr)
    except AttributeError:
        return False
    _save_file()
    return True


def backup():
    _orig.clear()
    stale = {}
    if os.path.isfile(path()):
        try:
            with open(path(), "r", encoding="utf-8") as f:
                stale = json.load(f)
        except Exception:
            perf.exception("prefs: cannot read stale backup " + path())
    for section, attr in KEYS:
        key = section + "." + attr
        if key in stale:
            _orig[key] = stale[key]
            continue
        try:
            _orig[key] = _get(section, attr)
        except AttributeError:
            pass
    for key, v in stale.items():
        _orig.setdefault(key, v)
    _save_file()


def restore():
    """Write the original values back and drop the backup file."""
    for key, value in _orig.items():
        section, attr = key.split(".", 1)
        _set(section, attr, value)
    _orig.clear()
    try:
        if os.path.isfile(path()):
            os.remove(path())
    except Exception:
        perf.exception("prefs: cannot remove backup " + path())


def originals():
    return dict(_orig)


def _on_exit_pre(*_args):
    restore()


def register():
    backup()
    registry.add_handler("exit_pre", _on_exit_pre)


def unregister():
    restore()
