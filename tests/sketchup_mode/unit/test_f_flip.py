# SPDX-License-Identifier: GPL-2.0-or-later
"""F tests: Virar (P1) — mirror in the box planes, normals outward, Option copy, 1 undo."""

import unittest

import bpy
from mathutils import Vector as V

from su import testing
from su.core import geom, selection
from su.core.selection import FACE, Ref

from test_f_move import bbox, nonplanar
from test_f_scale import signed_volume
from test_f_select import FCase

FLIP = "su.flip"


class TestFlip(FCase):
    TOOL = FLIP

    def tap(self, p, **mods):
        self.clock.t += 1
        inf = testing.pt(*p)
        testing.dispatch(testing.ev('LEFTMOUSE', 'PRESS', **mods), None, inf)
        testing.dispatch(testing.ev('LEFTMOUSE', 'RELEASE', **mods), None, inf)

    def test_flip_whole_box_in_place(self):
        selection.select_all()
        v0 = signed_volume(self.doc.bm)
        before = bbox(self.doc.bm)
        s0 = bpy.context.scene.su_undo_serial
        self.tap((4, 1, 1))                 # on the red (YZ) plane through the centre x=4
        self.assertEqual(bbox(self.doc.bm), before)
        self.assertGreater(signed_volume(self.doc.bm) * v0, 0)
        self.assertEqual(bpy.context.scene.su_undo_serial - s0, 1)

    def test_flip_face_copy(self):
        top = self.face((4, 3, 3))
        selection.set([Ref(self.key, FACE, top)])
        self.tap((4, 3, 3), copy=True)      # the face's box is flat in Z: the planes are X (red) and Y (green)
        self.assertEqual(len(self.doc.bm.faces), 7)
        self.assertEqual(nonplanar(self.doc.bm), 0)


if __name__ == "__main__":
    unittest.main()
