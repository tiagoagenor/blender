# SPDX-License-Identifier: GPL-2.0-or-later
"""Theme, visual preferences and studio light (owner: D). PLANO.md §4.6, §4.7, §3.3.

Ported from visual_spike `apply_theme()` / `apply_prefs()`. Pitfalls kept from the spike:
`import _rna_xml` (not `rna_xml`); toolbar/sidebar region background is `theme.regions.sidebars`;
`apps.show_edge_resize` must stay True (False kills region-edge drags); `show_statusbar_vram` is
read-only on some systems (setattr in try).

* The theme, `app_flag`s, splash and navigate-gizmo flags are swapped in by Blender from the
  template's `userpref.blend` (built by tools/sketchup_mode/build_userpref.py with `apply_theme()` +
  `apply_template_prefs()`). `ensure_theme()` re-applies the theme at runtime only when the template
  userpref.blend has not been built yet.
* Other visual preferences are NOT swapped by Blender: `apply_runtime_prefs()` sets them at load and
  remembers the user's values; `unregister()` restores them.
* Studio light: the committed `studiolights/sketchup.sl` (written by `write_studio_light`) is LOADED from
  the template folder; nothing is written to the user's data files.
"""

import math
import os

import bpy

from . import colors as C
from . import perf

ORDER = 60

TEMPLATE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDIO_LIGHT_NAME = "sketchup.sl"
STUDIO_LIGHT_PATH = os.path.join(TEMPLATE_DIR, "studiolights", STUDIO_LIGHT_NAME)

# Camera-relative solid lighting (P0, CRITICA_R3_SKETCHUP §3.2): the default box in the start view gives
# front ≈255, side ≈210, top ≈160 (top seen from above is the darkest). Solved for the start view
# (yaw 33°, pitch 6.6°) with Workbench's wrapped Lambert (smooth 0): ambient + col·max(0, n·l).
# 0.9344 = Workbench fast_rcp(1.0) (its approximation of 1/(1+wrap)²), compensated here.
LIGHT_AMBIENT = 0.20
LIGHT_DIRECTION = (-0.088, 0.043, 0.995)      # view space: x right, y up, z towards the viewer
LIGHT_DIFFUSE = 0.962 / 0.9344


def rgb(c):
    return (c[0] / 255.0, c[1] / 255.0, c[2] / 255.0)


def rgba(c, a=1.0):
    return rgb(c) + (a,)


# ---------------------------------------------------------------------------------------------- theme
def _theme_preset_path():
    for d in bpy.utils.preset_paths("interface_theme"):
        p = os.path.join(d, "Blender_Light.xml")
        if os.path.isfile(p):
            return p
    return ""


