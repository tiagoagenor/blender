# SPDX-License-Identifier: GPL-2.0-or-later
"""F tests: components (P1) on B's shared-mesh kernel — Criar componente (G), copies share the
definition (Mover+Option, arrays, clipboard), Tornar exclusivo, place-instance tool, tray rows."""

import unittest

import bpy

from su import testing
from su.core import document, selection
from su.core.selection import FACE, OBJECT, Ref
from su.ops import edit_ops
from su.tools import move
from su.ui import tray_components

from test_f_select import FCase


def drop_components():
    for o in [o for o in bpy.data.objects if o.type == 'MESH' and document.is_component(o)]:
        bpy.data.objects.remove(o)
    for me in [m for m in bpy.data.meshes if "su_def" in m and m.users == 0]:
        bpy.data.meshes.remove(me)


class CompCase(FCase):
    def setUp(self):
        drop_components()
        super().setUp()
        selection.set([Ref(self.key, FACE, self.face((4, 3, 3)))])
        self.c = edit_ops.make_component()

    def tearDown(self):
        super().tearDown()
        drop_components()


class TestComponents(CompCase):
    def test_make_component(self):
        c = self.c
        self.assertTrue(document.is_component(c.obj))
        self.assertTrue(document.definition_name(c.obj).startswith("Componente#"))
        self.assertEqual(len(self.doc.bm.faces), 5)
        self.assertEqual(len(c.obj.data.polygons), 1)
        self.assertEqual(selection.get(), {Ref(c.key, OBJECT, 0)})
        self.assertIn((c.obj.data.name, 1), tray_components.rows())

    def test_instance_name_blank_and_editable(self):
        from su.ui import tray_entity_info as info
        self.assertEqual(info.instance_name(self.c.obj), "")
        self.c.obj["su_instance_name"] = "Porta da frente"
        self.assertTrue(edit_ops.copy_selection())
        edit_ops.paste_in_place()
        pasted = selection.objects()[0]
        self.assertEqual(info.instance_name(pasted), "Porta da frente")
        pl = move.ComponentPlacer(self.c.obj.data.name)
        pl.start()
        placed = bpy.data.objects.get(pl.place(testing.pt(30, 0, 0)))
        self.assertEqual(info.instance_name(placed), "")

    def test_move_copy_and_array_share_definition(self):
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), "su.move", testing.pt(0, 0, 0))
        self.clock.t += 1
        testing.dispatch(testing.ev('LEFTMOUSE', 'PRESS', copy=True), None, testing.pt(0, 0, 0))
        testing.dispatch(testing.ev('LEFTMOUSE', 'RELEASE', copy=True), None, testing.pt(0, 0, 0))
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING', 10, 0), None, testing.pt(1, 0, 0))
        testing.type_text("10")
        testing.type_text("3x")
        inst = document.instances(self.c.obj.data)
        self.assertEqual(len(inst), 4)
        self.assertTrue(all(o.data == self.c.obj.data for o in inst))

    def test_clipboard_shares_definition(self):
        self.assertTrue(edit_ops.copy_selection())
        self.assertTrue(edit_ops.paste_in_place())
        self.assertEqual(len(document.instances(self.c.obj.data)), 2)

    def test_make_unique(self):
        selection.set([Ref(self.c.key, OBJECT, 0)])
        self.assertTrue(edit_ops.copy_selection())
        edit_ops.paste_in_place()
        pasted = selection.objects()[0]
        s0 = bpy.context.scene.su_undo_serial
        self.assertTrue(edit_ops.make_unique_selection())
        self.assertEqual(bpy.context.scene.su_undo_serial - s0, 1)
        self.assertNotEqual(pasted.data, self.c.obj.data)
        self.assertEqual(len(document.instances(self.c.obj.data)), 1)

    def test_placer(self):
        defname = self.c.obj.data.name
        pl = move.ComponentPlacer(defname)
        self.assertTrue(pl.start())
        self.assertEqual(len(document.instances(defname)), 2)        # preview (hidden) + original
        s0 = bpy.context.scene.su_undo_serial
        name = pl.place(testing.pt(20, 0, 0))
        self.assertEqual(bpy.context.scene.su_undo_serial - s0, 1)
        placed = bpy.data.objects.get(name)
        self.assertTrue(document.is_component(placed))
        self.assertEqual(selection.get(), {Ref(name, OBJECT, 0)})
        lo = min((placed.matrix_world @ v.co).x for v in placed.data.vertices)
        self.assertAlmostEqual(lo, 20.0, places=4)

    def test_placer_cancel_removes_preview(self):
        defname = self.c.obj.data.name
        pl = move.ComponentPlacer(defname)
        pl.start()
        pl.follow(testing.pt(20, 0, 0))
        pl.cancel()
        self.assertEqual(len(document.instances(defname)), 1)


if __name__ == "__main__":
    unittest.main()
