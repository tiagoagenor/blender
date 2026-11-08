# SPDX-License-Identifier: GPL-2.0-or-later
"""E: Siga-me — AC-SIG-1 (tubo em L com mitra, caminho pré-selecionado), AC-SIG-2 (moldura fechada nas
bordas do topo de uma caixa), path chosen by hovering an edge, kernel order_path."""

import unittest

from mathutils import Vector

from su import testing
from su.core import document, geom, geom_extrude, selection
from su.tools import base

from test_e_pushpull import PPCase, face_inf

FM = "su.followme"


def V(*a):
    return Vector(a)


class TestFollowMe(PPCase):
    TOOL = FM

    def tearDown(self):
        selection.clear()
        super().tearDown()

    def add(self, pts, closed):
        doc = document.root()
        geom.add_polyline(doc.bm, [V(*p) for p in pts], closed)
        doc.write(undo_key="test")

    def select_edges(self, pred):
        doc = document.root()
        bm = doc.bm
        bm.edges.ensure_lookup_table()
        refs = [selection.Ref(doc.key, 'EDGE', e.index) for e in bm.edges if pred(e)]
        selection.set(refs)
        return len(refs)

    def test_order_path(self):
        pts, closed = geom_extrude.order_path([((1, 0, 0), (2, 0, 0)), ((0, 0, 0), (1, 0, 0))])
        self.assertFalse(closed)
        self.assertEqual([tuple(p) for p in pts][0] in {(0.0, 0.0, 0.0), (2.0, 0.0, 0.0)}, True)
        pts, closed = geom_extrude.order_path([((0, 0, 0), (1, 0, 0)), ((1, 0, 0), (1, 1, 0)), ((1, 1, 0), (0, 0, 0))])
        self.assertTrue(closed)
        self.assertEqual(len(pts), 3)

    def test_ac_sig_1_l_tube(self):
        self.add([(0, 0, 1), (4, 0, 1), (4, 3, 1)], False)                       # path (L)
        self.add([(0, -0.25, 0.75), (0, 0.25, 0.75), (0, 0.25, 1.25), (0, -0.25, 1.25)], True)   # profile
        n = self.select_edges(lambda e: all(abs(v.co.z - 1) < 1e-6 and (abs(v.co.y) < 1e-6 or abs(v.co.x - 4) < 1e-6)
                                            for v in e.verts) and not all(abs(v.co.x) < 1e-6 for v in e.verts))
        self.assertEqual(n, 2)
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), FM, testing.pt(0, 0, 1))
        r = testing.click(face_inf((0, 0, 1)))
        self.assertIs(r, base.Result.IDLE)
        st = self.stats()
        self.assertEqual(st["faces"], 10)                        # 2 caps + 2 × 4 sides, no mitre face
        self.assertEqual(st["non_planar"], 0)
        bm = document.root().bm
        mitre = [f for f in bm.faces if all(abs((v.co - V(4, 0, 1)).dot(V(1, -1, 0).normalized())) < 1e-5 for v in f.verts)]
        self.assertEqual(mitre, [])
        # end cap at y = 3.25? no: the tube ends at the path end y = 3 facing +Y
        ends = [f for f in bm.faces if abs(f.calc_center_median().y - 3.0) < 1e-6]
        self.assertEqual(len(ends), 1)
        self.assertGreater(ends[0].normal.y, 0.99)
        start = [f for f in bm.faces if abs(f.calc_center_median().x) < 1e-6]
        self.assertEqual(len(start), 1)
        self.assertLess(start[0].normal.x, -0.99)
        # sides point away from the path
        for f in bm.faces:
            c = f.calc_center_median()
            if abs(f.normal.z) > 0.99:
                self.assertGreater(f.normal.z * (c.z - 1.0), 0.0)
        self.assertEqual(self.steps(), 3)                       # 2 test writes + Siga-me

    def test_ac_sig_2_closed_moulding(self):
        self.box(4, 4, "2")
        self.add([(1, 0, 2), (1, -0.1, 2), (1, -0.1, 2.1), (1, 0, 2.1)], True)      # profile outside the wall
        n = self.select_edges(lambda e: all(abs(v.co.z - 2) < 1e-6 and (abs(v.co.y) < 1e-6 or abs(v.co.y - 4) < 1e-6
                                                                          or abs(v.co.x) < 1e-6 or abs(v.co.x - 4) < 1e-6)
                                            for v in e.verts))
        self.assertEqual(n, 5)                                   # the top edge is split at x = 1 by the profile
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), FM, testing.pt(0, 0, 1))
        testing.click(face_inf((1, -0.05, 2.05)))
        st = self.stats()
        self.assertEqual(st["non_planar"], 0)
        bm = document.root().bm
        frame = [f for f in bm.faces if f.calc_center_median().z > 2.0 - 1e-6 and not abs(f.calc_center_median().z - 2.0) < 1e-6
                 or (abs(f.calc_center_median().z - 2.0) < 1e-6 and abs(f.normal.z) > 0.99 and
                     (f.calc_center_median().x < 0 or f.calc_center_median().y < 0 or f.calc_center_median().x > 4
                      or f.calc_center_median().y > 4))]
        self.assertGreaterEqual(len(frame), 16)
        self.assertFalse(any(abs(f.calc_center_median().x - 1.0) < 1e-6 and abs(f.normal.x) > 0.99 for f in bm.faces))
        tops = [f for f in bm.faces if abs(f.calc_center_median().z - 2.1) < 1e-6]
        self.assertTrue(tops and all(f.normal.z > 0.99 for f in tops))
        self.assertEqual(self.steps(), 4)                       # box (2) + profile + Siga-me

    def test_path_by_hovering_an_edge(self):
        self.add([(0, 0, 1), (4, 0, 1)], False)
        self.add([(0, -0.25, 0.75), (0, 0.25, 0.75), (0, 0.25, 1.25), (0, -0.25, 1.25)], True)
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), FM, testing.pt(0, 0, 1))
        testing.click(face_inf((0, 0, 1)))
        self.assertTrue(base.DISPATCH.running)
        self.assertEqual(testing.state_dump()["hint_key"], "tool.su.followme.hint_path")
        bm = document.root().bm
        bm.edges.ensure_lookup_table()
        e = next(e for e in bm.edges if all(abs(v.co.z - 1) < 1e-6 and abs(v.co.y) < 1e-6 for v in e.verts)
                 and any(v.co.x > 1 for v in e.verts))
        inf = testing.pt(2, 0, 1, kind="ON_EDGE", ref_edge=(document.root().key, e.index), doc_key=document.root().key)
        testing.move(inf)
        self.assertTrue(base.controller(FM).path_world)
        testing.click(inf)
        self.assertFalse(base.DISPATCH.running)
        self.assertEqual(self.stats()["faces"], 6)


if __name__ == "__main__":
    unittest.main()
