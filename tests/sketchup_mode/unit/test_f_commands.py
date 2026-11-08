# SPDX-License-Identifier: GPL-2.0-or-later
"""F tests: edit commands (Criar grupo / componente, Explodir, Inverter faces, Ocultar / Reexibir,
Tudo conectado) and Informações da entidade (summary)."""

import unittest

import bpy

from su.core import document, edit_context, geom, materials, selection, state
from su.core.selection import EDGE, FACE, OBJECT, Ref
from su.ops import edit_ops
from su.ui import tray_entity_info

from test_b_geom import counts
from test_f_select import FCase


class TestCommands(FCase):
    def steps(self, fn):
        s0 = bpy.context.scene.su_undo_serial
        r = fn()
        return r, bpy.context.scene.su_undo_serial - s0

    def test_make_group_from_faces(self):
        top = self.face((4, 3, 3))
        selection.set([Ref(self.key, FACE, top)])
        g, n = self.steps(edit_ops.make_group)
        self.assertEqual(n, 1)
        self.assertIsNotNone(g)
        self.assertEqual(selection.get(), {Ref(g.key, OBJECT, 0)})
        self.assertEqual(len(g.bm.faces), 1)
        self.assertEqual(len(self.doc.bm.faces), 5)
        self.assertEqual([m.name for m in g.obj.data.materials][:2], [materials.MAT_FRONT, materials.MAT_BACK])

    def test_make_group_nests_groups(self):
        g1 = document.group_from(self.doc, [self.face((4, 3, 3))], [])
        g1.write(undo_key=None)
        self.doc.write(undo_key=None)
        selection.set([Ref(g1.key, OBJECT, 0)])
        g2 = edit_ops.make_group()
        self.assertEqual(g1.obj.parent, g2.obj)

    def test_make_component_is_group_with_hint(self):
        selection.set([Ref(self.key, FACE, self.face((4, 3, 3)))])
        self.assertTrue(edit_ops.make_component())
        self.assertEqual(state.STATE.hint_key, "edit.component_is_group")
        self.assertEqual(len(selection.objects()), 1)

    def test_explode(self):
        top = self.face((4, 3, 3))
        selection.set([Ref(self.key, FACE, top)])
        g = edit_ops.make_group()
        name = g.key
        r, n = self.steps(edit_ops.explode_selection)
        self.assertTrue(r)
        self.assertEqual(n, 1)
        self.assertIsNone(bpy.data.objects.get(name))
        root = document.root()
        self.assertEqual(counts(root.bm), (8, 12, 6))
        self.assertTrue(any(r.kind == FACE for r in selection.get()))

    def test_reverse_faces(self):
        top = self.face((4, 3, 3))
        nz = self.doc.bm.faces[top].normal.z
        selection.set([Ref(self.key, FACE, top)])
        self.assertTrue(edit_ops.reverse_selected_faces())
        self.doc.bm.faces.ensure_lookup_table()
        self.assertAlmostEqual(self.doc.bm.faces[top].normal.z, -nz)

    def test_hide_unhide_edges_and_groups(self):
        e = self.edge((0, 0, 3), (8, 0, 3))
        g = document.group_from(self.doc, [self.face((4, 3, 3))], [])
        g.write(undo_key=None)
        self.doc.write(undo_key=None)
        e = self.edge((0, 0, 3), (8, 0, 3))
        selection.set([Ref(self.key, EDGE, e), Ref(g.key, OBJECT, 0)])
        self.assertTrue(edit_ops.hide_selection())
        lay = geom.layers(self.doc.bm)
        self.assertTrue(self.doc.bm.edges[e][lay.hidden])
        self.assertTrue(g.obj.hide_get())
        self.assertTrue(selection.is_empty())
        self.assertTrue(edit_ops.unhide('LAST'))
        self.assertFalse(g.obj.hide_get())
        self.doc.bm.edges.ensure_lookup_table()
        self.assertFalse(self.doc.bm.edges[e][geom.layers(self.doc.bm).hidden])
        selection.set([Ref(self.key, EDGE, e)])
        edit_ops.hide_selection()
        self.assertTrue(edit_ops.unhide('ALL'))
        self.doc.bm.edges.ensure_lookup_table()
        self.assertFalse(self.doc.bm.edges[e][geom.layers(self.doc.bm).hidden])

    def test_select_connected_op(self):
        selection.set([Ref(self.key, FACE, self.face((4, 3, 3)))])
        bpy.ops.su.select_connected()
        self.assertEqual(self.kinds(), (6, 12, 0))

    def test_entity_info_summary(self):
        selection.set([Ref(self.key, FACE, self.face((4, 3, 3)))])
        s = tray_entity_info.summarize()
        self.assertEqual([e[0] for e in s["entities"]], ["FACE"])
        self.assertAlmostEqual(s["area"], 48.0, places=3)
        selection.set([Ref(self.key, EDGE, self.edge((0, 0, 3), (8, 0, 3)))])
        s = tray_entity_info.summarize()
        self.assertEqual([e[0] for e in s["entities"]], ["EDGE"])
        self.assertAlmostEqual(s["length"], 8.0, places=4)
        selection.select_all()
        s = tray_entity_info.summarize()
        self.assertEqual(len(s["entities"]), 18)


if __name__ == "__main__":
    unittest.main()
