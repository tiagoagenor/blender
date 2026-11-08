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
    for name in ("perf", "constants", "colors", "registry", "events", "i18n",
                 "core.state", "core.undo", "core.viewutil", "draw.handlers", "tools.base"):
        h.check("module loaded: " + name, name in su.loaded_modules())
    h.check("Scene.su_undo_serial registered", hasattr(bpy.context.scene, "su_undo_serial"))
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
