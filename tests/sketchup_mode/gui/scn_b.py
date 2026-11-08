# SPDX-License-Identifier: GPL-2.0-or-later
"""Scenario B (owner: B): the geometry kernel inside the running app — "Apagar uma face"
(doc/sketchup_mode/ROTEIRO_CASA.md AF-1, AF-2, AF-3, AF-4, AF-6 kernel parts) through the real
Document (to_mesh, events, memfile undo). Tools/selection (double click, Delete key, context menu)
belong to F. Screenshots: <out_dir>/b_*.png (the edges overlay is switched on here because the
edge renderer of D may not exist yet)."""

import math
import os

import bpy
from mathutils import Euler, Matrix, Vector

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

    # --- items 5–8: selection undo, fold, group, explode
    selection = importlib.import_module(su.__name__ + ".core.selection")
    geom.add_edge(doc.bm, V((0, 0, 3)), V((8, 0, 3)))           # heal front + top again
    geom.add_edge(doc.bm, V((0, 0, 0)), V((8, 0, 0)))
    with ctx():
        doc.write(undo_key="undo.adjust")
    h.check("box healed again: V8 A12 F6", counts() == (8, 12, 6), counts())
    top = find_face((4, 3, 3))
    top_ref = selection.Ref(doc.key, selection.FACE, top.index)
    selection.set([top_ref])
    with ctx():
        doc.write(undo_key="undo.adjust")
    geom.erase_faces(doc.bm, [doc.bm.faces[top_ref.index]])
    with ctx():
        doc.write(undo_key="undo.adjust", select=())
    h.check("Excluir clears the selection", selection.is_empty())
    with ctx():
        bpy.ops.ed.undo()
    yield 0.2
    h.check("AF-6 undo restores face AND selection", counts() == (8, 12, 6) and selection.get() == {top_ref},
            (counts(), selection.get()))
    with ctx():
        bpy.ops.ed.redo()
    yield 0.2
    h.check("AF-6 redo: face gone, selection empty", counts() == (8, 12, 5) and selection.is_empty())
    with ctx():
        bpy.ops.ed.undo()
    yield 0.2
    doc = document.root()
    selection.clear()

    # AC-MOV-5 (kernel): one top corner 1 m up → top folds into 2 planar triangles
    corner = next(v for v in doc.bm.verts if (v.co - V((8, 6, 3))).length < 1e-6)
    corner.co.z = 4.0
    r = geom.ensure_planar(doc.bm, list(doc.bm.faces))
    with ctx():
        doc.write(undo_key="undo.adjust")
    h.check("AC-MOV-5 fold: 1 fold edge, V8 A13 F7", len(r.new_edges) == 1 and counts() == (8, 13, 7), counts())
    h.check("AC-MOV-5 all faces planar", all(geom.is_planar(f) for f in doc.bm.faces))
    yield from shot("b_dobra")
    with ctx():
        bpy.ops.ed.undo()
    yield 0.2
    doc = document.root()
    h.check("undo of fold: V8 A12 F6", counts() == (8, 12, 6), counts())

    # Criar grupo with the top (double click = face + edges), lift the group 1 m
    top = find_face((4, 3, 3))
    refs = selection.expand_face(selection.Ref(doc.key, selection.FACE, top.index))
    h.check("AC-SEL-1 double click: 1 face + 4 edges",
            sum(x.kind == 'FACE' for x in refs) == 1 and sum(x.kind == 'EDGE' for x in refs) == 4)
    three = selection.connected(refs[0])
    h.check("AC-SEL-1 triple click: 6 faces + 12 edges",
            sum(x.kind == 'FACE' for x in three) == 6 and sum(x.kind == 'EDGE' for x in three) == 12)
    g = document.group_from(doc, [x.index for x in refs if x.kind == 'FACE'],
                            [x.index for x in refs if x.kind == 'EDGE'], "Tampa")
    g.obj.matrix_world = Matrix.Translation((0, 0, 1)) @ g.obj.matrix_world
    with ctx():
        g.write(undo_key=None)
        doc.write(undo_key="undo.adjust")
    h.check("group 'Tampa': V4 A4 F1; box V8 A12 F5", counts() == (8, 12, 5) and
            (len(g.bm.verts), len(g.bm.edges), len(g.bm.faces)) == (4, 4, 1))
    look((4, 3, 2), 24)
    yield from shot("b_grupo_tampa")
    g.obj.matrix_world = doc.world()
    pdoc, res = document.explode(g.obj)
    with ctx():
        pdoc.write(undo_key="undo.adjust")
    h.check("explode welds the top back: V8 A12 F6", counts() == (8, 12, 6), counts())
    h.check("validate() clean at the end", geom.validate(doc.bm) == [], geom.validate(doc.bm))
    yield from shot("b_explodir")

    # --- components (P1): the whole box becomes a definition, a 2nd instance 12 m away; erasing the
    # top inside instance 2 opens BOTH boxes (shared mesh); D's GN copy and C's ray_cast per instance
    spatial = importlib.import_module(su.__name__ + ".core.spatial")
    refs = selection.connected(selection.Ref(doc.key, selection.FACE, 0))
    c1 = document.component_from(doc, [x.index for x in refs if x.kind == 'FACE'],
                                 [x.index for x in refs if x.kind == 'EDGE'], "Caixa")
    with ctx():
        c1.write(undo_key=None)
        doc.write(undo_key="undo.adjust")
    o2 = document.duplicate(c1.obj)
    o2.matrix_world = Matrix.Translation((12, 0, 0)) @ o2.matrix_world
    c2 = document.get(o2)
    with ctx():
        bpy.ops.ed.undo_push(message="copy")
    yield 0.3
    h.check("component: 2 instances share the definition",
            document.instances("Caixa") == sorted([c1.obj, o2], key=lambda o: o.name) and o2.data == c1.obj.data)
    h.check("D's SU_Display modifier on both instances",
            all(o.modifiers.get("SU_Display") is not None for o in (c1.obj, o2)),
            [[m.name for m in o.modifiers] for o in (c1.obj, o2)])
    look((10, 3, 1.5), 34)
    yield from shot("b_componentes")
    edit_context = importlib.import_module(su.__name__ + ".core.edit_context")
    edit_context.enter(o2)
    ed = document.active()
    top2 = next(f for f in ed.bm.faces if (f.calc_center_median() - V((4, 3, 3))).length < 1e-4)
    geom.erase_faces(ed.bm, [top2])
    with ctx():
        ed.write(undo_key="undo.adjust", select=())
    edit_context.exit()
    yield 0.3
    h.check("edit inside instance 2 → both instances open (5 faces each)",
            len(c1.obj.data.polygons) == 5 and len(o2.data.polygons) == 5)
    hit = spatial.ray_cast(bpy.context, V((16, 3, 10)), V((0, 0, -1)))
    h.check("C's ray_cast through the open top of instance 2 hits its floor",
            hit.ok and hit.doc_key == o2.name and abs(hit.point.z) < 1e-4, (hit.ok, hit.doc_key, hit.point))
    yield from shot("b_componentes_editados")
    h.log("screens:", shots)
