# SPDX-License-Identifier: GPL-2.0-or-later
"""B tests: fold (ensure_planar / is_planar, AC-MOV-5/6 kernel), entities (logical_face, surface,
pick_entity, curves + metadata; AC-SEL-1..3 kernel parts)."""

import math
import unittest

import bmesh
from mathutils import Vector as V

from su.core import entities, geom

from test_b_document import _fresh_root
from test_b_geom import box, counts, find_edge, find_face, first, new_bm, rect

UP = V((0, 0, 1))


def cylinder(bm, sides=24, r=1.0, h=2.0):
    """Cylinder like Círculo + Empurrar/puxar: caps are curve faces, sides are su_soft quads."""
    lay = geom.ensure_layers(bm)
    bot = [bm.verts.new((r * math.cos(2 * math.pi * i / sides), r * math.sin(2 * math.pi * i / sides), 0))
           for i in range(sides)]
    top = [bm.verts.new(v.co + V((0, 0, h))) for v in bot]
    for ring, cid in ((bot, 1), (top, 2)):
        for i in range(sides):
            bm.edges.new((ring[i], ring[(i + 1) % sides]))[lay.curve] = cid
    for i in range(sides):
        bm.edges.new((bot[i], top[i]))[lay.soft] = True
    geom.new_face(bm, bot, normal=V((0, 0, -1)))
    geom.new_face(bm, top, normal=UP)
    for i in range(sides):
        j = (i + 1) % sides
        f = geom.new_face(bm, [bot[i], bot[j], top[j], top[i]])
        geom.orient_face(f, (bot[i].co + bot[j].co) * 0.5)
    bm.edges.index_update()
    bm.faces.index_update()


class Case(unittest.TestCase):
    def setUp(self):
        self.bm = new_bm()

    def tearDown(self):
        problems = geom.validate(self.bm)
        self.bm.free()
        self.assertEqual(problems, [])


class TestFold(Case):
    def test_ac_mov_5_one_vertex_up(self):
        box(self.bm)
        top = find_face(self.bm, (4, 3, 3))
        corner = next(v for v in top.verts if (v.co - V((8, 6, 3))).length < 1e-6)
        corner.co.z = 3.5
        top.normal_update()
        self.assertFalse(geom.is_planar(top))
        r = geom.ensure_planar(self.bm, list(self.bm.faces))
        self.assertEqual(len(r.new_edges), 1)
        self.assertEqual(len(r.new_faces), 1)
        self.assertEqual(counts(self.bm), (8, 13, 7))
        lay = geom.layers(self.bm)
        self.assertFalse(r.new_edges[0][lay.bridge])          # the fold is a visible edge
        for f in self.bm.faces:
            self.assertTrue(geom.is_planar(f))
            if f.calc_center_median().z > 2.9:
                self.assertGreater(f.normal.z, 0.5)              # pieces keep the outward side

    def test_ac_mov_6_ridge_up_needs_no_fold(self):
        box(self.bm)
        geom.add_edge(self.bm, V((4, 0, 3)), V((4, 6, 3)))
        for v in self.bm.verts:
            if abs(v.co.x - 4) < 1e-6 and abs(v.co.z - 3) < 1e-6:
                v.co.z = 4.0
        r = geom.ensure_planar(self.bm, list(self.bm.faces))
        self.assertEqual(r.new_edges, [])
        self.assertEqual(counts(self.bm), (10, 15, 7))
        self.assertTrue(all(geom.is_planar(f) for f in self.bm.faces))

    def test_material_kept_and_planar_untouched(self):
        rect(self.bm, 0, 0, 2, 2)
        f = first(self.bm.faces)
        f.material_index = 3
        self.assertEqual(geom.ensure_planar(self.bm, [f]).new_edges, [])
        next(v for v in f.verts if v.co.x > 1 and v.co.y > 1).co.z = 0.3
        geom.ensure_planar(self.bm, [f])
        self.assertEqual({g.material_index for g in self.bm.faces}, {3})
        self.assertEqual(len(self.bm.faces), 2)

    def test_hexagon_one_vertex_out(self):
        pts = [V((math.cos(a), math.sin(a), 0)) for a in (i * math.pi / 3 for i in range(6))]
        geom.add_closed_shape(self.bm, pts, UP)
        f = first(self.bm.faces)
        f.verts[0].co.z = 0.4
        geom.ensure_planar(self.bm, [f])
        self.assertTrue(all(geom.is_planar(g) for g in self.bm.faces))
        self.assertEqual(len(self.bm.faces), 2)          # one triangle with the moved vertex + rest


