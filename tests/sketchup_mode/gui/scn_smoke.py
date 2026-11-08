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
    if "su.rectangle" in importlib.import_module(su.__name__ + ".tools.base").TOOLS:
        yield from _m_a(h)
    else:
        h.log("M-A E2E skipped: su.rectangle not registered")


def _m_a(h):
    """M-A E2E (PLANO §9.1-MA): Linha 3×2 via Medidas → face; Retângulo 2×3 typed with the mouse over the
    tray; Cmd+Z removes the rectangle and keeps the line's face. Real simulated input only."""
    import importlib
    T = h.testing
    units = importlib.import_module(h.su.__name__ + ".core.units")
    sep = units.list_sep(None)
    T.reset_model()
    win, area, R = h.area_regions()
    if not area.spaces.active.show_region_ui:
        area.spaces.active.show_region_ui = True
        yield 0.5
        win, area, R = h.area_regions()
    ru = R['UI']

    # Linha 3×2 from the origin by Measurements
    h.glide(*h.world_xy((0.0, 0.0, 0.0)))
    yield 0.2
    h.key('L', unicode='l')
    yield 0.4
    h.check("M-A: L → Linha", h.state()["tool"] == "su.line", h.state()["tool"])
    h.glide(*h.world_xy((0.0, 0.0, 0.0)))
    yield 0.3
    h.click()
    yield 0.3
    for toward, text in (((1.0, 0.0, 0.0), "3"), ((3.0, 1.0, 0.0), "2"), ((2.0, 2.0, 0.0), "3"),
                         ((0.0, 1.0, 0.0), "2")):
        h.glide(*h.world_xy(toward))
        yield 0.3
        h.type_text(text)
        yield 0.5
    st = h.stats()
    h.check("M-A: Linha 3×2 → 1 face 6 m²", st.get("faces") == 1 and abs(st.get("area", 0) - 6.0) < 1e-3,
            (st.get("faces"), st.get("area"), st.get("bbox")))

    # Retângulo 2×3 from the Linha's corner (3,0,0), typed with the mouse over the tray
    h.glide(*h.world_xy((3.0, 0.0, 0.0)))
    yield 0.2
    h.key('R', unicode='r')
    yield 0.4
    h.check("M-A: R → Retângulo", h.state()["tool"] == "su.rectangle", h.state()["tool"])
    h.glide(*h.world_xy((3.0, 0.0, 0.0)))
    yield 0.3
    h.click()
    yield 0.3
    h.glide(*h.world_xy((4.0, 1.0, 0.0)))
    yield 0.3
    h.move(*h.region_xy(ru, 0.5, 0.5))          # mouse over the tray while typing
    yield 0.3
    h.type_text("2" + sep + "3")
    yield 0.6
    st = h.stats()
    h.check("M-A: `2;3` Enter over the tray → rectangle (2 faces, 12 m²)",
            st.get("faces") == 2 and abs(st.get("area", 0) - 12.0) < 1e-3, (st.get("faces"), st.get("area")))
    h.check("M-A: normals −Z", st.get("normals") == [[0.0, 0.0, -1.0]] * 2, st.get("normals"))
    h.park_mouse()
    yield 0.5
    h.screenshot(os.path.join(h.out_dir, "smoke_m_a.png"))
    yield 0.3

    # Cmd+Z removes only the rectangle
    h.key('Z', oskey=True)
    yield 0.8
    st = h.stats()
    h.check("M-A: Cmd+Z removes the rectangle, keeps the line face",
            st.get("faces") == 1 and abs(st.get("area", 0) - 6.0) < 1e-3 and st["bbox"][1][0] < 3.0 + 1e-4,
            (st.get("faces"), st.get("area"), st.get("bbox")))
    h.check("M-A: no active object", h.state()["active_object"] is None)
