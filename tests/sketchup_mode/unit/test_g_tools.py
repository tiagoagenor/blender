# SPDX-License-Identifier: GPL-2.0-or-later
"""G: Fita métrica, Transferidor, Dimensões through testing.dispatch (headless) + guides as inference
sources for C's engine (AC-FIT-1..4, AC-TRA-1..2, AC-DIM-1)."""

import math
import unittest

import bpy
from mathutils import Vector

import test_c_fakes as F
from su import perf, testing
from su.core import guides, state
from su.core.inference import InferenceEngine, QueryCtx
from su.core.state import Inference, Locks
from su.tools import base


def pt(x, y, z=0.0, kind="FREE", **kw):
    return testing.pt(x, y, z, kind=kind, **kw)


class GCase(unittest.TestCase):
    TOOL = ""

    def setUp(self):
        self.n_err = perf.errors()
        base.DISPATCH.reset()
        base._instances.pop(self.TOOL, None)
        state.STATE.reset()
        guides.delete_guides()
        d = guides.data()
        d.dims.clear()
        d.texts.clear()
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), self.TOOL, pt(0, 0))
        self.serial0 = bpy.context.scene.su_undo_serial

    def tearDown(self):
        base.DISPATCH.set_tool(base.ToolContext(), '')
        guides.delete_guides()
        self.assertEqual(perf.errors(), self.n_err, perf.messages()[self.n_err:])

    def steps(self):
        return bpy.context.scene.su_undo_serial - self.serial0

    def click(self, inf, **kw):
        return testing.click(inf, **kw)


class TestTape(GCase):
    TOOL = "su.tape"

    def test_ac_fit_1_parallel_guide_typed(self):
        edge = pt(1, 0, 0, "ON_EDGE", direction=Vector((1, 0, 0)))
        self.click(edge)
        self.assertTrue(base.DISPATCH.running)
        testing.move(pt(1.3, 0.3, 0))
        self.assertEqual(testing.state_dump()["hint_key"], "tool.su.tape.hint_offset")
        testing.type_text("0,5")
        self.assertFalse(base.DISPATCH.running)
        g = guides.data().guides
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0].kind, 'LINE')
        self.assertLess((Vector(g[0].direction) - Vector((1, 0, 0))).length, 1e-6)
        # the guide line is at 0.5 from the edge line (y = 0.5, z = 0)
        self.assertAlmostEqual(g[0].co[1], 0.5, places=6)
        self.assertAlmostEqual(g[0].co[2], 0.0, places=6)
        self.assertEqual(self.steps(), 1)

    def test_parallel_guide_click_and_retype(self):
        self.click(pt(0, 0, 0, "ON_EDGE", direction=Vector((0, 1, 0))))
        testing.move(pt(2, 1, 0))
        self.click(pt(2, 1, 0))
        g = guides.data().guides
        self.assertEqual(len(g), 1)
        self.assertAlmostEqual(g[0].co[0], 2.0, places=6)
        testing.type_text("3")                       # idle retype = Ajustar
        self.assertAlmostEqual(guides.data().guides[0].co[0], 3.0, places=6)
        self.assertEqual(self.steps(), 2)

    def test_ac_fit_2_measure_only(self):
        self.click(pt(0, 0, 0, "ENDPOINT"))
        testing.dispatch(testing.ev('LEFT_ALT', 'PRESS', copy=True))      # Option tap: measure only
        testing.move(pt(3, 4, 0))
        self.click(pt(3, 4, 0))
        self.assertEqual(len(guides.data().guides), 0)
        self.assertEqual(testing.state_dump()["vcb_value"], "5,00m")
        self.assertEqual(self.steps(), 0)
        # toggle back: guides again
        self.click(pt(0, 0, 0, "ENDPOINT"))
        testing.dispatch(testing.ev('LEFT_ALT', 'PRESS', copy=True))
        self.click(pt(1, 0, 0))
        self.assertEqual(len(guides.data().guides), 1)

    def test_ac_fit_3_guide_point(self):
        self.click(pt(1, 1, 0, "ENDPOINT"))
        testing.move(pt(1, 3, 0))
        self.click(pt(1, 3, 0))
        g = guides.data().guides
        self.assertEqual((len(g), g[0].kind), (1, 'POINT'))
        self.assertLess((Vector(g[0].co) - Vector((1, 3, 0))).length, 1e-6)
        self.assertLess((Vector(g[0].anchor) - Vector((1, 1, 0))).length, 1e-6)

    def test_guide_point_typed_and_esc(self):
        self.click(pt(0, 0, 0, "ENDPOINT"))
        testing.move(pt(0, 0, 2))
        testing.type_text("1,5")
        self.assertLess((Vector(guides.data().guides[0].co) - Vector((0, 0, 1.5))).length, 1e-6)
        self.click(pt(0, 0, 0, "ENDPOINT"))
        testing.dispatch(testing.ev('ESC', 'PRESS'))
        self.assertFalse(base.DISPATCH.running)
        self.assertEqual(len(guides.data().guides), 1)


