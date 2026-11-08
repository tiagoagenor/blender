# SPDX-License-Identifier: GPL-2.0-or-later
"""F tests: Girar (AC-GIR-1..3) through testing.dispatch."""

import math
import unittest

import bpy
from mathutils import Vector as V

from su import testing
from su.core import selection
from su.tools import base

from test_f_move import bbox, nonplanar
from test_f_select import FCase

ROTATE = "su.rotate"


class TestRotate(FCase):
    TOOL = ROTATE

    def tap(self, p, **mods):
        self.clock.t += 1
        inf = testing.pt(*p)
        testing.dispatch(testing.ev('LEFTMOUSE', 'PRESS', **mods), None, inf)
        testing.dispatch(testing.ev('LEFTMOUSE', 'RELEASE', **mods), None, inf)

    def test_ac_gir_1_protractor_plane_of_vertical_face(self):
        ctrl = base.controller(ROTATE)
        inf = testing.pt(4, 0, 1.5, kind="ON_FACE", elem=("FACE", self.face((4, 0, 1.5))), doc_key=self.key,
                         normal=V((0, -1, 0)), side=1)
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), None, inf)
        self.assertEqual(ctrl.axis, "Y")
        self.assertAlmostEqual(abs(ctrl.normal.y), 1.0)

    def test_ac_gir_2_exact_90(self):
        selection.select_all()
        before = selection.get()
        s0 = bpy.context.scene.su_undo_serial
        self.tap((0, 0, 0))
        self.tap((1, 0, 0))
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING', 5, 5), None, testing.pt(0.2, 1, 0))
        testing.type_text("90")
        mn, mx = bbox(self.doc.bm)
        self.assertAlmostEqual(mn.x, -6.0, places=4)
        self.assertAlmostEqual(mx.y, 8.0, places=4)
        self.assertEqual(nonplanar(self.doc.bm), 0)
        self.assertEqual(selection.get(), before)
        self.assertEqual(bpy.context.scene.su_undo_serial - s0, 1)

    def test_snap_15(self):
        selection.select_all()
        self.tap((0, 0, 0))
        self.tap((1, 0, 0))
        a = math.radians(44.0)
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING', 5, 5), None, testing.pt(math.cos(a), math.sin(a), 0))
        self.assertAlmostEqual(math.degrees(base.controller(ROTATE).angle), 45.0, places=4)
        testing.dispatch(testing.ev('ESC', 'PRESS'))
        self.assertAlmostEqual(bbox(self.doc.bm)[0].x, 0.0, places=5)

    def test_ac_gir_3_copy_array(self):
        selection.select_all()
        self.tap((0, 0, 0), copy=True)
        self.tap((1, 0, 0))
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING', 5, 5), None, testing.pt(0, 1, 0))
        testing.type_text("90")
        self.assertEqual(len(self.doc.bm.faces), 12)
        testing.type_text("3x")
        bm = self.doc.bm
        self.assertEqual(len(bm.faces), 24)
        mn, mx = bbox(bm)
        self.assertAlmostEqual(mn.x, -8.0, places=4)
        self.assertAlmostEqual(mn.y, -8.0, places=4)
        self.assertEqual(len(selection.get()), 18)


if __name__ == "__main__":
    unittest.main()
