# SPDX-License-Identifier: GPL-2.0-or-later
"""Shell / visual scenario (owner: D). PLANO.md §9.2-D (aceite) — run: tools/sketchup_mode/run_gui.sh scn_d

1. Layout: start-up steps finished, one workspace and one 3D area, HEADER hidden / TOOL_HEADER shown,
   LTS in the catalogue order (2 columns, separators), region widths from startup.blend, tray category
   "Bandeja" with every section closed, overrides of menus / toolbar / status bar in place, Blender UI
   panels hidden, theme + studio light + view transform Standard.
2. Demo scene like shell_v3 (box 2×3×1.5 with a user diagonal on its front face and a bridge on its top,
   cylinder with soft sides, rectangle on the ground with its back face up), GN back copy on every object.
3. Screenshot (out_dir/scn_d.png) + colour probes (out_dir/probes.json): sky, horizon, ground, chrome,
   faces front ≈255 / side ≈210 / top ≈160, back face blue-grey, black edges, diagonal visible, bridge
   invisible, cylinder without side facets.
"""

import json
import math
import os
import sys

import bmesh
import bpy
from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Vector

SU = "bl_app_templates_system.SketchUp_Mode.su"
TOL_FACE = 14


def mod(name):
    return sys.modules[SU + "." + name]


# ------------------------------------------------------------------------------------------- scene
def _link(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _edge_attr(me, name, indices):
    a = me.attributes.get(name) or me.attributes.new(name, 'BOOLEAN', 'EDGE')
    for i in indices:
        a.data[i].value = True


def build_scene():
    # box 2 × 3 × 1.5 at x∈[0,2], y∈[0,3]
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * 2 + 1.0, v.co.y * 3 + 1.5, v.co.z * 1.5 + 0.75))
    bm.normal_update()
    front = next(f for f in bm.faces if f.normal.y < -0.9)
    top = next(f for f in bm.faces if f.normal.z > 0.9)
    fv = sorted(front.verts, key=lambda v: (v.co.x, v.co.z))     # (0,0) (0,1.5) (2,0) (2,1.5)
    diag = bmesh.ops.connect_verts(bm, verts=[fv[0], fv[3]])["edges"][0]       # user line: visible
    tv = sorted(top.verts, key=lambda v: (v.co.x, v.co.y))
    bridge = bmesh.ops.connect_verts(bm, verts=[tv[0], tv[3]])["edges"][0]     # CDT bridge: hidden
    bm.edges.index_update()
    diag_i, bridge_i = diag.index, bridge.index
    diag_co = [tuple(v.co) for v in diag.verts]
    box = _link("Caixa", bm)
    _edge_attr(box.data, "su_bridge", [bridge_i])
    _edge_attr(box.data, "su_soft", [])
    # cylinder r 0.55, h 1.8, soft sides
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.55, radius2=0.55, depth=1.8)
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector((-2.6, 1.6, 0.9)))
    for f in bm.faces:
        f.smooth = len(f.verts) == 4
    bm.edges.index_update()
    soft = [e.index for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1.0]
    cyl = _link("Cilindro", bm)
    _edge_attr(cyl.data, "su_soft", soft)
    # rectangle on the ground, normal −Z (back face up)
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in ((-4.2, -0.4, 0), (-4.2, -2.4, 0), (-1.2, -2.4, 0), (-1.2, -0.4, 0))]
    f = bm.faces.new(vs)
    f.normal_update()
    if f.normal.z > 0:
        f.normal_flip()
    rect = _link("Retangulo", bm)
    gn = mod("draw.display_gn")
    for ob in (box, cyl, rect):
        gn.ensure(ob)
    return dict(box=box, cyl=cyl, rect=rect, diag=diag_co, bridge_i=bridge_i)


