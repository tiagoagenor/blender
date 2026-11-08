# SPDX-License-Identifier: GPL-2.0-or-later
"""F tests: Escala (AC-ESC-1..4) through testing.dispatch."""

import unittest

import bpy
from mathutils import Vector as V

from su import testing
from su.core import document, selection, state
from su.core.selection import OBJECT, Ref

from test_f_move import bbox, nonplanar
from test_f_select import FCase

SCALE = "su.scale"


def signed_volume(bm):
    vol = 0.0
    for f in bm.faces:
        vs = [v.co for v in f.verts]
        for i in range(1, len(vs) - 1):
            vol += vs[0].dot(vs[i].cross(vs[i + 1])) / 6.0
    return vol


class TestScale(FCase):
    TOOL = SCALE

    def grip(self, p, **mods):
        self.clock.t += 1
        inf = testing.pt(*p)
        testing.dispatch(testing.ev('LEFTMOUSE', 'PRESS', **mods), None, inf)
        testing.dispatch(testing.ev('LEFTMOUSE', 'RELEASE', **mods), None, inf)

    def test_ac_esc_1_corner_uniform(self):
        selection.select_all()
        before = selection.get()
        s0 = bpy.context.scene.su_undo_serial
        self.grip((8, 6, 3))
        testing.type_text("2")
        mn, mx = bbox(self.doc.bm)
        self.assertEqual(tuple(round(c, 4) for c in mx), (16.0, 12.0, 6.0))
        self.assertEqual(tuple(round(c, 4) for c in mn), (0.0, 0.0, 0.0))
        self.assertEqual(selection.get(), before)
        self.assertEqual(bpy.context.scene.su_undo_serial - s0, 1)
        self.assertEqual(state.STATE.vcb_value, "2,00")          # uniform: ONE factor (SketchUp)

    def test_ac_esc_2_face_length(self):
        selection.select_all()
        self.grip((8, 3, 1.5))
        testing.type_text("3m")
        mn, mx = bbox(self.doc.bm)
        self.assertAlmostEqual(mx.x, 3.0, places=4)
        self.assertAlmostEqual(mx.y, 6.0, places=4)
        self.assertEqual(state.STATE.vcb_value.count(";"), 0)  # face grip: 1 value
        self.assertAlmostEqual(mx.z, 3.0, places=4)

    def test_ac_esc_3_mirror_keeps_normals_out(self):
        selection.select_all()
        v0 = signed_volume(self.doc.bm)
        self.grip((8, 3, 1.5))
        testing.type_text("-1")
        mn, mx = bbox(self.doc.bm)
        self.assertAlmostEqual(mn.x, -8.0, places=4)
        self.assertAlmostEqual(mx.x, 0.0, places=4)
        self.assertGreater(v0 * signed_volume(self.doc.bm), 0.0)
        self.assertEqual(nonplanar(self.doc.bm), 0)

    def test_ac_esc_4_group_matrix_only(self):
        g = document.group_from(self.doc, [self.face((4, 3, 3))], [])
        g.write(undo_key=None)
        self.doc.write(undo_key=None)
        co = [v.co.copy() for v in g.bm.verts]
        selection.set([Ref(g.key, OBJECT, 0)])
        self.grip((8, 6, 3))
        testing.type_text("2")
        self.assertAlmostEqual(g.obj.matrix_world.to_scale().x, 2.0, places=4)
        self.assertEqual([v.co.copy() for v in document.get_by_key(g.key).bm.verts], co)

    def test_drag_edge_grip_two_axes(self):
        selection.select_all()
        self.clock.t += 1
        testing.dispatch(testing.ev('LEFTMOUSE', 'PRESS', 0, 0), None, testing.pt(8, 6, 1.5))
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING', 0, 40), None, testing.pt(16, 12, 1.5))
        testing.dispatch(testing.ev('LEFTMOUSE', 'RELEASE', 0, 80), None, testing.pt(16, 12, 1.5))
        mn, mx = bbox(self.doc.bm)
        self.assertEqual(tuple(round(c, 4) for c in mx), (16.0, 12.0, 3.0))
        self.assertEqual(state.STATE.vcb_value, "2,00; 2,00")   # edge grip: 2 axes, 2 values


if __name__ == "__main__":
    unittest.main()
