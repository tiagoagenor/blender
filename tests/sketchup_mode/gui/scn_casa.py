# SPDX-License-Identifier: GPL-2.0-or-later
"""ROTEIRO_CASA.md Parte 1 — "primeira casa" (owner: A; the tools are E/F/G's).

Each step drives the REAL dispatcher with testing.dispatch at the screen projection of the 3D points of
the script (so the real inference of C snaps: "Ponto de origem", "Ponto central", eixos...), types the
Measurements values through vcb.feed, then checks V/A/F (A = visible edges, no su_bridge; F = logical
faces), validate() and planarity, and takes a screenshot:
    <out_dir>/casa_passoN.png  and  doc/sketchup_mode/screens/casa_passoN.png (1600 px, for the phone).
A step whose tool is not registered yet fails with "tool not registered" and the run stops there
(later steps depend on its geometry); step 5 (guides) does not change the geometry, so a missing Fita
métrica only fails that step. Step 11 = Cmd+Z down to the empty model and Cmd+Shift+Z back.
Summary: <out_dir>/casa_resumo.json. Expected to pass step by step as E (Retângulo, Empurrar/puxar),
F (Mover) and G (Fita métrica) land.
"""

import json
import os
import subprocess

import bpy
from mathutils import Vector


class Missing(Exception):
    pass


