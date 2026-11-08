# SPDX-License-Identifier: GPL-2.0-or-later
"""F tests: clipboard (P1) — Copiar / Recortar / Colar no local, geometry and groups."""

import unittest

import bpy

from su.core import document, materials, selection
from su.core.selection import FACE, OBJECT, Ref
from su.ops import edit_ops

from test_b_geom import counts
from test_f_select import FCase


class TestClipboard(FCase):
    def test_copy_paste_in_place_geometry(self):
        red = materials.palette_material(0)
        top = self.face((4, 3, 3))
        materials.paint(self.doc, [top], red, 1)
        self.doc.write(undo_key=None)
        selection.set([Ref(self.key, FACE, top)])
        self.assertTrue(edit_ops.copy_selection())
        s0 = bpy.context.scene.su_undo_serial
        self.assertTrue(edit_ops.paste_in_place())
        self.assertEqual(bpy.context.scene.su_undo_serial - s0, 1)
        self.assertEqual(len(self.doc.bm.faces), 7)
        sel = [r for r in selection.get() if r.kind == FACE]
        self.assertEqual(len(sel), 1)
        self.assertEqual(materials.material_of(self.doc, sel[0].index, 1), red)

    def test_cut_and_paste_group(self):
        g = document.group_from(self.doc, [self.face((4, 3, 3))], [])
        g.write(undo_key=None)
        self.doc.write(undo_key=None)
        name = g.key
        selection.set([Ref(name, OBJECT, 0)])
        self.assertTrue(edit_ops.cut_selection())
        self.assertIsNone(bpy.context.scene.objects.get(name))
        self.assertTrue(edit_ops.paste_in_place())
        objs = selection.objects()
        self.assertEqual(len(objs), 1)
        self.assertIn(objs[0].name, bpy.context.scene.objects)
        self.assertEqual(len(objs[0].data.polygons), 1)


if __name__ == "__main__":
    unittest.main()
