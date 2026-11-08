# SPDX-License-Identifier: GPL-2.0-or-later
"""Undo steps with selection restore (owner: A). Contract: PLANO.md §2.4, §3.7, §3.8.

`scene.su_undo_serial` (IntProperty, saved in the memfile) is incremented by every `push()`.
`_SEL[serial]` keeps the selection that belongs to that undo state:
  * `before_change()` (called by Document.write before mutating) stores the PRE-operation selection
    under the current serial;
  * `push()` increments the serial and stores the POST-operation selection under the new one.
On undo_post/redo_post the restored serial picks the matching selection; then events "undo".
Selection comes from core.selection (owner B) when it exists; until then nothing is restored.
"""

import sys

import bpy

from .. import events, i18n, perf, registry

ORDER = 110

_SEL = {}      # serial -> selection snapshot (dict) or None


def _selection():
    return sys.modules.get(__package__ + ".selection")


def _snapshot():
    sel = _selection()
    if sel is None or not hasattr(sel, "snapshot"):
        return None
    return sel.snapshot()


def _scene():
    return getattr(bpy.context, "scene", None)


def serial():
    scene = _scene()
    return scene.su_undo_serial if scene is not None else 0


def before_change():
    """Remember the current (pre-operation) selection under the current serial."""
    scene = _scene()
    if scene is None:
        return
    _SEL[scene.su_undo_serial] = _snapshot()


def push(message_key):
    """Create one undo step named i18n.t(message_key), remembering the post-operation selection."""
    scene = _scene()
    if scene is None:
        perf.error("undo.push({!r}) without scene".format(message_key))
        return
    scene.su_undo_serial += 1
    _SEL[scene.su_undo_serial] = _snapshot()
    if bpy.ops.ed.undo_push.poll():
        bpy.ops.ed.undo_push(message=i18n.t(message_key))


def _restore(direction):
    from . import state
    from .. import registry
    from ..tools import base
    if base.DISPATCH.running:
        base.DISPATCH.cancel(base.tool_context())
    document = registry.optional("core.document")
    if document is not None and hasattr(document, "invalidate_all"):
        document.invalidate_all()
    scene = _scene()
    sel = _selection()
    if scene is not None and sel is not None and hasattr(sel, "restore"):
        sel.restore(_SEL.get(scene.su_undo_serial))
    state.STATE.last_action = None
    events.emit("undo", direction=direction)


def _on_undo_post(*_args):
    _restore('UNDO')


def _on_redo_post(*_args):
    _restore('REDO')


def _on_load_pre(*_args):
    _SEL.clear()


def register():
    bpy.types.Scene.su_undo_serial = bpy.props.IntProperty(
        name="SketchUp Mode undo serial", default=0, options={'HIDDEN'})
    registry.add_handler("undo_post", _on_undo_post)
    registry.add_handler("redo_post", _on_redo_post)
    registry.add_handler("load_pre", _on_load_pre)


def unregister():
    _SEL.clear()
    if hasattr(bpy.types.Scene, "su_undo_serial"):
        del bpy.types.Scene.su_undo_serial