def apply_theme(context=None):
    """Blender_Light + SketchUp overrides on preferences.themes[0] (spike values)."""
    context = context or bpy.context
    prefs = context.preferences
    preset = _theme_preset_path()
    if preset:
        try:
            import _rna_xml
            _rna_xml.xml_file_run(context, preset, bpy.types.USERPREF_MT_interface_theme_presets.preset_xml_map)
        except Exception:
            perf.exception("theme: Blender_Light preset")
    th = prefs.themes[0]
    ui = th.user_interface
    chrome, hdr, body, text = C.UI_CHROME, C.UI_PANEL_HEADER, C.UI_TRAY_BODY, C.UI_TEXT
    border, navy = C.UI_BORDER, C.ICON_NAVY
    sel_fill, sel_line = C.UI_TOOL_ACTIVE_FILL, C.UI_TOOL_ACTIVE_LINE

    ui.panel_header = rgba(hdr)
    ui.panel_back = rgba(body)
    ui.panel_sub_back = rgba(body)
    ui.panel_title = rgb(text)
    ui.panel_text = rgb(text)
    ui.panel_outline = rgba(border)
    ui.panel_roundness = 0.0
    ui.editor_border = rgb(border)
    ui.editor_outline = rgba(border, 0.0)
    try:
        ui.editor_outline_active = rgba(border, 0.0)
    except Exception:
        pass
    ui.icon_saturation = 1.0
    # Large Tool Set buttons: chrome, active = light blue fill + blue outline (SketchUp selected tool)
    for wn in ("wcol_toolbar_item", "wcol_tool"):
        w = getattr(ui, wn)
        w.inner = rgba(chrome)
        w.inner_sel = rgba(sel_fill)
        w.outline = rgba(chrome)
        w.outline_sel = rgba(sel_line)
        w.item = rgba(navy)
        w.text = rgb(navy)
        w.text_sel = rgb(navy)
        w.roundness = 0.25
    for wn in ("wcol_regular", "wcol_text", "wcol_toggle"):
        w = getattr(ui, wn)
        w.inner = (1.0, 1.0, 1.0, 1.0)
        w.outline = rgba(border)
        w.text = rgb(text)
        w.text_sel = rgb(text)
    # Medidas box (status bar): white field with a thin light border
    w = ui.wcol_text
    w.inner_sel = (1.0, 1.0, 1.0, 1.0)
    w.outline = rgba((190, 190, 198))
    w.roundness = 0.15
    # Tray rows: flat bands #E0E1E9, no rounding
    w = ui.wcol_box
    w.inner = rgba(hdr)
    w.outline = rgba((250, 250, 252))
    w.roundness = 0.0
    w.text = rgb(text)
    w = ui.wcol_pulldown
    w.text = rgb(text)
    w.inner_sel = rgba(sel_fill)
    w.text_sel = rgb(text)
    # Single-category sidebar still draws a tab: make it invisible (blends into the chrome)
    w = ui.wcol_tab
    for a in ("inner", "inner_sel", "outline", "outline_sel", "item"):
        try:
            setattr(w, a, rgba(chrome))
        except Exception:
            pass
    w.text = rgb(chrome)
    w.text_sel = rgb(chrome)
    sb = th.regions.sidebars
    sb.back = rgba(chrome)
    sb.tab_back = rgba(chrome)

    v = th.view_3d
    sp = v.space
    sp.header = rgba(chrome)
    sp.header_text = rgb(text)
    sp.header_text_hi = rgb(text)
    sp.text = rgb(text)
    sp.text_hi = rgb(text)
    sp.title = rgb(text)
    g = sp.gradients
    g.background_type = 'SINGLE_COLOR'
    g.high_gradient = rgb(C.BACKGROUND)
    g.gradient = rgb(C.BACKGROUND)
    v.wire = rgb(C.EDGE)
    v.object_selected = rgb(C.SELECTION)
    v.object_active = rgb(C.SELECTION)
    v.face_back = rgba(C.FACE_BACK)
    v.face_front = (0.0, 0.0, 0.0, 0.0)
    v.edge_width = 1
    for sname in ("topbar", "statusbar"):
        s = getattr(th, sname).space
        s.back = rgb(chrome)
        s.header = rgba(chrome)
        s.text = rgb(text)
        s.header_text = rgb(text)
        s.header_text_hi = rgb(text)
        s.text_hi = rgb(text)


def theme_is_applied(context=None):
    context = context or bpy.context
    w = context.preferences.themes[0].user_interface.wcol_toolbar_item
    return all(abs(a - b) < 2e-3 for a, b in zip(w.inner_sel, rgba(C.UI_TOOL_ACTIVE_FILL)))


def ensure_theme(context=None):
    if not theme_is_applied(context):
        apply_theme(context)


# ---------------------------------------------------------------------------------------------- prefs
def apply_template_prefs(context=None):
    """Preferences Blender takes from the TEMPLATE's userpref.blend (BKE_blender_userdef_app_template_data_swap)."""
    p = (context or bpy.context).preferences
    p.view.show_splash = False
    p.view.show_navigate_ui = False
    p.apps.show_corner_split = False
    p.apps.show_regions_visibility_toggle = False
    p.apps.show_edge_resize = True          # spike: False kills region-edge drags


