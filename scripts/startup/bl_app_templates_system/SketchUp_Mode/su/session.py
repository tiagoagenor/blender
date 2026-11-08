# SPDX-License-Identifier: GPL-2.0-or-later
"""File load and data-change handling by events (owner: A). Contract: PLANO.md §2.4, §3.10.

on_load_post (from su/__init__'s load_post handler):
  events.emit("load")  → subscribers by owner (B: root "Modelo"; F: material slots 0/1; D: GN + style;
                         G: FOV/clip; ...). Synchronous changes made here end up in the file's initial
                         undo step ("Original": Blender builds the undo stack AFTER load_post), so
                         "open → Cmd+Z → Modelo exists" holds by construction.
  active object = None (invariant: the mode never has an active object), then on a timer:
  tool Selecionar (when registered), and ONE undo.push("undo.init") only if data changed after
  load_post (e.g. by timer-driven setup).
Readiness: driver_namespace["su_ready"] becomes True after the post-load step, once no `hold()` is
pending and, when D's ui/startup.py is loaded, after its driver_namespace["su_ui_ready"] (timer-driven
layout/theme/start view). Other owners may delay it with hold(name)/release(name). The GUI harness
waits for su_ready.
on_depsgraph_update: documents changed by something other than our own writes (and not during a
tool operation, which may preview-write) are invalidated (document.get(obj).invalidate()).
"""

import bpy

from . import events, perf, registry

ORDER = 9

READY_KEY = "su_ready"
READY_DELAY_S = 0.5
DEFAULT_TOOL = "su.select"

_holds = set()
_loaded = [False]
_fp = [None]
_own = set()             # doc keys written by us since the last depsgraph update


def _ns():
    return bpy.app.driver_namespace


def hold(name):
    """Delay readiness until release(name)."""
    _holds.add(name)
    _ns()[READY_KEY] = False


def release(name):
    _holds.discard(name)
    _maybe_ready()


def is_ready():
    return bool(_ns().get(READY_KEY))


UI_READY_KEY = "su_ui_ready"      # D's ui/startup.py step chain (theme, layout, start view)
UI_READY_TIMEOUT_S = 30.0
_ui_wait = {"t": 0.0}


def _ui_pending():
    import sys
    startup = sys.modules.get(__package__ + ".ui.startup")
    return startup is not None and not bpy.app.background and not _ns().get(UI_READY_KEY)


def _maybe_ready():
    if not _loaded[0] or _holds:
        return
    if _ui_pending():
        if _ui_wait["t"] < UI_READY_TIMEOUT_S:
            _ui_wait["t"] += 0.2
            registry.deferred(_maybe_ready, 0.2)
        else:
            perf.error("session: su_ui_ready not set after {:.0f}s".format(UI_READY_TIMEOUT_S))
            _ns()[READY_KEY] = True
        return
    _ns()[READY_KEY] = True


def fingerprint():
    d = bpy.data
    return (len(d.objects), len(d.meshes), len(d.materials), len(d.node_groups), len(d.collections),
            sum(len(o.modifiers) for o in d.objects), sum(len(o.material_slots) for o in d.objects))


def clear_active_object():
    for scene in bpy.data.scenes:
        for vl in scene.view_layers:
            if vl.objects.active is not None:
                vl.objects.active = None


def on_load_post():
    _ns()[READY_KEY] = False
    _loaded[0] = False
    _ui_wait["t"] = 0.0
    _own.clear()
    events.emit("load")
    clear_active_object()
    _fp[0] = fingerprint()
    if bpy.app.background:
        _loaded[0] = True
        _maybe_ready()
        return
    registry.deferred(_after_load, 0.0)


def _after_load():
    from .tools import base
    if DEFAULT_TOOL in base.TOOLS:
        base.set_workspace_tool(DEFAULT_TOOL)
    else:
        base.DISPATCH.sync(base.tool_context())
    clear_active_object()
    if fingerprint() != _fp[0]:
        from .core import undo
        undo.push("undo.init")
    _loaded[0] = True
    registry.deferred(_maybe_ready, READY_DELAY_S)


def _on_geometry(doc_key=None, **_kw):
    if doc_key:
        _own.add(doc_key)


def on_depsgraph_update(dg):
    from .tools import base
    document = registry.optional("core.document")
    if document is None or not hasattr(document, "get"):
        _own.clear()
        return
    if base.DISPATCH.running:
        return
    for upd in dg.updates:
        if not upd.is_updated_geometry:
            continue
        ob = upd.id.original if isinstance(upd.id, bpy.types.Object) else None
        if ob is None or ob.type != 'MESH':
            continue
        try:
            doc = document.get(ob)
        except Exception:
            doc = None
        if doc is None or getattr(doc, "key", None) in _own:
            continue
        doc.invalidate()
    _own.clear()


def _on_depsgraph_update_post(_scene, dg):
    on_depsgraph_update(dg)


def register():
    events.subscribe("geometry", _on_geometry, order=10)
    registry.add_handler("depsgraph_update_post", _on_depsgraph_update_post)


def unregister():
    _holds.clear()
    _own.clear()
    _loaded[0] = False