class TestEntities(Case):
    def test_logical_face_with_hole(self):
        rect(self.bm, 0, 0, 3, 3)
        rect(self.bm, 1, 1, 2, 2)
        self.bm.faces.index_update()
        inner = next(f for f in self.bm.faces
                     if all(1 - 1e-6 <= c <= 2 + 1e-6 for v in f.verts for c in v.co.xy))
        ring_piece = next(f for f in self.bm.faces if f is not inner)
        lf = entities.logical_face(self.bm, ring_piece)
        self.assertGreaterEqual(len(lf.faces), 2)
        self.assertEqual(len(lf.outer_loop), 4)
        self.assertEqual(len(lf.inner_loops), 1)
        self.assertEqual(len(lf.inner_loops[0]), 4)
        self.assertAlmostEqual(lf.plane[0].z, -1.0, places=6)
        kind, idx = entities.pick_entity(self.bm, 'FACE', ring_piece.index)
        self.assertEqual(kind, 'FACE')
        self.assertEqual(idx, sorted(f.index for f in lf.faces))
        self.assertEqual(entities.pick_entity(self.bm, 'FACE', inner.index), ('FACE', [inner.index]))

    def test_ac_sel_2_circle_edge_is_curve(self):
        pts = geom.circle_points(V((0, 0, 0)), UP, 1.0, 24)
        geom.add_closed_shape(self.bm, pts, UP, curve_id=5)
        self.bm.edges.index_update()
        kind, idx = entities.pick_entity(self.bm, 'EDGE', 3)
        self.assertEqual(kind, 'CURVE')
        self.assertEqual(len(idx), 24)

    def test_plain_edge(self):
        rect(self.bm, 0, 0, 2, 2)
        self.bm.edges.index_update()
        self.assertEqual(entities.pick_entity(self.bm, 'EDGE', 1), ('EDGE', [1]))

    def test_ac_sel_3_cylinder_side_is_surface(self):
        cylinder(self.bm)
        side = next(f for f in self.bm.faces if len(f.verts) == 4)
        kind, idx = entities.pick_entity(self.bm, 'FACE', side.index)
        self.assertEqual(kind, 'SURFACE')
        self.assertEqual(len(idx), 24)
        cap = next(f for f in self.bm.faces if len(f.verts) == 24)
        self.assertEqual(entities.pick_entity(self.bm, 'FACE', cap.index), ('FACE', [cap.index]))
        rim = next(e for e in self.bm.edges if e[geom.layers(self.bm).curve] == 2)
        self.assertEqual(len(entities.curve_edges(self.bm, rim)), 24)

    def test_ac_sel_1_box_top_kernel(self):
        box(self.bm)
        self.bm.faces.index_update()
        top = find_face(self.bm, (4, 3, 3))
        self.assertEqual(entities.pick_entity(self.bm, 'FACE', top.index), ('FACE', [top.index]))


class TestCurveMeta(unittest.TestCase):
    def test_meta_round_trip_and_new_id(self):
        doc = _fresh_root()
        self.assertEqual(entities.new_curve_id(doc), 1)
        pts = geom.circle_points(V((0, 0, 0)), UP, 1.0, 12)
        geom.add_closed_shape(doc.bm, pts, UP, curve_id=1)
        entities.set_curve_meta(doc, 1, {"kind": "CIRCLE", "radius": 1.0, "sides": 12})
        entities.set_curve_meta(doc, 4, {"kind": "ARC"})
        self.assertEqual(entities.get_curve_meta(doc, 1)["sides"], 12)
        self.assertEqual(entities.new_curve_id(doc), 5)
        entities.set_curve_meta(doc, 4, None)
        self.assertIsNone(entities.get_curve_meta(doc, 4))
        self.assertEqual(entities.new_curve_id(doc), 2)


if __name__ == "__main__":
    unittest.main()
