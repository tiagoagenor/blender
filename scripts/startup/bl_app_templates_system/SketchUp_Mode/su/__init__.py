# SPDX-License-Identifier: GPL-2.0-or-later
"""SketchUp Mode package (owner: A) — auto-discovery and registration (PLANO.md §2.3-1).

`register()` imports every module under su/** (sub-packages recursively), sorts them by their
module-level `ORDER` (0–99 platform, 100–199 core, 200–299 draw, 300–399 tools, 400–499 ops,
500–599 ui; a module without ORDER gets its folder's default) and calls `register()` where defined.
An import or register error of one module = perf.error + that module is skipped (scn_smoke fails
when perf.errors() > 0). The only finalizer is `keymap.finalize()` (when su/keymap.py exists).
`draw/` is not imported in background mode (unit tests).

Readiness: after each load_post, session.on_load_post() emits "load" and later sets
bpy.app.driver_namespace["su_ready"] = True (deferred; owners with timer-driven setup delay it with
session.hold(name)/release(name)); the GUI harness waits for it.
"""

import importlib
import os
import pkgutil
import sys

import bpy

from . import perf

DEFAULT_ORDER = {"": 50, "core": 150, "draw": 250, "tools": 350, "ops": 450, "ui": 550}
SKIP_IN_BACKGROUND = frozenset({"draw"})
READY_KEY = "su_ready"
READY_DELAY_S = 0.5

_active = []          # registered modules, in registration order
_loaded = []          # every imported module (relative names), in ORDER
_failed = []          # names of modules skipped because of an error
_registered = [False]


def _module_names():
    """Dotted names (relative to this package) of every module under su/**, depth-first, sorted."""
    names = []

    def walk(path, prefix):
        for info in sorted(pkgutil.iter_modules([path]), key=lambda i: i.name):
            if info.name.startswith("_"):
                continue
            rel = prefix + info.name
            if info.ispkg:
                if bpy.app.background and rel.split(".")[0] in SKIP_IN_BACKGROUND:
                    continue
                walk(os.path.join(path, info.name), rel + ".")
            else:
                names.append(rel)

    walk(__path__[0], "")
    return names


def _order_of(rel, mod):
    order = getattr(mod, "ORDER", None)
    if isinstance(order, (int, float)):
        return order
    top = rel.split(".")[0] if "." in rel else ""
    return DEFAULT_ORDER.get(top, 600)


def discover():
    """Import all modules; return [(order, rel_name, module)] sorted. Import errors are recorded."""
    found = []
    for rel in _module_names():
        name = __name__ + "." + rel
        try:
            mod = importlib.import_module(name)
        except Exception:
            perf.exception("import {:s} failed — module skipped".format(name))
            _failed.append(rel)
            continue
        found.append((_order_of(rel, mod), rel, mod))
    found.sort(key=lambda f: (f[0], f[1]))
    return found


def _on_load_post(*_args):
    bpy.app.driver_namespace[READY_KEY] = False
    session = sys.modules.get(__name__ + ".session")
    if session is not None and hasattr(session, "on_load_post"):
        session.on_load_post()          # emits "load" and sets su_ready itself (session.hold/release)
        return
    else:
        from . import events
        events.emit("load")
    if not bpy.app.background:
        from . import registry
        registry.deferred(_mark_ready, READY_DELAY_S)


def _mark_ready():
    bpy.app.driver_namespace[READY_KEY] = True


def register():
    if _registered[0]:
        return
    _registered[0] = True
    _failed.clear()
    _loaded.clear()
    for _order, rel, mod in discover():
        _loaded.append(rel)
        fn = getattr(mod, "register", None)
        if fn is None:
            continue
        try:
            fn()
        except Exception:
            perf.exception("register {:s}.{:s} failed — module skipped".format(__name__, rel))
            _failed.append(rel)
            continue
        _active.append(mod)
    keymap = sys.modules.get(__name__ + ".keymap")
    if keymap is not None and hasattr(keymap, "finalize"):
        try:
            keymap.finalize()
        except Exception:
            perf.exception("keymap.finalize failed")
    from . import registry
    registry.add_handler("load_post", _on_load_post)


def unregister():
    if not _registered[0]:
        return
    from . import events, registry
    registry.cancel_deferred()
    registry.remove_all_handlers()
    while _active:
        mod = _active.pop()
        fn = getattr(mod, "unregister", None)
        if fn is None:
            continue
        try:
            fn()
        except Exception:
            perf.exception("unregister {:s} failed".format(mod.__name__))
    registry.restore_all()
    events.clear()
    bpy.app.driver_namespace.pop(READY_KEY, None)
    _loaded.clear()
    _registered[0] = False


def is_registered():
    return _registered[0]


def failed_modules():
    return list(_failed)


def loaded_modules():
    return list(_loaded)


def active_modules():
    return [m.__name__[len(__name__) + 1:] for m in _active]
