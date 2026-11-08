# SPDX-License-Identifier: GPL-2.0-or-later
"""G — construction, camera and scenes in the real GUI, with simulated input.

nav   FOV 35° vertical (start + after a region resize, AC-NAV-7); wheel ×5 keeps the point under the
      cursor (AC-NAV-1); MMB orbit keeps the PRESS point (AC-NAV-2) with the blue axis vertical; Shift+MMB
      pan; double MMB recentres (AC-NAV-3); Ctrl+Cmd+drag orbits about the PRESS point (AC-NAV-5);
      Shift+Z frames the model in 90 % (AC-NAV-6); Exibições padrão ▸ Superior looks −Z (AC-NAV-8);
      Órbita tool (O) and Aplicar zoom typed FOV.
The "3D View" items of ops/view_ops.KEYMAP_VIEW3D are installed here when A's keymap does not have
them yet (they are A's to install; the scenario must exercise the same bindings).
Run a subset: SU_SCN_G=nav,tape tools/sketchup_mode/run_gui.sh scn_g
"""

import importlib
import math
import os

import bpy
from mathutils import Vector

PARTS = ("nav", "tape", "protractor", "dimension", "p1")
SCREENS = os.path.join(os.environ.get("SU_ROOT", ""), "doc", "sketchup_mode", "screens")


def _mod(h, rel):
    return importlib.import_module(h.su.__name__ + "." + rel)


def ensure_view3d_keymap(h):
    """Install view_ops.KEYMAP_VIEW3D in the add-on keyconfig's "3D View" keymap (A's job; test fixture)."""
    vo = _mod(h, "ops.view_ops")
    kc = bpy.context.window_manager.keyconfigs.addon
    km = kc.keymaps.get("3D View") or kc.keymaps.new("3D View", space_type='VIEW_3D', region_type='WINDOW')
    have = {(k.idname, k.type, k.value, k.shift) for k in km.keymap_items}
    added = 0
    for idname, args, data in vo.KEYMAP_VIEW3D:
        key = (idname, args["type"], args["value"], bool(args.get("shift", False)))
        if key in have:
            continue
        kmi = km.keymap_items.new(idname, **args)
        for name, value in (data or {}).get("properties", ()):
            setattr(kmi.properties, name, value)
        added += 1
    h.log("KEYMAP_VIEW3D installed by the scenario:", added)
    return added


def make_box(h, mn=(0.0, 0.0, 0.0), mx=(4.0, 3.0, 2.5)):
    import bmesh
    document = _mod(h, "core.document")
    h.testing.reset_model()
    doc = document.root()
    bm = doc.bm
    c = [(x, y, z) for z in (mn[2], mx[2]) for y in (mn[1], mx[1]) for x in (mn[0], mx[0])]
    vs = [bm.verts.new(p) for p in c]
    for f in ((0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (1, 3, 7, 5), (3, 2, 6, 7), (2, 0, 4, 6)):
        bm.faces.new([vs[i] for i in f])
    bm.normal_update()
    doc.write(undo_key=None)
    bpy.context.view_layer.update()
    return doc


def view(h):
    win, area, R = h.area_regions()
    return area, R['WINDOW'], area.spaces.active.region_3d


def proj(h, co):
    from bpy_extras import view3d_utils
    _a, r, rv3d = view(h)
    return view3d_utils.location_3d_to_region_2d(r, rv3d, Vector(co))


def win_xy(h, co):
    _a, r, _rv = view(h)
    s = proj(h, co)
    return int(round(r.x + s.x)), int(round(r.y + s.y))


def vfov(h):
    _a, _r, rv3d = view(h)
    return math.degrees(2.0 * math.atan(1.0 / rv3d.window_matrix[1][1]))


def fwd(h):
    _a, _r, rv3d = view(h)
    return rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))


def shot(h, name):
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=3)
    path = os.path.join(h.out_dir, name)
    h.screenshot(path)
    return path


MOD_KEYS = {"ctrl": 'LEFT_CTRL', "oskey": 'OSKEY', "shift": 'LEFT_SHIFT', "alt": 'LEFT_ALT'}


