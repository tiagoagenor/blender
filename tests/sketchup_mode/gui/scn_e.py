# SPDX-License-Identifier: GPL-2.0-or-later
"""Scenario E (owner: E): drawing tools in the real GUI with simulated input.

Parts (all by default; `shot.sh scn_e:<part>` / SU_SHOT_VARIANT runs one):
  retangulo  R, origin, mouse into +X+Y, `8;6` Enter → floor 8×6 (V4 A4 F1, normal −Z); retype `5;4`
             (Ajustar); standing rectangle (AC-RET-2); Esc leaves nothing; Cmd+Z.
Screenshots: <out_dir>/e_*.png (copied to doc/sketchup_mode/screens/ by hand, reduced with sips)."""

import os

import bpy


def _counts(h):
    st = h.stats()
    return st.get("verts"), (st.get("edges") or 0) - (st.get("bridges") or 0), st.get("logical_faces") or 0


def _settle(h, park=True):
    if park:
        h.park_mouse()
    yield 0.4
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=3)
    yield 0.3


def part_retangulo(h):
    T = h.testing
    T.reset_model()
    s0 = bpy.context.scene.su_undo_serial
    h.glide(*h.world_xy((1.0, 1.0, 0.0)))
    yield 0.3
    h.key('R', unicode='r')
    yield 0.5
    d = h.state()
    h.check("R activates su.rectangle", d["tool"] == "su.rectangle" and d["workspace_tool"] == "su.rectangle",
            (d["tool"], d["workspace_tool"]))
    h.check("hint = primeiro canto", d["hint_key"] == "tool.su.rectangle.hint_start", d["hint_key"])
    h.check("Medidas label = Dimensões", d["vcb_label"] == "Dimensões", d["vcb_label"])
    h.glide(*h.world_xy((0.0, 0.0, 0.0)))
    yield 0.4
    h.check("origin inferred", h.state()["inference"]["kind"] in {"ORIGIN", "ENDPOINT"}, h.state()["inference"])
    h.click()
    yield 0.3
    h.check("first corner: running", h.state()["running"])
    h.glide(*h.world_xy((3.0, 2.0, 0.0)))
    yield 0.4
    d = h.state()
    h.check("live Dimensões value while moving", ";" in d["vcb_value"] or "," in d["vcb_value"], d["vcb_value"])
    yield from _settle(h, park=False)
    h.screenshot(os.path.join(h.out_dir, "e_retangulo_preview.png"))
    yield 0.2
    h.glide(*h.world_xy((3.0, 2.0, 0.0)))
    yield 0.2
    h.type_text("8;6")
    yield 0.6
    st = h.stats()
    h.check("floor: V4 A4 F1", _counts(h) == (4, 4, 1), _counts(h))
    h.check("floor area 48 m²", abs(st.get("area", 0) - 48.0) < 1e-3, st.get("area"))
    h.check("floor normal −Z (back up)", st.get("normals") == [[0.0, 0.0, -1.0]], st.get("normals"))
    h.check("floor bbox (0,0,0)–(8,6,0)", st.get("bbox") == [[0.0, 0.0, 0.0], [8.0, 6.0, 0.0]], st.get("bbox"))
    d = h.state()
    h.check("Medidas shows 8,00m; 6,00m", d["vcb_value"] == "8,00m; 6,00m", d["vcb_value"])
    h.check("1 undo step", bpy.context.scene.su_undo_serial - s0 == 1, bpy.context.scene.su_undo_serial - s0)
    h.check("tool idle after the rectangle", not d["running"])
    yield from _settle(h)
    h.screenshot(os.path.join(h.out_dir, "e_retangulo.png"))
    yield 0.3

    # retype → Ajustar
    s1 = bpy.context.scene.su_undo_serial
    h.type_text("5;4")
    yield 0.6
    st = h.stats()
    h.check("retype 5;4 → 5×4 (Ajustar)", st.get("bbox") == [[0.0, 0.0, 0.0], [5.0, 4.0, 0.0]], st.get("bbox"))
    h.check("Ajustar = 1 undo step", bpy.context.scene.su_undo_serial - s1 == 1)
    h.key('Z', oskey=True)
    yield 0.8
    st = h.stats()
    h.check("Cmd+Z → back to 8×6", st.get("bbox") == [[0.0, 0.0, 0.0], [8.0, 6.0, 0.0]], st.get("bbox"))

    # Esc leaves nothing
    h.glide(*h.world_xy((10.0, 0.0, 0.0)))
    yield 0.3
    h.click()
    yield 0.2
    h.glide(*h.world_xy((12.0, 2.0, 0.0)))
    yield 0.3
    h.key('ESC')
    yield 0.4
    h.check("Esc cancels without garbage", _counts(h) == (4, 4, 1) and not h.state()["running"], _counts(h))

    # standing rectangle (AC-RET-2): from (10,0,0) to the projection of (12,0,3)
    T.reset_model()
    h.glide(*h.world_xy((0.0, 0.0, 0.0)))
    yield 0.4
    h.click()
    yield 0.2
    h.glide(*h.world_xy((2.0, 0.0, 3.0)))
    yield 0.4
    h.click()
    yield 0.5
    st = h.stats()
    bb = st.get("bbox")
    ok = bb is not None and abs(bb[1][1] - bb[0][1]) < 1e-4 and bb[1][2] > 1.0
    h.check("standing rectangle in a vertical plane (AC-RET-2)", ok, bb)
    h.log("standing rectangle bbox", bb, "normals", st.get("normals"))
    yield from _settle(h)
    h.screenshot(os.path.join(h.out_dir, "e_retangulo_em_pe.png"))
    yield 0.3
    d = h.state()
    h.check("no active object", d["active_object"] is None, d["active_object"])
    h.check("single window (no popup)", len(bpy.context.window_manager.windows) == 1)


