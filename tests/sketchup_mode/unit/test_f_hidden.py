# SPDX-License-Identifier: GPL-2.0-or-later
"""F tests: hidden faces (P1) — Ocultar on faces (su_hidden_face), not pickable, Selecionar tudo skips
them, Reexibir tudo / último / selecionados, Geometria oculta makes them pickable, 1 undo."""

import unittest

import bpy

from su.core import selection
from su.core.selection import FACE, Ref
from su.ops import edit_ops
from su.tools import select as sel_tool

from test_f_select import FCase


def hidden(doc):
    lay = doc.bm.faces.layers.bool.get(sel_tool.HIDDEN_FACE)
    return sorted(f.index for f in doc.bm.faces if lay is not None and f[lay])


class TestHiddenFaces(FCase):
    def tearDown(self):
        bpy.context.scene.su_style.show_hidden_geometry = False
        super().tearDown()

    def hide_top(self):
        top = self.face((4, 3, 3))
        selection.set([Ref(self.key, FACE, top)])
        s0 = bpy.context.scene.su_undo_serial
        self.assertTrue(edit_ops.hide_selection())
        self.assertEqual(bpy.context.scene.su_undo_serial - s0, 1)
        return top

    def test_hide_face_attribute_and_edges_stay(self):
        top = self.hide_top()
        self.assertEqual(hidden(self.doc), [top])
        self.assertTrue(selection.is_empty())
        self.assertEqual(len(self.doc.bm.faces), 6)
        self.assertEqual(sel_tool.hidden_faces(self.doc.obj), {top})

    def test_hidden_face_not_pickable_nor_select_all(self):
        top = self.hide_top()
        self.click(self.inf_face(top))
        self.assertTrue(selection.is_empty())
        bpy.ops.su.select_all()
        self.assertEqual(self.kinds(), (5, 12, 0))
        bpy.context.scene.su_style.show_hidden_geometry = True
        self.click(self.inf_face(top))
        self.assertEqual(selection.get(), {Ref(self.key, FACE, top)})

    def test_unhide_all_last_selected(self):
        top = self.hide_top()
        self.assertTrue(edit_ops.unhide('ALL'))
        self.assertEqual(hidden(self.doc), [])
        self.hide_top()
        self.assertTrue(edit_ops.unhide('LAST'))
        self.assertEqual(hidden(self.doc), [])
        self.hide_top()
        bpy.context.scene.su_style.show_hidden_geometry = True
        selection.set([Ref(self.key, FACE, top)])
        self.assertTrue(edit_ops.unhide('SELECTED'))
        self.assertEqual(hidden(self.doc), [])

    def test_undo_restores(self):
        bpy.ops.ed.undo_push(message="base")
        self.hide_top()
        bpy.ops.ed.undo()
        from su.core import document
        self.assertEqual(hidden(document.root()), [])


if __name__ == "__main__":
    unittest.main()
