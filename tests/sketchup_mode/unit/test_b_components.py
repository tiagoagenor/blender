# SPDX-License-Identifier: GPL-2.0-or-later
"""B tests: components (P1, kernel) — definition = shared mesh (mesh["su_def"]), instances = objects
sharing it. Edit through one instance → every instance changes; make_unique; duplicate; explode."""

import unittest

import bpy
from mathutils import Matrix, Vector as V

from su import events
from su.core import document, edit_context, geom, selection
from su.core.selection import EDGE, FACE, Ref

from test_b_document import _fresh_root
from test_b_geom import box, counts, find_face


def _drop_docs():
    for obj in [o for o in bpy.data.objects
                if o.type == 'MESH' and o.su_doc.kind in (document.KIND_GROUP, document.KIND_COMPONENT)]:
        me = obj.data
        bpy.data.objects.remove(obj)
        if me.users == 0:
            bpy.data.meshes.remove(me)


class Base(unittest.TestCase):
    def setUp(self):
        edit_context.exit_all()
        _drop_docs()
        self.doc = _fresh_root()
        selection.clear()
        box(self.doc.bm)
        self.doc.write(undo_key=None)
        # the whole box becomes a component
        refs = selection.connected(Ref(self.doc.key, FACE, 0))
        seen = []
        fn = lambda doc_key: seen.append(doc_key)
        events.subscribe("doc", fn)
        try:
            self.c1 = document.component_from(self.doc, [r.index for r in refs if r.kind == FACE],
                                              [r.index for r in refs if r.kind == EDGE], "Caixa")
        finally:
            events.unsubscribe("doc", fn)
        self.c1.write(undo_key=None)
        self.doc.write(undo_key=None)
        self.doc_events = seen

    def tearDown(self):
        edit_context.exit_all()
        selection.clear()

    def second(self, dx=10.0):
        o2 = document.duplicate(self.c1.obj)
        o2.matrix_world = Matrix.Translation((dx, 0, 0)) @ o2.matrix_world
        bpy.context.view_layer.update()
        return document.get(o2)


class TestComponents(Base):
    def test_component_from(self):
        obj = self.c1.obj
        self.assertEqual(self.doc_events, [self.c1.key])
        self.assertEqual(obj.su_doc.kind, document.KIND_COMPONENT)
        self.assertTrue(document.is_component(obj))
        self.assertEqual(document.definition_name(obj), "Caixa")
        self.assertIn(obj.data, document.definitions())
        self.assertEqual(document.instances("Caixa"), [obj])
        self.assertEqual(counts(self.c1.bm), (8, 12, 6))
        self.assertEqual(counts(self.doc.bm), (0, 0, 0))
        self.assertEqual(geom.validate(self.c1.bm), [])

    def test_unique_definition_names(self):
        refs = selection.connected(Ref(self.c1.key, FACE, 0))
        c = document.component_from(self.c1, [r.index for r in refs if r.kind == FACE][:1], [], "Caixa")
        self.assertEqual(document.definition_name(c.obj), "Caixa#1")

    def test_duplicate_shares_definition(self):
        c2 = self.second()
        self.assertIs(c2.obj.data, self.c1.obj.data)
        self.assertEqual(document.instances(self.c1.obj.data), sorted([self.c1.obj, c2.obj], key=lambda o: o.name))
        self.assertIs(c2.bm, self.c1.bm)                    # one live bmesh per definition
        self.assertEqual(c2.version, self.c1.version)

    def test_group_duplicate_gets_own_mesh(self):
        g = document.create_group("G")
        o2 = document.duplicate(g.obj)
        self.assertIsNot(o2.data, g.obj.data)

    def test_edit_one_instance_changes_all(self):
        c2 = self.second()
        seen = []
        fn = lambda doc_key: seen.append(doc_key)
        events.subscribe("geometry", fn)
        edit_context.enter(c2.obj)
        try:
            doc = document.active()
            self.assertIs(doc, c2)
            top = find_face(doc.bm, (4, 3, 3))                 # local coordinates of the definition
            geom.erase_faces(doc.bm, [top])
            doc.write(undo_key=None, select=())
        finally:
            events.unsubscribe("geometry", fn)
            edit_context.exit()
        self.assertEqual(seen, [c2.key, self.c1.key])
        for o in (self.c1.obj, c2.obj):
            self.assertEqual(len(o.data.polygons), 5)
        self.assertEqual(counts(self.c1.bm), (8, 12, 5))
        mn = min((c2.world() @ v.co).x for v in c2.bm.verts)
        self.assertAlmostEqual(mn, 10.0, places=5)          # same definition, instance's own matrix

    def test_preview_cancel_through_instance(self):
        c2 = self.second()
        c2.begin()
        geom.erase_faces(c2.bm, list(c2.bm.faces))
        c2.preview_write()
        self.assertEqual(len(self.c1.obj.data.polygons), 0)
        c2.cancel()
        self.assertEqual(len(self.c1.obj.data.polygons), 6)
        self.assertEqual(counts(self.c1.bm), (8, 12, 6))

    def test_make_unique(self):
        c2 = self.second()
        u = document.make_unique(c2.obj)
        self.assertIs(u, c2)
        self.assertIsNot(c2.obj.data, self.c1.obj.data)
        self.assertEqual(document.definition_name(c2.obj), "Caixa#1")
        self.assertEqual(document.instances("Caixa"), [self.c1.obj])
        geom.erase_faces(self.c1.bm, [find_face(self.c1.bm, (4, 3, 3))])
        self.c1.write(undo_key=None)
        self.assertEqual(len(self.c1.obj.data.polygons), 5)
        self.assertEqual(len(c2.obj.data.polygons), 6)      # the unique copy did not follow
        self.assertIs(document.make_unique(c2.obj), c2)      # single user: no-op
        self.assertEqual(document.definition_name(c2.obj), "Caixa#1")

    def test_explode_one_instance_keeps_definition(self):
        c2 = self.second()
        name2 = c2.key
        pdoc, res = document.explode(c2.obj)
        pdoc.write(undo_key=None)
        self.assertIs(pdoc, self.doc)
        self.assertIsNone(bpy.data.objects.get(name2))
        self.assertEqual(counts(self.doc.bm), (8, 12, 6))
        self.assertAlmostEqual(min(v.co.x for v in self.doc.bm.verts), 10.0, places=5)
        self.assertEqual(document.instances("Caixa"), [self.c1.obj])
        self.assertEqual(counts(self.c1.bm), (8, 12, 6))
        self.assertEqual(geom.validate(self.doc.bm), [])
        pdoc, _res = document.explode(self.c1.obj)          # last instance: the definition goes
        self.assertIsNone(bpy.data.meshes.get("Caixa"))
        self.assertEqual(document.definitions(), [])

    def test_undo_restores_every_instance(self):
        c2 = self.second()
        bpy.ops.ed.undo_push(message="base")
        self.c1.write(undo_key="undo.init")
        geom.erase_faces(c2.bm, [find_face(c2.bm, (4, 3, 3))])
        c2.write(undo_key="undo.adjust")
        self.assertEqual(len(self.c1.obj.data.polygons), 5)
        bpy.ops.ed.undo()
        o1 = bpy.data.objects[self.c1.key]
        o2 = bpy.data.objects[c2.key]
        self.assertIs(o1.data, o2.data)
        self.assertEqual(len(o1.data.polygons), 6)
        self.assertEqual(counts(document.get(o2).bm), (8, 12, 6))


if __name__ == "__main__":
    unittest.main()
