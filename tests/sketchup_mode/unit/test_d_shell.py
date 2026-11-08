# SPDX-License-Identifier: GPL-2.0-or-later
"""Shell / visual tests (owner: D), headless: tray sections, LTS layout and labels, studio light file,
edge classification by attributes (AC-LIN-2 rule), GN back copy, style props."""

import importlib
import os
import unittest

import bmesh
import bpy
from mathutils import Vector

from su import i18n, icons, theme
from su.core import style
from su.ui import toolset, tray


def _box_with_lines():
    """2×3×1.5 box: diagonal on the front face (user line), diagonal on top marked su_bridge,
    one vertical edge marked su_hidden. Returns (object, diag_index, bridge_index, hidden_index)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * 2 + 1.0, v.co.y * 3 + 1.5, v.co.z * 1.5 + 0.75))
    bm.normal_update()
    front = next(f for f in bm.faces if f.normal.y < -0.9)
    top = next(f for f in bm.faces if f.normal.z > 0.9)
    fv = sorted(front.verts, key=lambda v: (v.co.x, v.co.z))
    diag = bmesh.ops.connect_verts(bm, verts=[fv[0], fv[3]])["edges"][0]
    tv = sorted(top.verts, key=lambda v: (v.co.x, v.co.y))
    bridge = bmesh.ops.connect_verts(bm, verts=[tv[0], tv[3]])["edges"][0]
    vert = next(e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1.0)
    bm.edges.index_update()
    di, bi, hi = diag.index, bridge.index, vert.index
    me = bpy.data.meshes.new("test_d_box")
    bm.to_mesh(me)
    bm.free()
    for name, idx in (("su_bridge", bi), ("su_hidden", hi)):
        a = me.attributes.new(name, 'BOOLEAN', 'EDGE')
        a.data[idx].value = True
    ob = bpy.data.objects.new("test_d_box", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob, di, bi, hi


def _cylinder():
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=1.0, radius2=1.0, depth=2.0)
    bm.edges.index_update()
    soft = [e.index for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1.0]
    me = bpy.data.meshes.new("test_d_cyl")
    bm.to_mesh(me)
    bm.free()
    a = me.attributes.new("su_soft", 'BOOLEAN', 'EDGE')
    for i in soft:
        a.data[i].value = True
    return me, soft


class TestTray(unittest.TestCase):
    def tearDown(self):
        tray.unregister_section("test_x")
        tray.unregister_section("test_p2")

    def test_default_sections_in_sketchup_order(self):
        ids = [s for s, _ in tray.sections()]
        self.assertEqual(ids, ["entity", "materials", "components", "styles", "shadows", "scenes",
                               "soften", "outliner"])
        self.assertFalse(any("tag" in s or "etiqueta" in s for s in ids))

    def test_register_replace_and_p2(self):
        tray.register_section(45, "test_x", "tray.styles", lambda l, c: None)
        ids = [s for s, _ in tray.sections()]
        self.assertLess(ids.index("styles"), ids.index("test_x"))
        tray.register_section(45, "test_p2", "tray.styles", lambda l, c: None, priority='P2')
        self.assertEqual("test_p2" in [s for s, _ in tray.sections()], tray.SHOW_P2_SECTIONS)

    def test_all_closed_by_default(self):
        self.assertFalse(tray.is_open("styles", bpy.context.window_manager))


class TestToolset(unittest.TestCase):
    def test_lts_layout(self):
        lts, gs, fly = toolset.layout_lists()
        self.assertEqual(lts[0], "su.select")
        self.assertEqual(toolset.lts_ids(), list(lts))
        groups, cur = [], []
        for t in lts:
            if t is None:
                groups.append(cur)
                cur = []
            else:
                cur.append(t)
        groups.append(cur)
        self.assertEqual(len(groups[0]) % 2, 1, "first group odd: empty cell after Criar componente")

    def test_every_tool_has_icon_and_label(self):
        lts, gs, fly = toolset.layout_lists()
        ids = {t for t in lts if t} | {t.rstrip("*") for g in gs for t in g}
        for t in ids:
            self.assertIn(t, icons.TOOL_ICONS, t)
            self.assertNotEqual(toolset.label(t), t)

    def test_no_tag_wording(self):
        texts = list(toolset.LABELS.values()) + [i18n.t(k) for k in tray.STRINGS]
        for s in texts:
            self.assertNotIn("etiqueta", s.lower())
            self.assertNotIn("tag", s.lower().split())

    def test_p2_disabled(self):
        self.assertFalse(toolset.is_enabled("su.lasso"))
        self.assertTrue(toolset.is_enabled("su.line"))


class TestStudioLight(unittest.TestCase):
    def test_file_matches_calibration(self):
        with open(theme.STUDIO_LIGHT_PATH, encoding="ascii") as f:
            self.assertEqual(f.read(), theme.studio_light_text())

    def test_box_shading_targets(self):
        """front ≈255, side ≈210, top ≈160 for the start view (Workbench wrapped Lambert, smooth 0)."""
        import math
        yaw, p = math.radians(33.0), math.radians(6.6)
        fwd = Vector((-math.sin(yaw) * math.cos(p), math.cos(yaw) * math.cos(p), -math.sin(p)))
        right = fwd.cross(Vector((0, 0, 1))).normalized()
        up = right.cross(fwd)
        L = Vector(theme.LIGHT_DIRECTION).normalized()

        def shade(n):
            nv = Vector((right.dot(n), up.dot(n), -fwd.dot(n)))
            lin = theme.LIGHT_AMBIENT + theme.LIGHT_DIFFUSE * 0.9344 * max(0.0, nv.dot(L))
            lin = min(1.0, lin)
            return 255 * (12.92 * lin if lin <= 0.0031308 else 1.055 * lin ** (1 / 2.4) - 0.055)
        self.assertAlmostEqual(shade(Vector((0, -1, 0))), 255, delta=3)
        self.assertAlmostEqual(shade(Vector((1, 0, 0))), 210, delta=6)
        self.assertAlmostEqual(shade(Vector((0, 0, 1))), 160, delta=6)


class TestEdges(unittest.TestCase):
    def setUp(self):
        self.edges = importlib.import_module("su.draw.edges")

    def test_attribute_filter(self):
        ob, di, bi, hi = _box_with_lines()
        try:
            d = self.edges.edge_classes(ob.data)
            self.assertTrue(d["always"][di], "user diagonal on a flat face must be drawn (AC-LIN-2)")
            self.assertFalse(d["always"][bi] or d["profile"][bi], "bridge never drawn")
            self.assertFalse(d["always"][hi] or d["profile"][hi], "hidden never drawn")
            self.assertEqual(int(d["always"].sum()), len(ob.data.edges) - 2)
        finally:
            me = ob.data
            bpy.data.objects.remove(ob)
            bpy.data.meshes.remove(me)

    def test_soft_edges_only_as_silhouette(self):
        me, soft = _cylinder()
        try:
            d = self.edges.edge_classes(me)
            self.assertFalse(d["always"][soft].any())
            self.assertTrue(d["profile"][soft].all())
            sil = self.edges.silhouette_mask(d, (10.0, 0.0, 0.0))
            self.assertEqual(len(sil), 2, "a cylinder seen from the side has two profile edges")
            sil_o = self.edges.silhouette_mask(d, None, (-1.0, 0.0, 0.0))
            self.assertEqual(len(sil_o), 2)
        finally:
            bpy.data.meshes.remove(me)


class TestDisplayGN(unittest.TestCase):
    def test_back_copy(self):
        gn = importlib.import_module("su.draw.display_gn")
        ob, *_ = _box_with_lines()
        try:
            gn.ensure(ob)
            self.assertIsNotNone(ob.modifiers.get(gn.MODIFIER))
            self.assertEqual(len(ob.data.materials), 2)
            n = len(ob.data.polygons)
            ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
            self.assertEqual(len(ev.polygons), 2 * n)
            self.assertTrue(all(p.material_index == 0 for p in list(ev.polygons)[:n]))
            self.assertTrue(all(p.material_index == 1 for p in list(ev.polygons)[n:]))
            for i in range(n):
                self.assertAlmostEqual(ev.polygons[i].normal.dot(ob.data.polygons[i].normal), 1.0, places=4)
                self.assertAlmostEqual(ev.polygons[n + i].normal.dot(ob.data.polygons[i].normal), -1.0, places=4)
            gn.set_back_copy(False)
            self.assertFalse(ob.modifiers[gn.MODIFIER].show_viewport)
            gn.set_back_copy(True)
            # unlit back faces: reversed winding, colour = sRGB of the back material (#A4B2BB)
            pos, col = gn.back_triangles(ob.data)
            self.assertEqual(len(pos), 3 * len(ob.data.loop_triangles))
            r, g, b, _a = (round(x * 255) for x in col[0])
            self.assertEqual((r, g, b), (164, 178, 187))
        finally:
            me = ob.data
            bpy.data.objects.remove(ob)
            bpy.data.meshes.remove(me)


class TestIcons(unittest.TestCase):
    def test_every_tool_icon_is_an_original_drawing_with_dim(self):
        for tid, h in icons.TOOL_ICONS.items():
            self.assertTrue(h.startswith("draw."), tid)
            self.assertTrue(os.path.isfile(icons.dat_path(h) + ".dat"), h)
            self.assertTrue(os.path.isfile(icons.dat_path(h + icons.DIM_SUFFIX) + ".dat"), h)
        for name, h in icons.UI_ICONS.items():
            self.assertTrue(os.path.isfile(icons.dat_path(h) + ".dat") or h.startswith("bi."), h)


class TestExport(unittest.TestCase):
    def test_obj_export_without_back_copy(self):
        gn = importlib.import_module("su.draw.display_gn")
        file_ops = importlib.import_module("su.ops.file_ops")
        ob, *_ = _box_with_lines()
        path = os.path.join(bpy.app.tempdir, "test_d_export.obj")
        try:
            gn.ensure(ob)
            n = sum(len(o.data.polygons) for o in bpy.context.scene.objects if o is not None and o.type == 'MESH')
            self.assertTrue(file_ops.export('OBJ', path))
            with open(path, encoding="utf-8") as f:
                faces = sum(1 for l in f if l.startswith("f "))
            self.assertEqual(faces, n, "export must skip the GN back copy (no duplicated faces)")
        finally:
            me = ob.data
            bpy.data.objects.remove(ob)
            bpy.data.meshes.remove(me)
            if os.path.exists(path):
                os.remove(path)


class TestStyle(unittest.TestCase):
    def test_scene_style_and_view_transform(self):
        sc = bpy.context.scene
        self.assertTrue(hasattr(sc, "su_style"))
        style.apply()
        self.assertEqual(sc.view_settings.view_transform, 'Standard')
        before = sc.su_style.show_axes
        style.toggle("show_axes")
        self.assertNotEqual(before, sc.su_style.show_axes)
        style.toggle("show_axes")

    def test_face_styles(self):
        st = bpy.context.scene.su_style
        for fs in ('XRAY', 'WIREFRAME', 'HIDDEN_LINE', 'SHADED', 'MONOCHROME', 'TEXTURED'):
            st.face_style = fs
        self.assertEqual(st.face_style, 'TEXTURED')


if __name__ == "__main__":
    unittest.main()
