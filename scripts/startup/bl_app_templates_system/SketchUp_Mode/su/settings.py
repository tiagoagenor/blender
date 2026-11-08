# SPDX-License-Identifier: GPL-2.0-or-later
"""Persistent user settings of the mode (owner: A). Contract: PLANO.md §2.4.

Minimal JSON file in Blender's user CONFIG folder (`sketchup_mode.json`; inside the isolated stage in
development). Keys and defaults below; unknown keys raise KeyError so typos surface early.
"""

import json
import os

import bpy

from . import perf

ORDER = 6

DEFAULTS = {
    "language": "pt_BR",
    "trackpad_mode": "sketchup",       # 'sketchup' | 'blender'
    "trackpad_invert_zoom": False,
    "click_style": "auto",             # 'auto' | 'click_move_click' | 'drag'
    "continue_line": True,
}
FILE_NAME = "sketchup_mode.json"

_values = dict(DEFAULTS)


def path():
    return os.path.join(bpy.utils.user_resource('CONFIG'), FILE_NAME)


def load():
    _values.clear()
    _values.update(DEFAULTS)
    p = path()
    if not os.path.isfile(p):
        return
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in data.items():
            if k in DEFAULTS:
                _values[k] = v
    except Exception:
        perf.exception("settings: cannot read " + p)


def save():
    p = path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(_values, f, indent=1, ensure_ascii=False)
    except Exception:
        perf.exception("settings: cannot write " + p)


def get(key):
    if key not in DEFAULTS:
        raise KeyError("unknown setting {!r}".format(key))
    return _values[key]


def set(key, value):
    if key not in DEFAULTS:
        raise KeyError("unknown setting {!r}".format(key))
    _values[key] = value
    save()


def register():
    load()