def _drag(h, button, x0, y0, dx, dy, steps=8, **mods):
    """Press-drag-release. Modifiers are real key events too (the window's event state must hold them:
    CLICK_DRAG takes the modifiers of the PRESS from there)."""
    h.move(x0, y0)
    held = {}
    for m in ("ctrl", "oskey", "shift", "alt"):
        if mods.get(m):
            held[m] = True
            h.event(MOD_KEYS[m], 'PRESS', **held)
    h.event(button, 'PRESS', **mods)
    for i in range(1, steps + 1):
        h.event('MOUSEMOVE', 'NOTHING', x0 + dx * i / steps, y0 + dy * i / steps, **mods)
        h._mouse = (int(x0 + dx * i / steps), int(y0 + dy * i / steps))
    h.event(button, 'RELEASE', **mods)
    for m in reversed(list(held)):
        h.event(MOD_KEYS[m], 'RELEASE', **held)
        held.pop(m)


def part_nav(h):
    camera = _mod(h, "core.camera")
    added = ensure_view3d_keymap(h)
    h.check("KEYMAP_VIEW3D present (installed by the scenario: {:d})".format(added), True)
    yield 0.3
    h.check("AC-NAV-7 start: vertical FOV 35° ±0.5", abs(vfov(h) - 35.0) <= 0.5, vfov(h))
    area, r, rv3d = view(h)
    sp = area.spaces.active
    was_ui = sp.show_region_ui
    w0 = r.width
    sp.show_region_ui = not was_ui
    yield 0.8
    area, r, rv3d = view(h)
    h.check("AC-NAV-7 after region resize: vertical FOV 35° ±0.5 (width {}→{})".format(w0, r.width),
            abs(vfov(h) - 35.0) <= 0.5, vfov(h))
    sp.show_region_ui = was_ui
    yield 0.8
    h.check("AC-NAV-7 back: 35° ±0.5", abs(vfov(h) - 35.0) <= 0.5, vfov(h))

    make_box(h)
    camera.zoom_extents()
    yield 0.4
    P = Vector((2.0, 0.0, 1.25))            # centre of the front face (y = 0)

    # AC-NAV-1 — wheel ×5 at the cursor
    x, y = (int(round(c)) for c in win_xy(h, P))
    h.move(x, y)
    yield 0.2
    _a, r, rv3d = view(h)
    H = camera.hit_point(r, rv3d, (x - r.x, y - r.y))     # the geometry point under the (integer) cursor
    d0 = (camera.current().eye() - H).length
    for _ in range(5):
        h.event('WHEELUPMOUSE', 'PRESS')
        yield 0.05
    yield 0.3
    s = proj(h, H)
    _a, r, _rv = view(h)
    err = (Vector((s.x + r.x, s.y + r.y)) - Vector((x, y))).length if s else 1e9
    d1 = (camera.current().eye() - H).length
    h.check("AC-NAV-1 wheel ×5: point stays under the cursor (±2 px)", err <= 2.0, err)
    h.check("wheel up = zoom in", d1 < d0 * 0.6, (d0, d1))
    for _ in range(3):
        h.event('WHEELDOWNMOUSE', 'PRESS')
        yield 0.05
    yield 0.3
    h.check("wheel down = zoom out", (camera.current().eye() - H).length > d1, d1)

    # AC-NAV-2 — MMB orbit about the PRESS point, blue axis vertical
    x, y = win_xy(h, P)
    _drag(h, 'MIDDLEMOUSE', x, y, 120, 50)
    yield 0.4
    s = proj(h, P)
    _a, r, rv3d = view(h)
    err = (Vector((s.x + r.x, s.y + r.y)) - Vector((x, y))).length if s else 1e9
    right = rv3d.view_rotation @ Vector((1.0, 0.0, 0.0))
    h.check("AC-NAV-2 MMB orbit: PRESS point stays (±2 px)", err <= 2.0, err)
    h.check("orbit: blue axis vertical (no roll)", abs(right.z) < 1e-4, right)

    # Shift+MMB pan: the grabbed point follows the cursor
    x, y = win_xy(h, P)
    _drag(h, 'MIDDLEMOUSE', x, y, 90, -40, shift=True)
    yield 0.4
    s = proj(h, P)
    _a, r, _rv = view(h)
    err = (Vector((s.x + r.x, s.y + r.y)) - Vector((x + 90, y - 40))).length if s else 1e9
    h.check("Shift+MMB pan: grabbed point follows the cursor (±2 px)", err <= 2.0, err)

    # AC-NAV-3 — double MMB recentres
    camera.zoom_extents()
    yield 0.3
    Q = Vector((4.0, 1.5, 1.25))           # centre of the +X face
    x, y = win_xy(h, Q)
    h.move(x, y)
    yield 0.2
    _a, r, rv3d = view(h)
    Q = camera.hit_point(r, rv3d, (x - r.x, y - r.y))     # the visible point under the cursor
    for _ in range(2):
        h.event('MIDDLEMOUSE', 'PRESS')
        h.event('MIDDLEMOUSE', 'RELEASE')
    yield 0.5
    s = proj(h, Q)
    _a, r, _rv = view(h)
    err = (s - Vector((r.width / 2, r.height / 2))).length if s else 1e9
    h.check("AC-NAV-3 double MMB: point at the centre (±2 px)", err <= 2.0, err)

    # AC-NAV-5 — Ctrl+Cmd+drag orbits about the PRESS point
    camera.zoom_extents()
    yield 0.3
    x, y = win_xy(h, P)
    fwd0 = fwd(h)
    _drag(h, 'LEFTMOUSE', x, y, -100, 30, steps=10, ctrl=True, oskey=True)
    yield 0.5
    s = proj(h, P)
    _a, r, _rv = view(h)
    err = (Vector((s.x + r.x, s.y + r.y)) - Vector((x, y))).length if s else 1e9
    h.check("AC-NAV-5 Ctrl+Cmd+drag orbits", (fwd(h) - fwd0).length > 0.05, (fwd0, fwd(h)))
    h.check("AC-NAV-5 pivot = PRESS point (±2 px)", err <= 2.0, err)
    h.check("Ctrl+Cmd+drag: no tool operation started", not h.state()["running"])
    if len(bpy.context.window_manager.windows) == 1:
        pass
    h.key('ESC')
    yield 0.3

    # AC-NAV-6 — Shift+Z
    h.park_mouse()
    h.key('Z', shift=True)
    yield 0.5
    v = camera.current()
    corners = [Vector((x_, y_, z_)) for x_ in (0, 4) for y_ in (0, 3) for z_ in (0, 2.5)]
    e = camera._extent(v, corners)
    ext = max((e[1] - e[0]) / 2, (e[3] - e[2]) / 2) if e else 0
    h.check("AC-NAV-6 Shift+Z: model fills 90 % (±1 %)", abs(ext - 0.9) <= 0.01, (ext, e))
    h.park_mouse()
    yield 0.4
    save_screen(h, "g_orbita.png")
    yield 0.3

    # AC-NAV-8 — Exibições padrão ▸ Superior
    with bpy.context.temp_override(window=h.window(), area=area, region=r):
        bpy.ops.su.view_standard(view='TOP')
    yield 0.3
    h.check("AC-NAV-8 Superior looks −Z", (fwd(h) - Vector((0, 0, -1))).length < 1e-4, fwd(h))
    with bpy.context.temp_override(window=h.window(), area=area, region=r):
        bpy.ops.su.view_standard(view='ISO')
        bpy.ops.su.set_projection(persp=False)
    yield 0.3
    h.check("Câmera ▸ Projeção paralela", not view(h)[2].is_perspective)
    with bpy.context.temp_override(window=h.window(), area=area, region=r):
        bpy.ops.su.set_projection(persp=True)
    yield 0.5
    h.check("Perspectiva again, FOV 35° ±0.5", view(h)[2].is_perspective and abs(vfov(h) - 35) <= 0.5, vfov(h))

    # Órbita tool (O): LMB drag orbits about the press point
    camera.zoom_extents()
    yield 0.3
    h.park_mouse()
    h.key('O', unicode='o')
    yield 0.4
    h.check("O → Órbita", h.state()["workspace_tool"] == "su.orbit", h.state()["workspace_tool"])
    x, y = win_xy(h, P)
    fwd0 = fwd(h)
    _drag(h, 'LEFTMOUSE', x, y, 80, 0)
    yield 0.4
    s = proj(h, P)
    _a, r, _rv = view(h)
    err = (Vector((s.x + r.x, s.y + r.y)) - Vector((x, y))).length if s else 1e9
    h.check("Órbita tool: drag orbits about the press point (±2 px)",
            (fwd(h) - fwd0).length > 0.05 and err <= 2.0, err)

    # Aplicar zoom (Z): typed field of view
    h.key('Z', unicode='z')
    yield 0.4
    h.check("Z → Aplicar zoom", h.state()["workspace_tool"] == "su.zoom")
    h.type_text("50")
    yield 0.5
    h.check("Aplicar zoom: `50` → FOV 50°", abs(vfov(h) - 50.0) <= 0.5, vfov(h))
    h.type_text("35")
    yield 0.5
    h.check("Aplicar zoom: `35` → FOV 35°", abs(vfov(h) - 35.0) <= 0.5, vfov(h))
    h.key('SPACE', unicode=' ')
    yield 0.3

    # Previous / Next
    n_before = camera.history_state()
    with bpy.context.temp_override(window=h.window(), area=area, region=r):
        bpy.ops.su.view_standard(view='FRONT')
    yield 0.2
    with bpy.context.temp_override(window=h.window(), area=area, region=r):
        bpy.ops.su.view_previous()
    yield 0.3
    h.check("Câmera ▸ Anterior leaves the Frontal view", (fwd(h) - Vector((0, 1, 0))).length > 0.1, (n_before, fwd(h)))
    with bpy.context.temp_override(window=h.window(), area=area, region=r):
        bpy.ops.su.view_next()
    yield 0.3
    h.check("Câmera ▸ Próxima returns to Frontal", (fwd(h) - Vector((0, 1, 0))).length < 1e-4, fwd(h))
    camera.zoom_extents()
    h.check("no active object", h.state()["active_object"] is None)


