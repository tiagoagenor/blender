# SPDX-License-Identifier: GPL-2.0-or-later
"""E: Linha (assumida de A) — AC-LIN-2 (diagonal / cruzamento), AC-LIN-3 (cura), AC-LIN-4 (borda a borda
numa face vertical), AC-LIN-5 (laço vertical com ↑), double click, retype (Ajustar) after a chain."""

import unittest

from mathutils import Vector

from su import testing
from su.core import document, geom, geom_extrude
from su.tools import base

from test_e_pushpull import PPCase

LINE = "su.line"


class TestLine(PPCase):
    TOOL = LINE

    def line(self, *pts):
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), LINE, testing.pt(0, 0, 0))
        r = None
        for p in pts:
            r = testing.click(p if not isinstance(p, tuple) else testing.pt(*p, kind="ENDPOINT"))
        return r

    def test_ac_lin_2_diagonal_and_crossing(self):
        self.rect((0, 0, 0), (1, 1, 0), "4;4")
        r = self.line((0, 0, 0), (4, 4, 0))
        self.assertIs(r, base.Result.IDLE)                      # a split face ends the chain
        self.assertEqual(self.counts(), (4, 5, 2))
        self.line((4, 0, 0), (0, 4, 0))
        self.assertEqual(self.counts(), (5, 8, 4))
        self.assertEqual(self.logical_areas(), [4.0, 4.0, 4.0, 4.0])
        st = self.stats()
        self.assertTrue(all(n == [0.0, 0.0, -1.0] for n in st["normals"]))

    def test_ac_lin_3_heal_top(self):
        self.box(8, 6, "3")
        doc = document.root()
        geom.erase_faces(doc.bm, geom_extrude.faces_at(doc.bm, Vector((4, 3, 3))))
        doc.write(undo_key="test")
        self.assertEqual(self.counts(), (8, 12, 5))
        r = self.line((0, 0, 3), (8, 0, 3))
        self.assertIs(r, base.Result.IDLE)
        self.assertEqual(self.counts(), (8, 12, 6))
        self.assert_closed_out()

    def test_ac_lin_4_edge_to_edge_on_wall(self):
        self.rect((0, 0, 0), (2, 0, 3), "4;3")
        self.assertEqual(abs(self.stats()["normals"][0][1]), 1.0)
        self.line(testing.pt(0, 0, 1.5, kind="ON_EDGE"), testing.pt(4, 0, 1.5, kind="ON_EDGE"))
        self.assertEqual(self.counts(), (6, 7, 2))
        self.assertEqual(self.logical_areas(), [6.0, 6.0])

    def test_ac_lin_5_vertical_loop_with_up_lock(self):
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), LINE, testing.pt(0, 0, 0))
        testing.click((0, 0, 0))
        testing.dispatch(testing.ev('UP_ARROW', 'PRESS'))
        testing.move(testing.pt(0, 0, 1, linear="AXIS_Z", locked=True))
        testing.type_text("2")
        testing.dispatch(testing.ev('UP_ARROW', 'PRESS'))           # unlock
        testing.click((2, 0, 2))
        testing.click((2, 0, 0))
        r = testing.click(testing.pt(0, 0, 0, kind="ENDPOINT"))
        self.assertIs(r, base.Result.IDLE)
        st = self.stats()
        self.assertEqual(self.counts(), (4, 4, 1))
        self.assertAlmostEqual(abs(st["normals"][0][1]), 1.0, places=6)
        self.assertEqual(st["bbox"], [[0.0, 0.0, 0.0], [2.0, 0.0, 2.0]])

    def test_double_click_ends_chain(self):
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), LINE, testing.pt(0, 0, 0))
        testing.click((0, 0, 0), x=10, y=10)
        testing.click((1, 0, 0), x=100, y=10)
        r = testing.click((1, 0, 0), x=100, y=10)
        self.assertIs(r, base.Result.IDLE)
        self.assertEqual(self.counts(), (2, 1, 0))
        self.assertEqual(self.steps(), 1)

    def test_retype_last_segment_of_chain(self):
        self.line((0, 0, 0), (1, 0, 0), (1, 1, 0))
        testing.dispatch(testing.ev('ESC', 'PRESS'))
        testing.type_text("2")
        st = self.stats()
        self.assertEqual(self.counts(), (3, 2, 0))
        self.assertEqual(st["bbox"], [[0.0, 0.0, 0.0], [1.0, 2.0, 0.0]])
        self.assertEqual(self.steps(), 3)

    def test_retype_after_closing_segment(self):
        self.line((0, 0, 0), (2, 0, 0), (0, 2, 0), (0, 0, 0))
        self.assertEqual(self.counts(), (3, 3, 1))
        testing.type_text("1")
        self.assertEqual(self.counts(), (4, 3, 0))          # the closing segment is now 1 m: no face
        testing.type_text("2")
        self.assertEqual(self.counts(), (3, 3, 1))          # back to 2 m: the face again


if __name__ == "__main__":
    unittest.main()
