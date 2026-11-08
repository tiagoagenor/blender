# SPDX-License-Identifier: GPL-2.0-or-later
"""Scenario B (owner: B): the geometry kernel inside the running app — "Apagar uma face"
(doc/sketchup_mode/ROTEIRO_CASA.md AF-1, AF-2, AF-3, AF-4, AF-6 kernel parts) through the real
Document (to_mesh, events, memfile undo). Tools/selection (double click, Delete key, context menu)
belong to F. Screenshots: <out_dir>/b_*.png (the edges overlay is switched on here because the
edge renderer of D may not exist yet)."""

import math
import os

import bpy
from mathutils import Euler, Vector

V = Vector


def run(h):
    su = h.su
    import importlib
    document = importlib.import_module(su.__name__ + ".core.document")
    geom = importlib.import_module(su.__name__ + ".core.geom")

    win, area, R = h.area_regions()
    h.check("3D viewport present", area is not None)
    if area is None:
        return
    region = R['WINDOW']
    space = area.spaces.active
    rv3d = space.region_3d

    def ctx():
        return bpy.context.temp_override(window=win, area=area, region=region)

    # scenario-local display: only our document, edges visible, no culling (see inside the box)
    for obj in bpy.context.scene.objects:
        if not (obj.type == 'MESH' and obj.su_doc.kind == document.KIND_MODEL):
            obj.hide_viewport = True
    space.overlay.show_wireframes = True
    space.overlay.wireframe_threshold = 1.0
    space.shading.show_backface_culling = False

    doc = document.root()
    h.check("root 'Modelo' exists", doc is not None and doc.obj is not None)
    geom.erase_edges(doc.bm, list(doc.bm.edges))
    with ctx():
        doc.write(undo_key="undo.init")

    def counts():
        bm = doc.bm
        lay = geom.layers(bm)
        return (len(bm.verts), sum(1 for e in bm.edges if not e[lay.bridge]), len(bm.faces))

    def look(center, dist):
        rv3d.view_location = V(center)
        rv3d.view_distance = dist
        rv3d.view_rotation = Euler((math.radians(62), 0.0, math.radians(-35)), 'XYZ').to_quaternion()
        rv3d.view_perspective = 'PERSP'
        area.tag_redraw()

    shots = []

    def shot(name):
        path = os.path.join(h.out_dir, name + ".png")
        h.park_mouse()
        area.tag_redraw()
        yield 0.4
        h.screenshot(path)
        yield 0.3
        h.check("screenshot " + name, os.path.isfile(path), path)
        shots.append(path)

    def find_face(center):
        for f in doc.bm.faces:
            if (f.calc_center_median() - V(center)).length < 1e-4:
                return f
        return None

    def find_edge(a, b):
        for e in doc.bm.edges:
            p, q = e.verts[0].co, e.verts[1].co
            if {tuple(round(c, 5) for c in p), tuple(round(c, 5) for c in q)} == \
                    {tuple(map(float, a)), tuple(map(float, b))}:
                return e
        return None

    # --- AF-1: rectangle 8×6 on the ground, erase the face → 4 edges stay
    pts = [V((0, 0, 0)), V((8, 0, 0)), V((8, 6, 0)), V((0, 6, 0))]
    geom.add_polyline(doc.bm, pts, True)
    with ctx():
        doc.write(undo_key="undo.adjust")
    h.check("AF-1 rectangle: V4 A4 F1", counts() == (4, 4, 1), counts())
    look((4, 3, 0), 18)
    yield from shot("b_retangulo")
    geom.erase_faces(doc.bm, list(doc.bm.faces))
    with ctx():
        doc.write(undo_key="undo.adjust")
    h.check("AF-1 erase face: V4 A4 F0", counts() == (4, 4, 0), counts())
    h.check("AF-1 mesh written", len(doc.obj.data.polygons) == 0 and len(doc.obj.data.edges) == 4)
    yield from shot("b_apagar_face_retangulo")
    with ctx():
        bpy.ops.ed.undo()
    yield 0.2
    doc = document.root()
    h.check("AF-6 undo of AF-1: face back", counts() == (4, 4, 1), counts())
    geom.erase_edges(doc.bm, list(doc.bm.edges))
    with ctx():
        doc.write(undo_key="undo.adjust")

    # --- box 8×6×3 drawn edge by edge (faces close by themselves)
    b = [V((0, 0, 0)), V((8, 0, 0)), V((8, 6, 0)), V((0, 6, 0))]
    t = [p + V((0, 0, 3)) for p in b]
    for i in range(4):
        geom.add_edge(doc.bm, b[i], b[(i + 1) % 4])
    for i in range(4):
        geom.add_edge(doc.bm, b[i], t[i])
    for i in range(4):
        geom.add_edge(doc.bm, t[i], t[(i + 1) % 4])
    with ctx():
        doc.write(undo_key="undo.adjust")
    h.check("box: V8 A12 F6", counts() == (8, 12, 6), counts())
    look((4, 3, 1.5), 22)
    yield from shot("b_caixa")

    # --- AF-2: erase the top → open box, 12 edges, 5 faces
    geom.erase_faces(doc.bm, [find_face((4, 3, 3))])
    with ctx():
        doc.write(undo_key="undo.adjust")
    h.check("AF-2 open box: V8 A12 F5", counts() == (8, 12, 5), counts())
    yield from shot("b_caixa_aberta")

    # --- AF-4: redraw the front top edge over the existing one → top healed (+Z)
    geom.add_edge(doc.bm, V((0, 0, 3)), V((8, 0, 3)))
    with ctx():
        doc.write(undo_key="undo.adjust")
    top = find_face((4, 3, 3))
    h.check("AF-4 healed: V8 A12 F6", counts() == (8, 12, 6), counts())
    h.check("AF-4 top normal +Z", top is not None and top.normal.z > 0.999,
            top.normal if top is not None else None)
    yield from shot("b_caixa_curada")

    # --- AF-3: erase the front top edge → it takes the top and the front face
    geom.erase_edges(doc.bm, [find_edge((0, 0, 3), (8, 0, 3))])
    with ctx():
        doc.write(undo_key="undo.adjust")
    h.check("AF-3 erase edge: V8 A11 F4", counts() == (8, 11, 4), counts())
    yield from shot("b_caixa_aresta_apagada")

    # --- AF-6: undo twice → healed box again, then redo
    with ctx():
        bpy.ops.ed.undo()
    yield 0.2
    doc = document.root()
    h.check("AF-6 undo of AF-3: V8 A12 F6", counts() == (8, 12, 6), counts())
    with ctx():
        bpy.ops.ed.redo()
    yield 0.2
    doc = document.root()
    h.check("AF-6 redo of AF-3: V8 A11 F4", counts() == (8, 11, 4), counts())
    h.check("validate() clean", geom.validate(doc.bm) == [], geom.validate(doc.bm))
    h.log("screens:", shots)
