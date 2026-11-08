# SPDX-License-Identifier: GPL-2.0-or-later
"""Class registration, monkey-patch overrides, app handlers and deferred calls (owner: A).

Everything registered through here is undone by `su.unregister()` (restore_all, remove_all_handlers,
cancel_deferred), so switching templates leaves Blender as it was.
"""

import bpy
from bpy.app.handlers import persistent

from . import perf

ORDER = 3

_overrides = []     # [(owner, attr, original, had_attr)] in application order
_handlers = []      # [(list_name, wrapped_fn)]
_timers = []        # registered timer callables


def register_classes(classes):
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_classes(classes):
    for cls in reversed(list(classes)):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            perf.exception("unregister_class {!r}".format(cls))


def override(owner, attr, new):
    """Replace `owner.attr` by `new`, remembering the original (first override wins the original)."""
    had = attr in vars(owner) if isinstance(owner, type) else hasattr(owner, attr)
    original = vars(owner).get(attr) if isinstance(owner, type) else getattr(owner, attr, None)
    _overrides.append((owner, attr, original, had))
    setattr(owner, attr, new)


def restore_all():
    while _overrides:
        owner, attr, original, had = _overrides.pop()
        try:
            if had:
                setattr(owner, attr, original)
            else:
                delattr(owner, attr)
        except Exception:
            perf.exception("restore {!r}.{:s}".format(owner, attr))


def add_handler(list_name, fn):
    """Append `fn` to `bpy.app.handlers.<list_name>` (persistent; exceptions go to perf.error)."""
    @persistent
    def wrapped(*args):
        try:
            fn(*args)
        except Exception:
            perf.exception("handler {:s} {:s}".format(list_name, getattr(fn, "__qualname__", repr(fn))))
    wrapped.su_target = fn
    getattr(bpy.app.handlers, list_name).append(wrapped)
    _handlers.append((list_name, wrapped))
    return wrapped


def remove_all_handlers():
    while _handlers:
        list_name, wrapped = _handlers.pop()
        lst = getattr(bpy.app.handlers, list_name)
        if wrapped in lst:
            lst.remove(wrapped)


def deferred(fn, delay=0.0):
    """Run `fn()` once on a timer after `delay` seconds (exceptions go to perf.error)."""
    def tick():
        if tick in _timers:
            _timers.remove(tick)
        try:
            fn()
        except Exception:
            perf.exception("deferred {:s}".format(getattr(fn, "__qualname__", repr(fn))))
        return None
    _timers.append(tick)
    bpy.app.timers.register(tick, first_interval=max(0.0, float(delay)))
    return tick


def cancel_deferred():
    while _timers:
        tick = _timers.pop()
        if bpy.app.timers.is_registered(tick):
            bpy.app.timers.unregister(tick)
