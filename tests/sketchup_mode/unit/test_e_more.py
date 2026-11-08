# SPDX-License-Identifier: GPL-2.0-or-later
"""E: tools promoted from P2 — Retângulo girado, Arco de três pontos, Pizza, Desenho à mão livre."""

import math
import unittest

from mathutils import Vector

from su import testing
from su.core import document, entities, geom
from su.tools import base, catalog

from test_e_rectangle import ToolCase


class TestRegistered(unittest.TestCase):
    def test_enabled_in_catalog(self):
        for tid in ("su.rotated_rectangle", "su.arc3", "su.pie", "su.freehand", "su.arc"):
            self.assertTrue(catalog.is_enabled(tid), tid)
            self.assertNotEqual(base.TOOLS[tid].meta.priority, "P2", tid)


class TestRotatedRectangle(ToolCase):
    TOOL = "su.rotated_rectangle"

    def test_three_clicks_tilted(self):
        testing.click((0, 0, 0))
        testing.click((2, 0, 0))                     # first edge along X
        testing.move((2, 1, 1))                      # width tilted 45° about the edge
        r = testing.click((2, 1, 1))
        self.assertIs(r, base.Result.IDLE)
        st = self.stats()
        self.assertEqual((st["verts"], st["edges"], st["faces"]), (4, 4, 1))
        self.assertAlmostEqual(st["area"], 2 * math.sqrt(2), places=5)
        n = Vector(st["normals"][0])
        self.assertAlmostEqual(abs(n.y), math.sqrt(0.5), places=5)
        self.assertAlmostEqual(abs(n.z), math.sqrt(0.5), places=5)
        self.assertEqual(self.steps(), 1)

    def test_typed_length_width_angle(self):
        testing.click((0, 0, 0))
        testing.move((1, 0, 0))
        testing.type_text("3")                       # first edge length
        self.assertEqual(testing.state_dump()["hint_key"], "tool.su.rotated_rectangle.hint_width")
        testing.move((3, 1, 0))
        testing.type_text("2;90")                    # width 2, angle 90° (vertical)
        st = self.stats()
        bb = st["bbox"]
        self.assertAlmostEqual(bb[1][0], 3.0, places=5)
        self.assertAlmostEqual(bb[1][2] - bb[0][2], 2.0, places=5)
        self.assertAlmostEqual(bb[1][1] - bb[0][1], 0.0, places=5)
        self.assertAlmostEqual(st["area"], 6.0, places=5)


class TestArc3(ToolCase):
    TOOL = "su.arc3"

    def test_semicircle_through_three_points(self):
        testing.click((0, 0, 0))
        testing.click((1, 1, 0))                     # passes through the top
        testing.move((2, 0, 0))
        r = testing.click((2, 0, 0))
        self.assertIs(r, base.Result.IDLE)
        st = self.stats()
        self.assertEqual((st["verts"], st["edges"]), (13, 12))
        bb = st["bbox"]
        self.assertAlmostEqual(bb[1][1], 1.0, places=5)
        self.assertAlmostEqual(bb[0][1], 0.0, places=5)
        bm = document.root().bm
        lay = geom.layers(bm)
        meta = entities.get_curve_meta(document.root(), next(iter({e[lay.curve] for e in bm.edges})))
        self.assertAlmostEqual(meta["radius"], 1.0, places=5)
        self.assertEqual([round(c, 5) for c in meta["center"]], [1.0, 0.0, 0.0])

    def test_major_arc_and_segments(self):
        testing.type_text("8s")
        testing.click((1, 0, 0))
        testing.click((-1, 0, 0))                    # opposite side: the arc goes the long way round
        testing.click((0, -1, 0))
        st = self.stats()
        self.assertEqual(st["edges"], 8)
        bb = st["bbox"]
        self.assertGreater(bb[1][1], 0.95)                  # goes over the top (0, 1): 270° sweep
        self.assertAlmostEqual(bb[0][1], -1.0, places=5)

    def test_collinear_keeps_drawing(self):
        testing.click((0, 0, 0))
        testing.click((1, 0, 0))
        r = testing.click((2, 0, 0))
        self.assertIs(r, base.Result.RUNNING)
        self.assertEqual(testing.doc_stats()["edges"], 0)


class TestPie(ToolCase):
    TOOL = "su.pie"

    def test_quarter_pie_is_a_face(self):
        testing.click((0, 0, 0))
        testing.click((2, 0, 0))
        testing.move((0.02, 2, 0))
        testing.click((0.02, 2, 0))                  # snaps to 90°
        st = self.stats()
        self.assertEqual((st["verts"], st["edges"], st["faces"]), (14, 14, 1))
        self.assertAlmostEqual(st["area"], 0.5 * 12 * 4 * math.sin(math.pi / 24), places=4)
        self.assertEqual(st["normals"], [[0.0, 0.0, -1.0]])
        self.assertEqual(self.steps(), 1)


class TestFreehand(ToolCase):
    TOOL = "su.freehand"

    def stroke(self, pts, close=False):
        testing.dispatch(testing.ev('LEFTMOUSE', 'PRESS', 0, 0), None, testing.pt(*pts[0]))
        for i, p in enumerate(pts[1:-1]):
            testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING', 10 + i, 0), None, testing.pt(*p))
        return testing.dispatch(testing.ev('LEFTMOUSE', 'RELEASE', 200, 200), None, testing.pt(*pts[-1]))

    def test_open_stroke_is_one_curve(self):
        pts = [(x * 0.1, math.sin(x * 0.3), 0) for x in range(21)]
        r = self.stroke(pts)
        self.assertIs(r, base.Result.IDLE)
        st = self.stats()
        self.assertEqual(st["faces"], 0)
        self.assertGreater(st["edges"], 10)
        bm = document.root().bm
        lay = geom.layers(bm)
        self.assertEqual(len({e[lay.curve] for e in bm.edges}), 1)
        self.assertEqual(self.steps(), 1)

    def test_closed_stroke_makes_a_face(self):
        pts = [(math.cos(a * math.pi / 20), math.sin(a * math.pi / 20), 0) for a in range(41)]
        self.stroke(pts)
        st = self.stats()
        self.assertEqual(st["faces"] >= 1, True)
        self.assertAlmostEqual(st["area"], math.pi, delta=0.05)

    def test_click_without_drag_draws_nothing(self):
        testing.click((0, 0, 0))
        self.assertEqual(testing.doc_stats()["edges"], 0)
        self.assertFalse(base.DISPATCH.running)


if __name__ == "__main__":
    unittest.main()
