# SPDX-License-Identifier: GPL-2.0-or-later
"""A (vertical slice) — platform + Linha in the real GUI, with simulated input:

 1. filtered keyconfig active; `L` with the mouse over the tray activates Linha (Window keymap);
 2. hover → inference; Ctrl+click does not start the tool;
 3. Linha 3×2 by Measurements (L, origin, ← move, `3` Enter, ...) → 1 face of 6 m², normal −Z, 4 undo steps;
 4. MMB in the middle of a chain: the chain continues (AC-LIN-6);
 5. new chain; mouse over the tray, `3` Enter → 3 m segment (tool modal); Esc; `4` Enter over the tray
    (idle → su.vcb_key + su.vcb_capture) → "Ajustar" to 4 m;
 6. Cmd+Z ×2 removes the new line and keeps the rectangle face;
 7. no active object, no popup, screenshots.
B/C modules missing at run time are replaced by the unit-test fakes (h.install_fakes)."""

import os

import bpy


def run(h):
    T = h.testing
    fakes = h.install_fakes()
    h.check("fakes (modules not merged yet): " + (", ".join(n.rsplit(".", 2)[-2] + "." + n.rsplit(".", 1)[-1]
                                                          for n in fakes) or "none"), True)
    kcs = bpy.context.window_manager.keyconfigs
    h.check("keyconfig SketchUp_Mode active", kcs.active is not None and kcs.active.name == "SketchUp_Mode",
            kcs.active.name if kcs.active else None)
    win, area, R = h.area_regions()
    space = area.spaces.active
    if not space.show_region_ui:
        space.show_region_ui = True          # the tray (D) opens it; here we only need the region
    yield 0.6
    win, area, R = h.area_regions()
    rw, ru = R['WINDOW'], R['UI']
    T.reset_model()
    s0 = bpy.context.scene.su_undo_serial

    # 1. L over the tray
    h.move(*h.region_xy(ru, 0.5, 0.6))
    yield 0.3
    h.key('L', unicode='l')
    yield 0.5
    d = h.state()
    h.check("L over the tray activates su.line", d["workspace_tool"] == "su.line" and d["tool"] == "su.line", d["tool"])
    h.check("hint = ponto inicial", d["hint_key"] == "tool.su.line.hint_start", d["hint_key"])

    # 2. hover + Ctrl+click
    h.glide(*h.world_xy((1.0, 1.0, 0.0)))
    yield 0.4
    d = h.state()
    base = __import__(h.su.__name__ + ".tools.base", fromlist=["x"])
    h.check("hover gives an inference", d["inference"]["kind"] != "NONE",
            (d["inference"], "hover events", base.HOVER_CALLS[0]))
    h.event('LEFTMOUSE', 'PRESS', ctrl=True)
    h.event('LEFTMOUSE', 'RELEASE', ctrl=True)
    yield 0.4
    h.check("Ctrl+click does not start the tool", not h.state()["running"])
    if len(bpy.context.window_manager.windows) == 1:
        h.key('ESC')                         # close a context menu, if any opened
        yield 0.3

    # 2b. modifier clicks reach the tool (tool keymap items use "any": True)
    for mod in ("shift", "alt", "oskey"):
        h.event('LEFTMOUSE', 'PRESS', **{mod: True})
        h.event('LEFTMOUSE', 'RELEASE', **{mod: True})
        yield 0.3
        le = base.DISPATCH.last_event
        got = {"shift": getattr(le, "shift", None), "alt": getattr(le, "copy", None),
               "oskey": getattr(le, "alt_action", None)}[mod]
        h.check("{:s}+click reaches the tool (ev.{:s})".format(mod, mod), le is not None and got is True,
                (getattr(le, "type", None), getattr(le, "value", None), got))
        h.key('ESC')
        yield 0.3
    h.check("modifier clicks leave no geometry", h.stats().get("edges") == 0, h.stats().get("edges"))

    # 3. rectangle 3×2 by Measurements
    h.glide(*h.world_xy((0.0, 0.0, 0.0)))
    yield 0.3
    h.check("origin inferred", h.state()["inference"]["kind"] in {"ORIGIN", "ENDPOINT"}, h.state()["inference"])
    h.click()
    yield 0.3
    h.check("chain started (modal running)", h.state()["running"])
    for toward, text in (((1.0, 0.0, 0.0), "3"), ((3.0, 1.0, 0.0), "2"), ((2.0, 2.0, 0.0), "3"),
                         ((0.0, 1.0, 0.0), "2")):
        h.glide(*h.world_xy(toward))
        yield 0.3
        lin = h.state()["inference"]["linear"]
        h.type_text(text)
        yield 0.5
        h.log("segment toward", toward, text, "linear", lin, "stats", h.stats().get("edges"))
    st = h.stats()
    h.check("rectangle: 4 edges, 1 face", (st.get("edges"), st.get("faces")) == (4, 1), st)
    h.check("rectangle area 6 m²", abs(st.get("area", 0) - 6.0) < 1e-4, st.get("area"))
    h.check("face normal −Z", st.get("normals") == [[0.0, 0.0, -1.0]], st.get("normals"))
    h.check("4 undo steps (1 per segment)", bpy.context.scene.su_undo_serial - s0 == 4,
            bpy.context.scene.su_undo_serial - s0)
    h.check("face closed the chain", not h.state()["running"])
    h.park_mouse()
    yield 0.5
    h.screenshot(os.path.join(h.out_dir, "a_linha_retangulo.png"))
    yield 0.3

    # 4. MMB orbit in the middle of a chain
    p0 = h.world_xy((5.0, 0.0, 0.0))
    h.glide(*p0)
    yield 0.3
    h.click()
    yield 0.3
    h.glide(*h.world_xy((5.0, 1.0, 0.0)))
    yield 0.3
    x, y = h._mouse
    h.event('MIDDLEMOUSE', 'PRESS')
    yield 0.1
    for i in range(1, 6):
        h.move(x + 6 * i, y)
        yield 0.05
    h.event('MIDDLEMOUSE', 'RELEASE')
    yield 0.4
    h.check("chain continues after MMB orbit (AC-LIN-6)", h.state()["running"])
    # the orbit changed the view: aim at the +Y axis again in the new view
    h.glide(*h.world_xy((5.0, 1.0, 0.0)))
    yield 0.3
    a_lin = h.state()["inference"]["linear"]

    # 5. `3` Enter with the mouse over the tray while drawing, then idle retype `4`
    h.move(*h.region_xy(ru, 0.5, 0.5))
    yield 0.3
    h.type_text("3")
    yield 0.5
    st = h.stats()
    h.check("`3` Enter over the tray (running) → segment", st.get("edges") == 5, st)
    h.log("linear before tray", a_lin, "bbox", st.get("bbox"))
    h.key('ESC')
    yield 0.4
    h.check("Esc ends the chain", not h.state()["running"])
    serial_before = bpy.context.scene.su_undo_serial
    h.type_text("4")
    yield 0.6
    st2 = h.stats()
    h.check("`4` Enter over the tray (idle) → Ajustar (1 undo step)",
            bpy.context.scene.su_undo_serial == serial_before + 1, bpy.context.scene.su_undo_serial - serial_before)
    grow = (st2["bbox"][1][1] - st["bbox"][1][1]) if st2.get("bbox") and st.get("bbox") else None
    h.check("last segment re-sized 3 → 4 m", grow is not None and abs(grow - 1.0) < 1e-3, (st.get("bbox"), st2.get("bbox")))
    h.check("no Measurements text left", h.state()["vcb_buffer"] == "")
    h.park_mouse()
    yield 0.4
    h.screenshot(os.path.join(h.out_dir, "a_linha_ajustar.png"))
    yield 0.3

    # 6. Cmd+Z ×2: back to the rectangle only
    h.key('Z', oskey=True)
    yield 0.6
    h.key('Z', oskey=True)
    yield 0.8
    st = h.stats()
    h.check("Cmd+Z ×2 removes the new line, keeps the face", (st.get("edges"), st.get("faces")) == (4, 1), st)

    # 7. invariants
    d = h.state()
    h.check("no active object", d["active_object"] is None, d["active_object"])
    h.check("single window (no popup)", len(bpy.context.window_manager.windows) == 1)
    h.park_mouse()
    yield 0.4
    h.screenshot(os.path.join(h.out_dir, "a_final.png"))
    yield 0.3
