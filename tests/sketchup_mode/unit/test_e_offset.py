# SPDX-License-Identifier: GPL-2.0-or-later
"""E: Equidistância through testing.dispatch — AC-EQD-1..3, ROTEIRO_CASA B2 (+ B3/B4 with Excluir in the
kernel), outward offset, retype, Esc."""

import unittest

from mathutils import Vector

from su import testing
from su.core import document, geom, geom_extrude
from su.tools import base

from test_e_pushpull import PPCase, face_inf

OFFSET = "su.offset"


class TestOffset(PPCase):
    TOOL = OFFSET

    def offset(self, p, toward, text, side=-1):
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), OFFSET, testing.pt(*p))
        testing.click(face_inf(p, side))
        testing.move(toward)
        return testing.type_text(text)

    def test_ac_eqd_1(self):
        self.rect((0, 0, 0), (1, 1, 0), "2;2")
        self.offset((0.1, 1, 0), (0.3, 1, 0), "0,5")
        self.assertFalse(base.DISPATCH.running)
        self.assertEqual(self.counts(), (8, 8, 2))
        self.assertEqual(self.logical_areas(), [1.0, 3.0])
        self.assertEqual(self.steps(), 2)

    def test_roteiro_b2_b3_b4(self):
        self.rect((0, 0, 0), (1, 1, 0), "8;6")
        self.offset((0.05, 3, 0), (0.1, 3, 0), "0,15")
        self.assertEqual(self.counts(), (8, 8, 2))
        self.assertEqual(self.logical_areas(), [4.11, 43.89])
        doc = document.root()                       # B3: Excluir the inner face (F's tool: kernel here)
        geom.erase_faces(doc.bm, geom_extrude.faces_at(doc.bm, Vector((4, 3, 0))))
        doc.write(undo_key="test")
        self.assertEqual(self.counts(), (8, 8, 1))
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), "su.pushpull", testing.pt(0, 0, 0))
        self.pull((0.07, 3, 0), (0.07, 3, 1), "2,8", side=-1)       # B4
        self.assertEqual(self.counts(), (16, 24, 10))

    def test_ac_eqd_2_double_click(self):
        self.rect((0, 0, 0), (1, 1, 0), "2;2")
        self.rect((5, 0, 0), (6, 1, 0), "2;2")
        self.offset((0.1, 1, 0), (0.3, 1, 0), "0,25")
        testing.click(face_inf((6, 1, 0), -1), x=300, y=300)
        testing.click(face_inf((6, 1, 0), -1), x=300, y=300)
        self.assertFalse(base.DISPATCH.running)
        self.assertEqual(self.counts(), (16, 16, 4))
        self.assertEqual(self.logical_areas(), [1.75, 1.75, 2.25, 2.25])

    def test_ac_eqd_3_face_with_hole(self):
        self.rect((0, 0, 0), (1, 1, 0), "4;4")
        self.rect((1.5, 1.5, 0), (2, 2, 0), "1;1", start=face_inf((1.5, 1.5, 0), -1))
        doc = document.root()
        geom.erase_faces(doc.bm, geom_extrude.faces_at(doc.bm, Vector((2, 2, 0))))
        doc.write(undo_key="test")
        self.offset((0.1, 2, 0), (0.2, 2, 0), "0,25")
        self.assertEqual(self.counts(), (16, 16, 3))
        self.assertEqual(self.logical_areas(), [1.25, 3.75, 10.0])

    def test_outward_and_retype(self):
        self.rect((0, 0, 0), (1, 1, 0), "2;2")
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), OFFSET, testing.pt(0, 0, 0))
        testing.click(face_inf((0.1, 1, 0), -1))
        testing.move((-0.3, 1, 0))                   # outside: grows
        testing.type_text("1")
        self.assertEqual(self.stats()["bbox"], [[-1.0, -1.0, 0.0], [3.0, 3.0, 0.0]])
        self.assertEqual(self.logical_areas(), [4.0, 12.0])
        testing.type_text("0,5")                     # retype
        self.assertEqual(self.stats()["bbox"], [[-0.5, -0.5, 0.0], [2.5, 2.5, 0.0]])

    def test_too_big_is_refused_and_esc(self):
        self.rect((0, 0, 0), (1, 1, 0), "2;2")
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), OFFSET, testing.pt(0, 0, 0))
        testing.click(face_inf((0.1, 1, 0), -1))
        testing.move((0.3, 1, 0))
        testing.type_text("1,5")
        self.assertTrue(base.DISPATCH.running)
        self.assertEqual(self.counts(), (4, 4, 1))
        testing.dispatch(testing.ev('ESC', 'PRESS'))     # clears the typed value
        testing.dispatch(testing.ev('ESC', 'PRESS'))     # cancels
        self.assertFalse(base.DISPATCH.running)
        self.assertEqual(self.counts(), (4, 4, 1))


if __name__ == "__main__":
    unittest.main()
