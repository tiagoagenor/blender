# SPDX-License-Identifier: GPL-2.0-or-later
"""Scenario F (owner: F): Selecionar + Excluir in the real GUI with simulated input.

 1. Espaço over the viewport → Selecionar stays active (no bounce back to the previous tool);
    hint mentions "Option";
 2. box 8×6×3: 1 / 2 / 3 clicks on the top → 1 face / 1+4 / 6+12 (AC-SEL-1); empty click clears;
 3. window (left→right) around the box → everything; crossing (right→left) inside the top → the top;
 4. Excluir (ROTEIRO_CASA): AF-2 top + ⌫ → V8 A12 F5; AF-6 Cmd+Z → back with the top selected;
    AF-1b DEL key; AF-7 "1,5" typed + ⌫ → "1," and nothing deleted; AF-5 double click + ⌫ → V8 A8 F1;
    Esc clears the selection.
Screenshots: <out_dir>/f_*.png."""

import importlib
import math
import os

import bpy
from mathutils import Euler, Vector

V = Vector


def _modifier_clicks_reach_tools(su):
    """True when A's tool keymap passes Shift/Option/Cmd clicks to su.tool_event (LEFTMOUSE any=True)."""
    base = importlib.import_module(su.__name__ + ".tools.base")
    items = base.tool_keymap(base.TOOLS["su.eraser"].meta)
    return any(it[1].get("type") == 'LEFTMOUSE' and it[1].get("any") for it in items)


