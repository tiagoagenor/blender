# SPDX-License-Identifier: GPL-2.0-or-later
"""Group edit context (owner: B). Contract: PLANO.md §2.4-B. Minimal v1: a stack of object names.

The root "Modelo" is the implicit bottom of the stack (never on it). `enter(obj)` opens a group
(its parent chain must be the current context), `exit()` closes the innermost one.
"""

import bpy

from .. import events

ORDER = 121

_STACK = []        # object names, outermost first


def stack():
    return [o for o in (bpy.data.objects.get(n) for n in _STACK) if o is not None]


def current_object():
    objs = stack()
    return objs[-1] if objs else None


def enter(obj):
    if obj is None:
        return
    _STACK.append(obj.name)
    events.emit("selection")


def exit():
    if _STACK:
        _STACK.pop()
        events.emit("selection")


def exit_all():
    if _STACK:
        _STACK.clear()
        events.emit("selection")


def is_in_context(obj):
    """True when obj is directly editable in the current context (a child of the open group, or a
    top-level object when no group is open)."""
    cur = current_object()
    return obj is not None and obj.parent == cur


def top_level_pick(obj):
    """The object a click on `obj` selects in the current context: the ancestor of obj whose parent
    is the open group (or None when obj is not inside the current context)."""
    cur = current_object()
    o = obj
    while o is not None and o.parent != cur:
        o = o.parent
    return o


def _on_load(**_kw):
    _STACK.clear()


def register():
    events.subscribe("load", _on_load, order=90)


def unregister():
    _STACK.clear()
    events.unsubscribe("load", _on_load)
