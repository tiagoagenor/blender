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

    # 7. Mover: the ridge of the house (ROTEIRO_CASA Parte 1, passos 3–4; AC-MOV-6)
    base = importlib.import_module(su.__name__ + ".tools.base")
    space.show_region_ui = True
    new_box()
    geom.add_edge(doc.bm, V((0, 3, 3)), V((8, 3, 3)))
    with ctx():
        doc.write(undo_key="undo.adjust")
    rv3d.view_location = V((4, 3, 1.5))
    rv3d.view_distance = 24.0
    yield 0.4
    h.check("ridge line splits the top: 7 faces", len(doc.bm.faces) == 7, len(doc.bm.faces))
    h.move(*h.region_xy(region, 0.85, 0.85))
    h.key('M', unicode='m')
    yield 0.5
    h.check("M activates su.move", h.state()["tool"] == "su.move", h.state()["tool"])
    ridge = h.world_xy((4, 3, 3))
    h.glide(*ridge)
    yield 0.5
    hov = base.controller("su.move").hover_refs[0]
    h.check("Mover hover highlights the ridge edge", len(hov) == 1 and hov[0].kind == 'EDGE', hov)
    s0 = bpy.context.scene.su_undo_serial
    def dbg(tag):
        d = h.state()
        mv = base.controller("su.move")
        h.log("DBG", tag, d["tool"], d["running"], d["inference"], d["locks"], d["vcb_buffer"], d["vcb_value"],
              "start", mv.start, "cur", mv.current, "sess", mv.session is not None)
    h.click(*ridge)
    yield 0.4
    dbg("after click")
    h.key('UP_ARROW')
    yield 0.2
    dbg("after up")
    h.glide(*h.world_xy((4, 3, 7)))
    yield 0.4
    dbg("after glide")
    h.type_text("2", enter=False)
    yield 0.3
    dbg("after 2")
    h.key('RET')
    yield 0.8
    dbg("after ret")
    bm = doc.bm
    zs = sorted(round(v.co.z, 4) for v in bm.verts)
    planar = sum(1 for f in bm.faces if not geom.is_planar(f, 1e-4))
    pent = sorted(len(f.verts) for f in bm.faces).count(5)
    h.check("AC-MOV-6 ridge at z=5", zs[-2:] == [5.0, 5.0], zs)
    h.check("AC-MOV-6 2 roof slopes + 2 pentagonal gables, 7 planar faces",
            len(bm.faces) == 7 and planar == 0 and pent == 2, (len(bm.faces), planar, pent))
    h.check("AC-MOV-6 one undo step", bpy.context.scene.su_undo_serial - s0 == 1, bpy.context.scene.su_undo_serial - s0)
    yield from shot("f_mover_cumeeira")

    # 8. Mover with copy (Option during the move) + 2x (AC-MOV-2) — the house is copied twice
    rv3d.view_location = V((14, 0, 1.5))
    rv3d.view_distance = 55.0
    yield 0.4
    h.move(*h.region_xy(region, 0.85, 0.85))
    h.key('A', oskey=True)
    yield 0.4
    h.check("Cmd+A selects everything (7 faces + 15 edges)", kinds()[:2] == (7, 15), kinds())
    h.click(*h.world_xy((0, 0, 0)))
    yield 0.4
    h.key('RIGHT_ARROW')
    h.glide(*h.world_xy((5, 0, 0)))
    yield 0.3
    h.key('LEFT_ALT')
    yield 0.3
    h.type_text("10")
    yield 0.8
    h.check("Option toggles copy: 2 houses", len(doc.bm.faces) == 14, len(doc.bm.faces))
    h.type_text("2x")
    yield 0.8
    bm = doc.bm
    h.check("AC-MOV-2 `2x` → 3 houses", len(bm.faces) == 21, len(bm.faces))
    bm.faces.ensure_lookup_table()
    sel_f = [bm.faces[r.index] for r in selection.get() if r.kind == 'FACE' and r.index < len(bm.faces)]
    h.check("AC-MOV-2 selection = the last copy",
            len(sel_f) == 7 and all(min(v.co.x for v in f.verts) >= 19.99 for f in sel_f),
            [round(min(v.co.x for v in f.verts), 2) for f in sel_f])
    yield from shot("f_mover_copia")

    # 9. Girar the last copy 90° about its front-right corner (AC-GIR-2 in the GUI)
    h.move(*h.region_xy(region, 0.85, 0.85))
    h.key('Q', unicode='q')
    yield 0.5
    h.check("Q activates su.rotate", h.state()["tool"] == "su.rotate", h.state()["tool"])
    h.glide(*h.world_xy((28, 0, 0)))
    yield 0.4
    h.click(*h.world_xy((28, 0, 0)))
    yield 0.4
    h.glide(*h.world_xy((28, 5, 0)))
    yield 0.3
    h.click()
    yield 0.4
    h.glide(*h.world_xy((23, 0, 0)))
    yield 0.4
    path = os.path.join(h.out_dir, "f_girar_transferidor.png")     # protractor under the cursor, mid-rotation
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=2)
    h.screenshot(path)
    shots.append(path)
    yield 0.3
    h.type_text("90")
    yield 0.8
    bm = doc.bm
    bm.verts.ensure_lookup_table()
    pts = {v.index for r in selection.get() if r.kind == 'FACE' and r.index < len(bm.faces)
           for v in bm.faces[r.index].verts}
    bm.verts.ensure_lookup_table()
    xs = [bm.verts[i].co.x for i in pts]
    ys = [bm.verts[i].co.y for i in pts]
    h.check("AC-GIR-2 copy turned 90° about (28,0,0): x 22..28, y −8..0",
            pts and abs(min(xs) - 22) < 1e-3 and abs(max(xs) - 28) < 1e-3 and abs(min(ys) + 8) < 1e-3
            and abs(max(ys)) < 1e-3, (min(xs) if xs else None, max(xs) if xs else None,
                                      min(ys) if ys else None, max(ys) if ys else None))
    h.check("Girar keeps the selection (7 faces)", kinds()[0] == 7, kinds())
    yield from shot("f_girar")

    # 10. Escala: corner grip `2` (AC-ESC-1 in the GUI)
    h.move(*h.region_xy(region, 0.85, 0.85))
    h.key('S', unicode='s')
    yield 0.5
    h.check("S activates su.scale", h.state()["tool"] == "su.scale", h.state()["tool"])
    grip = h.world_xy((28, 0, 5))
    h.glide(*grip)
    yield 0.5
    yield from shot("f_escala_alcas")
    h.glide(*grip, steps=1)
    yield 0.3
    h.click(*grip)
    yield 0.4
    h.type_text("2")
    yield 0.8
    bm = doc.bm
    bm.verts.ensure_lookup_table()
    pts = {v.index for r in selection.get() if r.kind == 'FACE' and r.index < len(bm.faces)
           for v in bm.faces[r.index].verts}
    co = [bm.verts[i].co for i in pts]
    ext = (round(max(c.x for c in co) - min(c.x for c in co), 3), round(max(c.y for c in co) - min(c.y for c in co), 3),
           round(max(c.z for c in co) - min(c.z for c in co), 3)) if co else None
    h.check("AC-ESC-1 corner `2` doubles the copy (6×8×5 → 12×16×10)", ext == (12.0, 16.0, 10.0), ext)
    h.check("Escala: faces planar", sum(1 for f in bm.faces if not geom.is_planar(f, 1e-4)) == 0)
    yield from shot("f_escala")

    # 11. Comandos: G = Criar grupo (componente até P1), Informações da entidade, menu de contexto,
    #     Ocultar / Reexibir, Explodir (AF-8 via the menu's operator)
    rv3d.view_location = V((4, 3, 1.5))
    rv3d.view_distance = 24.0
    new_box()
    yield 0.4
    h.move(*h.region_xy(region, 0.85, 0.85))
    h.key('SPACE', unicode=' ')
    yield 0.4
    top = h.world_xy((4, 3, 3))
    h.click(*top)
    h.click(*top)
    h.click(*top)
    yield 0.6
    h.check("triple click → whole box", kinds() == (6, 12, 0), kinds())
    h.key('G', unicode='g')
    yield 0.6
    objs = selection.objects()
    h.check("G → Criar grupo (selection = the new group)", len(objs) == 1 and kinds() == (0, 0, 1), kinds())
    h.check("G hint: components not available yet", h.state()["hint_key"] == "edit.component_is_group",
            h.state()["hint_key"])
    h.check("root emptied into the group", len(doc.bm.faces) == 0, len(doc.bm.faces))
    tray.set_open("entity", True)
    yield 0.4
    yield from shot("f_criar_grupo")
    # right click over the group: A's su.context_menu opens F's SU_MT_context
    h.move(*top)
    yield 0.2
    h.event('RIGHTMOUSE', 'PRESS')
    h.event('RIGHTMOUSE', 'RELEASE')
    yield 0.6
    path = os.path.join(h.out_dir, "f_menu_contexto.png")
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=2)
    h.screenshot(path)
    shots.append(path)
    yield 0.3
    h.key('ESC')
    yield 0.4
    # double click enters the group, Esc leaves it
    h.click(*top)
    h.click(*top)
    yield 0.6
    ec = importlib.import_module(su.__name__ + ".core.edit_context")
    h.check("double click on the group enters it", len(ec.stack()) == 1, [o.name for o in ec.stack()])
    h.key('ESC')
    yield 0.4
    h.check("Esc leaves the group", len(ec.stack()) == 0, [o.name for o in ec.stack()])
    h.click(*top)
    yield 0.5
    with ctx():
        bpy.ops.su.hide()
    yield 0.4
    g = objs[0]
    gname = g.name
    h.check("Ocultar hides the group", g.hide_get(), g.hide_get())
    with ctx():
        bpy.ops.su.unhide_all()
    yield 0.4
    h.check("Reexibir ▸ Tudo shows it again", not g.hide_get(), g.hide_get())
    selection.set([selection.Ref(gname, "OBJECT", 0)])
    with ctx():
        bpy.ops.su.explode()
    yield 0.5
    h.check("Explodir → geometry back in the model", len(doc.bm.faces) == 6 and bpy.data.objects.get(gname) is None,
            len(doc.bm.faces))
    tray.set_open("entity", False)

    # 12. Guides / dimensions (G) with Selecionar + ⌫ and with Apagar
    guides = importlib.import_module(su.__name__ + ".core.guides")
    sel_tool = importlib.import_module(su.__name__ + ".tools.select")
    guides.delete_guides(None)
    gd = guides.data()
    guides.delete_annotations(dims=range(len(gd.dims)), texts=range(len(gd.texts)))
    guides.add_guide_line(V((0, -2, 0)), V((1, 0, 0)))
    guides.add_dimension(V((0, 0, 0)), V((8, 0, 0)), V((0, -4, 0)))
    yield 0.4
    h.move(*h.region_xy(region, 0.85, 0.85))
    h.key('SPACE', unicode=' ')
    yield 0.4
    h.click(*h.world_xy((3, -2, 0)))
    yield 0.5
    h.check("Selecionar picks the guide line", sel_tool.ANNOT == {('GUIDE', 0)}, sel_tool.ANNOT)
    s0 = bpy.context.scene.su_undo_serial
    h.key('BACK_SPACE')
    yield 0.5
    h.check("⌫ deletes the selected guide (1 undo)", guides.count() == 0 and bpy.context.scene.su_undo_serial - s0 == 1,
            (guides.count(), bpy.context.scene.su_undo_serial - s0))
    h.key('E', unicode='e')
    yield 0.4
    h.click(*h.world_xy((4, -4, 0)))
    yield 0.5
    h.check("Apagar erases the dimension under the cursor", len(guides.data().dims) == 0, len(guides.data().dims))

    h.key('SPACE', unicode=' ')
    yield 0.4
    d = h.state()
    h.check("no active object", d["active_object"] is None, d["active_object"])
    h.log("screens:", shots)