def set_tool(h, tool_id):
    base = _mod(h, "tools.base")
    base.set_workspace_tool(tool_id)


def hover(h, co, settle=0.35):
    h.glide(*win_xy(h, co))
    return settle


def inf_kind(h):
    return h.state()["inference"]["kind"]


def save_screen(h, name):
    """Copy a print to doc/sketchup_mode/screens (light copy for the phone, sips -Z 1600)."""
    import subprocess
    src = shot(h, name)
    if SCREENS and os.path.isdir(SCREENS):
        subprocess.run(["sips", "-Z", "1600", src, "--out", os.path.join(SCREENS, name)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return src


def zoom_out(h, steps=3):
    _a, r, rv3d = view(h)
    _mod(h, "ops.view_ops").zoom_steps(r, rv3d, (r.width / 2, r.height / 2), -steps)


def part_tape(h):
    camera = _mod(h, "core.camera")
    guides = _mod(h, "core.guides")
    make_box(h)
    guides.delete_guides()
    camera.standard_view("ISO")
    camera.zoom_extents()
    zoom_out(h)
    yield 0.4
    h.park_mouse()
    h.key('T', unicode='t')
    yield 0.4
    h.check("T → Fita métrica", h.state()["workspace_tool"] == "su.tape", h.state()["workspace_tool"])
    h.check("Fita: hint", h.state()["hint_key"] == "tool.su.tape.hint_start", h.state()["hint_key"])
    yield hover(h, (1.2, 0.0, 0.0))
    h.check("hover on the front bottom edge: Em aresta", inf_kind(h) == "ON_EDGE", h.state()["inference"])
    h.click()
    yield 0.3
    yield hover(h, (1.2, -0.8, 0.0))
    h.check("parallel guide follows (hint)", h.state()["hint_key"] == "tool.su.tape.hint_offset", h.state()["hint_key"])
    s0 = bpy.context.scene.su_undo_serial
    h.type_text("1")
    yield 0.5
    g = guides.data().guides
    ok = len(g) == 1 and g[0].kind == 'LINE' and abs(g[0].co[1] + 1.0) < 1e-4 and abs(g[0].co[2]) < 1e-4
    h.check("AC-FIT-1 `1` Enter → guide line at 1 m (y = −1, along X)", ok,
            [(x.kind, tuple(x.co), tuple(x.direction)) for x in g])
    h.check("1 undo step per guide", bpy.context.scene.su_undo_serial - s0 == 1)
    # second guide from the right bottom edge (x = 4), 1 m out → x = 5
    yield hover(h, (4.0, 1.2, 0.0))
    h.click()
    yield 0.3
    yield hover(h, (4.7, 1.2, 0.0))
    h.type_text("1")
    yield 0.5
    g = guides.data().guides
    h.check("second guide at x = 5 (along Y)", len(g) == 2 and abs(g[1].co[0] - 5.0) < 1e-4,
            [(x.kind, tuple(x.co)) for x in g])
    # AC-FIT-2: Option → measure only
    yield hover(h, (0.0, 0.0, 0.0))
    h.click()
    yield 0.2
    h.key('LEFT_ALT', alt=True)
    yield 0.2
    yield hover(h, (4.0, 0.0, 0.0))
    h.click()
    yield 0.4
    d = h.state()
    h.check("AC-FIT-2 Option: measure only (no guide, Medidas 4,00m)",
            len(guides.data().guides) == 2 and d["vcb_value"] == "4,00m", (len(guides.data().guides), d["vcb_value"]))
    h.check("measure-only hint", d["hint_key"] == "tool.su.tape.hint_start_measure", d["hint_key"])
    yield hover(h, (4.0, 3.0, 2.5))
    h.click()
    yield 0.2
    h.key('LEFT_ALT', alt=True)              # Option tap while measuring: back to guide creation
    yield 0.2
    yield hover(h, (4.0, 3.0, 3.5))
    h.click()
    yield 0.4
    g = guides.data().guides
    h.check("AC-FIT-3 guide point from an endpoint", len(g) == 3 and g[2].kind == 'POINT',
            [(x.kind, tuple(x.co)) for x in g])
    # Linha: "Na linha" on a guide, intersection of the two guides (AC-FIT-4)
    h.key('L', unicode='l')
    yield 0.3
    yield hover(h, (2.5, -1.0, 0.0))
    h.check("Linha over the guide: Na linha (ON_GUIDE)", inf_kind(h) == "ON_GUIDE", h.state()["inference"])
    yield hover(h, (5.0, -1.0, 0.0), 0.5)
    inf = h.state()["inference"]
    h.check("AC-FIT-4 intersection of two guides inferable by Linha", inf["kind"] == "INTERSECTION"
            and abs(inf["point"][0] - 5.0) < 1e-4 and abs(inf["point"][1] + 1.0) < 1e-4, inf)
    save_screen(h, "g_fita_guia.png")
    yield 0.3
    h.key('ESC')
    h.key('SPACE', unicode=' ')
    yield 0.3


def part_protractor(h):
    camera = _mod(h, "core.camera")
    guides = _mod(h, "core.guides")
    base = _mod(h, "tools.base")
    make_box(h)
    guides.delete_guides()
    camera.standard_view("ISO")
    camera.zoom_extents()
    yield 0.4
    set_tool(h, "su.protractor")
    yield 0.3
    h.check("Transferidor active", h.state()["tool"] == "su.protractor", h.state()["tool"])
    yield hover(h, (4.0, 1.5, 1.2), 0.5)
    ctrl = base.controller("su.protractor")
    h.check("AC-TRA-1 hover on the vertical +X face: gizmo in its plane (red)",
            (ctrl.normal - Vector((1, 0, 0))).length < 1e-3 and ctrl.axis == "X", (ctrl.normal, ctrl.axis))
    save_screen(h, "g_transferidor_face.png")
    yield 0.2
    yield hover(h, (2.0, -1.5, 0.0), 0.4)
    h.check("hover on the ground: blue gizmo", ctrl.axis == "Z" and abs(ctrl.normal.z - 1) < 1e-6, (ctrl.normal, ctrl.axis))
    yield hover(h, (0.0, 0.0, 0.0))
    h.click()
    yield 0.3
    yield hover(h, (1.3, 0.0, 0.0))
    h.click()
    yield 0.3
    h.check("baseline placed", ctrl.stage == 2 and h.state()["running"], ctrl.stage)
    yield hover(h, (1.0, 0.45, 0.0), 0.4)
    save_screen(h, "g_transferidor.png")
    yield 0.2
    s0 = bpy.context.scene.su_undo_serial
    h.type_text("30")
    yield 0.5
    g = guides.data().guides
    want = Vector((math.cos(math.radians(30)), math.sin(math.radians(30)), 0.0))
    h.check("AC-TRA-2 base +X, `30` → guide (cos30, sin30, 0)",
            len(g) == 1 and (Vector(g[0].direction) - want).length < 1e-4, [tuple(x.direction) for x in g])
    h.check("1 undo step", bpy.context.scene.su_undo_serial - s0 == 1)
    h.key('L', unicode='l')
    yield 0.3
    p = want * -2.0
    yield hover(h, tuple(p), 0.4)
    h.check("AC-TRA-2 Linha snaps on the angled guide (ON_GUIDE)", inf_kind(h) == "ON_GUIDE", h.state()["inference"])
    h.key('ESC')
    h.key('SPACE', unicode=' ')
    yield 0.3


def part_dimension(h):
    camera = _mod(h, "core.camera")
    guides = _mod(h, "core.guides")
    ann = _mod(h, "draw.annotations")
    make_box(h)
    guides.delete_guides()
    guides.data().dims.clear()
    camera.standard_view("ISO")
    camera.zoom_extents()
    yield 0.4
    set_tool(h, "su.dimension")
    yield 0.3
    yield hover(h, (4.0, 1.2, 0.0))
    h.check("hover the 3 m bottom edge of +X face: Em aresta", inf_kind(h) == "ON_EDGE", h.state()["inference"])
    h.click()
    yield 0.3
    yield hover(h, (5.2, 1.5, 0.0))
    s0 = bpy.context.scene.su_undo_serial
    h.click()
    yield 0.4
    d = guides.data().dims
    h.check("AC-DIM-1 edge of 3 m → 3,00m", len(d) == 1 and guides.dimension_text(0) == "3,00m",
            [guides.dimension_text(i) for i in range(len(d))])
    h.check("dimension pulled out (offset > 0.5 m)", len(d) == 1 and Vector(d[0].offset).length > 0.5,
            [tuple(x.offset) for x in d])
    h.check("1 undo step", bpy.context.scene.su_undo_serial - s0 == 1)
    # 8 m edge (§12 step 13) by two points
    make_box(h, (0, 0, 0), (8, 3, 2.5))
    camera.zoom_extents()
    yield 0.4
    yield hover(h, (0.0, 0.0, 0.0))
    h.click()
    yield 0.2
    yield hover(h, (8.0, 0.0, 0.0))
    h.click()
    yield 0.2
    yield hover(h, (4.0, -1.2, 0.0))
    h.click()
    yield 0.4
    h.check("Dimensões: 8 m edge by two endpoints → 8,00m", len(d) == 2 and guides.dimension_text(1) == "8,00m",
            [guides.dimension_text(i) for i in range(len(d))])
    h.park_mouse()
    yield 0.4
    h.check("dimension texts drawn", ann.last_drawn()["dims"] == 2, ann.last_drawn())
    save_screen(h, "g_cotas.png")
    yield 0.2
    # AC-DIM-2 Cmd+Z removes it
    h.key('Z', oskey=True)
    yield 0.8
    h.check("AC-DIM-2 Cmd+Z → the last dimension is gone", len(guides.data().dims) == 1, len(guides.data().dims))
    h.key('Z', oskey=True, shift=True)
    yield 0.8
    h.check("Cmd+Shift+Z → back", len(guides.data().dims) == 2, len(guides.data().dims))
    # AC-DIM-3 legible while orbiting (screen-space text)
    x, y = win_xy(h, (4.0, 1.5, 1.25))
    _drag(h, 'MIDDLEMOUSE', x, y, -260, 90)
    yield 0.5
    h.park_mouse()
    yield 0.3
    h.check("AC-DIM-3 texts still drawn after orbiting", ann.last_drawn()["dims"] == 2, ann.last_drawn())
    save_screen(h, "g_cotas_orbita.png")
    yield 0.2
    h.key('SPACE', unicode=' ')
    yield 0.3


def run(h):
    want = [p.strip() for p in os.environ.get("SU_SCN_G", ",".join(PARTS)).split(",") if p.strip()]
    for name in want:
        fn = globals().get("part_" + name)
        if fn is None:
            continue
        h.log("---- part", name)
        yield from fn(h)
    if len(bpy.context.window_manager.windows) == 1:
        h.check("single window (no popup)", True)