def build_e_cylinder(h, center=(4.2, -0.8, 0.0), radius="0,5", height="1,4"):
    """A real cylinder made by E's Círculo + Empurrar/puxar in the root "Modelo" (None if E is absent)."""
    try:
        testing = mod("testing")
        document = mod("core.document")
        geom_extrude = mod("core.geom_extrude")
        mod("tools.circle")
        mod("tools.pushpull")
    except KeyError:
        return None
    cx, cy, cz = center
    testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), "su.circle", testing.pt(cx, cy, cz))
    testing.click(testing.pt(cx, cy, cz))
    testing.move(testing.pt(cx + 1.0, cy, cz))
    testing.type_text(radius)
    testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), "su.pushpull", testing.pt(cx, cy, cz))
    doc = document.root()
    bm = doc.bm
    bm.faces.index_update()
    p = Vector((cx + 0.1, cy + 0.1, cz))
    f = geom_extrude.faces_at(bm, p)[0]
    f.normal_update()
    inf = testing.pt(*p, kind="ON_FACE", elem=("FACE", f.index), doc_key=doc.key, normal=f.normal.copy(),
                     side=-1, plane=(p.copy(), f.normal.copy()))
    testing.click(inf)
    testing.move(testing.pt(cx + 0.1, cy + 0.1, 0.5))
    testing.type_text(height)
    testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), "su.select", testing.pt(0, 0, 0))
    h.check("E cylinder built (soft sides)", any(a.name == "su_soft" for a in doc.obj.data.attributes),
            [a.name for a in doc.obj.data.attributes])
    return doc.obj


# ------------------------------------------------------------------------------------------- pixels
class Shot:
    def __init__(self, path):
        import numpy as np
        img = bpy.data.images.load(path)
        self.w, self.h = img.size
        px = np.empty(self.w * self.h * 4, np.float32)
        img.pixels.foreach_get(px)
        self.px = (px.reshape(self.h, self.w, 4)[:, :, :3] * 255.0 + 0.5).astype(np.int32)
        bpy.data.images.remove(img)

    def at(self, x, y):
        x, y = int(round(x)), int(round(y))
        if not (0 <= x < self.w and 0 <= y < self.h):
            return None
        return tuple(int(c) for c in self.px[y, x])

    def darkest(self, x, y, r=3):
        best = None
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                c = self.at(x + dx, y + dy)
                if c is not None and (best is None or sum(c) < sum(best)):
                    best = c
        return best


def near(c, target, tol):
    return c is not None and all(abs(a - b) <= tol for a, b in zip(c, target))