def _frame_view(h, center, dist):
    win, area, R = h.area_regions()
    rv3d = area.spaces.active.region_3d
    from mathutils import Vector
    rv3d.view_location = Vector(center)
    rv3d.view_distance = dist
    area.tag_redraw()


def _ctrl(h, tool_id):
    import importlib
    base = importlib.import_module(h.su.__name__ + ".tools.base")
    return base.controller(tool_id)


def part_casa(h):
    """ROTEIRO_CASA Parte 1 passos 1, 2, 6, 7, 8, 9 (sem a cumeeira/guias): piso, volume, porta, janela."""
    T = h.testing
    T.reset_model()
    import importlib
    importlib.import_module(h.su.__name__ + ".core.undo").push("undo.init")     # empty model = an undo step
    _frame_view(h, (4.0, 3.0, 1.2), 22.0)
    yield 0.5
    s0 = bpy.context.scene.su_undo_serial
    # passo 1 — piso
    h.glide(*h.world_xy((1.0, 1.0, 0.0)))
    yield 0.3
    h.key('R', unicode='r')
    yield 0.4
    h.glide(*h.world_xy((0.0, 0.0, 0.0)))
    yield 0.4
    h.click()
    yield 0.3
    h.glide(*h.world_xy((3.0, 2.0, 0.0)))
    yield 0.3
    h.type_text("8;6")
    yield 0.6
    h.check("passo 1: piso V4 A4 F1", _counts(h) == (4, 4, 1), _counts(h))
    yield from _settle(h)
    h.screenshot(os.path.join(h.out_dir, "e_casa_passo1.png"))
    yield 0.2

    # passo 2 — volume
    h.glide(*h.world_xy((4.0, 3.0, 0.0)))
    yield 0.3
    h.key('P', unicode='p')
    yield 0.4
    d = h.state()
    h.check("P activates su.pushpull", d["tool"] == "su.pushpull", d["tool"])
    h.check("Medidas label = Distância", d["vcb_label"] == "Distância", d["vcb_label"])
    h.glide(*h.world_xy((4.2, 3.1, 0.0)))
    yield 0.4
    pp = _ctrl(h, "su.pushpull")
    h.check("hover highlights the floor (stipple)", bool(pp.hover_polys), h.state()["inference"])
    yield from _settle(h, park=False)
    h.screenshot(os.path.join(h.out_dir, "e_pushpull_hover.png"))
    yield 0.2
    h.click()
    yield 0.3
    h.check("push/pull running", h.state()["running"])
    h.glide(*h.world_xy((4.2, 3.1, 1.6)))
    yield 0.5
    h.check("live preview: a box", _counts(h) == (8, 12, 6), _counts(h))
    h.log("preview distance", h.state()["vcb_value"])
    yield from _settle(h, park=False)
    h.screenshot(os.path.join(h.out_dir, "e_pushpull_preview.png"))
    yield 0.2
    h.type_text("3")
    yield 0.6
    st = h.stats()
    h.check("passo 2: caixa V8 A12 F6", _counts(h) == (8, 12, 6), _counts(h))
    h.check("caixa 8×6×3", st.get("bbox") == [[0.0, 0.0, 0.0], [8.0, 6.0, 3.0]], st.get("bbox"))
    h.check("Medidas shows 3,00m", h.state()["vcb_value"] == "3,00m", h.state()["vcb_value"])
    h.check("2 undo steps so far", bpy.context.scene.su_undo_serial - s0 == 2, bpy.context.scene.su_undo_serial - s0)
    yield from _settle(h)
    h.screenshot(os.path.join(h.out_dir, "e_pushpull_caixa.png"))
    yield 0.2

    # passo 6 — porta (retângulo na fachada a partir do ponto central da aresta inferior)
    h.glide(*h.world_xy((3.0, 0.0, 0.5)))
    yield 0.3
    h.key('R', unicode='r')
    yield 0.4
    h.glide(*h.world_xy((4.0, 0.0, 0.0)))
    yield 0.5
    inf = h.state()["inference"]
    h.check("ponto central da aresta inferior", inf["kind"] == "MIDPOINT", inf)
    h.click()
    yield 0.3
    h.glide(*h.world_xy((4.6, 0.0, 1.2)))
    yield 0.4
    h.type_text("1;2,1")
    yield 0.6
    h.check("passo 6: porta → V12 A17 F7 (sem cumeeira)", _counts(h) == (12, 17, 7), _counts(h))
    # passo 7 — rebaixo da porta
    h.glide(*h.world_xy((4.5, 0.0, 1.05)))
    yield 0.3
    h.key('P', unicode='p')
    yield 0.4
    h.glide(*h.world_xy((4.55, 0.0, 1.0)))
    yield 0.4
    h.click()
    yield 0.3
    h.glide(*h.world_xy((4.55, 0.4, 1.0)))
    yield 0.4
    h.type_text("0,15")
    yield 0.6
    h.check("passo 7: rebaixo da porta → V16 A24 F10", _counts(h) == (16, 24, 10), _counts(h))
    # passo 8 — janela (sem guias: canto em (1; 0; 0,9) sobre a fachada)
    h.glide(*h.world_xy((1.5, 0.0, 1.5)))
    yield 0.3
    h.key('R', unicode='r')
    yield 0.4
    h.glide(*h.world_xy((1.0, 0.0, 0.9)))
    yield 0.4
    h.click()
    yield 0.3
    h.glide(*h.world_xy((1.6, 0.0, 1.6)))
    yield 0.4
    h.type_text("1,2;1,2")
    yield 0.6
    c8 = _counts(h)
    h.check("passo 8: janela → V20 A28 F11", c8 == (20, 28, 11), c8)
    # passo 9 — rebaixo da janela
    h.glide(*h.world_xy((1.7, 0.0, 1.6)))
    yield 0.3
    h.key('P', unicode='p')
    yield 0.4
    h.glide(*h.world_xy((1.65, 0.0, 1.55)))
    yield 0.4
    h.click()
    yield 0.3
    h.glide(*h.world_xy((1.65, 0.4, 1.55)))
    yield 0.4
    h.type_text("0,1")
    yield 0.6
    h.check("passo 9: rebaixo da janela → V24 A36 F15", _counts(h) == (24, 36, 15), _counts(h))
    st = h.stats()
    h.check("nenhuma face não plana", st.get("non_planar") == 0 and st.get("validate") == [], st.get("validate"))
    h.check("6 undo steps", bpy.context.scene.su_undo_serial - s0 == 6, bpy.context.scene.su_undo_serial - s0)
    yield from _settle(h)
    h.screenshot(os.path.join(h.out_dir, "e_casa_porta_janela.png"))
    yield 0.2
    # Cmd+Z ×6 → empty, Cmd+Shift+Z ×6 → back
    for _i in range(6):
        h.key('Z', oskey=True)
        yield 0.5
    h.check("Cmd+Z ×6 → modelo vazio", _counts(h) == (0, 0, 0), _counts(h))
    for _i in range(6):
        h.key('Z', oskey=True, shift=True)
        yield 0.5
    h.check("Cmd+Shift+Z ×6 → casa de volta", _counts(h) == (24, 36, 15), _counts(h))
    d = h.state()
    h.check("no active object", d["active_object"] is None, d["active_object"])
    h.check("single window (no popup)", len(bpy.context.window_manager.windows) == 1)


