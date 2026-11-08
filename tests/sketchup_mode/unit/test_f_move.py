# SPDX-License-Identifier: GPL-2.0-or-later
"""F tests: TransformSession + Mover (AC-MOV-1..3, 5..10) through testing.dispatch."""

import unittest

import bpy
from mathutils import Matrix, Vector as V

from su import testing
from su.core import document, geom, geom_transform, selection
from su.core.selection import EDGE, FACE, OBJECT, Ref

from test_b_geom import counts, find_edge, find_face
from test_f_select import FCase

MOVE = "su.move"


def bbox(bm):
    xs = [v.co for v in bm.verts]
    return (V((min(p.x for p in xs), min(p.y for p in xs), min(p.z for p in xs))),
            V((max(p.x for p in xs), max(p.y for p in xs), max(p.z for p in xs))))


def nonplanar(bm):
    return sum(1 for f in bm.faces if not geom.is_planar(f, 1e-4))


class TestMove(FCase):
    TOOL = MOVE

    def grab(self, at, inf=None, **mods):
        self.clock.t += 1
        testing.dispatch(testing.ev('LEFTMOUSE', 'PRESS', **mods), None, inf or testing.pt(*at))
        testing.dispatch(testing.ev('LEFTMOUSE', 'RELEASE', **mods), None, inf or testing.pt(*at))

    def toward(self, p):
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING', 10, 0), None, testing.pt(*p))

    def test_ac_mov_1_move_keeps_selection(self):
        selection.select_all()
        before = selection.get()
        s0 = bpy.context.scene.su_undo_serial
        self.grab((0, 0, 0))
        self.toward((1, 0, 0))
        testing.type_text("2")
        mn, mx = bbox(self.doc.bm)
        self.assertAlmostEqual(mn.x, 2.0, places=5)
        self.assertAlmostEqual(mx.x, 10.0, places=5)
        self.assertEqual(selection.get(), before)
        self.assertEqual(bpy.context.scene.su_undo_serial - s0, 1)
        # Ajustar: retype 3 after the move
        testing.type_text("3")
        self.assertAlmostEqual(bbox(self.doc.bm)[0].x, 3.0, places=5)

    def test_ac_mov_2_copy_and_array(self):
        selection.select_all()
        self.grab((0, 0, 0), copy=True)
        self.toward((1, 0, 0))
        testing.type_text("10")
        self.assertEqual(len(self.doc.bm.faces), 12)
        self.assertEqual(len(selection.get()), 18)
        testing.type_text("3x")
        bm = self.doc.bm
        self.assertEqual(len(bm.faces), 24)
        self.assertAlmostEqual(bbox(bm)[1].x, 38.0, places=4)
        sel_faces = [bm.faces[r.index] for r in selection.get() if r.kind == FACE]
        self.assertEqual(len(sel_faces), 6)
        self.assertTrue(all(f.calc_center_median().x > 29.99 for f in sel_faces))

    def test_ac_mov_3_divide(self):
        selection.select_all()
        self.grab((0, 0, 0), copy=True)
        self.toward((1, 0, 0))
        testing.type_text("40")
        testing.type_text("/4")
        bm = self.doc.bm
        self.assertEqual(len(bm.faces), 30)      # original + 4 copies (10, 20, 30, 40)
        xs = sorted({round(min(v.co.x for v in f.verts), 4) for f in bm.faces})
        for x in (0.0, 10.0, 20.0, 30.0, 40.0):
            self.assertIn(x, xs)

    def test_ac_mov_5_vertex_folds(self):
        bm = self.doc.bm
        v = next(v for v in bm.verts if (v.co - V((8, 6, 3))).length < 1e-6)
        inf = testing.pt(8, 6, 3, kind="ENDPOINT", elem=("VERT", v.index), doc_key=self.key)
        self.grab((8, 6, 3), inf=inf)
        self.toward((8, 6, 4))
        testing.type_text("0.5")
        bm = self.doc.bm
        self.assertEqual(nonplanar(bm), 0)
        self.assertEqual(len(bm.faces), 7)
        self.assertEqual(counts(bm)[1], 13)
        self.assertEqual(geom.validate(bm), [])

    def test_ac_mov_6_ridge(self):
        geom.add_edge(self.doc.bm, V((0, 3, 3)), V((8, 3, 3)))
        self.doc.write(undo_key=None)
        e = find_edge(self.doc.bm, (0, 3, 3), (8, 3, 3))
        selection.set([Ref(self.key, EDGE, e.index)])
        self.grab((4, 3, 3))
        self.toward((4, 3, 4))
        testing.type_text("1")
        bm = self.doc.bm
        self.assertEqual(len(bm.faces), 7)
        self.assertEqual(nonplanar(bm), 0)
        self.assertEqual(sorted(len(f.verts) for f in bm.faces).count(5), 2)
        self.assertEqual(geom.validate(bm), [])

    def test_ac_mov_7_shear_top(self):
        top = self.face((4, 3, 3))
        selection.set([Ref(self.key, FACE, top)])
        self.grab((4, 3, 3))
        self.toward((5, 3, 3))
        testing.type_text("0.5")
        bm = self.doc.bm
        self.assertEqual(nonplanar(bm), 0)
        self.assertAlmostEqual(bbox(bm)[1].x, 8.5, places=5)

    def test_ac_mov_8_stretch_without_selection(self):
        top = self.face((4, 3, 3))
        inf = self.inf_face(top, point=(4, 3, 3))
        self.clock.t += 1
        testing.dispatch(testing.ev('LEFTMOUSE', 'PRESS', 0, 0), None, inf)
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING', 0, 30), None, testing.pt(4, 3, 4))
        testing.dispatch(testing.ev('LEFTMOUSE', 'RELEASE', 0, 60), None, testing.pt(4, 3, 4))
        self.assertAlmostEqual(bbox(self.doc.bm)[1].z, 4.0, places=5)
        self.assertEqual(len(self.doc.bm.faces), 6)

    def test_ac_mov_9_group_does_not_stick(self):
        g = document.group_from(self.doc, [self.face((4, 3, 3))], [])
        g.write(undo_key=None)
        self.doc.write(undo_key=None)
        root_before = bbox(self.doc.bm)
        selection.set([Ref(g.key, OBJECT, 0)])
        self.grab((0, 0, 3))
        self.toward((1, 0, 3))
        testing.type_text("10")
        self.assertAlmostEqual(g.obj.matrix_world.translation.x, 10.0, places=5)
        self.assertEqual(bbox(self.doc.bm), root_before)
        self.assertEqual(selection.get(), {Ref(g.key, OBJECT, 0)})

    def test_ac_mov_10_undo_keeps_selection(self):
        bpy.ops.ed.undo_push(message="base")
        selection.select_all()
        before = selection.get()
        self.grab((0, 0, 0))
        self.toward((1, 0, 0))
        testing.type_text("2")
        bpy.ops.ed.undo()
        root = document.root()
        self.assertAlmostEqual(bbox(root.bm)[0].x, 0.0, places=5)
        self.assertEqual(selection.get(), before)

    def test_esc_cancels(self):
        selection.select_all()
        self.grab((0, 0, 0))
        self.toward((3, 0, 0))
        testing.dispatch(testing.ev('ESC', 'PRESS'))
        self.assertAlmostEqual(bbox(self.doc.bm)[0].x, 0.0, places=5)


class TestSession(FCase):
    TOOL = MOVE

    def test_restrict_keeps_faces_planar(self):
        top = self.face((4, 3, 3))
        s = geom_transform.TransformSession([Ref(self.key, FACE, top)], fold='RESTRICT')
        m = Matrix.Rotation(0.3, 4, 'Z')          # twisting the top would bend the 4 sides
        got = s.set_matrix(Matrix.Translation((4, 3, 3)) @ m @ Matrix.Translation((-4, -3, -3)))
        self.assertEqual(got, Matrix.Identity(4))
        self.assertEqual(nonplanar(self.doc.bm), 0)
        s.cancel()


if __name__ == "__main__":
    unittest.main()
