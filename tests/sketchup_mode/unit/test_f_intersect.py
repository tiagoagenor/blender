# SPDX-License-Identifier: GPL-2.0-or-later
"""F tests: Interseccionar faces (P1) — a plane through a box splits 4 of its faces."""

import unittest

import bpy
from mathutils import Vector as V

from su.core import document, geom, selection
from su.core.selection import OBJECT, Ref
from su.ops import edit_ops

from test_f_move import nonplanar
from test_f_select import FCase


class TestIntersect(FCase):
    def test_plane_through_box(self):
        g = document.create_group("Plano")
        geom.add_polyline(g.bm, [V((4, -1, -1)), V((4, 7, -1)), V((4, 7, 4)), V((4, -1, 4))], True)
        g.write(undo_key=None)
        selection.set([Ref(g.key, OBJECT, 0)])
        s0 = bpy.context.scene.su_undo_serial
        n = edit_ops.intersect_faces('MODEL')
        self.assertEqual(n, 4)
        self.assertEqual(bpy.context.scene.su_undo_serial - s0, 1)
        bm = self.doc.bm
        self.assertEqual(len(bm.faces), 11)      # 4 split faces + the section face the closed loop makes
        self.assertEqual(nonplanar(bm), 0)
        self.assertEqual(geom.validate(bm), [])


if __name__ == "__main__":
    unittest.main()
