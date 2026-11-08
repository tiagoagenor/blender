# SPDX-License-Identifier: GPL-2.0-or-later
"""S-E (owner: A): template round trip leaves the user's Blender as it was (PLANO §5.2, §9.2-A item 11).

1. In the mode: the backup holds the user's values; simulate an owner changing navigation prefs.
2. File › New › General (read_homefile app_template=""): our template unregisters → prefs restored,
   backup file removed, keyconfig back to the previous one, no su module registered, no perf error.
3. Back to SketchUp Mode: registered again, filtered keyconfig active again.
(kill -9 is covered by the stale-backup rule, unit test test_a_prefs.test_stale_backup_wins.)"""

import importlib
import os

import bpy


def run(h):
    su = h.su
    prefs = importlib.import_module(su.__name__ + ".prefs")
    inputs = bpy.context.preferences.inputs
    orig = dict(prefs.originals())
    h.check("backup has the user's navigation prefs", "inputs.use_zoom_to_mouse" in orig, sorted(orig))
    h.check("backup file exists", os.path.isfile(prefs.path()), prefs.path())
    zoom0, inv0 = orig["inputs.use_zoom_to_mouse"], orig["inputs.invert_zoom_wheel"]
    inputs.use_zoom_to_mouse = not zoom0                 # what G does for "zoom no cursor"
    inputs.invert_zoom_wheel = not inv0
    kc_prev = None
    yield 0.3

    win = h.window()
    with bpy.context.temp_override(window=win):
        bpy.ops.wm.read_homefile(app_template="")
    yield 1.5
    kcs = bpy.context.window_manager.keyconfigs
    h.check("General: SketchUp Mode unregistered", not su.is_registered())
    h.check("General: prefs restored", (inputs.use_zoom_to_mouse, inputs.invert_zoom_wheel) == (zoom0, inv0),
            (inputs.use_zoom_to_mouse, inputs.invert_zoom_wheel, zoom0, inv0))
    h.check("General: backup file removed", not os.path.isfile(prefs.path()))
    h.check("General: keyconfig is not SketchUp_Mode", kcs.active is not None and kcs.active.name != "SketchUp_Mode",
            kcs.active.name if kcs.active else None)
    h.check("General: SketchUp_Mode keyconfig removed", kcs.get("SketchUp_Mode") is None)
    kc_prev = kcs.active.name if kcs.active else None
    h.check("General: su.tool_event gone", not hasattr(bpy.types, "SU_OT_tool_event"))

    with bpy.context.temp_override(window=h.window()):
        bpy.ops.wm.read_homefile(app_template="SketchUp_Mode")
    yield h.until(lambda: bpy.app.driver_namespace.get("su_ready"), 30.0, "su_ready after switching back")
    yield 0.5
    kcs = bpy.context.window_manager.keyconfigs
    h.check("back: SketchUp Mode registered", su.is_registered())
    h.check("back: keyconfig SketchUp_Mode active", kcs.active is not None and kcs.active.name == "SketchUp_Mode",
            (kcs.active.name if kcs.active else None, kc_prev))
    h.check("back: fresh backup", os.path.isfile(prefs.path()))
