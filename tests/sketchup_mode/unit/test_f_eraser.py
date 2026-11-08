# SPDX-License-Identifier: GPL-2.0-or-later
"""F tests: Apagar (AC-APG-1..4; ROTEIRO_CASA AF-3, AF-3b, AF-3c) through testing.dispatch."""

import unittest

import bpy
from mathutils import Vector as V

from su import testing
from su.core import document, geom, selection

from test_b_geom import box, counts, find_edge, rect
from test_f_select import FCase

ERASER = "su.eraser"


class TestEraser(FCase):
    TOOL = ERASER

    def steps(self, fn):
        s0 = bpy.context.scene.su_undo_serial
        fn()
        return bpy.context.scene.su_undo_serial - s0

    def test_af3_edge_takes_its_faces(self):
        e = self.edge((0, 0, 3), (8, 0, 3))
        n = self.steps(lambda: self.click(self.inf_edge(e)))
        self.assertEqual(counts(self.doc.bm), (8, 11, 4))
        self.assertEqual(n, 1)
        self.assertEqual(geom.validate(self.doc.bm), [])

    def test_af3b_face_click_does_nothing(self):
        n = self.steps(lambda: self.click(self.inf_face(self.face((4, 3, 3)))))
        self.assertEqual(counts(self.doc.bm), (8, 12, 6))
        self.assertEqual(n, 0)

    def test_ac_apg_1_dividing_line_merges(self):
        bm = self.doc.bm
        bm.clear()
        rect(bm, 0, 0, 4, 2)
        geom.add_edge(bm, V((2, 0, 0)), V((2, 2, 0)))
        self.doc.write(undo_key=None)
        self.assertEqual(len(self.doc.bm.faces), 2)
        self.click(self.inf_edge(self.edge((2, 0, 0), (2, 2, 0))))
        self.assertEqual(counts(self.doc.bm), (4, 4, 1))

    def test_ac_apg_2_drag_over_curve_one_step(self):
        bm = self.doc.bm
        bm.clear()
        pts = geom.circle_points(V((0, 0, 0)), V((0, 0, 1)), 1.0, 24)
        geom.add_polyline(bm, pts, True, curve_id=3)
        self.doc.write(undo_key=None)
        e0, e1 = self.doc.bm.edges[0].index, self.doc.bm.edges[5].index
        s0 = bpy.context.scene.su_undo_serial
        self.clock.t += 1
        testing.dispatch(testing.ev('LEFTMOUSE', 'PRESS'), None, self.inf_edge(e0))
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING', 20, 0), None, self.inf_edge(e1))
        testing.dispatch(testing.ev('LEFTMOUSE', 'RELEASE', 40, 0), None, self.inf_edge(e1))
        self.assertEqual(len(self.doc.bm.edges), 0)
        self.assertEqual(bpy.context.scene.su_undo_serial - s0, 1)

    def test_ac_apg_3_option_softens(self):
        e = self.edge((8, 0, 0), (8, 0, 3))
        self.click(self.inf_edge(e), copy=True)
        bm = self.doc.bm
        lay = geom.layers(bm)
        ed = find_edge(bm, (8, 0, 0), (8, 0, 3))
        self.assertTrue(ed[lay.soft])
        self.assertTrue(all(f.smooth for f in ed.link_faces))
        self.assertEqual(counts(bm), (8, 12, 6))
        # Shift+Option unsoftens
        self.click(self.inf_edge(ed.index), copy=True, shift=True)
        ed = find_edge(self.doc.bm, (8, 0, 0), (8, 0, 3))
        self.assertFalse(ed[geom.layers(self.doc.bm).soft])

    def test_shift_hides(self):
        e = self.edge((0, 0, 3), (8, 0, 3))
        self.click(self.inf_edge(e), shift=True)
        bm = self.doc.bm
        self.assertTrue(find_edge(bm, (0, 0, 3), (8, 0, 3))[geom.layers(bm).hidden])
        self.assertEqual(len(bm.faces), 6)

    def test_ac_apg_4_group_goes(self):
        g = document.group_from(self.doc, [self.face((4, 3, 3))], [])
        g.write(undo_key=None)
        self.doc.write(undo_key=None)
        name = g.key
        self.click(self.inf_edge(0, key=name))
        self.assertIsNone(bpy.data.objects.get(name))


if __name__ == "__main__":
    unittest.main()
