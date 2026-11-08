# SPDX-License-Identifier: GPL-2.0-or-later
"""Shell start-up sequence and start view (owner: D). Ported from the visual spike (PLANO.md §4.7).

On every "load" (GUI only) the spike's steps run ONE PER TIMER TICK (0.3 s; mutating the layout in the
same tick crashed `area_close` in the spike). Every step is idempotent, so with the generated
`startup.blend` (layout already clean, region widths saved) most of them do nothing:
  1. theme/prefs/studio light (su.theme)        2. one workspace "SketchUp"
  3. close every area but the 3D viewport       4. regions, style.apply, hide panels, tool Selecionar
  5. tray category + start view (new file)      6–7. vertical FOV 35° exactly (lens fitted ×2)
Then `driver_namespace["su_ui_ready"] = True` (scenarios and build_startup.py wait for it).

Start view (from ref image 2): vertical FOV 35°, yaw 33° from +Y towards −X, pitch 6.6° down, world
origin at NDC (−0.26, −0.387), 11.5 m away. Viewport lens ≠ FOV: after a redraw `fit_lens` reads
`window_matrix[1][1]` and scales the lens. Applied only to new (unsaved) files.
"""

import math
import sys

import bpy
from mathutils import Matrix, Vector

from .. import events, perf, registry
from . import hide

ORDER = 590

READY_KEY = "su_ui_ready"
STEP_S = 0.3
CAM = dict(yaw_deg=33.0, pitch_deg=6.6, origin_ndc=(-0.26, -0.387), vfov_deg=35.0, dist=11.5)
_run = {"serial": 0}


def _sib(name):
    return sys.modules.get(__package__.rsplit(".", 1)[0] + "." + name)


def _win():
    wm = bpy.context.window_manager
    return wm.windows[0] if wm and wm.windows else None


def _area():
    win = _win()
    return hide.main_view3d_area(win) if win else None


# ------------------------------------------------------------------------------------------- view
def set_view(area):
    sp = area.spaces.active
    r3 = sp.region_3d
    region = next(r for r in area.regions if r.type == 'WINDOW')
    yaw, pitch = math.radians(CAM["yaw_deg"]), math.radians(CAM["pitch_deg"])
    fwd = Vector((-math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), -math.sin(pitch)))
    right = fwd.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(fwd)
    R = Matrix((right, up, -fwd)).transposed()            # columns = view x, y, z
    r3.view_perspective = 'PERSP'
    r3.view_rotation = R.to_quaternion()
    aspect = region.width / max(1, region.height)
    tv = math.tan(math.radians(CAM["vfov_deg"]) / 2)
    nx, ny = CAM["origin_ndc"]
    dw = R @ Vector((nx * tv * aspect, ny * tv, -1.0)).normalized()
    C = -dw * CAM["dist"]                                 # camera position: origin lands on (nx, ny)
    r3.view_distance = 10.0
    r3.view_location = C + fwd * 10.0


def fit_lens(area):
    """Make the vertical FOV exactly CAM['vfov_deg'] (needs a drawn region: window_matrix is current)."""
    sp = area.spaces.active
    cur = sp.region_3d.window_matrix[1][1]
    target = 1.0 / math.tan(math.radians(CAM["vfov_deg"]) / 2)
    if cur > 1e-6:
        sp.lens = sp.lens * target / cur


def is_new_file():
    return not bpy.data.filepath


# ------------------------------------------------------------------------------------------- steps
def s_theme():
    theme = _sib("theme")
    if theme is not None:
        theme.apply()


def s_workspace():
    win = _win()
    if win is not None:
        hide.keep_one_workspace(win)


def s_areas():
    win = _win()
    if win is not None:
        hide.close_other_areas(win)


def s_space():
    area = _area()
    if area is None:
        return
    hide.configure_regions(area)
    style = _sib("core.style")
    if style is not None:
        style.apply()
    hide.hide_ui_panels()
    session = _sib("session")
    if session is None:                       # A's session.on_load_post selects the tool once it exists
        win = _win()
        try:
            with bpy.context.temp_override(window=win, area=area):
                bpy.ops.wm.tool_set_by_id(name="su.select")
        except Exception:
            perf.exception("startup: tool su.select")


def s_tray():
    area = _area()
    if area is None:
        return
    tray = _sib("ui.tray")
    for r in area.regions:
        if r.type == 'UI' and tray is not None:
            try:
                r.active_panel_category = tray.CATEGORY
            except Exception:
                pass
    if is_new_file():
        set_view(area)
    area.tag_redraw()


def s_lens():
    area = _area()
    if area is not None and is_new_file():
        fit_lens(area)
        set_view(area)
        area.tag_redraw()


STEPS = (s_theme, s_workspace, s_areas, s_space, s_tray, s_lens, s_lens)


def run_steps():
    """Start the step chain (a newer load cancels the older chain)."""
    _run["serial"] += 1
    serial = _run["serial"]
    bpy.app.driver_namespace[READY_KEY] = False
    steps = list(STEPS)

    def tick():
        if serial != _run["serial"]:
            return
        fn = steps.pop(0)
        try:
            fn()
        except Exception:
            perf.exception("startup step " + fn.__name__)
        if steps:
            registry.deferred(tick, STEP_S)
        else:
            bpy.app.driver_namespace[READY_KEY] = True

    registry.deferred(tick, STEP_S)


def _on_load(**_kw):
    if bpy.app.background:
        return
    run_steps()


def is_ready():
    return bool(bpy.app.driver_namespace.get(READY_KEY))


def register():
    events.subscribe("load", _on_load, order=900)


def unregister():
    _run["serial"] += 1
    bpy.app.driver_namespace.pop(READY_KEY, None)
