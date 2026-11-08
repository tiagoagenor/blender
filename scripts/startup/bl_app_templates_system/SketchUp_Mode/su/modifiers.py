# SPDX-License-Identifier: GPL-2.0-or-later
"""Modifier keys, Mac convention (owner: A). Contract: PLANO.md §2.4, §5.3.

Option (event.alt) = copy / add / new face / soften / adjacent / toggle guide / from centre.
Cmd (event.oskey) = eyedropper / fold face / overlap / perimeter / cycle inferences.
Ctrl is never a tool modifier on the Mac (Ctrl+click = context menu, Ctrl+Cmd+drag = orbit).
Texts always name the Mac key: label("copy") -> "Option" (never "Ctrl").
"""

ORDER = 7

_LABELS = {
    "copy": "Option", "option": "Option", "alt": "Option",
    "alt_action": "Cmd", "cmd": "Cmd", "command": "Cmd", "oskey": "Cmd",
    "shift": "Shift", "ctrl": "Control", "control": "Control",
}


def is_copy(ev):
    """Option pressed. Accepts a bpy event (`alt`) or a tools.base.Ev (`copy`)."""
    if hasattr(ev, "alt"):
        return bool(ev.alt)
    return bool(getattr(ev, "copy", False))


def is_alt_action(ev):
    """Cmd pressed. Accepts a bpy event (`oskey`) or a tools.base.Ev (`alt_action`)."""
    if hasattr(ev, "oskey"):
        return bool(ev.oskey)
    return bool(getattr(ev, "alt_action", False))


def label(name):
    """Display name of a modifier role or key: label("copy") -> "Option", label("alt_action") -> "Cmd"."""
    return _LABELS.get(name.lower(), name)
