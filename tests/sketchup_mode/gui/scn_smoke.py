# SPDX-License-Identifier: GPL-2.0-or-later
"""Smoke scenario (owner: A) — runs on every merge. A0 version: the template opens empty and closes
without errors (the harness adds isolation, su_ready, single window and perf.errors() == 0).
Grows into the M-A E2E (Linha 3×2 via Medidas, Retângulo 2×3, Cmd+Z, `3` Enter over the tray)."""

import os

import bpy


def run(h):
    su = h.su
    h.check("su registered", su.is_registered())
    h.check("no module skipped", not su.failed_modules(), su.failed_modules())
    for name in ("perf", "constants", "colors", "registry", "events", "i18n", "settings", "modifiers",
                 "keymap", "session", "testing", "core.state", "core.undo", "core.viewutil", "draw.handlers",
                 "tools.base", "tools.catalog", "tools.line", "ops.tool_ops"):
        h.check("module loaded: " + name, name in su.loaded_modules())
    h.check("Scene.su_undo_serial registered", hasattr(bpy.context.scene, "su_undo_serial"))
    h.check("WindowManager.su_vcb registered", hasattr(bpy.context.window_manager, "su_vcb"))
    kcs = bpy.context.window_manager.keyconfigs
    h.check("keyconfig SketchUp_Mode active", kcs.active is not None and kcs.active.name == "SketchUp_Mode",
            kcs.active.name if kcs.active else None)
    km = kcs.addon.keymaps.get("Window")
    ids = [(k.idname, k.type) for k in km.keymap_items] if km else []
    h.check("Window keymap: su.vcb_key first (TEXTINPUT, RET, NUMPAD_ENTER, BACK_SPACE, ESC)",
            [t for i, t in ids if i == "su.vcb_key"] == ['TEXTINPUT', 'RET', 'NUMPAD_ENTER', 'BACK_SPACE', 'ESC'], ids)
    h.check("Window keymap: L → su.tool_activate", ("su.tool_activate", 'L') in ids, ids)
    from bl_ui.space_toolsystem_common import ToolSelectPanelHelper
    tools = ToolSelectPanelHelper._tool_class_from_space_type('VIEW_3D')._tools['OBJECT']
    flat = [getattr(t, "idname", None) for t in ToolSelectPanelHelper._tools_flatten(tools) if t is not None]
    h.check("su.line is a workspace tool", "su.line" in flat)
    d = h.state()
    h.check("session: no active object", d["active_object"] is None, d["active_object"])
    h.check("dispatcher follows the workspace tool", d["tool"] == d["workspace_tool"], (d["tool"], d["workspace_tool"]))
    win, area, regions = h.area_regions()
    h.check("3D viewport present", area is not None)
    # draw-layer pipeline: a temporary POST_VIEW and POST_PIXEL layer must be called on redraw
    import importlib
    handlers = importlib.import_module(su.__name__ + ".draw.handlers")
    seen = set()
    handlers.add_layer("smoke_3d", 'POST_VIEW', 99, lambda dc: seen.add(("3d", dc.rv3d is not None)))
    handlers.add_layer("smoke_2d", 'POST_PIXEL', 99, lambda dc: seen.add(("2d", dc.region is not None)))
    if area is not None:
        area.tag_redraw()
    h.park_mouse()
    yield 0.5              # a few redraws: draw-layer errors would surface in perf.errors()
    handlers.remove_layer("smoke_3d")
    handlers.remove_layer("smoke_2d")
    h.check("draw layers called (POST_VIEW + POST_PIXEL)", seen == {("3d", True), ("2d", True)}, seen)
    shot = os.path.join(h.out_dir, "smoke.png")
    h.screenshot(shot)
    yield 0.3
    h.check("screenshot written", os.path.isfile(shot), shot)