def run(h):
    yield h.until(lambda: bpy.app.driver_namespace.get("su_ui_ready"), 30.0, "su_ui_ready")
    yield 0.5
    win, area, R = h.area_regions()
    sp = area.spaces.active
    ps = bpy.context.preferences.system.pixel_size
    probes = {}

    # ---- 1. layout
    h.check("one workspace", len(bpy.data.workspaces) == 1, [w.name for w in bpy.data.workspaces])
    h.check("one area (3D viewport)", len(win.screen.areas) == 1, [a.type for a in win.screen.areas])
    h.check("HEADER hidden, TOOL_HEADER shown", (not sp.show_region_header) and sp.show_region_tool_header)
    h.check("toolbar + tray shown", sp.show_region_toolbar and sp.show_region_ui)
    tools_w, ui_w = R['TOOLS'].width / ps, R['UI'].width / ps
    probes["region_widths_pt"] = {"TOOLS": tools_w, "UI": ui_w}
    h.check("LTS width ≈ 96 pt (startup.blend)", 85 <= tools_w <= 105, tools_w)
    h.check("tray width ≈ 300 pt (startup.blend)", 280 <= ui_w <= 320, ui_w)
    tray = mod("ui.tray")
    ui_region = R['UI']
    h.check("tray drawn without category (no tab strip, §9.2-D 9.4)", ui_region.active_panel_category == "UNSUPPORTED",
            ui_region.active_panel_category)
    h.check("tray: all sections closed", bpy.context.window_manager.su_tray.open_ids == "",
            bpy.context.window_manager.su_tray.open_ids)
    secs = [s for s, _ in tray.sections()]
    h.check("tray sections in SketchUp order (no tags)", secs == ["entity", "materials", "components", "styles",
                                                                  "shadows", "scenes", "soften", "outliner"], secs)
    toolset = mod("ui.toolset")
    lts_expected = toolset.layout_lists()[0]
    h.check("LTS order + separators", toolset.lts_ids() == list(lts_expected), toolset.lts_ids())
    h.check("two-column LTS", bpy.types.VIEW3D_PT_tools_active._layout_generator_detect_from_region.__name__
            == "_force_two_columns")
    h.check("toolbar override", bpy.types.VIEW3D_HT_tool_header.draw is mod("ui.header_toolbar").draw_toolbar)
    h.check("status bar override", bpy.types.STATUSBAR_HT_header.draw is mod("ui.statusbar").draw)
    h.check("menu row override", bpy.types.TOPBAR_HT_upper_bar.draw_left is mod("ui.topbar").topbar_left)
    h.check("Blender UI panels hidden", mod("ui.hide").hidden_count() > 40, mod("ui.hide").hidden_count())
    h.check("theme applied", mod("theme").theme_is_applied())
    h.check("studio light sketchup.sl", sp.shading.studio_light == mod("theme").STUDIO_LIGHT_NAME,
            sp.shading.studio_light)
    h.check("Workbench MATERIAL + back-face culling", sp.shading.color_type == 'MATERIAL'
            and sp.shading.show_backface_culling)
    h.check("view transform Standard", bpy.context.scene.view_settings.view_transform == 'Standard')
    h.check("idle hint uses Option", "Option" in mod("ui.statusbar").hint_text() or sys.platform != "darwin",
            mod("ui.statusbar").hint_text())
    h.check("no 'Etiqueta'/'Tag' in UI strings", not any(
        ("etiqueta" in str(v).lower() or " tag" in (" " + str(v).lower()))
        for v in list(mod("ui.toolset").LABELS.values()) + list(mod("ui.topbar").STRINGS.values())
        + list(tray.STRINGS.values())))
    h.check("active tool su.select", mod("tools.base").active_tool_id() == "su.select",
            mod("tools.base").active_tool_id())
    ic = mod("icons")
    for tid in ("su.line", "su.move", "su.pushpull", "su.orbit", "su.pan", "su.zoom"):
        h.check("original icon " + tid, ic.TOOL_ICONS[tid].startswith("draw.") and ic.tool_icon(tid) > 0,
                (ic.TOOL_ICONS[tid], ic.tool_icon(tid)))
    h.check("start view FOV 35°", abs(math.degrees(2 * math.atan(1 / sp.region_3d.window_matrix[1][1])) - 35.0) < 0.5)

    # ---- 2. demo scene
    sc = build_scene()
    ecyl = build_e_cylinder(h)
    for ob in (sc["box"], sc["cyl"], sc["rect"]):
        m = ob.modifiers.get("SU_Display")
        h.check("GN back copy on " + ob.name, m is not None and m.node_group is not None)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = sc["box"].evaluated_get(dg).data
    n = len(sc["box"].data.polygons)
    h.check("GN doubles faces, originals first", len(ev.polygons) == 2 * n
            and all(p.material_index == 0 for p in list(ev.polygons)[:n])
            and all(p.material_index == 1 for p in list(ev.polygons)[n:]),
            (len(ev.polygons), n, [p.material_index for p in ev.polygons]))
    area.tag_redraw()
    h.park_mouse()
    yield 1.0

    # ---- 3. screenshot + probes
    path = os.path.join(h.out_dir, "scn_d.png")
    h.screenshot(path)
    yield 0.5
    shot = Shot(path)
    reg, rv3d = R['WINDOW'], sp.region_3d

    def wxy(co):
        p = location_3d_to_region_2d(reg, rv3d, Vector(co))
        return None if p is None else (reg.x + p.x, reg.y + p.y)

    def probe(name, co_or_xy, target=None, tol=TOL_FACE, darkest=False):
        xy = wxy(co_or_xy) if len(co_or_xy) == 3 else co_or_xy
        c = None if xy is None else (shot.darkest(*xy) if darkest else shot.at(*xy))
        probes[name] = {"xy": xy, "rgb": c, "target": target}
        if target is not None:
            h.check("probe " + name, near(c, target, tol), (c, target))
        return c

    probe("sky top", (reg.x + reg.width * 0.6, reg.y + reg.height - 2 * ps), (30, 166, 221), 8)
    probe("ground", (reg.x + reg.width * 0.9, reg.y + 30), (191, 191, 198), 6)
    hz = mod("draw.sky").horizon_ndc_y(rv3d)
    hy = reg.y + (hz + 1) * 0.5 * reg.height
    probe("horizon (sky side)", (reg.x + reg.width * 0.9, hy + 4), (191, 229, 245), 8)
    tr = R['TOOLS']
    probe("chrome (LTS background)", (tr.x + tr.width * 0.5, tr.y + 8), (241, 241, 246), 5)
    if ecyl is not None:
        edges_mod = mod("draw.edges")
        root = ecyl
        eye = root.matrix_world.inverted() @ rv3d.view_matrix.inverted().translation
        data = edges_mod.edge_classes(root.data)
        sil = edges_mod.silhouette_mask(data, tuple(eye))
        probes["E cylinder profile candidates"] = int(data["profile"].sum())
        h.check("E cylinder: 2 profile edges for this view", len(sil) == 2, len(sil))
        for k, ei in enumerate(sil):
            a, b = (root.matrix_world @ root.data.vertices[v].co for v in root.data.edges[int(ei)].vertices)
            c = probe("E cylinder profile {:d}".format(k), tuple(a.lerp(b, 0.5)), darkest=True)
            h.check("E cylinder profile {:d} black".format(k), c is not None and max(c) <= 60, c)
    probe("face front (−Y)", (1.3, 0.0, 0.4), (255, 255, 255))
    probe("face side (+X)", (2.0, 1.5, 0.75), (210, 210, 210))
    probe("face top", (1.6, 2.2, 1.5), (160, 160, 160))
    c = probe("back face up (rectangle) ≈ #A4B2BB unlit", (-2.7, -1.4, 0.0), (164, 178, 187), 8)
    h.check("back face blue-grey (b > r)", c is not None and c[2] > c[0] + 6, c)
    e = probe("edge black (box vertical)", (2.0, 0.0, 0.75), darkest=True)
    h.check("edge black", e is not None and max(e) <= 40, e)
    a, b = Vector(sc["diag"][0]), Vector(sc["diag"][1])
    m1 = a.lerp(b, 0.62)
    d = probe("user diagonal on a flat face", tuple(m1), darkest=True)
    h.check("diagonal visible (AC-LIN-2 visual)", d is not None and max(d) <= 60, d)
    me = sc["box"].data
    bv = me.edges[sc["bridge_i"]].vertices
    bm_ = (me.vertices[bv[0]].co + me.vertices[bv[1]].co) / 2
    bb = probe("bridge on the top", tuple(bm_), darkest=True)
    h.check("bridge invisible", bb is not None and min(bb) >= 120, bb)
    cyl_side = probe("cylinder side (no facets)", (-2.6 + 0.55 * math.cos(math.radians(-60)),
                                                   1.6 + 0.55 * math.sin(math.radians(-60)), 0.9), darkest=True)
    h.check("cylinder side without facet lines", cyl_side is not None and min(cyl_side) >= 120, cyl_side)
    # ---- 4. selection display (§9.2-D item 4): face stipple, blue edges, group bbox
    sel = mod("core.selection")
    me = sc["box"].data
    side = next(p.index for p in me.polygons if p.normal.x > 0.9)
    side_edges = [me.edges[me.loops[li].edge_index].index for li in me.polygons[side].loop_indices]
    refs = [sel.Ref("Caixa", "FACE", side)] + [sel.Ref("Caixa", "EDGE", e) for e in side_edges]
    refs.append(sel.Ref("Cilindro", "OBJECT", 0))
    sel.set(refs)
    h.check("selection set", sel.count() == len(refs), sel.count())
    area.tag_redraw()
    yield 1.0
    path2 = os.path.join(h.out_dir, "scn_d_sel.png")
    h.screenshot(path2)
    yield 0.5
    shot2 = Shot(path2)
    c = wxy((2.0, 1.5, 0.75))
    blue_px = plain = 0
    for dy in range(-12, 13):
        for dx in range(-12, 13):
            q = shot2.at(c[0] + dx, c[1] + dy)
            if q is None:
                continue
            if q[2] > q[0] + 60:
                blue_px += 1
            elif near(q, (209, 209, 209), 14):
                plain += 1
    probes["selected face patch"] = {"blue": blue_px, "plain": plain}
    h.check("selected face = blue dot screen (stipple)", blue_px >= 8 and plain >= 100, (blue_px, plain))

    def bluest(xy, r=3):
        best = None
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                q = shot2.at(xy[0] + dx, xy[1] + dy)
                if q is not None and (best is None or q[2] - q[0] > best[2] - best[0]):
                    best = q
        return best
    eb = bluest(wxy((2.0, 3.0, 0.75)))
    probes["selected edge"] = eb
    h.check("selected edge blue", eb is not None and eb[2] >= 180 and eb[0] <= 70, eb)
    sel.clear()

    # ---- 4b. hidden faces (F's Ocultar → su_hidden_face): collapsed by the GN, edges stay
    bme = sc["box"].data
    tops = [p.index for p in bme.polygons if p.normal.z > 0.9]       # the top is 2 triangles (bridge)
    top_i = tops[0]
    a = bme.attributes.get("su_hidden_face") or bme.attributes.new("su_hidden_face", 'BOOLEAN', 'FACE')
    for i in tops:
        a.data[i].value = True
    bme.update()
    mod("draw.edges").mark_dirty("Caixa")
    area.tag_redraw()
    yield 1.0
    path4 = os.path.join(h.out_dir, "scn_d_hidden.png")
    h.screenshot(path4)
    yield 0.5
    shot4 = Shot(path4)
    tc = shot4.at(*wxy(tuple(bme.polygons[top_i].center)))
    probes["hidden top face (see the inside)"] = tc
    h.check("hidden face gone (inside back faces seen, not the grey top)", tc is not None and tc[2] - tc[0] >= 15, tc)
    te = shot4.darkest(*wxy((1.0, 0.0, 1.5)))
    h.check("edges of the hidden face stay black", te is not None and max(te) <= 60, te)
    st = bpy.context.scene.su_style
    st.show_hidden_geometry = True
    yield 1.0
    path5 = os.path.join(h.out_dir, "scn_d_hidden_shown.png")
    h.screenshot(path5)
    yield 0.5
    shot5 = Shot(path5)
    c5 = wxy(tuple(bme.polygons[top_i].center))
    dots = sum(1 for dy in range(-10, 11) for dx in range(-10, 11)
               if (q := shot5.at(c5[0] + dx, c5[1] + dy)) is not None and max(q) < 140)
    probes["hidden face shown: dark dots"] = dots
    h.check("Geometria oculta: hidden face drawn with dots", dots >= 5, dots)
    st.show_hidden_geometry = False
    for i in tops:
        a.data[i].value = False
    bme.update()
    mod("draw.edges").mark_dirty("Caixa")
    yield 0.5

    # ---- 5. P1 styles (§9.2-D item 10): back edges, tray Estilos › Editar open
    st = bpy.context.scene.su_style
    st.show_back_edges = True
    tray.set_open("styles", True)
    bpy.context.window_manager.su_tray.styles_tab = 'EDIT'
    area.tag_redraw()
    yield 1.0
    path3 = os.path.join(h.out_dir, "scn_d_styles.png")
    h.screenshot(path3)
    yield 0.5
    shot3 = Shot(path3)
    hidden = wxy((0.0, 3.0, 0.75))           # back-left vertical edge, behind the box
    hd = shot3.darkest(*hidden, r=4) if hidden else None
    probes["back edge (hidden, dashed)"] = hd
    h.check("back edges drawn behind faces", hd is not None and max(hd) <= 110, hd)
    st.face_style = 'XRAY'
    yield 0.6
    h.check("Raio X: GN back copy off", not sc["box"].modifiers["SU_Display"].show_viewport)
    st.face_style = 'TEXTURED'
    st.show_back_edges = False
    h.check("back copy on again", sc["box"].modifiers["SU_Display"].show_viewport)
    with open(os.path.join(h.out_dir, "probes.json"), "w", encoding="utf-8") as f:
        json.dump(probes, f, indent=1, ensure_ascii=False, default=str)
    h.check("screenshot written", os.path.isfile(path))
