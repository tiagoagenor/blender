# SPDX-License-Identifier: GPL-2.0-or-later
"""Build the template's startup.blend (owner: D). PLANO.md §4.7. Started by build_all.sh (GUI, lock):

    Blender --app-template SketchUp_Mode --enable-event-simulate --python build_startup.py -- <template dir> <out png>

Waits for the shell start-up steps (driver_namespace["su_ui_ready"], su/ui/startup.py), resizes the Large
Tool Set and the tray by simulated edge drags (Region.width is read-only; visual_spike/driver.py), removes
the factory objects/data, re-applies the start view, saves `startup.blend` (copy) into the template and a
screenshot, then quits. Coordinates: region.x/y/width/height (physical px), nothing depends on the window size.
"""

import os
import sys
import traceback

import bpy

sys.dont_write_bytecode = True

ARGS = sys.argv[sys.argv.index("--") + 1:]
TPL, SHOT = os.path.abspath(ARGS[0]), os.path.abspath(ARGS[1])
TOOLS_W = 96          # logical px (LTS, 2 columns)
UI_W = 300            # logical px (tray)
LOG = os.path.join(os.path.dirname(SHOT), "build_startup_log.txt")
SU = "bl_app_templates_system.SketchUp_Mode.su"


def log(*a):
    with open(LOG, "a", encoding="utf-8") as f:
        print(*a, file=f)


def area_regions():
    win = bpy.context.window_manager.windows[0]
    a = max((a for a in win.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width * a.height)
    return win, a, {r.type: r for r in a.regions}


def drag(kind, width_logical):
    st = {}

    def f():
        win, a, R = area_regions()
        ps = bpy.context.preferences.system.pixel_size
        r = R[kind]
        y = r.y + r.height // 2
        if kind == 'TOOLS':
            x0, x1 = r.x + r.width - 1, r.x + int(width_logical * ps)
        else:
            x0, x1 = r.x + 1, r.x + r.width - int(width_logical * ps) - 2
        log(kind, "before", r.x, r.width, "drag", x0, "->", x1)
        st.update(x0=x0, x1=x1, y=y)
        win.event_simulate('MOUSEMOVE', 'NOTHING', x=x0, y=y)

    def g():
        bpy.context.window_manager.windows[0].event_simulate('LEFTMOUSE', 'PRESS', x=st["x0"], y=st["y"])

    def h():
        win = bpy.context.window_manager.windows[0]
        for i in range(1, 11):
            win.event_simulate('MOUSEMOVE', 'NOTHING', x=int(st["x0"] + (st["x1"] - st["x0"]) * i / 10), y=st["y"])

    def k():
        bpy.context.window_manager.windows[0].event_simulate('LEFTMOUSE', 'RELEASE', x=st["x1"], y=st["y"])

    return [f, g, h, k]


def park():
    win, a, R = area_regions()
    r = R['WINDOW']
    win.event_simulate('MOUSEMOVE', 'NOTHING', x=r.x + int(r.width * 0.8), y=r.y + int(r.height * 0.75))


def clean_data():
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.materials,
                 bpy.data.images, bpy.data.textures, bpy.data.curves):
        for idb in list(coll):
            coll.remove(idb)
    sc = bpy.context.scene
    us = sc.unit_settings
    us.system = 'METRIC'
    us.length_unit = 'METERS'
    sc.render.engine = 'BLENDER_WORKBENCH'
    wm = bpy.context.window_manager
    if hasattr(wm, "su_tray"):
        wm.su_tray.open_ids = ""          # tray all closed at first opening


def view():
    startup = sys.modules[SU + ".ui.startup"]
    win, a, R = area_regions()
    startup.set_view(a)
    a.tag_redraw()


def lens():
    startup = sys.modules[SU + ".ui.startup"]
    win, a, R = area_regions()
    startup.fit_lens(a)
    startup.set_view(a)
    a.tag_redraw()


def report():
    win, a, R = area_regions()
    log("final", {k: (v.x, v.width, v.height) for k, v in R.items()})


def save():
    path = os.path.join(TPL, "startup.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, copy=True, compress=True)
    log("saved", path, os.path.getsize(path))


def shot():
    win = bpy.context.window_manager.windows[0]
    with bpy.context.temp_override(window=win):
        bpy.ops.screen.screenshot(filepath=SHOT)


def quit_():
    bpy.ops.wm.quit_blender()


Q = [clean_data] + drag('TOOLS', TOOLS_W) + drag('UI', UI_W) + [park, view, lens, lens, report, save, None, shot, quit_]
_t = {"waited": 0.0}


def tick():
    if not bpy.app.driver_namespace.get("su_ui_ready"):
        _t["waited"] += 0.3
        if _t["waited"] > 90:
            log("timeout waiting for su_ui_ready")
            bpy.ops.wm.quit_blender()
            return None
        return 0.3
    if not Q:
        return None
    fn = Q.pop(0)
    try:
        if fn:
            fn()
    except Exception:
        log(traceback.format_exc())
    return 0.35


bpy.context.preferences.view.show_splash = False
bpy.app.timers.register(tick, first_interval=1.0)