def run(h):
    T = h.testing
    su = h.su
    base = __import__(su.__name__ + ".tools.base", fromlist=["x"])
    units = __import__(su.__name__ + ".core.units", fromlist=["x"])
    dec, sep = units.decimal_sep(None), units.list_sep(None)
    root = os.environ.get("SU_ROOT", "")
    screens = os.path.join(root, "doc", "sketchup_mode", "screens") if root else ""
    summary = []

    def num(*vals):
        return sep.join(("{:g}".format(v)).replace(".", dec) for v in vals)

    def rxy(co):
        win, area, R = h.area_regions()
        from bpy_extras import view3d_utils
        p = view3d_utils.location_3d_to_region_2d(R['WINDOW'], area.spaces.active.region_3d, Vector(co))
        return int(round(p.x)), int(round(p.y))

    def move(co):
        x, y = rxy(co)
        T.dispatch(T.ev('MOUSEMOVE', 'NOTHING', x, y))

    def click(co):
        x, y = rxy(co)
        T.dispatch(T.ev('MOUSEMOVE', 'NOTHING', x, y))
        T.dispatch(T.ev('LEFTMOUSE', 'PRESS', x, y))
        T.dispatch(T.ev('LEFTMOUSE', 'RELEASE', x, y))

    def use(tool_id):
        if tool_id not in base.TOOLS:
            raise Missing(tool_id)
        base.set_workspace_tool(tool_id)

    def counts():
        st = h.stats()
        if not st.get("ok"):
            return None, st
        return (st["verts"], st["edges"] - st["bridges"], st["logical_faces"]), st

    def shot(n):
        h.park_mouse()
        src = os.path.join(h.out_dir, "casa_passo{:d}.png".format(n))
        h.screenshot(src)
        if screens and os.path.isdir(screens):
            subprocess.run(["sips", "-Z", "1600", src, "--out", os.path.join(screens, os.path.basename(src))],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def finish_step(n, name, expect, extra=None):
        c, st = counts()
        ok = c == expect and st.get("non_planar") == 0 and not st.get("validate")
        detail = {"VAF": c, "esperado": expect, "non_planar": st.get("non_planar"), "validate": st.get("validate")}
        if extra is not None:
            ok_extra, info = extra(st)
            ok = ok and ok_extra
            detail["extra"] = info
        h.check("passo {:d} — {:s}".format(n, name), ok, detail)
        summary.append({"passo": n, "nome": name, "ok": ok, **detail})
        return ok

    def missing(n, name, tid):
        h.check("passo {:d} — {:s}".format(n, name), False, "tool not registered yet: " + tid)
        summary.append({"passo": n, "nome": name, "ok": False, "faltando": tid})

    # ---------------------------------------------------------------------------------------- 0
    T.reset_model()
    yield 0.5
    s0 = bpy.context.scene.su_undo_serial
    states = []                                  # (serial, VAF) after each geometric step
    ok = finish_step(0, "modelo vazio", (0, 0, 0))
    states.append((bpy.context.scene.su_undo_serial, counts()[0]))
    shot(0)
    yield 0.4

    steps = []

    def step(n, name, expect, extra=None, geometric=True):
        def deco(fn):
            steps.append((n, name, expect, extra, geometric, fn))
            return fn
        return deco

    @step(1, "piso 8×6 (Retângulo)", (4, 4, 1),
          lambda st: (abs(st["area"] - 48.0) < 1e-3 and st["normals"] == [[0.0, 0.0, -1.0]],
                      (st["area"], st["normals"])))
    def _1():
        use("su.rectangle")
        move((0, 0, 0))
        yield 0.2
        click((0, 0, 0))
        yield 0.4
        move((2.0, 1.5, 0))
        yield 0.2
        T.type_text(num(8, 6))

    @step(2, "volume 3 m (Empurrar/puxar)", (8, 12, 6),
          lambda st: (st["bbox"] == [[0.0, 0.0, 0.0], [8.0, 6.0, 3.0]], st["bbox"]))
    def _2():
        use("su.pushpull")
        move((4, 3, 0))
        yield 0.2
        click((4, 3, 0))
        yield 0.4
        move((4, 3, 1.0))
        yield 0.2
        T.type_text(num(3))

    @step(3, "cumeeira (Linha entre pontos centrais)", (10, 15, 7))
    def _3():
        use("su.line")
        move((0, 3, 3))
        yield 0.2
        click((0, 3, 3))
        yield 0.4
        move((8, 3, 3))
        yield 0.2
        click((8, 3, 3))
        yield 0.4
        if base.DISPATCH.running:
            T.dispatch(T.ev('ESC', 'PRESS'))

    @step(4, "telhado: Mover a cumeeira 2 m no azul", (10, 15, 7),
          lambda st: (abs(st["bbox"][1][2] - 5.0) < 1e-4, st["bbox"]))
    def _4():
        use("su.move")
        move((4, 3, 3))
        yield 0.2
        click((4, 3, 3))
        yield 0.4
        move((4, 3, 4))
        yield 0.2
        T.type_text(num(2))

    @step(5, "guias da janela (Fita métrica)", (10, 15, 7), geometric=False)
    def _5():
        use("su.tape")
        click((0, 0, 1.5))
        yield 0.4
        move((0.5, 0, 1.5))
        yield 0.2
        T.type_text(num(1))
        yield 0.4
        click((3, 0, 0))
        yield 0.4
        move((3, 0, 0.5))
        yield 0.2
        T.type_text(num(0.9))

    @step(6, "porta 1×2,1 na fachada (Retângulo)", (14, 20, 8))
    def _6():
        use("su.rectangle")
        move((4, 0, 0))
        yield 0.2
        click((4, 0, 0))
        yield 0.4
        move((4.6, 0, 1.0))
        yield 0.2
        T.type_text(num(1, 2.1))

    @step(7, "rebaixo da porta 0,15 (Empurrar/puxar)", (18, 27, 11))
    def _7():
        use("su.pushpull")
        move((4.5, 0, 1.0))
        yield 0.2
        click((4.5, 0, 1.0))
        yield 0.4
        move((4.5, 0.3, 1.0))
        yield 0.2
        T.type_text(num(0.15))

    @step(8, "janela 1,2×1,2 (Retângulo na interseção das guias)", (22, 31, 12))
    def _8():
        use("su.rectangle")
        move((1, 0, 0.9))
        yield 0.2
        click((1, 0, 0.9))
        yield 0.4
        move((1.6, 0, 1.5))
        yield 0.2
        T.type_text(num(1.2, 1.2))

    @step(9, "rebaixo da janela 0,1 (Empurrar/puxar)", (26, 39, 16))
    def _9():
        use("su.pushpull")
        move((1.6, 0, 1.5))
        yield 0.2
        click((1.6, 0, 1.5))
        yield 0.4
        move((1.6, 0.3, 1.5))
        yield 0.2
        T.type_text(num(0.1))

    stopped = False
    for n, name, expect, extra, geometric, fn in steps:
        if stopped:
            break
        try:
            yield from fn()
        except Missing as ex:
            missing(n, name, str(ex))
            if geometric:
                stopped = True
            continue
        yield 0.6
        ok = finish_step(n, name, expect, extra)
        shot(n)
        yield 0.4
        if geometric:
            states.append((bpy.context.scene.su_undo_serial, counts()[0]))
            if not ok:
                stopped = True

    # ---------------------------------------------------------------------------------------- 11
    if not stopped and len(states) > 1:
        win, area, R = h.area_regions()
        n_steps = bpy.context.scene.su_undo_serial - s0
        seen = []
        for _i in range(n_steps):
            with bpy.context.temp_override(window=win, area=area):
                bpy.ops.ed.undo()
            yield 0.3
            seen.append(counts()[0])
        # every earlier step state must appear, newest first, in the undo sequence
        want = [vaf for _serial, vaf in reversed(states[:-1])]
        it = iter(seen)
        back = all(any(v == w for v in it) for w in want)
        h.check("passo 11 — Cmd+Z até o vazio passa por cada estado", back and counts()[0] == (0, 0, 0),
                {"visto": seen, "esperado (ordem)": want})
        for _i in range(n_steps):
            with bpy.context.temp_override(window=win, area=area):
                bpy.ops.ed.redo()
            yield 0.3
        h.check("passo 11 — Cmd+Shift+Z volta ao fim", counts()[0] == states[-1][1], (counts()[0], states[-1]))
        summary.append({"passo": 11, "nome": "desfazer/refazer", "ok": counts()[0] == states[-1][1]})
        shot(11)
        yield 0.4

    d = h.state()
    h.check("sem objeto ativo", d["active_object"] is None, d["active_object"])
    h.check("uma janela (sem popup)", len(bpy.context.window_manager.windows) == 1)
    with open(os.path.join(h.out_dir, "casa_resumo.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, ensure_ascii=False)
