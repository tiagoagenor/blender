# SPDX-License-Identifier: GPL-2.0-or-later
"""G (P1): Janela de zoom / Posição da câmera math, Texto, Texto em 3D (group + "doc"), Cenas data."""

import math
import unittest

import bpy
from mathutils import Vector

import test_c_fakes as F
from su import events, perf, testing
from su.core import camera, geom, guides, state
from su.core.camera import View
from su.tools import base, camera_tools, text


def pt(x, y, z=0.0, kind="FREE", **kw):
    return testing.pt(x, y, z, kind=kind, **kw)


class TestCameraTools(unittest.TestCase):
    def view(self):
        region, rv3d = F.camera()
        return View.from_rv3d(region, rv3d)

    def test_zoom_window_fills_region(self):
        v = self.view()
        target = Vector((2.0, 2.0, 0.5))
        s = v.project(target)
        x0, y0, x1, y1 = s.x - 100, s.y - 80, s.x + 100, s.y + 80
        camera_tools.zoom_window_view(v, x0, y0, x1, y1, target)
        c = v.project(target)
        self.assertLess((c - Vector(v.center_xy())).length, 1e-3)          # centre of the window → centre
        d0 = (self.view().eye() - target).length
        self.assertAlmostEqual((v.eye() - target).length, d0 * max(200 / 1000, 160 / 800), places=5)

    def test_place_eye(self):
        v = self.view()
        camera_tools.place_eye(v, (1.0, 2.0, 1.676))
        self.assertLess((v.eye() - Vector((1.0, 2.0, 1.676))).length, 1e-6)
        self.assertAlmostEqual(v.fwd.z, 0.0, places=6)                     # looking horizontally
        self.assertAlmostEqual(v.right.z, 0.0, places=6)
        camera_tools.place_eye(v, (0.0, 0.0, 1.676), target=(5.0, 0.0, 1.676))
        self.assertLess((v.fwd - Vector((1, 0, 0))).length, 1e-6)

    def test_position_camera_tool_headless(self):
        base.DISPATCH.reset()
        base._instances.pop("su.position_camera", None)
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), "su.position_camera", pt(0, 0))
        self.assertEqual(testing.state_dump()["vcb_label_key"], "vcb.eye_height")
        testing.type_text("1,5")
        self.assertAlmostEqual(base.controller("su.position_camera").height, 1.5)
        testing.click(pt(-3, -2, 0))
        self.assertLess((base.controller("su.position_camera").last[0] - Vector((-3, -2, 0))).length, 1e-9)
        base.DISPATCH.set_tool(base.ToolContext(), '')


class TestText(unittest.TestCase):
    def setUp(self):
        self.n_err = perf.errors()
        base.DISPATCH.reset()
        base._instances.pop("su.text", None)
        state.STATE.reset()
        d = guides.data()
        d.texts.clear()
        testing.reset_model()

    def tearDown(self):
        base.DISPATCH.set_tool(base.ToolContext(), '')
        guides.data().texts.clear()
        testing.reset_model()
        self.assertEqual(perf.errors(), self.n_err, perf.messages()[self.n_err:])

    def test_leader_text_edge_length(self):
        from su.core import document
        doc = document.root()
        a, b = doc.bm.verts.new((0, 0, 0)), doc.bm.verts.new((3, 0, 0))
        doc.bm.edges.new((a, b))
        doc.write(undo_key=None)
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), "su.text", pt(0, 0))
        s0 = bpy.context.scene.su_undo_serial
        testing.click(pt(1.2, 0, 0, "ON_EDGE", ref_edge=(doc.key, 0), doc_key=doc.key))
        self.assertTrue(base.DISPATCH.running)
        testing.move(pt(1.5, -1, 0))
        testing.click(pt(1.5, -1, 0))
        t = guides.data().texts
        self.assertEqual(len(t), 1)
        self.assertEqual(t[0].text, "3,00m")
        self.assertLess((Vector(t[0].leader_end) - Vector((1.5, -1, 0))).length, 1e-6)
        self.assertEqual(bpy.context.scene.su_undo_serial - s0, 1)

    def test_leader_text_point(self):
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), "su.text", pt(0, 0))
        testing.click(pt(1, 2, 0, "ENDPOINT"))
        testing.click(pt(2, 3, 0))
        self.assertEqual(guides.data().texts[0].text, "[1,00m; 2,00m; 0,00m]")


class TestText3D(unittest.TestCase):
    def setUp(self):
        self.n_err = perf.errors()

    def tearDown(self):
        self.assertEqual(perf.errors(), self.n_err, perf.messages()[self.n_err:])

    def test_mesh_planar_with_holes_and_soft_sides(self):
        bm = text.text3d_bmesh("AO", 0.5, True, 0.1)
        try:
            self.assertGreater(len(bm.faces), 4)
            lay = geom.layers(bm)
            self.assertTrue(all(geom.is_planar(f, 1e-4) for f in bm.faces))
            self.assertTrue(any(e[lay.bridge] for e in bm.edges))             # letters with holes
            self.assertTrue(any(e[lay.soft] for e in bm.edges))               # curved sides of the O
            zs = [v.co.z for v in bm.verts]
            self.assertAlmostEqual(min(zs), 0.0, places=6)
            self.assertAlmostEqual(max(zs), 0.1, places=5)
        finally:
            bm.free()

    def test_create_group_emits_doc(self):
        seen = []
        fn = lambda doc_key="", **_kw: seen.append(doc_key)
        events.subscribe("doc", fn)
        try:
            doc = text.create_text3d((1.0, 2.0, 0.0), None, {"text": "SU", "height": 0.3})
        finally:
            events.unsubscribe("doc", fn)
        try:
            self.assertIn(doc.key, seen)
            obj = doc.obj
            self.assertEqual(obj.su_doc.kind, 'GROUP')
            self.assertLess((obj.matrix_world.translation - Vector((1, 2, 0))).length, 1e-6)
            self.assertGreater(len(obj.data.polygons), 0)
        finally:
            me = obj.data
            bpy.data.objects.remove(obj)
            bpy.data.meshes.remove(me)

    def test_place_on_vertical_face(self):
        m = text.place_matrix((0, 0, 1), (0, -1, 0))
        n = m.to_3x3() @ Vector((0, 0, 1))
        up = m.to_3x3() @ Vector((0, 1, 0))
        self.assertLess((n - Vector((0, -1, 0))).length, 1e-6)
        self.assertLess((up - Vector((0, 0, 1))).length, 1e-6)            # letters upright


class TestScenes(unittest.TestCase):
    def setUp(self):
        camera.pages().pages.clear()

    def tearDown(self):
        camera.pages().pages.clear()

    def test_add_update_remove(self):
        i = camera.add_page()
        j = camera.add_page()
        pg = camera.pages()
        self.assertEqual((i, j, pg.active), (0, 1, 1))
        self.assertEqual([p.name for p in pg.pages], ["Cena 1", "Cena 2"])
        region, rv3d = F.camera()
        v = View.from_rv3d(region, rv3d)
        camera.store_page(pg.pages[0], v)
        w = camera.page_view(pg.pages[0], v)
        self.assertTrue(w.same_as(v, 1e-5))
        self.assertTrue(camera.remove_page(1))
        self.assertEqual((len(pg.pages), pg.active), (1, 0))


if __name__ == "__main__":
    unittest.main()
