# SPDX-License-Identifier: GPL-2.0-or-later
"""Colour probes (owner: A; targets in tests/sketchup_mode/expected/colors.json). PLANO §8.3.

Empty scene: sky top, horizon, ground, top bar, status bar, tray body. Then a ground rectangle drawn
with Linha (testing.dispatch at the screen projections, real inference): back face colour at its centre
and a black edge. Probes that need a tool not merged yet ("pending") are reported, not failed.
Measured values: <out_dir>/sondas.json. Screenshots: sondas_vazio.png, sondas_retangulo.png."""

import json
import os

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))


def run(h):
    T = h.testing
    base = __import__(h.su.__name__ + ".tools.base", fromlist=["x"])
    spec = json.load(open(os.path.join(os.path.dirname(HERE), "expected", "colors.json"), encoding="utf-8"))
    probes, tol0 = spec["probes"], spec["tolerance"]
    measured = {}

    def check(name, got):
        p = probes[name]
        tol = p.get("tol", tol0)
        measured[name] = {"got": got, "want": p["rgb"], "tol": tol}
        h.check("sonda {:s} {} ≈ {} ±{}".format(name, got, p["rgb"], tol), h.color_close(got, p["rgb"], tol))

    T.reset_model()
    win, area, R = h.area_regions()
    rw, ru = R['WINDOW'], R['UI']
    h.park_mouse()
    yield 0.6
    path = os.path.join(h.out_dir, "sondas_vazio.png")
    h.screenshot(path)
    yield 0.4
    shot = h.load_png(path)

    # horizon: scan the viewport column at 60% width from the top for the first ground-coloured pixel
    x = rw.x + int(rw.width * 0.6)
    ground = probes["ground"]["rgb"]
    y_h = None
    for y in range(rw.y + rw.height - 4, rw.y, -2):
        if h.color_close(h.probe(shot, x, y, 0), ground, 6):
            y_h = y
            break
    check("sky_top", h.probe(shot, x, rw.y + int(rw.height * 0.97)))
    if y_h is not None:
        check("horizon", h.probe(shot, x, y_h + 8))
    else:
        h.check("horizon found", False)
    check("ground", h.probe(shot, rw.x + int(rw.width * 0.6), rw.y + int(rw.height * 0.03)))
    # TOPBAR / STATUSBAR are global areas (not in screen.areas): probe above / below the 3D area
    win_h = shot[1]
    a_top = area.y + area.height
    check("chrome_topbar", h.probe(shot, area.x + int(area.width * 0.9), (a_top + win_h) // 2))
    check("statusbar", h.probe(shot, area.x + int(area.width * 0.6), max(2, area.y // 2)))
    check("tray_body", h.probe(shot, ru.x + int(ru.width * 0.5), ru.y + int(ru.height * 0.15)))

    # ground rectangle with Linha → back face (verso up) and black edges
    from bpy_extras import view3d_utils

    def rxy(co):
        p = view3d_utils.location_3d_to_region_2d(rw, area.spaces.active.region_3d, Vector(co))
        return int(round(p.x)), int(round(p.y))

    base.set_workspace_tool("su.line")
    pts = [(1, 1, 0), (4, 1, 0), (4, 3, 0), (1, 3, 0), (1, 1, 0)]
    for co in pts:
        x, y = rxy(co)
        T.dispatch(T.ev('MOUSEMOVE', 'NOTHING', x, y))
        T.dispatch(T.ev('LEFTMOUSE', 'PRESS', x, y))
        T.dispatch(T.ev('LEFTMOUSE', 'RELEASE', x, y))
        yield 0.4
    st = h.stats()
    h.check("retângulo de Linha: 1 face", st.get("faces") == 1, st)
    h.park_mouse()
    yield 0.6
    path = os.path.join(h.out_dir, "sondas_retangulo.png")
    h.screenshot(path)
    yield 0.4
    shot = h.load_png(path)
    cx, cy = rxy((2.5, 2.0, 0))
    check("face_back", h.probe(shot, rw.x + cx, rw.y + cy))
    # edge: darkest pixel in a small vertical window across the edge y=1 at x=2.5
    ex, ey = rxy((2.5, 1.0, 0))
    darkest = min((h.probe(shot, rw.x + ex, rw.y + ey + dy, 0) for dy in range(-4, 5)), key=sum)
    check("edge", darkest)

    for name, p in probes.items():
        if "pending" in p and p["pending"] not in base.TOOLS:
            measured[name] = {"pending": p["pending"]}
            h.log("sonda pendente", name, "(precisa de", p["pending"] + ")")
    with open(os.path.join(h.out_dir, "sondas.json"), "w", encoding="utf-8") as f:
        json.dump(measured, f, indent=1, ensure_ascii=False)
