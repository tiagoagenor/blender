# SPDX-License-Identifier: GPL-2.0-or-later
"""Document tests (owner: B): root, write/begin/cancel/invalidate, layers round-trip, memfile undo
of erase/heal (ROTEIRO_CASA AF-6, kernel part: exact counts, normals and materials)."""

import unittest

import bpy
from mathutils import Vector as V

from su import events
from su.core import document, geom

from test_b_geom import box, counts, find_face, rect


def _fresh_root():
    for obj in [o for o in bpy.data.objects if o.type == 'MESH' and o.su_doc.kind == document.KIND_MODEL]:
        me = obj.data
        bpy.data.objects.remove(obj)
        bpy.data.meshes.remove(me)
    document.invalidate_all()
    return document.root()


def _state(doc):
    bm = doc.bm
    faces = sorted((tuple(round(c, 6) for c in f.calc_center_median()),
                    tuple(round(c, 6) for c in f.normal), f.material_index) for f in bm.faces)
    return counts(bm), faces


class TestDocument(unittest.TestCase):
    def setUp(self):
        self.doc = _fresh_root()

    def test_root_is_unique_model(self):
        self.assertEqual(self.doc.obj.name, document.MODEL_NAME)
        self.assertEqual(self.doc.obj.su_doc.kind, document.KIND_MODEL)
        self.assertIs(document.root(), self.doc)
        self.assertIs(document.active(), self.doc)
        self.assertIn(self.doc, document.visible_documents())

    def test_write_mesh_event_version_undo_serial(self):
        seen = []
        fn = lambda **kw: seen.append(kw["doc_key"])
        events.subscribe("geometry", fn)
        try:
            s0 = bpy.context.scene.su_undo_serial
            rect(self.doc.bm, 0, 0, 3, 2)
            self.doc.write(undo_key="undo.init")
        finally:
            events.unsubscribe("geometry", fn)
        me = self.doc.obj.data
        self.assertEqual((len(me.vertices), len(me.edges), len(me.polygons)), (4, 4, 1))
        self.assertEqual(self.doc.version, 1)
        self.assertEqual(seen, [self.doc.key])
        self.assertEqual(bpy.context.scene.su_undo_serial, s0 + 1)
        self.assertIn("su_back_mat", me.attributes)
        self.assertEqual(me.attributes["su_back_mat"].data[0].value, 1)

    def test_layers_round_trip(self):
        geom.rebuild_face(self.doc.bm, [V((0, 0, 0)), V((3, 0, 0)), V((3, 3, 0)), V((0, 3, 0))],
                          [[V((1, 1, 0)), V((2, 1, 0)), V((2, 2, 0)), V((1, 2, 0))]], V((0, 0, 1)), 0, 1,
                          through_holes={0})
        lay = geom.layers(self.doc.bm)
        n_bridge = sum(1 for e in self.doc.bm.edges if e[lay.bridge])
        self.doc.write(undo_key=None)
        self.doc.invalidate()
        lay = geom.layers(self.doc.bm)
        self.assertEqual(sum(1 for e in self.doc.bm.edges if e[lay.bridge]), n_bridge)
        self.assertEqual(geom.validate(self.doc.bm), [])

    def test_begin_cancel(self):
        rect(self.doc.bm, 0, 0, 3, 2)
        self.doc.write(undo_key=None)
        self.doc.begin()
        geom.erase_faces(self.doc.bm, list(self.doc.bm.faces))
        self.doc.preview_write()
        self.assertEqual(len(self.doc.obj.data.polygons), 0)
        self.doc.cancel()
        self.assertEqual(len(self.doc.bm.faces), 1)
        self.assertEqual(len(self.doc.obj.data.polygons), 1)

    def test_invalidate_reloads_mesh(self):
        rect(self.doc.bm, 0, 0, 3, 2)
        self.doc.invalidate()                      # never written: the edit is dropped
        self.assertEqual(len(self.doc.bm.verts), 0)


class TestUndoAF6(unittest.TestCase):
    """AF-6 (kernel/headless part): Cmd+Z after each erase restores the exact previous state; redo
    re-applies. Memfile undo works in background (ed.undo / ed.redo); selection restore is A/F."""

    def setUp(self):
        self.doc = _fresh_root()
        bpy.ops.ed.undo_push(message="test base")
        box(self.doc.bm)
        for i, f in enumerate(self.doc.bm.faces):
            f.material_index = i % 3
        self.doc.write(undo_key="undo.init")
        self.boxed = _state(self.doc)

    def undo_redo(self, edit):
        edit(self.doc.bm)
        self.doc.write(undo_key="undo.adjust")
        after = _state(self.doc)
        self.assertNotEqual(after, self.boxed)
        bpy.ops.ed.undo()
        doc = document.root()
        self.assertEqual(_state(doc), self.boxed)
        bpy.ops.ed.redo()
        self.assertEqual(_state(document.root()), after)
        self.assertEqual(geom.validate(document.root().bm), [])

    def test_af6_after_af2_erase_top(self):
        self.undo_redo(lambda bm: geom.erase_faces(bm, [find_face(bm, (4, 3, 3))]))

    def test_af6_after_af3_erase_edge(self):
        from test_b_geom import find_edge
        self.undo_redo(lambda bm: geom.erase_edges(bm, [find_edge(bm, (0, 0, 3), (8, 0, 3))]))

    def test_af6_after_af5_erase_top_and_edges(self):
        def edit(bm):
            top = find_face(bm, (4, 3, 3))
            edges = list(top.edges)
            geom.erase_faces(bm, [top])
            geom.erase_edges(bm, edges)
        self.undo_redo(edit)

    def test_heal_then_undo(self):
        geom.erase_faces(self.doc.bm, [find_face(self.doc.bm, (4, 3, 3))])
        self.doc.write(undo_key="undo.adjust")
        opened = _state(self.doc)
        geom.add_edge(self.doc.bm, V((0, 0, 3)), V((8, 0, 3)))
        self.doc.write(undo_key="undo.adjust")
        self.assertEqual(counts(self.doc.bm), (8, 12, 6))
        bpy.ops.ed.undo()
        self.assertEqual(_state(document.root()), opened)


if __name__ == "__main__":
    unittest.main()