# (data path relative to preferences, value) — not swapped by app templates; restored on unregister.
RUNTIME_PREFS = (
    ("system.use_region_overlap", False),
    ("view.mini_axis_type", 'NONE'),
    ("view.show_statusbar_stats", False),
    ("view.show_statusbar_memory", False),
    ("view.show_statusbar_vram", False),
    ("view.show_statusbar_version", False),
    ("view.show_statusbar_scene_duration", False),
    ("view.show_tooltips_python", False),
)
_saved_prefs = {}


def _resolve(prefs, path):
    owner, _, attr = path.rpartition(".")
    for part in owner.split("."):
        prefs = getattr(prefs, part)
    return prefs, attr


def apply_runtime_prefs(context=None):
    prefs = (context or bpy.context).preferences
    for path, value in RUNTIME_PREFS:
        try:
            owner, attr = _resolve(prefs, path)
            if path not in _saved_prefs:
                _saved_prefs[path] = getattr(owner, attr)
            if getattr(owner, attr) != value:
                setattr(owner, attr, value)
        except Exception:
            pass                            # e.g. show_statusbar_vram read-only


def restore_runtime_prefs(context=None):
    prefs = (context or bpy.context).preferences
    for path, value in _saved_prefs.items():
        try:
            owner, attr = _resolve(prefs, path)
            setattr(owner, attr, value)
        except Exception:
            pass
    _saved_prefs.clear()


# ---------------------------------------------------------------------------------------------- light
def studio_light_text(ambient=LIGHT_AMBIENT, direction=LIGHT_DIRECTION, diffuse=LIGHT_DIFFUSE):
    """Contents of a Blender solid studio light (.sl, 'Version 1') with one camera-relative light."""
    d = direction
    n = math.sqrt(sum(x * x for x in d)) or 1.0
    d = tuple(x / n for x in d)
    lines = ["Version 1"]
    lines += ["light_ambient.{:s} {:.6f}".format(a, ambient) for a in "xyz"]
    for i in range(4):
        on = i == 0
        lines.append("light[{:d}].flag {:d}".format(i, 1 if on else 0))
        lines.append("light[{:d}].smooth {:.6f}".format(i, 0.0))
        for a in "xyz":
            lines.append("light[{:d}].col.{:s} {:.6f}".format(i, a, diffuse if on else 0.0))
        for a in "xyz":
            lines.append("light[{:d}].spec.{:s} {:.6f}".format(i, a, 0.0))
        for a, x in zip("xyz", d if on else (0.0, 0.0, 1.0)):
            lines.append("light[{:d}].vec.{:s} {:.6f}".format(i, a, x))
    return "\n".join(lines) + "\n"


def write_studio_light(path=STUDIO_LIGHT_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="ascii") as f:
        f.write(studio_light_text())


def ensure_studio_light(context=None):
    """Load studiolights/sketchup.sl from the template folder (once per session). Returns its name or ''."""
    prefs = (context or bpy.context).preferences
    for sl in prefs.studio_lights:
        if sl.name == STUDIO_LIGHT_NAME and os.path.realpath(sl.path) == os.path.realpath(STUDIO_LIGHT_PATH):
            return sl.name
    if not os.path.isfile(STUDIO_LIGHT_PATH):
        perf.error("theme: missing " + STUDIO_LIGHT_PATH)
        return ""
    try:
        sl = prefs.studio_lights.load(STUDIO_LIGHT_PATH, 'STUDIO')
        return sl.name
    except Exception:
        perf.exception("theme: load studio light")
        return ""


def _unload_studio_light():
    try:
        prefs = bpy.context.preferences
        for sl in list(prefs.studio_lights):
            if os.path.realpath(sl.path) == os.path.realpath(STUDIO_LIGHT_PATH):
                prefs.studio_lights.remove(sl)
    except Exception:
        pass


def apply(context=None):
    """Everything visual at the preference level (called by ui.startup's first step)."""
    ensure_theme(context)
    apply_runtime_prefs(context)
    return ensure_studio_light(context)


def register():
    pass


def unregister():
    if bpy.app.background:
        return
    restore_runtime_prefs()
    _unload_studio_light()
