# SPDX-License-Identifier: GPL-2.0-or-later
"""F tests: materials + Pintura (AC-PNT-1..4) through testing.dispatch."""

import unittest

import bpy
from mathutils import Vector as V

from su import testing
from su.core import document, geom, materials, selection
from su.core.selection import FACE, Ref

from test_b_geom import rect
from test_f_select import FCase

PAINT = "su.paint"


class TestMaterials(FCase):
    BOX = False

    def test_slots_and_paint_sides(self):
        rect(self.doc.bm, 0, 0, 2, 2)
        self.doc.write(undo_key=None)
        red = materials.palette_material(0)
        self.assertEqual(materials.slot_for(self.doc.obj, None, 1), 0)
        self.assertEqual(materials.slot_for(self.doc.obj, None, -1), 1)
        s = materials.slot_for(self.doc.obj, red)
        self.assertEqual(s, 2)
        self.assertEqual(materials.slot_for(self.doc.obj, red), 2)
        materials.paint(self.doc, [0], red, -1)
        f = self.doc.bm.faces[0]
        self.assertEqual(f.material_index, 0)
        self.assertEqual(f[geom.layers(self.doc.bm).back], 2)
        self.assertEqual(materials.material_of(self.doc, 0, -1), red)
        self.assertIsNone(materials.material_of(self.doc, 0, 1))

    def test_group_gets_slots_on_doc_event(self):
        g = document.create_group("G")
        self.assertEqual([m.name for m in g.obj.data.materials], [materials.MAT_FRONT, materials.MAT_BACK])

    def test_new_color(self):
        m = materials.new_color((10, 20, 30))
        self.assertEqual(m.su_mat.kind, materials.KIND_COLOR)
        self.assertAlmostEqual(m.su_mat.rgb[2], 30 / 255.0, places=4)


class TestPaint(FCase):
    TOOL = PAINT

    def setUp(self):
        super().setUp()
        self.red = materials.palette_material(0)
        materials.set_active(self.red)

    def tearDown(self):
        materials.set_active(None)
        super().tearDown()

    def mat(self, idx, side=1, doc=None):
        return materials.material_of(doc or self.doc, idx, side)

    def test_ac_pnt_1_back_side_of_floor(self):
        bm = self.doc.bm
        bm.clear()
        rect(bm, 0, 0, 8, 6)                 # floor: normal −Z, back side seen from above
        self.doc.write(undo_key=None)
        s0 = bpy.context.scene.su_undo_serial
        self.click(testing.pt(4, 3, 0, kind="ON_FACE", elem=("FACE", 0), doc_key=self.key, side=-1))
        self.assertEqual(self.mat(0, -1), self.red)
        self.assertIsNone(self.mat(0, 1))
        self.assertEqual(bpy.context.scene.su_undo_serial - s0, 1)

    def test_front_side(self):
        top = self.face((4, 3, 3))
        self.click(self.inf_face(top))
        self.assertEqual(self.mat(top, 1), self.red)

    def test_ac_pnt_2_surface(self):
        bm = self.doc.bm
        bm.clear()
        lay = geom.ensure_layers(bm)
        vs = [bm.verts.new(c) for c in ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (1, 0, 1), (1, 1, 1))]
        bm.faces.new((vs[0], vs[1], vs[2], vs[3]))
        bm.faces.new((vs[1], vs[4], vs[5], vs[2]))
        bm.edges.get((vs[1], vs[2]))[lay.soft] = True
        self.doc.write(undo_key=None)
        self.click(self.inf_face(0))
        self.assertEqual((self.mat(0), self.mat(1)), (self.red, self.red))

    def test_ac_pnt_3_eyedropper(self):
        top = self.face((4, 3, 3))
        blue = materials.palette_material(9)
        materials.paint(self.doc, [top], blue, 1)
        self.doc.write(undo_key=None)
        self.click(self.inf_face(top), alt_action=True)
        self.assertEqual(materials.active(), blue)
        self.click(self.inf_face(self.face((4, 0, 1.5))), alt_action=True)
        self.assertIsNone(materials.active())

    def test_ac_pnt_4_selection(self):
        ids = [self.face(c) for c in ((4, 3, 3), (4, 0, 1.5), (0, 3, 1.5))]
        selection.set([Ref(self.key, FACE, i) for i in ids])
        s0 = bpy.context.scene.su_undo_serial
        self.click(self.inf_face(ids[1]))
        self.assertEqual([self.mat(i) for i in ids], [self.red] * 3)
        self.assertIsNone(self.mat(self.face((4, 3, 0))))
        self.assertEqual(bpy.context.scene.su_undo_serial - s0, 1)

    def test_unselected_face_paints_only_itself(self):
        top = self.face((4, 3, 3))
        selection.set([Ref(self.key, FACE, top)])
        front = self.face((4, 0, 1.5))
        self.click(self.inf_face(front))
        self.assertEqual(self.mat(front), self.red)
        self.assertIsNone(self.mat(top))

    def test_shift_all_matching(self):
        self.click(self.inf_face(self.face((4, 3, 3))), shift=True)
        self.assertTrue(all(self.mat(f.index) == self.red for f in self.doc.bm.faces))

    def test_option_adjacent(self):
        blue = materials.palette_material(9)
        bottom = self.face((4, 3, 0))
        materials.paint(self.doc, [bottom], blue, 1)
        self.doc.write(undo_key=None)
        self.click(self.inf_face(self.face((4, 3, 3))), copy=True)
        self.assertEqual(self.mat(bottom), blue)
        self.assertEqual(sum(self.mat(f.index) == self.red for f in self.doc.bm.faces), 5)

    def test_group_default_faces(self):
        g = document.group_from(self.doc, [self.face((4, 3, 3))], [])
        g.write(undo_key=None)
        self.doc.write(undo_key=None)
        self.click(self.inf_face(0, key=g.key))
        self.assertEqual(materials.material_of(g, 0, 1), self.red)
        self.assertEqual(materials.material_of(g, 0, -1), self.red)


if __name__ == "__main__":
    unittest.main()