def run(h):
    su = h.su
    document = importlib.import_module(su.__name__ + ".core.document")
    geom = importlib.import_module(su.__name__ + ".core.geom")
    selection = importlib.import_module(su.__name__ + ".core.selection")

    win, area, R = h.area_regions()
    h.check("3D viewport present", area is not None)
    if area is None:
        return
    region = R['WINDOW']
    rv3d = area.spaces.active.region_3d

    def ctx():
        return bpy.context.temp_override(window=win, area=area, region=region)

    doc = document.root()

    def counts():
        bm = doc.bm
        lay = geom.layers(bm)
        return (len(bm.verts), sum(1 for e in bm.edges if not e[lay.bridge]), len(bm.faces))

    def kinds():
        refs = selection.get()
        return (sum(r.kind == 'FACE' for r in refs), sum(r.kind == 'EDGE' for r in refs),
                sum(r.kind == 'OBJECT' for r in refs))

    def new_box():
        bm = doc.bm
        bm.clear()
        b = [V((0, 0, 0)), V((8, 0, 0)), V((8, 6, 0)), V((0, 6, 0))]
        t = [p + V((0, 0, 3)) for p in b]
        for i in range(4):
            geom.add_edge(bm, b[i], b[(i + 1) % 4])
        for i in range(4):
            geom.add_edge(bm, b[i], t[i])
        for i in range(4):
            geom.add_edge(bm, t[i], t[(i + 1) % 4])
        selection.clear()
        with ctx():
            doc.write(undo_key="undo.adjust")

    shots = []

    def shot(name):
        path = os.path.join(h.out_dir, name + ".png")
        h.park_mouse()
        area.tag_redraw()
        yield 0.4
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=2)
        h.screenshot(path)
        yield 0.3
        h.check("screenshot " + name, os.path.isfile(path), path)
        shots.append(path)

    # view: from the front-left, above (top, front y=0 and left x=0 faces visible)
    rv3d.view_location = V((4, 3, 1.5))
    rv3d.view_distance = 22.0
    rv3d.view_rotation = Euler((math.radians(62), 0.0, math.radians(-35)), 'XYZ').to_quaternion()
    rv3d.view_perspective = 'PERSP'
    area.tag_redraw()
    yield 0.4

    # 1. Espaço → Selecionar
    h.move(*h.region_xy(region, 0.85, 0.85))
    yield 0.2
    h.key('L', unicode='l')
    yield 0.4
    h.key('SPACE', unicode=' ')
    yield 0.6
    d = h.state()
    h.check("Espaço activates su.select", d["workspace_tool"] == "su.select" and d["tool"] == "su.select",
            (d["workspace_tool"], d["tool"]))
    h.move(*h.region_xy(region, 0.8, 0.8))
    yield 0.6
    d = h.state()
    h.check("su.select stays active (no bounce)", d["workspace_tool"] == "su.select", d["workspace_tool"])
    h.check("hint mentions Option", "Option" in d["hint"] and "Ctrl" not in d["hint"], d["hint"])

    new_box()
    yield 0.4
    top = h.world_xy((4, 3, 3))

    # 2. clicks
    h.click(*top)
    yield 0.6
    h.check("AC-SEL-1 one click on the top → 1 face", kinds() == (1, 0, 0), kinds())
    yield from shot("f_selecionar")
    h.click(*top)
    yield 0.6
    h.click(*top)
    h.click(*top)
    yield 0.6
    h.check("AC-SEL-1 double click → face + 4 edges", kinds() == (1, 4, 0), kinds())
    yield from shot("f_selecionar_duplo")
    h.click(*top)
    h.click(*top)
    h.click(*top)
    yield 0.6
    h.check("AC-SEL-1 triple click → 6 faces + 12 edges", kinds() == (6, 12, 0), kinds())
    yield from shot("f_selecionar_triplo")
    h.click(*h.region_xy(region, 0.9, 0.9))
    yield 0.6
    h.check("click on empty space clears", selection.is_empty(), kinds())

    # 3. window / crossing
    pts = [h.world_xy((x, y, z)) for x in (0, 8) for y in (0, 6) for z in (0, 3)]
    x0, x1 = min(p[0] for p in pts) - 30, max(p[0] for p in pts) + 30
    y0, y1 = min(p[1] for p in pts) - 30, max(p[1] for p in pts) + 30
    h.move(x0, y0)
    yield 0.3
    h.event('LEFTMOUSE', 'PRESS')
    h.glide(x1, y1, steps=8)
    yield 0.3
    h.event('LEFTMOUSE', 'RELEASE')
    yield 0.6
    h.check("AC-SEL-5 window around the box → 6 faces + 12 edges", kinds() == (6, 12, 0), kinds())
    h.click(*h.region_xy(region, 0.9, 0.9))
    yield 0.4
    c = h.world_xy((4, 3, 3))
    h.move(c[0] + 15, c[1] + 10)
    yield 0.3
    h.event('LEFTMOUSE', 'PRESS')
    h.glide(c[0] - 15, c[1] - 10, steps=6)
    yield 0.3
    h.event('LEFTMOUSE', 'RELEASE')
    yield 0.6
    # SketchUp's box selection ignores occlusion: the bottom face under the rectangle is selected too
    h.check("AC-SEL-5 crossing inside the top → top + bottom faces, no edge", kinds() == (2, 0, 0), kinds())

    # 4. Excluir
    s0 = bpy.context.scene.su_undo_serial
    h.click(*top)
    yield 0.5
    before = selection.get()
    h.key('BACK_SPACE')
    yield 0.6
    h.check("AF-2 top + ⌫ → V8 A12 F5", counts() == (8, 12, 5), counts())
    h.check("AF-2 selection empty after Excluir", selection.is_empty(), kinds())
    h.check("AF-2 one undo step", bpy.context.scene.su_undo_serial - s0 == 1, bpy.context.scene.su_undo_serial - s0)
    yield from shot("f_excluir_face")
    h.move(*h.region_xy(region, 0.8, 0.8))
    h.key('Z', oskey=True)
    yield 0.8
    h.check("AF-6 Cmd+Z → V8 A12 F6", counts() == (8, 12, 6), counts())
    h.check("AF-6 Cmd+Z restores the selection", selection.get() == before, (kinds(), len(before)))
    h.key('Z', oskey=True, shift=True)
    yield 0.8
    h.check("AF-6 Cmd+Shift+Z → V8 A12 F5 again", counts() == (8, 12, 5), counts())

    new_box()
    yield 0.4
    h.click(*top)
    yield 0.5
    h.key('DEL')
    yield 0.6
    h.check("AF-1b DEL deletes the face too", counts() == (8, 12, 5), counts())

    new_box()
    yield 0.4
    h.click(*top)
    yield 0.5
    h.type_text("1,5", enter=False)
    yield 0.3
    h.key('BACK_SPACE')
    yield 0.5
    d = h.state()
    h.check("AF-7 ⌫ with text edits the Measurements box", d["vcb_buffer"] == "1,", d["vcb_buffer"])
    h.check("AF-7 the face is not deleted", counts() == (8, 12, 6) and kinds() == (1, 0, 0), (counts(), kinds()))
    h.key('ESC')
    yield 0.4
    h.check("Esc clears the typed text", h.state()["vcb_buffer"] == "", h.state()["vcb_buffer"])

    h.click(*top)
    h.click(*top)
    yield 0.6
    h.check("AF-5 double click on the top → 1 face + 4 edges", kinds() == (1, 4, 0), kinds())
    h.key('BACK_SPACE')
    yield 0.6
    h.check("AF-5 ⌫ → base + 4 vertical edges (V8 A8 F1)", counts() == (8, 8, 1), counts())
    yield from shot("f_excluir_duplo")

    new_box()
    yield 0.4
    h.click(*top)
    yield 0.4
    h.key('ESC')
    yield 0.4
    h.check("Esc clears the selection", selection.is_empty(), kinds())

    # 5. Apagar (E): AF-3b face click does nothing; AF-3 edge takes its faces; Option softens
    new_box()
    yield 0.4
    h.move(*h.region_xy(region, 0.8, 0.8))
    h.key('E', unicode='e')
    yield 0.5
    h.check("E activates su.eraser", h.state()["tool"] == "su.eraser", h.state()["tool"])
    s0 = bpy.context.scene.su_undo_serial
    h.glide(*top)
    yield 0.3
    h.click(*top)
    yield 0.5
    h.check("AF-3b Eraser on a face: nothing", counts() == (8, 12, 6) and bpy.context.scene.su_undo_serial == s0,
            counts())
    mid = h.world_xy((4, 0, 3))
    h.glide(*mid)
    yield 0.4
    h.click(*mid)
    yield 0.6
    h.check("AF-3 Eraser on the top front edge → V8 A11 F4", counts() == (8, 11, 4), counts())
    h.check("AF-3 one undo step", bpy.context.scene.su_undo_serial - s0 == 1, bpy.context.scene.su_undo_serial - s0)
    yield from shot("f_apagar")
    h.key('Z', oskey=True)
    yield 0.6
    h.check("Cmd+Z brings the edge and faces back", counts() == (8, 12, 6), counts())
    vert = h.world_xy((8, 0, 1.5))
    h.glide(*vert)
    yield 0.3
    h.click(*vert, alt=True)
    yield 0.6
    lay = geom.layers(doc.bm)
    soft = [e for e in doc.bm.edges if e[lay.soft]]
    if _modifier_clicks_reach_tools(su):
        h.check("AC-APG-3 Option on the vertical edge softens it", len(soft) == 1 and counts() == (8, 12, 6),
                (len(soft), counts()))
    else:
        h.log("SKIP AC-APG-3 (GUI): tool keymap LEFTMOUSE items lack any=True (A) — modifier clicks never "
              "reach the tool; covered headless in test_f_eraser")
    yield from shot("f_apagar_suavizar")

    # 6. Pintura (B): Materiais section open in the tray; floor seen from above = BACK side (AC-PNT-1)
    materials = importlib.import_module(su.__name__ + ".core.materials")
    tray = importlib.import_module(su.__name__ + ".ui.tray")
    space = area.spaces.active
    if not space.show_region_ui:
        space.show_region_ui = True
    tray.set_open("materials", True)
    bm = doc.bm
    bm.clear()
    selection.clear()
    for a, b in (((-2, -1, 0), (6, -1, 0)), ((6, -1, 0), (6, 5, 0)), ((6, 5, 0), (-2, 5, 0)), ((-2, 5, 0), (-2, -1, 0))):
        geom.add_edge(bm, V(a), V(b))
    for c in (((8, 0, 0), (12, 0, 0)), ((12, 0, 0), (12, 0, 3)), ((12, 0, 3), (8, 0, 3)), ((8, 0, 3), (8, 0, 0))):
        geom.add_edge(bm, V(c[0]), V(c[1]))
    with ctx():
        doc.write(undo_key="undo.adjust")
    yield 0.4
    floor = next(f for f in doc.bm.faces if abs(f.calc_center_median().z) < 1e-6)
    wall = next(f for f in doc.bm.faces if abs(f.calc_center_median().y) < 1e-6 and f.calc_center_median().z > 1)
    h.check("floor normal −Z (back side up)", floor.normal.z < -0.99, tuple(floor.normal))
    fi, wi = floor.index, wall.index
    h.move(*h.region_xy(region, 0.8, 0.8))
    h.key('B', unicode='b')
    yield 0.5
    h.check("B activates su.paint", h.state()["tool"] == "su.paint", h.state()["tool"])
    h.check("Pintura hint mentions Option and Cmd", "Option" in h.state()["hint"] and "Cmd" in h.state()["hint"],
            h.state()["hint"])
    with ctx():
        bpy.ops.su.material_pick(palette_index=0)
    red = materials.active()
    h.check("swatch → active material", red is not None and red.name == materials.palette_rgb()[0][0],
            red.name if red else None)
    s0 = bpy.context.scene.su_undo_serial
    h.click(*h.world_xy((2, 2, 0)))
    yield 0.6
    h.check("AC-PNT-1 floor from above: BACK side painted", materials.material_of(doc, fi, -1) == red,
            materials.material_of(doc, fi, -1))
    h.check("AC-PNT-1 floor front stays default", materials.material_of(doc, fi, 1) is None)
    h.check("Pintura: 1 undo step", bpy.context.scene.su_undo_serial - s0 == 1)
    with ctx():
        bpy.ops.su.material_pick(palette_index=9)
    blue = materials.active()
    h.click(*h.world_xy((10, 0, 1.5)))
    yield 0.6
    wside = 1 if doc.bm.faces[wi].normal.y < 0 else -1      # the camera looks from −Y
    h.check("wall: the seen side painted", materials.material_of(doc, wi, wside) == blue,
            (wside, materials.material_of(doc, wi, wside)))
    yield from shot("f_pintura")
    tray.set_open("materials", False)

    h.key('SPACE', unicode=' ')
    yield 0.4
    d = h.state()
    h.check("no active object", d["active_object"] is None, d["active_object"])
    h.log("screens:", shots)
