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
        mid = testing.pt(4, 0, 0, kind="MIDPOINT")                  # B5: door on the outer facade
        self.rect((4, 0, 0), face_inf((4.5, 0, 1)), "1;2,1", start=mid)
        self.pull((4.5, 0, 1), (4.5, 0.05, 1), "0,15")              # B6: through
        bm = document.root().bm
        sill = [f for f in bm.faces if geom_extrude.point_in_face(f, Vector((4.5, 0.075, 0.0)))]
        self.assertEqual(sill, [])                                  # doorway floor open, base cut into a "C"
        hole = [f for f in bm.faces if geom_extrude.point_in_face(f, Vector((4.5, 0.15, 1.0)))
                or geom_extrude.point_in_face(f, Vector((4.5, 0.0, 1.0)))]
        self.assertEqual(hole, [])
        self.assertEqual(self.stats()["non_planar"], 0)

    def test_primeiro_dia_slab_door(self):
        """PLANO §12 / scn_primeiro_dia passos 5–6: box 8×6×2,8, F 0,15 on the top, the inner face pushed
        2,65 down (room floor at z = 0,15), door 0,9×2,1 from the bottom-edge midpoint pushed 0,15 through:
        the doorway floor is open (bottom face cut into a notch), the wall face above the floor is perforated,
        and the slab front under the doorway (y = 0,15, z 0..0,15) is a face looking OUT (−Y)."""
        self.box(8, 6, "2,8")
        self.offset((4, 0.05, 2.8), (4, 0.3, 2.8), "0,15", side=1)
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), "su.pushpull", testing.pt(0, 0, 0))
        self.pull((4, 3, 2.8), (4, 3, 1.8), "2,65")
        self.assertEqual(self.counts()[2], 11)
        mid = testing.pt(4, 0, 0, kind="MIDPOINT")
        self.rect((4, 0, 0), face_inf((4.5, 0, 1)), "0,9;2,1", start=mid)
        self.assertEqual(self.counts()[2], 12)
        self.pull((4.45, 0, 1.05), (4.45, 0.12, 1.05), "0,15")
        bm = document.root().bm

        def at(x, y, z):
            return [f for f in bm.faces if geom_extrude.point_in_face(f, Vector((x, y, z)))]

        self.assertEqual(at(4.45, 0.075, 0.0), [])                 # doorway floor open
        self.assertEqual(at(4.45, 0.15, 1.0), [])                  # perforated above the room floor
        self.assertEqual(at(4.45, 0.0, 1.0), [])
        step = at(4.45, 0.15, 0.075)                                # slab front under the doorway
        self.assertEqual(len(step), 1)
        self.assertLess(step[0].normal.y, -0.99)
        self.assertEqual(self.stats()["non_planar"], 0)

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