def _draw_rect(h, p1, toward, text):
    h.glide(*h.world_xy(p1))
    yield 0.3
    h.key('R', unicode='r')
    yield 0.3
    h.glide(*h.world_xy(p1))
    yield 0.4
    h.click()
    yield 0.2
    h.glide(*h.world_xy(toward))
    yield 0.3
    h.type_text(text)
    yield 0.5


def _pull(h, at, toward, text=None, click_at=None):
    h.key('P', unicode='p')
    yield 0.3
    h.glide(*h.world_xy(at))
    yield 0.4
    h.click()
    yield 0.3
    h.glide(*h.world_xy(toward))
    yield 0.5
    if text is not None:
        h.type_text(text)
    else:
        h.click()
    yield 0.6


def part_encaixe(h):
    """AC-EMP-3 (encaixe no topo de outra caixa), AC-CIR-1/2 (cilindro suave)."""
    T = h.testing
    T.reset_model()
    _frame_view(h, (5.0, 2.0, 1.0), 20.0)
    yield 0.5
    yield from _draw_rect(h, (0.0, 0.0, 0.0), (1.0, 1.0, 0.0), "2;2")
    yield from _pull(h, (1.0, 1.0, 0.0), (1.0, 1.0, 0.5), "1")
    yield from _draw_rect(h, (4.0, 0.0, 0.0), (5.0, 1.0, 0.0), "2;2")
    yield from _pull(h, (5.0, 1.0, 0.0), (5.0, 1.0, 1.0), "2")
    h.check("two boxes", _counts(h) == (16, 24, 12), _counts(h))
    # pull the low box's top while hovering the tall box's top → snaps to its height
    yield from _pull(h, (1.0, 1.2, 1.0), (5.0, 1.2, 2.0))
    import importlib
    doc = importlib.import_module(h.su.__name__ + ".core.document").root()
    zs = [v.co.z for v in doc.bm.verts if v.co.x < 3.0]
    h.check("AC-EMP-3: encaixe → altura 2,000", abs(max(zs) - 2.0) < 1e-4, max(zs))
    yield from _settle(h)
    h.screenshot(os.path.join(h.out_dir, "e_pushpull_encaixe.png"))
    yield 0.2
    # cylinder (12 sides)
    area0 = h.stats().get("area", 0.0)
    h.glide(*h.world_xy((8.0, 1.0, 0.0)))
    yield 0.3
    h.key('C', unicode='c')
    yield 0.3
    h.type_text("12")
    yield 0.3
    h.check("Lados = 12 before the click", h.state()["vcb_value"] == "12", h.state()["vcb_value"])
    h.glide(*h.world_xy((8.0, 1.0, 0.0)))
    yield 0.4
    h.click()
    yield 0.2
    h.glide(*h.world_xy((9.0, 1.0, 0.0)))
    yield 0.3
    h.type_text("1")
    yield 0.5
    st = h.stats()
    h.check("AC-CIR-1: círculo de 12 lados, área 3,0", abs(st.get("area", 0) - area0 - 3.0) < 1e-3,
            st.get("area", 0) - area0)
    yield from _pull(h, (8.3, 1.2, 0.0), (8.3, 1.2, 1.0), "2")
    st = h.stats()
    h.check("AC-CIR-2: laterais suaves (12 arestas su_soft)", st.get("soft") == 12, st.get("soft"))
    yield from _settle(h)
    h.screenshot(os.path.join(h.out_dir, "e_cilindro.png"))
    yield 0.2
    d = h.state()
    h.check("no active object", d["active_object"] is None, d["active_object"])
    h.check("single window (no popup)", len(bpy.context.window_manager.windows) == 1)


PARTS = [("retangulo", part_retangulo), ("casa", part_casa), ("encaixe", part_encaixe)]


def run(h):
    win, area, R = h.area_regions()
    h.check("3D viewport present", area is not None)
    if area is None:
        return
    variant = os.environ.get("SU_SHOT_VARIANT", "")
    for name, fn in PARTS:
        if variant and name != variant:
            continue
        h.log("---- part", name)
        yield from fn(h)
