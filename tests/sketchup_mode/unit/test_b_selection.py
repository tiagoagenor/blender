# SPDX-License-Identifier: GPL-2.0-or-later
"""B tests: selection sets (AC-SEL-1 kernel 1/2/3 clicks), prune/remap/snapshot, undo restores the
pre-delete selection (ROTEIRO_CASA AF-6), edit_context and groups (create_group / group_from /
explode, event "doc")."""

import unittest

import bpy
from mathutils import Matrix, Vector as V

from su import events
from su.core import document, edit_context, geom, selection
from su.core.selection import EDGE, FACE, OBJECT, Ref

from test_b_document import _fresh_root
from test_b_geom import box, counts, find_edge, find_face


def _drop_groups():
    for obj in [o for o in bpy.data.objects if o.type == 'MESH' and o.su_doc.kind == document.KIND_GROUP]:
        me = obj.data
        bpy.data.objects.remove(obj)
        if me.users == 0:
            bpy.data.meshes.remove(me)


class Base(unittest.TestCase):
    def setUp(self):
        edit_context.exit_all()
        _drop_groups()
        self.doc = _fresh_root()
        selection.clear()
        box(self.doc.bm)
        self.doc.write(undo_key=None)
        self.top = find_face(self.doc.bm, (4, 3, 3)).index
        self.key = self.doc.key

    def tearDown(self):
        edit_context.exit_all()
        selection.clear()


class TestSets(Base):
    def test_basic_ops_version_event(self):
        seen = []
        fn = lambda **kw: seen.append(1)
        events.subscribe("selection", fn)
        try:
            v0 = selection.version()
            a, b = Ref(self.key, FACE, 0), Ref(self.key, EDGE, 1)
            selection.set([a])
            selection.add([b])
            self.assertEqual(selection.get(), {a, b})
            selection.toggle([a])
            self.assertEqual(selection.get(), {b})
            selection.remove([b])
            self.assertTrue(selection.is_empty())
            selection.clear()                       # no change → no event
        finally:
            events.unsubscribe("selection", fn)
        self.assertEqual(selection.version(), v0 + 4)
        self.assertEqual(len(seen), 4)

    def test_ac_sel_1_one_two_three_clicks(self):
        r = Ref(self.key, FACE, self.top)
        one = selection.entity(r)
        self.assertEqual(one, [r])
        two = selection.expand_face(r)
        self.assertEqual((sum(x.kind == FACE for x in two), sum(x.kind == EDGE for x in two)), (1, 4))
        three = selection.connected(r)
        self.assertEqual((sum(x.kind == FACE for x in three), sum(x.kind == EDGE for x in three)), (6, 12))
        e = find_edge(self.doc.bm, (0, 0, 3), (8, 0, 3)).index
        ee = selection.expand_edge(Ref(self.key, EDGE, e))
        self.assertEqual((sum(x.kind == FACE for x in ee), sum(x.kind == EDGE for x in ee)), (2, 1))

    def test_queries_and_bounds(self):
        selection.set(selection.expand_face(Ref(self.key, FACE, self.top)))
        self.assertEqual(selection.faces_of(self.key), {self.top})
        self.assertEqual(len(selection.edges_of(self.key)), 4)
        self.assertEqual(len(selection.verts_of(self.doc)), 4)
        mn, mx = selection.bounds_world()
        self.assertAlmostEqual(mn.z, 3.0, places=6)
        self.assertAlmostEqual((mx - V((8, 6, 3))).length, 0.0, places=6)

    def test_select_all_and_invert(self):
        g = document.create_group("G")
        selection.select_all()
        mine = {r for r in selection.get() if r.doc_key == self.key}
        self.assertEqual(len(mine), 18)
        self.assertIn(Ref(g.key, OBJECT, 0), selection.get())
        selection.set([Ref(self.key, FACE, self.top)])
        selection.invert()
        self.assertNotIn(Ref(self.key, FACE, self.top), selection.get())
        self.assertEqual(len({r for r in selection.get() if r.doc_key == self.key}), 17)

    def test_prune_on_geometry_and_remap(self):
        selection.set([Ref(self.key, FACE, 5), Ref(self.key, EDGE, 11)])
        geom.erase_faces(self.doc.bm, list(self.doc.bm.faces))
        self.doc.write(undo_key=None)
        self.assertEqual(selection.get(), {Ref(self.key, EDGE, 11)})
        selection.remap(self.key, {EDGE: {11: 2}})
        self.assertEqual(selection.get(), {Ref(self.key, EDGE, 2)})
        selection.remap(self.key, {EDGE: {}})
        self.assertTrue(selection.is_empty())

    def test_snapshot_restore(self):
        selection.set([Ref(self.key, FACE, 1)])
        snap = selection.snapshot()
        selection.clear()
        selection.restore(snap)
        self.assertEqual(selection.get(), {Ref(self.key, FACE, 1)})
        selection.restore(None)
        self.assertTrue(selection.is_empty())


