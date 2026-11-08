# SPDX-License-Identifier: GPL-2.0-or-later
"""PLANO.md §12 — "Teste final de aceite: primeiro dia" (15 passos, CRITICA_R3_SKETCHUP §4), owner A.

Everything goes through the NORMAL input paths with simulated events: shortcut keys and Medidas typed with
the mouse over the viewport (or over the tray / status bar where the step says so), clicks at the screen
projections of 3D points (C's real inference snaps), double/triple clicks, Option/Shift/Cmd, right click
(context menu), MMB / Shift+MMB / wheel (G's su.view_*), Cmd+Z / Cmd+Shift+Z, save + reopen.
Step 4 runs twice: mouse, then trackpad (TRACKPADPAN/TRACKPADZOOM, Ctrl+Cmd drag).

Per step: asserts + screenshot doc/sketchup_mode/screens/dia_passoNN.png (1600 px).
Known gaps are XFAIL (recorded with the reason, not hidden). Summary table: <out_dir>/dia_resumo.json.

Deviations from "literal", each written in the step:
 * the camera is moved by script between work areas (a user orbits/zooms; step 4 tests navigation itself);
 * a colour is picked with su.material_pick (the tray swatch is the same operator; Blender popups/panels
   are not addressable from RNA, so the click on the swatch itself is not simulated);
 * right click › Criar grupo: the menu opening + selection are checked; the item is then run with G
   (same command as the menu item and the toolbar button, PLANO §5.3).
"""

import json
import os
import subprocess
import traceback

import bpy
from mathutils import Vector

CAM_HOUSE = ((17.0, -13.0, 11.0), (4.0, 3.0, 1.4))
CAM_WIDE = ((26.0, -36.0, 26.0), (9.0, -3.0, 0.5))
CAM_ROOF = ((10.0, -20.0, 9.0), (3.0, -10.0, 1.5))
CAM_CYL = ((16.0, -11.0, 5.0), (12.0, -5.0, 0.5))
CYL_CENTER = (12.0, -5.0, 0.0)
PAINT_RECT = (6.0, -13.0, 0.0)            # ground rectangle to paint (corner), right of the roof box


