# SPDX-License-Identifier: GPL-2.0-or-later
"""F tests: guides / dimensions / texts (G's core/guides) in Selecionar, Excluir and Apagar."""

import unittest

import bpy
from mathutils import Vector as V

from su import testing
from su.core import guides, selection
from su.ops import edit_ops
from su.tools import select as sel_tool

from test_f_select import FCase


class GuideCase(FCase):
    def setUp(self):
        super().setUp()
        guides.delete_guides(None)
        d = guides.data()
        guides.delete_annotations(dims=range(len(d.dims)), texts=range(len(d.texts)))
        sel_tool.ANNOT.clear()
        self._orig = sel_tool.pick_annotation

    def tearDown(self):
        sel_tool.pick_annotation = self._orig
        sel_tool.ANNOT.clear()
        super().tearDown()

    def fake_pick(self, item):
        sel_tool.pick_annotation = lambda tc, xy: item


class TestGuidesSelect(GuideCase):
    def test_click_selects_guide_and_delete_removes_it(self):
        guides.add_guide_line(V((0, -1, 0)), V((1, 0, 0)))
        guides.add_guide_line(V((0, -2, 0)), V((1, 0, 0)))
        self.fake_pick(('GUIDE', 1))
        self.click(testing.pt(0, 0, 0))                     # nothing geometric under the cursor
        self.assertEqual(sel_tool.ANNOT, {('GUIDE', 1)})
        self.assertTrue(selection.is_empty())
        s0 = bpy.context.scene.su_undo_serial
        self.assertTrue(edit_ops.delete_selection())
        self.assertEqual(guides.count(), 1)
        self.assertEqual(bpy.context.scene.su_undo_serial - s0, 1)

    def test_click_on_face_clears_guides(self):
        sel_tool.ANNOT.add(('GUIDE', 0))
        self.fake_pick(None)
        self.click(self.inf_face(self.face((4, 3, 3))))
        self.assertEqual(sel_tool.ANNOT, set())

    def test_escape_clears_guides(self):
        sel_tool.ANNOT.add(('DIM', 0))
        edit_ops.escape()
        self.assertEqual(sel_tool.ANNOT, set())


class TestGuidesEraser(GuideCase):
    TOOL = "su.eraser"

    def test_eraser_deletes_dimension(self):
        guides.add_dimension(V((0, 0, 0)), V((8, 0, 0)), V((0, -1, 0)))
        self.fake_pick(('DIM', 0))
        self.click(testing.pt(4, -1, 0))
        self.assertEqual(len(guides.data().dims), 0)


if __name__ == "__main__":
    unittest.main()