class TestProtractor(GCase):
    TOOL = "su.protractor"

    def test_ac_tra_2_angle_guide(self):
        self.click(pt(0, 0, 0, "ORIGIN"))
        self.click(pt(1, 0, 0, "ON_EDGE"))                 # baseline +X
        self.assertTrue(base.DISPATCH.running)
        testing.move(pt(0.6, 0.4, 0))                       # positive side (+Y)
        self.assertEqual(testing.state_dump()["hint_key"], "tool.su.protractor.hint_angle")
        testing.type_text("30")
        g = guides.data().guides
        self.assertEqual(len(g), 1)
        d = Vector(g[0].direction)
        self.assertLess((d - Vector((math.cos(math.radians(30)), math.sin(math.radians(30)), 0))).length, 1e-6)
        self.assertLess(Vector(g[0].co).length, 1e-9)
        self.assertEqual(self.steps(), 1)

    def test_negative_side_and_click_snap(self):
        self.click(pt(0, 0, 0))
        self.click(pt(1, 0, 0))
        testing.move(pt(0.5, -0.5, 0))
        testing.type_text("45")
        d = Vector(guides.data().guides[0].direction)
        self.assertLess((d - Vector((math.sqrt(0.5), -math.sqrt(0.5), 0))).length, 1e-6)
        # click: snapped to 15° (headless = always near the gizmo)
        self.click(pt(0, 0, 0))
        self.click(pt(1, 0, 0))
        a = math.radians(32.0)
        self.click(pt(math.cos(a), math.sin(a), 0))
        d = Vector(guides.data().guides[1].direction)
        self.assertLess((d - Vector((math.cos(math.radians(30)), math.sin(math.radians(30)), 0))).length, 1e-6)

    def test_ac_tra_1_plane_of_vertical_face(self):
        face = pt(2, 0, 1, "ON_FACE", normal=Vector((0, -1, 0)), side=1)
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), None, face)
        ctrl = base.controller("su.protractor")
        self.assertLess((ctrl.normal - Vector((0, -1, 0))).length, 1e-6)
        self.assertEqual(ctrl.axis, "Y")                   # green protractor (XZ plane)
        self.click(face)
        self.click(pt(3, 0, 1))                             # baseline +X in the face plane
        testing.move(pt(2.5, 0, 1.5))
        testing.type_text("90")
        d = Vector(guides.data().guides[0].direction)
        self.assertAlmostEqual(abs(d.z), 1.0, places=6)    # vertical guide in the face plane

    def test_option_measure_only(self):
        self.click(pt(0, 0, 0), copy=True)
        self.click(pt(1, 0, 0))
        testing.move(pt(0, 1, 0))
        testing.type_text("60")
        self.assertEqual(len(guides.data().guides), 0)
        self.assertEqual(testing.state_dump()["vcb_value"], "60,0°")


class TestDimension(GCase):
    TOOL = "su.dimension"

    def test_two_points_and_offset(self):
        self.click(pt(0, 0, 0, "ENDPOINT"))
        self.click(pt(3, 0, 0, "ENDPOINT"))
        self.assertTrue(base.DISPATCH.running)
        testing.move(pt(1, -0.5, 0))
        self.click(pt(1, -0.5, 0))
        d = guides.data().dims
        self.assertEqual(len(d), 1)
        self.assertLess((Vector(d[0].offset) - Vector((0, -0.5, 0))).length, 1e-6)
        self.assertEqual(guides.dimension_text(0), "3,00m")              # AC-DIM-1
        self.assertEqual(self.steps(), 1)

    def test_ac_dim_1_click_on_edge(self):
        from su.core import document
        testing.reset_model()
        doc = document.root()
        v0, v1 = doc.bm.verts.new((0, 0, 0)), doc.bm.verts.new((0, 3, 0))
        doc.bm.edges.new((v0, v1))
        doc.write(undo_key=None)
        inf = pt(0, 1.2, 0, "ON_EDGE", ref_edge=(doc.key, 0), doc_key=doc.key, direction=Vector((0, 1, 0)))
        self.click(inf)
        ctrl = base.controller("su.dimension")
        self.assertEqual(ctrl.stage, 2)
        self.click(pt(-0.4, 1, 0))
        self.assertEqual(guides.dimension_text(0), "3,00m")
        testing.reset_model()


class TestGuidesInference(unittest.TestCase):
    """AC-FIT-4 / AC-TRA-2: C's engine snaps to guide lines and their intersections."""

    def setUp(self):
        F.cleanup()
        F.isolate_scene()
        guides.delete_guides()
        self.region, self.rv3d = F.camera()
        self.engine = InferenceEngine()

    def tearDown(self):
        guides.delete_guides()
        F.cleanup()

    def query(self, co, dx=0.0, dy=0.0):
        s = F.project(self.region, self.rv3d, co)
        return self.engine.query(QueryCtx(self.region, self.rv3d, (s[0] + dx, s[1] + dy), locks=Locks()))

    def test_on_guide_line(self):
        a = math.radians(30)
        guides.add_guide_line((0, 0, 0), (math.cos(a), math.sin(a), 0))
        p = Vector((math.cos(a), math.sin(a), 0)) * 2.0
        inf = self.query(p, 2, 1)
        self.assertEqual(inf.kind, "ON_GUIDE")
        self.assertLess((inf.point - p).length, 0.05)

    def test_ac_fit_4_intersection_of_guides(self):
        guides.add_guide_line((0, 1.5, 0), (1, 0, 0))
        guides.add_guide_line((2.5, 0, 0), (0, 1, 0))
        inf = self.query((2.5, 1.5, 0), 3, -2)
        self.assertEqual(inf.kind, "INTERSECTION")
        self.assertLess((inf.point - Vector((2.5, 1.5, 0))).length, 1e-6)

    def test_guide_point(self):
        guides.add_guide_point((1, 2, 0), (0, 0, 0))
        inf = self.query((1, 2, 0), 3, 2)
        self.assertEqual(inf.kind, "GUIDE_POINT")

    def test_hidden_guides_not_inferable(self):
        guides.add_guide_point((1, 2, 0), (0, 0, 0))
        st = bpy.context.scene.su_style
        st.show_guides = False
        try:
            self.assertEqual(guides.guides_arrays(), {"points": [], "lines": []})
        finally:
            st.show_guides = True


if __name__ == "__main__":
    unittest.main()