class TestUndoSelection(Base):
    def test_af6_undo_restores_selection_before_delete(self):
        bpy.ops.ed.undo_push(message="base")
        top = Ref(self.key, FACE, self.top)
        selection.set([top])
        self.doc.write(undo_key="undo.init")                  # state with the top selected
        geom.erase_faces(self.doc.bm, [self.doc.bm.faces[self.top]])
        self.doc.write(undo_key="undo.adjust", select=())     # Excluir: selection empty after
        self.assertTrue(selection.is_empty())
        self.assertEqual(counts(self.doc.bm), (8, 12, 5))
        bpy.ops.ed.undo()
        self.assertEqual(counts(document.root().bm), (8, 12, 6))
        self.assertEqual(selection.get(), {top})
        bpy.ops.ed.redo()
        self.assertEqual(counts(document.root().bm), (8, 12, 5))
        self.assertTrue(selection.is_empty())


class TestGroups(Base):
    def test_create_group_emits_doc(self):
        seen = []
        fn = lambda doc_key: seen.append(doc_key)
        events.subscribe("doc", fn)
        try:
            g = document.create_group("Grupo")
        finally:
            events.unsubscribe("doc", fn)
        self.assertEqual(seen, [g.key])
        self.assertEqual(g.obj.su_doc.kind, document.KIND_GROUP)

    def test_group_from_top_keeps_box_edges(self):
        seen = []
        fn = lambda doc_key: seen.append(doc_key)
        events.subscribe("doc", fn)
        try:
            refs = selection.expand_face(Ref(self.key, FACE, self.top))
            g = document.group_from(self.doc, [r.index for r in refs if r.kind == FACE],
                                    [r.index for r in refs if r.kind == EDGE], "Tampa")
        finally:
            events.unsubscribe("doc", fn)
        g.write(undo_key=None)
        self.doc.write(undo_key=None)
        self.assertEqual(seen, [g.key])
        self.assertEqual(counts(g.bm), (4, 4, 1))
        self.assertEqual(counts(self.doc.bm), (8, 12, 5))        # side faces keep their edges
        self.assertEqual(geom.validate(g.bm), [])
        self.assertIsNone(g.obj.parent)

    def test_group_from_and_explode_keep_hidden_face(self):
        bm = self.doc.bm
        lay = bm.faces.layers.bool.new("su_hidden_face")
        bm.faces.ensure_lookup_table()
        bm.faces[self.top][lay] = True
        self.doc.write(undo_key=None)
        refs = selection.expand_face(Ref(self.key, FACE, self.top))
        g = document.group_from(self.doc, [r.index for r in refs if r.kind == FACE],
                                [r.index for r in refs if r.kind == EDGE], "Tampa")
        g.write(undo_key=None)
        self.doc.write(undo_key=None)
        glay = g.bm.faces.layers.bool["su_hidden_face"]
        self.assertTrue(all(f[glay] for f in g.bm.faces))
        pdoc, res = document.explode(g.obj)
        plyr = pdoc.bm.faces.layers.bool["su_hidden_face"]
        self.assertTrue(res.new_faces[0][plyr])

    def test_edit_context_and_active(self):
        g = document.create_group("G")
        selection.set([Ref(g.key, OBJECT, 0)])
        self.assertTrue(edit_context.is_in_context(g.obj))
        edit_context.enter(g.obj)
        self.assertTrue(selection.is_empty())
        self.assertIs(document.active(), g)
        child = document.create_group("H", g.obj)
        self.assertTrue(edit_context.is_in_context(child.obj))
        self.assertFalse(edit_context.is_in_context(g.obj))
        edit_context.exit()
        self.assertIs(edit_context.top_level_pick(child.obj), g.obj)
        self.assertIs(document.active(), self.doc)

    def test_explode_welds_back(self):
        refs = selection.expand_face(Ref(self.key, FACE, self.top))
        g = document.group_from(self.doc, [r.index for r in refs if r.kind == FACE],
                                [r.index for r in refs if r.kind == EDGE], "Tampa")
        g.write(undo_key=None)
        self.doc.write(undo_key=None)
        name = g.key
        pdoc, res = document.explode(g.obj)
        pdoc.write(undo_key=None)
        self.assertIs(pdoc, self.doc)
        self.assertIsNone(bpy.data.objects.get(name))
        self.assertEqual(counts(self.doc.bm), (8, 12, 6))
        self.assertEqual(len(res.new_faces), 1)
        self.assertGreater(find_face(self.doc.bm, (4, 3, 3)).normal.z, 0.999)
        self.assertEqual(geom.validate(self.doc.bm), [])

    def test_explode_moved_group_and_children(self):
        g = document.create_group("G")
        geom.add_polyline(g.bm, [V((0, 0, 0)), V((1, 0, 0)), V((1, 1, 0)), V((0, 1, 0))], True)
        g.write(undo_key=None)
        g.obj.matrix_world = Matrix.Translation((20, 0, 0))
        child = document.create_group("C", g.obj)
        child.obj.matrix_world = Matrix.Translation((30, 0, 0))
        bpy.context.view_layer.update()
        pdoc, res = document.explode(g.obj)
        bpy.context.view_layer.update()
        self.assertIsNone(child.obj.parent)
        self.assertAlmostEqual(child.obj.matrix_world.translation.x, 30.0, places=5)
        f = res.new_faces[0]
        self.assertAlmostEqual(f.calc_center_median().x, 20.5, places=5)
        self.assertLess(f.normal.z, -0.999)


if __name__ == "__main__":
    unittest.main()