def run(h):
    su = h.su
    imp = lambda m: __import__(su.__name__ + "." + m, fromlist=["x"])
    base, state, units = imp("tools.base"), imp("core.state"), imp("core.units")
    document, selection, guides = imp("core.document"), imp("core.selection"), imp("core.guides")
    materials, tool_ops = imp("core.materials"), imp("ops.tool_ops")
    T, STATE = h.testing, state.STATE
    dec, sep = units.decimal_sep(None), units.list_sep(None)
    root = os.environ.get("SU_ROOT", "")
    screens = os.path.join(root, "doc", "sketchup_mode", "screens")
    results = []
    cur = {}

    # ------------------------------------------------------------------------------------------ helpers
    def num(*v):
        return sep.join("{:g}".format(x).replace(".", dec) for x in v)

    def regions():
        win, area, R = h.area_regions()
        return win, area, R['WINDOW'], R.get('UI'), area.spaces.active.region_3d

    def cam(spec):
        _w, area, _r, _u, rv3d = regions()
        eye, tgt = Vector(spec[0]), Vector(spec[1])
        rv3d.view_perspective = 'PERSP'
        rv3d.view_location = tgt
        rv3d.view_distance = (eye - tgt).length
        rv3d.view_rotation = (tgt - eye).normalized().to_track_quat('-Z', 'Y')
        area.tag_redraw()

    def at(co):
        return h.world_xy(Vector(co))

    def go(co):
        h.glide(*at(co), steps=4)

    def bbox_where(pred):
        """World bbox (min, max) of the root document's vertices satisfying pred(co)."""
        doc = document.root()
        mw = doc.world()
        pts = [mw @ v.co for v in doc.bm.verts if pred(mw @ v.co)]
        if not pts:
            return None
        return (Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)]))

    world = {}                                    # positions produced by earlier steps

    def clicks(n=1, **mods):
        for _i in range(n):
            h.event('LEFTMOUSE', 'PRESS', **mods)
            h.event('LEFTMOUSE', 'RELEASE', **mods)

    def key(k, uni=None, **mods):
        h.key(k, unicode=uni, **mods)

    def letter(ch):
        key(ch.upper() if ch != " " else 'SPACE', ch if ch != " " else None)

    def typ(text):
        h.type_text(text)

    def over_tray():
        _w, _a, _r, ui, _rv = regions()
        h.move(*h.region_xy(ui, 0.5, 0.45))

    def over_status():
        _w, area, _r, _u, _rv = regions()
        h.move(area.x + int(area.width * 0.6), max(2, area.y // 2))

    def st(doc_key=None):
        return h.stats(doc_key)

    def groups():
        return [o for o in bpy.context.scene.objects
                if o.type == 'MESH' and o.su_doc.kind in {'GROUP', 'COMPONENT'} and o.visible_get()]

    def check(name, cond, detail=""):
        cur.setdefault("checks", []).append((name, bool(cond)))
        return h.check("passo {:02d} — {:s}".format(cur["n"], name), cond, detail)

    def xfail(name, reason):
        cur.setdefault("xfail", []).append((name, reason))
        h.log("XFAIL passo", cur["n"], name, "—", reason)

    def tool_is(tid):
        return h.state()["tool"] == tid

    def esc_all():
        for _i in range(2):
            key('ESC')

    def shot(n):
        src = os.path.join(h.out_dir, "dia_passo{:02d}.png".format(n))
        h.park_mouse()
        h.screenshot(src)
        if os.path.isdir(screens):
            subprocess.run(["sips", "-Z", "1600", src, "--out", os.path.join(screens, os.path.basename(src))],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def serial():
        return bpy.context.scene.su_undo_serial

    STEPS = []

    def step(n, title):
        def deco(fn):
            STEPS.append((n, title, fn))
            return fn
        return deco

    # ------------------------------------------------------------------------------------------ 1
    @step(1, "Abrir o modo")
    def s1():
        d = h.state()
        check("uma janela, sem splash/popup", len(bpy.context.window_manager.windows) == 1)
        check("um workspace (sem abas do Blender)", len(bpy.data.workspaces) == 1, [w.name for w in bpy.data.workspaces])
        check("ferramenta Selecionar ativa", d["workspace_tool"] == "su.select" and d["tool"] == "su.select",
              (d["workspace_tool"], d["tool"]))
        hint = d["hint"] or ""
        if not hint:
            sb = imp("ui.statusbar")
            hint = sb.hint_text() if hasattr(sb, "hint_text") else ""
        check("dica com \"Option\"", "Option" in hint, hint)
        check("Medidas vazia", d["vcb_buffer"] == "", d["vcb_buffer"])
        check("modelo vazio", st().get("faces") == 0 and not groups(), st().get("faces"))
        yield 0.2

    # ------------------------------------------------------------------------------------------ 2
    @step(2, "Piso 8×6 (R, origem, 8;6)")
    def s2():
        cam(CAM_HOUSE)
        yield 0.4
        go((1.0, 1.0, 0.0))
        letter("r")
        yield 0.3
        check("R → Retângulo", tool_is("su.rectangle"))
        go((0.0, 0.0, 0.0))
        yield 0.3
        inf = h.state()["inference"]
        check("dica \"Ponto de origem\"", inf["tooltip_key"] == "inf.origin", inf)
        clicks()
        yield 0.3
        go((2.0, 1.5, 0.0))
        yield 0.3
        typ(num(8, 6))
        yield 0.6
        s = st()
        check("retângulo 8×6: 1 face, 48 m²", s["faces"] == 1 and abs(s["area"] - 48) < 1e-3, (s["faces"], s["area"]))
        check("verso para cima (normal −Z)", s["normals"] == [[0.0, 0.0, -1.0]], s["normals"])
        v = h.state()["vcb_value"]
        check("Medidas mostra as dimensões", ("8" + dec + "00") in v and ("6" + dec + "00") in v, v)

    # ------------------------------------------------------------------------------------------ 3
    @step(3, "Volume 3 e redigitar 2,8 (P)")
    def s3():
        go((4.0, 3.0, 0.5))
        letter("p")
        yield 0.3
        check("P → Empurrar/puxar", tool_is("su.pushpull"))
        go((4.0, 3.0, 0.0))
        yield 0.3
        clicks()
        yield 0.3
        go((4.0, 3.0, 1.0))
        yield 0.3
        typ(num(3))
        yield 0.6
        s = st()
        check("caixa 6 faces, altura 3", s["faces"] == 6 and abs(s["bbox"][1][2] - 3) < 1e-4, (s["faces"], s["bbox"]))
        top = [n for n in s["normals"] if n[2] > 0.99]
        check("frentes para fora (topo +Z)", len(top) == 1, s["normals"])
        typ(num(2.8))
        yield 0.6
        s = st()
        check("redigitar 2,8 → altura 2,80", abs(s["bbox"][1][2] - 2.8) < 1e-4, s["bbox"])

    # ------------------------------------------------------------------------------------------ 4
    def nav(trackpad):
        _w, area, region, _u, rv3d = regions()
        p = Vector((4.0, 0.0, 1.4))                       # point on the front wall
        go(p)
        yield 0.3
        x, y = h._mouse
        s0 = at(p)
        rot0 = rv3d.view_rotation.copy()
        if not trackpad:
            h.event('MIDDLEMOUSE', 'PRESS')
            for i in range(1, 9):
                h.move(x + 8 * i, y + 3 * i)
            h.event('MIDDLEMOUSE', 'RELEASE')
        else:
            h.drag('LEFTMOUSE', x, y, 64, 24, ctrl=True, oskey=True)
        yield 0.5
        check(("Ctrl+Cmd+arrastar" if trackpad else "MMB") + " orbita", rv3d.view_rotation.rotation_difference(rot0).angle > 1e-3)
        s1_ = at(p)
        drift = (Vector(s1_) - Vector(s0)).length
        check("pivô = ponto sob o cursor no início (±4 px)", drift <= 4 * bpy.context.preferences.system.pixel_size,
              ("drift px", round(drift, 1)))
        # pan
        loc0 = rv3d.view_location.copy()
        go(p)
        yield 0.2
        x, y = h._mouse
        if not trackpad:
            h.event('MIDDLEMOUSE', 'PRESS', shift=True)
            for i in range(1, 7):
                h.move(x + 10 * i, y)
            h.event('MIDDLEMOUSE', 'RELEASE', shift=True)
        else:
            h.drag('LEFTMOUSE', x, y, 60, 0, ctrl=True, oskey=True, shift=True)
        yield 0.5
        check(("Ctrl+Cmd+Shift+arrastar" if trackpad else "Shift+MMB") + " panorâmica",
              (rv3d.view_location - loc0).length > 1e-4)
        # zoom toward the cursor
        go(p)
        yield 0.3
        s0 = Vector(at(p))
        d0 = rv3d.view_distance
        x, y = h._mouse
        if not trackpad:
            for _i in range(5):
                h.event('WHEELUPMOUSE', 'PRESS')
        else:
            # two fingers = zoom (trackpad mode "sketchup"). event_simulate encodes the gesture delta as
            # (event xy − previous xy): each event is 6 px off the cursor, which goes back in between
            # (a real two-finger gesture does not move the cursor).
            for _i in range(5):
                h.move(x, y)
                h.event('TRACKPADPAN', 'NOTHING', x, y - 6)
            h.move(x, y)
        yield 0.6
        changed = abs(rv3d.view_distance - d0) > 1e-6 or (Vector(at(p)) - s0).length > 0.5
        if trackpad and not changed:
            xfail("trackpad: dois dedos = zoom", "event_simulate não produz o delta (mouse − mouse_prev) do TRACKPADPAN")
        else:
            if trackpad:   # direction = user setting "inverter zoom do trackpad", confirmed with the user (§8.4)
                check("trackpad: dois dedos aplicam zoom", abs(rv3d.view_distance - d0) > 1e-6, (d0, rv3d.view_distance))
            else:
                check("roda aproxima", rv3d.view_distance < d0, (d0, rv3d.view_distance))
            drift = (Vector(at(p)) - s0).length
            check("zoom no cursor: ponto continua sob o cursor (±4 px)",
                  drift <= 4 * bpy.context.preferences.system.pixel_size, ("drift px", round(drift, 1)))
        if not trackpad:
            # double click MMB → recenter the point under the cursor
            go(p)
            yield 0.3
            h.event('MIDDLEMOUSE', 'PRESS')
            h.event('MIDDLEMOUSE', 'RELEASE')
            h.event('MIDDLEMOUSE', 'PRESS')
            h.event('MIDDLEMOUSE', 'RELEASE')
            yield 0.6
            c = Vector((region.x + region.width / 2, region.y + region.height / 2))
            off = (Vector(at(p)) - c).length
            check("duplo clique MMB recentraliza (±10% da região)", off <= 0.1 * region.width, ("px do centro", round(off)))
        # Shift+Z zoom extents
        go(p)
        key('Z', shift=True)
        yield 0.6
        s = st()
        mn, mx = Vector(s["bbox"][0]), Vector(s["bbox"][1])
        corners = [Vector((a, b, c)) for a in (mn.x, mx.x) for b in (mn.y, mx.y) for c in (mn.z, mx.z)]
        inside = all(region.x <= at(k)[0] <= region.x + region.width and region.y <= at(k)[1] <= region.y + region.height
                     for k in corners)
        check("Shift+Z enquadra o modelo", inside)

    @step(4, "Navegar (mouse)")
    def s4():
        esc_all()
        letter(" ")
        yield 0.3
        yield from nav(False)

    @step(41, "Navegar (trackpad)")
    def s4b():
        cam(CAM_HOUSE)
        yield 0.4
        yield from nav(True)

    # ------------------------------------------------------------------------------------------ 5
    @step(5, "Paredes: F 0,15 no topo, P 2,65 para baixo")
    def s5():
        cam(CAM_HOUSE)
        yield 0.4
        go((4.0, 0.6, 2.8))
        letter("f")
        yield 0.3
        check("F → Equidistância", tool_is("su.offset"))
        go((4.0, 0.3, 2.8))
        yield 0.3
        clicks()
        yield 0.3
        go((4.0, 1.0, 2.8))
        yield 0.3
        typ(num(0.15))
        yield 0.6
        s = st()
        check("anel + face interna (7 faces)", s["logical_faces"] == 7, s["logical_faces"])
        go((4.0, 3.0, 2.0))
        letter("p")
        yield 0.3
        go((4.0, 3.0, 2.8))
        yield 0.3
        clicks()
        yield 0.3
        go((4.0, 3.0, 1.8))
        yield 0.3
        typ(num(2.65))
        yield 0.8
        s = st()
        check("cômodo oco: 11 faces, sem faces tortas", s["logical_faces"] == 11 and s["non_planar"] == 0,
              (s["logical_faces"], s["non_planar"]))
        hit = bpy.context.scene.ray_cast(bpy.context.evaluated_depsgraph_get(), Vector((4, 3, 5)), Vector((0, 0, -1)))
        check("piso interno em z = 0,15", hit[0] and abs(hit[1].z - 0.15) < 1e-3, tuple(hit[1]) if hit[0] else None)

    # ------------------------------------------------------------------------------------------ 6
    @step(6, "Porta 0,9×2,1 na aresta inferior e abertura passante")
    def s6():
        b0 = st()["bridges"]                       # the step-5 ring (face with a hole) has CDT bridges
        go((4.0, 0.0, 1.0))
        letter("r")
        yield 0.3
        go((4.0, 0.0, 0.0))
        yield 0.3
        inf = h.state()["inference"]
        check("início no ponto central da aresta inferior", inf["kind"] == "MIDPOINT", inf)
        clicks()
        yield 0.3
        go((4.5, 0.0, 1.0))
        yield 0.3
        typ(num(0.9, 2.1))
        yield 0.6
        s = st()
        check("porta na fachada (+1 face, sem pontes novas)", s["logical_faces"] == 12 and s["bridges"] == b0,
              (s["logical_faces"], b0, s["bridges"]))
        go((4.45, 0.0, 1.0))
        letter("p")
        yield 0.3
        go((4.45, 0.0, 1.05))
        yield 0.3
        clicks()
        yield 0.3
        go((4.45, 0.12, 1.05))
        yield 0.3
        typ(num(0.15))
        yield 0.8
        hit = bpy.context.scene.ray_cast(bpy.context.evaluated_depsgraph_get(), Vector((4.45, -1, 1)), Vector((0, 1, 0)))
        check("abertura passante (raio atinge a parede de trás, y = 5,85)",
              hit[0] and abs(hit[1].y - 5.85) < 1e-3, tuple(hit[1]) if hit[0] else None)
        s = st()
        check("sem faces tortas", s["non_planar"] == 0 and not s.get("validate"), (s["non_planar"], s.get("validate")))

    # ------------------------------------------------------------------------------------------ 7
    @step(7, "Linha com inferência: ponto central, eixo azul, 1")
    def s7():
        go((8.0, 3.0, 1.0))
        letter("l")
        yield 0.3
        e0, b0 = st()["edges"], st()["bridges"]
        go((8.0, 3.0, 0.0))
        yield 0.3
        inf = h.state()["inference"]
        check("\"Ponto central\" da aresta", inf["kind"] == "MIDPOINT", inf)
        clicks()
        yield 0.3
        go((8.0, 3.0, 0.7))
        yield 0.3
        inf = h.state()["inference"]
        check("linha azul (\"No eixo azul\")", inf["linear"] == "AXIS_Z", inf)
        typ(num(1))
        yield 0.5
        key('ESC')
        yield 0.3
        s = st()
        # +2 edges: the line and the half of the bottom edge split at its midpoint
        check("linha visível (aresta nova, não ponte)", s["edges"] == e0 + 2 and s["bridges"] == b0,
              (e0, s["edges"], b0, s["bridges"]))
        check("Esc encerra", not h.state()["running"])

    # ------------------------------------------------------------------------------------------ 8
    @step(8, "Telhado: caixa 4×4×3, cumeeira e Mover 1,5 ↑")
    def s8():
        cam(CAM_ROOF)
        yield 0.4
        f0 = st()["logical_faces"]
        go((1.0, -11.0, 0.0))
        letter("r")
        yield 0.3
        go((0.0, -12.0, 0.0))
        yield 0.3
        inf = h.state()["inference"]
        h.log("passo 8: inferência no 1º clique em (0,-12,0):", inf)
        check("1º clique no chão sob o cursor (±5 cm)", inf["kind"] != "NONE" and
              (Vector(inf["point"]) - Vector((0.0, -12.0, 0.0))).length < 0.05, inf)
        clicks()
        yield 0.3
        go((1.0, -11.0, 0.0))
        yield 0.2
        typ(num(4, 4))
        yield 0.5
        bb = bbox_where(lambda co: co.y < -5.0)
        check("retângulo 4×4", bb is not None and abs((bb[1] - bb[0]).x - 4) < 1e-4 and abs((bb[1] - bb[0]).y - 4) < 1e-4,
              bb)
        if bb is None:
            return
        mn, mx = bb
        c = (mn + mx) / 2
        world["roof"] = (mn.copy(), mx.copy())
        go(c)
        letter("p")
        yield 0.3
        clicks()
        yield 0.3
        go(c + Vector((0.0, 0.0, 1.0)))
        yield 0.2
        typ(num(3))
        yield 0.6
        s = st()
        check("caixa 4×4×3 (+6 faces)", s["logical_faces"] == f0 + 6, (f0, s["logical_faces"]))
        z = 3.0
        ridge_a, ridge_b = Vector((mn.x, c.y, z)), Vector((mx.x, c.y, z))
        go(ridge_a + Vector((0.5, 0.0, 0.0)))
        letter("l")
        yield 0.3
        go(ridge_a)
        yield 0.3
        inf = h.state()["inference"]
        check("ponto central (lado x mínimo)", inf["kind"] == "MIDPOINT" and
              (Vector(inf["point"]) - ridge_a).length < 1e-3, (inf, tuple(ridge_a)))
        clicks()
        yield 0.3
        go(ridge_b)
        yield 0.3
        inf = h.state()["inference"]
        check("ponto central (lado oposto)", inf["kind"] == "MIDPOINT" and
              (Vector(inf["point"]) - ridge_b).length < 1e-3, (inf, tuple(ridge_b)))
        clicks()
        yield 0.5
        if h.state()["running"]:
            key('ESC')
        mid = Vector((c.x, c.y, z))
        sel0 = [(r.doc_key, r.kind, r.index) for r in selection.get()]
        check("nada selecionado antes do Mover", not sel0, sel0[:6])
        go(mid)
        letter("m")
        yield 0.3
        inf = h.state()["inference"]
        clicks()
        yield 0.3
        check("Mover pega a cumeeira (ponto central sob o cursor)", inf["kind"] in {"MIDPOINT", "ON_EDGE"} and
              (Vector(inf["point"]) - mid).length < 1e-3, inf)
        key('UP_ARROW')                            # "↑ ou eixo azul": lock blue (from this camera the
        yield 0.3                                  # point above the ridge projects onto the back edge)
        check("↑ trava o eixo azul", STATE.locks.axis == "AXIS_Z", STATE.locks.axis)
        go(mid + Vector((0.0, -1.0, 1.0)))
        yield 0.3
        typ(num(1.5))
        yield 0.7
        s = st()
        check("2 águas + 2 oitões, nenhuma face torta", s["logical_faces"] == f0 + 7 and s["non_planar"] == 0,
              (f0, s["logical_faces"], s["non_planar"]))
        bb2 = bbox_where(lambda co: co.y < -5.0)
        check("cumeeira a 4,5 m", bb2 is not None and abs(bb2[1].z - 4.5) < 1e-3, bb2)

    # ------------------------------------------------------------------------------------------ 9
    @step(9, "Grupo (clique triplo, botão direito › Criar grupo) e cópias 2x")
    def s9():
        cam(CAM_HOUSE)
        yield 0.4
        go((8.0, 1.5, 1.4))
        letter(" ")
        yield 0.3
        clicks(3)
        yield 0.5
        n_sel = len(selection.get())
        check("clique triplo seleciona a casa inteira", n_sel > 30, n_sel)
        calls = tool_ops.CONTEXT_MENU_CALLS[0]
        h.event('RIGHTMOUSE', 'PRESS')
        h.event('RIGHTMOUSE', 'RELEASE')
        yield 0.5
        check("botão direito abre o menu de contexto", tool_ops.CONTEXT_MENU_CALLS[0] == calls + 1)
        check("a seleção fica (clicou numa entidade selecionada)", len(selection.get()) == n_sel, len(selection.get()))
        key('ESC')
        yield 0.3
        go((8.0, 1.5, 1.4))
        letter("g")                               # = item "Criar grupo" do menu (PLANO §5.3)
        yield 0.6
        gs = groups()
        check("grupo criado", len(gs) == 1, [g.name for g in gs])
        cam(CAM_WIDE)
        yield 0.4
        go((8.0, 0.0, 2.8))
        letter("m")
        yield 0.3
        clicks()
        yield 0.3
        key('LEFT_ALT')                            # Option: cópia
        yield 0.2
        go((12.0, 0.0, 2.8))
        yield 0.3
        typ(num(10))
        yield 0.6
        typ("2x")
        yield 0.8
        gs = groups()
        check("3 casas", len(gs) == 3, [g.name for g in gs])
        xs = sorted(round(g.matrix_world.translation.x, 3) for g in gs)
        check("cópias a 10 m no eixo vermelho", xs == [0.0, 10.0, 20.0], xs)
        objs = [r for r in selection.get() if r.kind == 'OBJECT']
        last = max(gs, key=lambda g: g.matrix_world.translation.x) if gs else None
        check("seleção = última cópia", last is not None and any(r.doc_key == last.name for r in objs),
              ([(r.doc_key, r.kind) for r in list(selection.get())[:4]], last.name if last else None))
        # a line touching a group does not stick to it
        e_root = st()["edges"]
        e_grp = st(last.name)["edges"] if last is not None else None
        go((20.0, -2.0, 0.0))
        letter("l")
        yield 0.3
        clicks()
        yield 0.3
        go((20.0, 0.0, 0.0))
        yield 0.3
        clicks()
        yield 0.4
        key('ESC')
        yield 0.3
        check("linha encostada no grupo não gruda", st()["edges"] == e_root + 1 and
              (last is None or st(last.name)["edges"] == e_grp), (e_root, st()["edges"], e_grp))

    # ------------------------------------------------------------------------------------------ 10
    @step(10, "Girar a cópia 90°")
    def s10():
        gs = groups()
        last = max(gs, key=lambda g: g.matrix_world.translation.x) if gs else None
        if last is None:
            check("há uma cópia", False)
            return
        letter(" ")
        go((24.0, 3.0, 1.4))
        yield 0.2
        clicks()                                   # select the copy (group)
        yield 0.4
        go((24.0, 3.0, 1.4))
        letter("q")
        yield 0.3
        check("Q → Girar", tool_is("su.rotate"))
        c = last.matrix_world.translation.copy()
        go(c)
        yield 0.3
        clicks()
        yield 0.3
        go(c + Vector((2.0, 0.0, 0.0)))
        yield 0.3
        clicks()
        yield 0.3
        go(c + Vector((1.0, 1.0, 0.0)))
        yield 0.3
        typ(num(90))
        yield 0.7
        rz = round(abs(last.matrix_world.to_euler().z) * 57.29578, 2)
        check("a cópia gira 90°", abs(rz - 90.0) < 0.05, rz)

    # ------------------------------------------------------------------------------------------ 11
    @step(11, "Cilindro: C 0,4, P 1, superfície")
    def s11():
        cam(CAM_CYL)
        yield 0.4
        ctr = Vector(CYL_CENTER)
        go(ctr + Vector((1, 0, 0)))
        letter("c")
        yield 0.3
        check("C → Círculo", tool_is("su.circle"))
        go(ctr)
        yield 0.3
        clicks()
        yield 0.3
        go(ctr + Vector((0.5, 0.0, 0.0)))
        yield 0.3
        typ(num(0.4))
        yield 0.6
        s0 = st()
        check("círculo: +1 face", s0["faces"] > 0, s0["faces"])
        go(ctr)
        letter("p")
        yield 0.3
        clicks()
        yield 0.3
        go(ctr + Vector((0.0, 0.0, 0.6)))
        yield 0.3
        typ(num(1))
        yield 0.7
        s = st()
        check("laterais suaves (arestas su_soft)", s["soft"] >= 12, s["soft"])
        check("cilindro: 1 superfície lateral + topo", s["surfaces"] == s0["surfaces"] + 2,
              (s0["surfaces"], s["surfaces"]))
        letter(" ")
        go(ctr + Vector((0.0, -0.4, 0.5)))
        yield 0.3
        clicks()
        yield 0.4
        faces = [r for r in selection.get() if r.kind == 'FACE']
        check("clique na lateral seleciona a superfície inteira", len(faces) >= 12, len(faces))

    # ------------------------------------------------------------------------------------------ 12
    @step(12, "Pintura: parede e retângulo no chão (verso)")
    def s12():
        cam(CAM_ROOF)
        yield 0.4
        a = Vector(PAINT_RECT)
        go(a + Vector((1, 1, 0)))
        letter("r")
        yield 0.3
        go(a)
        yield 0.2
        clicks()
        yield 0.3
        go(a + Vector((1.0, 1.0, 0.0)))
        yield 0.2
        typ(num(3, 3))
        yield 0.6
        bb = bbox_where(lambda co: a.x - 0.5 < co.x < a.x + 3.5 and a.y - 0.5 < co.y < a.y + 3.5 and co.z < 1e-4)
        check("retângulo 3×3 no chão", bb is not None and abs((bb[1] - bb[0]).x - 3) < 1e-4, bb)
        if bb is None or "roof" not in world:
            return
        rc = (bb[0] + bb[1]) / 2
        world["paint_rect"] = rc.copy()
        rmn, rmx = world["roof"]
        wall = Vector(((rmn.x + rmx.x) / 2, rmn.y, 1.0))       # front wall of the roof box (normal −Y)
        go(rc)
        letter("b")
        yield 0.3
        check("B → Pintura", tool_is("su.paint"))
        mat = materials.palette_material(3)
        win, area, region, _u, _rv = regions()
        with bpy.context.temp_override(window=win, area=area, region=region):
            bpy.ops.su.material_pick(name=mat.name)      # = swatch of the Materiais tray section
        yield 0.3
        go(rc)
        yield 0.3
        clicks()                                    # ground rectangle, back side up
        yield 0.4
        go(wall)
        yield 0.3
        clicks()
        yield 0.5
        doc = document.root()
        bm = doc.bm
        bm.faces.ensure_lookup_table()

        def face_at(co, n):
            best, dbest = None, None
            for f in bm.faces:
                if f.normal.dot(Vector(n)) > 0.99 and abs((Vector(co) - f.calc_center_median()).dot(f.normal)) < 1e-3:
                    d = (f.calc_center_median() - Vector(co)).length
                    if best is None or d < dbest:
                        best, dbest = f, d
            return best

        def mat_name(f, side):
            if f is None:
                return None
            m = materials.material_of(doc, f.index, side)
            return m.name if m is not None else None
        fr = face_at(rc, (0, 0, -1))
        fw = face_at(wall, (0, -1, 0))
        check("retângulo no chão pintado no verso", mat_name(fr, -1) == mat.name, mat_name(fr, -1))
        check("parede pintada na frente", mat_name(fw, 1) == mat.name, mat_name(fw, 1))
        h.park_mouse()
        yield 0.6
        path = os.path.join(h.out_dir, "dia_tinta.png")
        h.screenshot(path)
        yield 0.3
        img = h.load_png(path)
        got = h.probe(img, *at(rc))
        rgb = dict(materials.palette_rgb()).get(mat.name)
        want = list(rgb) if rgb else None
        check("verso pintado na cor, sem tom azul (±16)", want is not None and h.color_close(got, want, 16), (got, want))

    # ------------------------------------------------------------------------------------------ 13
    @step(13, "Fita métrica (guia a 1 m, \"Na linha\") e Dimensões 8,00m")
    def s13():
        if "roof" not in world:
            check("caixa do passo 8", False)
            return
        rmn, rmx = world["roof"]
        n0 = guides.count()
        e_mid = Vector(((rmn.x + rmx.x) / 2 + 0.7, rmn.y, 0.0))      # on the front bottom edge
        go(e_mid + Vector((0, -0.5, 0)))
        letter("t")
        yield 0.3
        go(e_mid)
        yield 0.3
        inf = h.state()["inference"]
        check("Fita começa na aresta", inf["kind"] in {"ON_EDGE", "MIDPOINT"}, inf)
        clicks()
        yield 0.3
        go(e_mid + Vector((0.0, -0.6, 0.0)))
        yield 0.3
        typ(num(1))
        yield 0.6
        check("guia criada", guides.count() == n0 + 1, (n0, guides.count()))
        go(Vector((rmn.x - 1.0, rmn.y - 1.6, 0.0)))
        letter("l")
        yield 0.3
        go(Vector((rmn.x - 1.0, rmn.y - 1.0, 0.0)))
        yield 0.4
        inf = h.state()["inference"]
        check("a Linha mostra \"Na linha\" sobre a guia (y = aresta − 1)", inf["kind"] == "ON_GUIDE", inf)
        key('ESC')
        cam(CAM_HOUSE)
        yield 0.4
        d = guides.data()
        nd0 = len(d.dims) if d is not None else 0
        go((4.0, 0.0, 3.5))
        if "su.dimension" not in base.TOOLS:
            check("ferramenta Dimensões", False, "su.dimension não registrada")
            return
        base.set_workspace_tool("su.dimension")   # (sem atalho no SketchUp)
        yield 0.3
        go((0.0, 0.0, 2.8))
        yield 0.3
        clicks()
        yield 0.3
        go((8.0, 0.0, 2.8))
        yield 0.3
        clicks()
        yield 0.3
        go((4.0, -1.0, 3.4))
        yield 0.3
        clicks()
        yield 0.5
        d = guides.data()
        ok = d is not None and len(d.dims) == nd0 + 1
        txt = guides.dimension_text(len(d.dims) - 1) if ok else None
        check("cota da aresta de 8 m = \"8" + dec + "00m\"", ok and txt == "8" + dec + "00m", txt)
        if not ok:
            return
        # AC-DIM-3: the text is drawn (white box + dark glyphs) facing the screen, before and after orbiting
        annotations = imp("draw.annotations")
        from types import SimpleNamespace
        dm = d.dims[len(d.dims) - 1]

        def text_visible(tag):
            _w, _a, region, _u, rv3d = regions()
            parts = annotations.dimension_screen(SimpleNamespace(region=region, rv3d=rv3d), dm.a, dm.b, dm.offset)
            if parts is None:
                return False, "fora da tela"
            mid = parts[2]
            path = os.path.join(h.out_dir, "dia_cota_{:s}.png".format(tag))
            h.screenshot(path)
            img = h.load_png(path)
            px = [h.probe(img, region.x + int(mid.x) + dx, region.y + int(mid.y) + dy, 0)
                  for dx in range(-40, 41, 2) for dy in range(-14, 15, 2)]
            light = sum(1 for c in px if min(c) >= 235)
            dark = sum(1 for c in px if max(c) <= 90)
            return light > 20 and dark > 3, {"claros": light, "escuros": dark, "desenhadas": annotations.last_drawn()}
        h.park_mouse()
        yield 0.5
        ok1, info1 = text_visible("antes")
        yield 0.2
        check("texto da cota desenhado (fundo branco + texto escuro)", ok1, info1)
        _w, area, region, _u, rv3d = regions()
        h.drag('MIDDLEMOUSE', region.x + region.width // 2, region.y + region.height // 2, 90, 30)
        yield 0.5
        h.park_mouse()
        yield 0.5
        ok2, info2 = text_visible("orbitado")
        yield 0.2
        check("texto legível depois de orbitar (AC-DIM-3)", ok2, info2)

    # ------------------------------------------------------------------------------------------ 14
    @step(14, "Teclado em qualquer lugar (Bandeja, barra de status, ⌫)")
    def s14():
        esc_all()
        over_tray()
        yield 0.3
        for ch, tid in (("l", "su.line"), ("r", "su.rectangle"), (" ", "su.select")):
            letter(ch)
            yield 0.4
            check("sobre a Bandeja: {!r} → {:s}".format(ch, tid), tool_is(tid), h.state()["tool"])
        cam(CAM_ROOF)
        yield 0.4
        if "paint_rect" not in world:
            check("retângulo do passo 12", False)
            return
        f = world["paint_rect"]
        go(f)
        letter("p")
        yield 0.3
        clicks()
        yield 0.3
        go(f + Vector((0, 0, 0.5)))
        yield 0.3
        typ(num(0.5))
        yield 0.6
        over_status()
        yield 0.3
        typ(num(1))
        yield 0.7
        hit = bpy.context.scene.ray_cast(bpy.context.evaluated_depsgraph_get(), f + Vector((0, 0, 5)), Vector((0, 0, -1)))
        check("sobre a barra de status: 1 Enter redigita (altura 1)", hit[0] and abs(hit[1].z - 1.0) < 1e-3,
              tuple(hit[1]) if hit[0] else None)
        go(f + Vector((0.0, 0.0, 1.0)))
        letter(" ")
        yield 0.3
        clicks()
        yield 0.4
        n = len(selection.get())
        typ_no_enter = "2"
        key('TWO', typ_no_enter)
        yield 0.2
        check("Medidas recebe \"2\"", h.state()["vcb_buffer"] == "2", h.state()["vcb_buffer"])
        key('BACK_SPACE')
        yield 0.3
        check("⌫ apaga o dígito e não exclui a seleção", h.state()["vcb_buffer"] == "" and len(selection.get()) == n > 0,
              (h.state()["vcb_buffer"], n, len(selection.get())))

    # ------------------------------------------------------------------------------------------ 15
    @step(15, "Apagar, desfazer/refazer com seleção, salvar e reabrir")
    def s15():
        cam(CAM_HOUSE)
        yield 0.4
        gs = groups()
        house = min(gs, key=lambda g: g.matrix_world.translation.x) if gs else None
        letter(" ")
        go((8.0, 1.5, 1.4))
        yield 0.3
        clicks(2)                                  # double click: enter the group
        yield 0.5
        ec = h.state()["context"]
        check("duplo clique entra no grupo", house is not None and house.name in ec, ec)
        e0 = st(house.name)["edges"] if house is not None else None
        go((8.0, 3.0, 0.5))
        letter("e")
        yield 0.3
        check("E → Apagar", tool_is("su.eraser"))
        clicks()
        yield 0.5
        e1 = st(house.name)["edges"] if house is not None else None
        # −2: the line, and the bottom edge is whole again (collinear halves merged)
        check("a linha do passo 7 some (aresta de baixo volta a ser inteira)", e0 is not None and e1 == e0 - 2, (e0, e1))
        letter(" ")
        key('ESC')
        key('ESC')
        yield 0.4
        # undo everything, then redo everything; the selection comes back
        sel_end = sorted((r.doc_key, r.kind, r.index) for r in selection.get())
        vis_end = (st()["faces"], len(groups()))
        steps_n = serial() - cur["serial0"]
        h.move(*at((4.0, 3.0, 1.0)))
        for _i in range(steps_n):
            key('Z', oskey=True)
            yield 0.15
        yield 0.6
        check("Cmd+Z até o vazio", st().get("faces") == 0 and not groups(), (st().get("faces"), len(groups()), serial()))
        for _i in range(steps_n):
            key('Z', oskey=True, shift=True)
            yield 0.15
        yield 0.8
        check("Cmd+Shift+Z refaz tudo", (st()["faces"], len(groups())) == vis_end, ((st()["faces"], len(groups())), vis_end))
        sel_now = sorted((r.doc_key, r.kind, r.index) for r in selection.get())
        check("a seleção volta", sel_now == sel_end, (len(sel_now), len(sel_end)))
        # save, close (read the empty template), reopen
        path = os.path.join(os.environ.get("TMPDIR", bpy.app.tempdir), "primeiro_dia.blend")
        before = (st()["faces"], st()["edges"], len(groups()), h.state()["tool"])
        win = h.window()
        with bpy.context.temp_override(window=win):
            bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=False)
        yield 0.5
        with bpy.context.temp_override(window=h.window()):
            bpy.ops.wm.read_homefile(app_template="SketchUp_Mode")
        yield h.until(lambda: bpy.app.driver_namespace.get("su_ready"), 30.0, "su_ready após Novo")
        check("fechar (Novo): modelo vazio", st().get("faces") == 0)
        with bpy.context.temp_override(window=h.window()):
            bpy.ops.wm.open_mainfile(filepath=path)
        yield h.until(lambda: bpy.app.driver_namespace.get("su_ready"), 30.0, "su_ready após Abrir")
        yield 0.6
        after = (st()["faces"], st()["edges"], len(groups()), h.state()["tool"])
        check("reabrir: mesmo modelo e mesma ferramenta", after == before, (before, after))
        check("sem objeto ativo", h.state()["active_object"] is None)

    # ------------------------------------------------------------------------------------------ driver
    cur["serial0"] = serial()
    for n, title, fn in STEPS:
        cur.clear()
        cur.update(n=n, serial0=results[0]["serial0"] if results else serial())
        nfail0 = sum(1 for c in h.checks if not c["ok"])
        try:
            yield from fn()
        except Exception:
            h.check("passo {:02d} — sem exceção".format(n), False, traceback.format_exc()[-800:])
        yield 0.3
        shot(n)
        yield 0.3
        fails = [nm for nm, ok in cur.get("checks", []) if not ok]
        crashed = sum(1 for c in h.checks if not c["ok"]) - nfail0 > len(fails)
        status = "FAIL" if fails or crashed else ("PASS (XFAIL parcial)" if cur.get("xfail") else "PASS")
        results.append({"passo": n, "titulo": title, "status": status, "falhas": fails,
                        "xfail": cur.get("xfail", []), "serial0": cur["serial0"]})
        h.log("PASSO", n, status, fails, cur.get("xfail", []))
    with open(os.path.join(h.out_dir, "dia_resumo.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, ensure_ascii=False)
