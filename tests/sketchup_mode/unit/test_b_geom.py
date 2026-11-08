# SPDX-License-Identifier: GPL-2.0-or-later
"""Geometry kernel tests (owner: B): add_edge / auto_faces / rebuild_face (CDT) / erase / heal.
Every test ends with geom.validate(bm) == []. AF-* ids = doc/sketchup_mode/ROTEIRO_CASA.md
("Apagar uma face", kernel-level parts); AC-* ids = PLANO.md §6."""

import math
import unittest

import bmesh
from mathutils import Vector

from su.core import geom

V = Vector
UP = V((0, 0, 1))


def new_bm():
    bm = bmesh.new()
    geom.ensure_layers(bm)
    return bm


def rect(bm, x0, y0, x1, y1, z=0.0):
    pts = [V((x0, y0, z)), V((x1, y0, z)), V((x1, y1, z)), V((x0, y1, z))]
    return geom.add_polyline(bm, pts, True)


def box(bm, sx=8.0, sy=6.0, sz=3.0):
    """Box drawn edge by edge (12 add_edge): faces appear as loops close."""
    b = [V((0, 0, 0)), V((sx, 0, 0)), V((sx, sy, 0)), V((0, sy, 0))]
    t = [p + V((0, 0, sz)) for p in b]
    for i in range(4):
        geom.add_edge(bm, b[i], b[(i + 1) % 4])
    for i in range(4):
        geom.add_edge(bm, b[i], t[i])
    for i in range(4):
        geom.add_edge(bm, t[i], t[(i + 1) % 4])


def counts(bm):
    lay = geom.layers(bm)
    return (len(bm.verts), sum(1 for e in bm.edges if not e[lay.bridge]), len(bm.faces))


def logical(bm):
    """[(area, normal)] of every logical face, sorted by area (4 places: mathutils is float32)."""
    out = []
    for cl in geom.clusters(bm, list(bm.faces)):
        out.append((round(sum(f.calc_area() for f in cl), 4), cl[0].normal.copy()))
    return sorted(out, key=lambda a: a[0])


def first(seq):
    return next(iter(seq))


def find_face(bm, center, tol=1e-4):
    for f in bm.faces:
        if (f.calc_center_median() - V(center)).length < tol:
            return f
    return None


def find_edge(bm, a, b, tol=1e-6):
    a, b = V(a), V(b)
    for e in bm.edges:
        p, q = e.verts[0].co, e.verts[1].co
        if ((p - a).length < tol and (q - b).length < tol) or ((p - b).length < tol and (q - a).length < tol):
            return e
    return None


def bridges(bm):
    lay = geom.layers(bm)
    return sum(1 for e in bm.edges if e[lay.bridge])


class KernelCase(unittest.TestCase):
    def setUp(self):
        self.bm = new_bm()

    def tearDown(self):
        problems = geom.validate(self.bm)
        self.bm.free()
        self.assertEqual(problems, [])

    def assertNormal(self, n, expected):
        self.assertAlmostEqual((V(n) - V(expected)).length, 0.0, places=6, msg="normal {} != {}".format(n, expected))


# ------------------------------------------------------------------------------------ add_edge

class TestAddEdge(KernelCase):
    def test_rectangle_by_segments_ac_lin_1(self):
        r = rect(self.bm, 0, 0, 3, 2)
        self.assertEqual(counts(self.bm), (4, 4, 1))
        self.assertEqual(len(r.new_faces), 1)
        f = first(self.bm.faces)
        self.assertAlmostEqual(f.calc_area(), 6.0, places=6)
        self.assertNormal(f.normal, (0, 0, -1))           # floor: back side up
        self.assertEqual(f.material_index, 0)
        self.assertEqual(f[geom.layers(self.bm).back], 1)

    def test_open_chain_no_face(self):
        geom.add_polyline(self.bm, [V((0, 0, 0)), V((1, 0, 0)), V((1, 1, 0))], False)
        self.assertEqual(counts(self.bm), (3, 2, 0))

    def test_weld_and_no_duplicate_edge(self):
        rect(self.bm, 0, 0, 3, 2)
        r = geom.add_edge(self.bm, V((0, 0, 0)), V((3, 0, 0)))      # redraw an existing edge
        self.assertEqual(r.new_edges, [])
        self.assertEqual(counts(self.bm), (4, 4, 1))
        geom.add_edge(self.bm, V((3, 2, 0)), V((3 + 1e-7, 3, 0)))   # welds to (3,2,0)
        self.assertEqual(counts(self.bm), (5, 5, 1))

    def test_diagonal_divides_ac_lin_2(self):
        rect(self.bm, 0, 0, 3, 2)
        r = geom.add_edge(self.bm, V((0, 0, 0)), V((3, 2, 0)))
        self.assertEqual(counts(self.bm), (4, 5, 2))
        self.assertEqual(len(r.new_faces), 2)
        self.assertEqual([a for a, _n in logical(self.bm)], [3.0, 3.0])
        for _a, n in logical(self.bm):
            self.assertNormal(n, (0, 0, -1))           # split pieces keep the original side

    def test_crossing_diagonals_split_both_ac_lin_2(self):
        rect(self.bm, 0, 0, 2, 2)
        geom.add_edge(self.bm, V((0, 0, 0)), V((2, 2, 0)))
        geom.add_edge(self.bm, V((2, 0, 0)), V((0, 2, 0)))
        self.assertEqual(counts(self.bm), (5, 8, 4))
        self.assertIsNotNone(find_edge(self.bm, (0, 0, 0), (1, 1, 0)))
        self.assertEqual([a for a, _n in logical(self.bm)], [1.0] * 4)

    def test_border_to_border_on_vertical_face_ac_lin_4(self):
        pts = [V((0, 0, 0)), V((4, 0, 0)), V((4, 0, 3)), V((0, 0, 3))]
        geom.add_polyline(self.bm, pts, True)
        self.assertEqual(len(self.bm.faces), 1)
        n0 = first(self.bm.faces).normal.copy()
        geom.add_edge(self.bm, V((1, 0, 0)), V((1, 0, 3)))     # endpoints split the borders
        self.assertEqual(counts(self.bm), (6, 7, 2))
        self.assertEqual([a for a, _n in logical(self.bm)], [3.0, 9.0])
        for _a, n in logical(self.bm):
            self.assertNormal(n, n0)

    def test_dangling_edge_on_face_does_not_split(self):
        rect(self.bm, 0, 0, 4, 4)
        geom.add_edge(self.bm, V((1, 1, 0)), V((2, 2, 0)))
        geom.add_edge(self.bm, V((0, 0, 0)), V((1, 1, 0)))     # from a corner: still a dangling chain
        self.assertEqual(len(self.bm.faces), 1)
        self.assertAlmostEqual(first(self.bm.faces).calc_area(), 16.0, places=6)

    def test_box_from_12_edges(self):
        box(self.bm)
        self.assertEqual(counts(self.bm), (8, 12, 6))
        center = V((4, 3, 1.5))
        for f in self.bm.faces:
            self.assertGreater(f.normal.dot(f.calc_center_median() - center), 0.0, "normal points outwards")
        self.assertAlmostEqual(sum(f.calc_area() for f in self.bm.faces), 2 * (48 + 24 + 18), places=5)

    def test_rectangle_inside_face_makes_hole_ac_ret_3(self):
        rect(self.bm, 0, 0, 3, 3)
        rect(self.bm, 1, 1, 2, 2)
        self.assertEqual(counts(self.bm), (8, 8, len(self.bm.faces)))
        lf = logical(self.bm)
        self.assertEqual([a for a, _n in lf], [1.0, 8.0])
        self.assertGreaterEqual(bridges(self.bm), 2)
        for _a, n in lf:
            self.assertNormal(n, (0, 0, -1))

    def test_door_on_wall_bottom_edge_ac_ret_4(self):
        wall = [V((0, 0, 0)), V((4, 0, 0)), V((4, 0, 2.8)), V((0, 0, 2.8))]
        geom.add_polyline(self.bm, wall, True)
        door = [V((1, 0, 0)), V((1, 0, 2.1)), V((1.9, 0, 2.1)), V((1.9, 0, 0))]
        geom.add_polyline(self.bm, door, False)
        self.assertEqual(bridges(self.bm), 0)
        self.assertEqual(len(self.bm.faces), 2)
        self.assertEqual([a for a, _n in logical(self.bm)], [round(0.9 * 2.1, 4), round(4 * 2.8 - 0.9 * 2.1, 4)])

    def test_rectangle_around_existing_face_contains_it(self):
        rect(self.bm, 1, 1, 2, 2)
        rect(self.bm, 0, 0, 3, 3)
        self.assertEqual([a for a, _n in logical(self.bm)], [1.0, 8.0])

    def test_nested_loops(self):
        rect(self.bm, 0, 0, 6, 6)
        rect(self.bm, 1, 1, 5, 5)
        rect(self.bm, 2, 2, 4, 4)
        self.assertEqual([a for a, _n in logical(self.bm)], [4.0, 12.0, 20.0])

    def test_curve_id_on_new_edges(self):
        pts = geom.circle_points(V((0, 0, 0)), UP, 1.0, 12)
        r = geom.add_closed_shape(self.bm, pts, UP, curve_id=7)
        lay = geom.layers(self.bm)
        self.assertEqual({e[lay.curve] for e in self.bm.edges}, {7})
        self.assertEqual(len(r.new_faces), 1)
        self.assertAlmostEqual(first(self.bm.faces).calc_area(), 3.0, places=6)        # AC-CIR-1
        self.assertNormal(first(self.bm.faces).normal, UP)


# --------------------------------------------------------------------------------- rebuild_face

SQ3 = [V((0, 0, 0)), V((3, 0, 0)), V((3, 3, 0)), V((0, 3, 0))]
H1 = [V((1, 1, 0)), V((2, 1, 0)), V((2, 2, 0)), V((1, 2, 0))]


class TestRebuildFace(KernelCase):
    def rebuild(self, outer, inners=(), normal=UP, mat=0, back=1, through=frozenset()):
        return geom.rebuild_face(self.bm, outer, list(inners), normal, mat, back, through_holes=through)

    def test_01_simple(self):
        fs = self.rebuild(SQ3)
        self.assertEqual(len(fs), 1)
        self.assertEqual(bridges(self.bm), 0)
        self.assertNormal(fs[0].normal, UP)

    def test_02_through_hole(self):
        fs = self.rebuild(SQ3, [H1], through={0})
        self.assertAlmostEqual(sum(f.calc_area() for f in fs), 8.0, places=6)
        self.assertGreaterEqual(bridges(self.bm), 2)
        self.assertEqual(len(geom.clusters(self.bm, list(self.bm.faces))), 1)

    def test_03_hole_with_inner_face(self):
        self.rebuild(SQ3, [H1])
        self.assertEqual([a for a, _n in logical(self.bm)], [1.0, 8.0])

    def test_04_hole_touching_border(self):
        hole = [V((1, 0, 0)), V((2, 0, 0)), V((2, 1, 0)), V((1, 1, 0))]
        fs = self.rebuild(SQ3, [hole], through={0})
        self.assertEqual(bridges(self.bm), 0)
        self.assertAlmostEqual(sum(f.calc_area() for f in fs), 8.0, places=6)

    def test_05_two_holes(self):
        outer = [V((0, 0, 0)), V((5, 0, 0)), V((5, 3, 0)), V((0, 3, 0))]
        h2 = [V((3, 1, 0)), V((4, 1, 0)), V((4, 2, 0)), V((3, 2, 0))]
        fs = self.rebuild(outer, [H1, h2], through={0, 1})
        self.assertAlmostEqual(sum(f.calc_area() for f in fs), 13.0, places=6)
        self.assertEqual(len(geom.clusters(self.bm, list(self.bm.faces))), 1)

    def test_06_hole_in_hole(self):
        outer = [V((0, 0, 0)), V((6, 0, 0)), V((6, 6, 0)), V((0, 6, 0))]
        mid = [V((1, 1, 0)), V((5, 1, 0)), V((5, 5, 0)), V((1, 5, 0))]
        inner = [V((2, 2, 0)), V((4, 2, 0)), V((4, 4, 0)), V((2, 4, 0))]
        self.rebuild(mid, [inner], through={0})          # ring 16 - 4
        self.rebuild(outer, [mid], through={0})          # outer ring, the existing ring is kept
        self.assertEqual([a for a, _n in logical(self.bm)], [12.0, 20.0])

    def test_07_concave_L_with_hole(self):
        L = [V((0, 0, 0)), V((4, 0, 0)), V((4, 1, 0)), V((1, 1, 0)), V((1, 4, 0)), V((0, 4, 0))]
        hole = [V((0.25, 2, 0)), V((0.75, 2, 0)), V((0.75, 3, 0)), V((0.25, 3, 0))]
        fs = self.rebuild(L, [hole], through={0})
        self.assertAlmostEqual(sum(f.calc_area() for f in fs), 7.0 - 0.5, places=6)

    def test_08_materials(self):
        fs = self.rebuild(SQ3, [H1], mat=3, back=5, through={0})
        lay = geom.layers(self.bm)
        self.assertEqual({f.material_index for f in fs}, {3})
        self.assertEqual({f[lay.back] for f in fs}, {5})

    def test_09_normal_down(self):
        fs = self.rebuild(SQ3, [H1], normal=V((0, 0, -1)), through={0})
        for f in fs:
            self.assertNormal(f.normal, (0, 0, -1))

    def test_10_vertical_plane(self):
        outer = [V((0, 0, 0)), V((0, 4, 0)), V((0, 4, 3)), V((0, 0, 3))]
        hole = [V((0, 1, 1)), V((0, 2, 1)), V((0, 2, 2)), V((0, 1, 2))]
        fs = self.rebuild(outer, [hole], normal=V((1, 0, 0)), through={0})
        self.assertAlmostEqual(sum(f.calc_area() for f in fs), 11.0, places=6)
        for f in fs:
            self.assertNormal(f.normal, (1, 0, 0))

    def test_11_replaces_existing_face(self):
        self.rebuild(SQ3)
        self.rebuild(SQ3, [H1], through={0})
        self.assertEqual([a for a, _n in logical(self.bm)], [8.0])

    def test_12_idempotent(self):
        self.rebuild(SQ3, [H1], through={0})
        n = counts(self.bm)
        self.rebuild(SQ3, [H1], through={0})
        self.assertEqual(counts(self.bm), n)
        self.assertEqual([a for a, _n in logical(self.bm)], [8.0])

    def test_13_existing_inner_face_kept(self):
        self.rebuild(H1, mat=4)
        self.rebuild(SQ3, [H1])                 # not through, but a face already covers the hole
        self.assertEqual(len(geom.clusters(self.bm, list(self.bm.faces))), 2)
        inner = find_face(self.bm, (1.5, 1.5, 0))
        self.assertEqual(inner.material_index, 4)

    def test_14_bridges_are_not_input_edges(self):
        self.rebuild(SQ3, [H1], through={0})
        lay = geom.layers(self.bm)
        for e in self.bm.edges:
            if e[lay.bridge]:
                self.assertEqual(len(e.link_faces), 2)
        self.assertEqual(counts(self.bm)[1], 8)

    def test_15_offset_plane(self):
        outer = [p + V((0, 0, 2.5)) for p in SQ3]
        hole = [p + V((0, 0, 2.5)) for p in H1]
        fs = self.rebuild(outer, [hole], through={0})
        for f in fs:
            self.assertAlmostEqual(f.calc_center_median().z, 2.5, places=6)


# -------------------------------------------------------------- erase (ROTEIRO_CASA "Apagar uma face")

class TestErase(KernelCase):
    def test_af1_erase_face_keeps_edges(self):
        rect(self.bm, 0, 0, 8, 6)
        r = geom.erase_faces(self.bm, [first(self.bm.faces)])
        self.assertEqual(r.removed_faces, 1)
        self.assertEqual(counts(self.bm), (4, 4, 0))

    def test_af2_erase_box_top_only(self):
        box(self.bm)
        for i, f in enumerate(self.bm.faces):
            f.material_index = i + 2
        before = {tuple(round(c, 6) for c in f.calc_center_median()):
                  (round(f.calc_area(), 6), f.normal.copy(), f.material_index) for f in self.bm.faces}
        top = find_face(self.bm, (4, 3, 3))
        geom.erase_faces(self.bm, [top])
        self.assertEqual(counts(self.bm), (8, 12, 5))
        self.assertIsNone(find_face(self.bm, (4, 3, 3)))
        for f in self.bm.faces:
            key = tuple(round(c, 6) for c in f.calc_center_median())
            area, n, mat = before[key]
            self.assertAlmostEqual(f.calc_area(), area, places=6)
            self.assertNormal(f.normal, n)
            self.assertEqual(f.material_index, mat)

    def test_af3_erase_edge_removes_its_two_faces(self):
        box(self.bm)
        e = find_edge(self.bm, (0, 0, 3), (8, 0, 3))
        r = geom.erase_edges(self.bm, [e])
        self.assertEqual(r.removed_faces, 2)
        self.assertEqual(counts(self.bm), (8, 11, 4))
        self.assertIsNone(find_face(self.bm, (4, 3, 3)))       # top
        self.assertIsNone(find_face(self.bm, (4, 0, 1.5)))     # front

    def test_af3b_nothing_to_erase(self):
        box(self.bm)
        geom.erase_edges(self.bm, [])
        geom.erase_faces(self.bm, [])
        self.assertEqual(counts(self.bm), (8, 12, 6))

    def test_af3c_erase_ridge_merges_top(self):
        box(self.bm)
        geom.add_edge(self.bm, V((4, 0, 3)), V((4, 6, 3)))
        self.assertEqual(counts(self.bm), (10, 15, 7))
        top_n = find_face(self.bm, (2, 3, 3)).normal.copy()
        e = find_edge(self.bm, (4, 0, 3), (4, 6, 3))
        r = geom.erase_edges(self.bm, [e])
        self.assertEqual(counts(self.bm), (8, 12, 6))
        top = find_face(self.bm, (4, 3, 3))
        self.assertIsNotNone(top)
        self.assertAlmostEqual(top.calc_area(), 48.0, places=6)
        self.assertNormal(top.normal, top_n)
        self.assertEqual(len(r.new_faces), 1)
        self.assertIsNotNone(find_edge(self.bm, (0, 0, 3), (8, 0, 3)))    # 8 m edges whole again

    def test_af4_redraw_edge_heals_top_ac_lin_3(self):
        box(self.bm)
        geom.erase_faces(self.bm, [find_face(self.bm, (4, 3, 3))])
        r = geom.add_edge(self.bm, V((0, 0, 3)), V((8, 0, 3)))
        self.assertEqual(r.new_edges, [])
        self.assertEqual(len(r.new_faces), 1)
        self.assertEqual(counts(self.bm), (8, 12, 6))
        top = find_face(self.bm, (4, 3, 3))
        self.assertNormal(top.normal, (0, 0, 1))      # closes the solid → outwards

    def test_af5_erase_top_and_its_edges(self):
        box(self.bm)
        top = find_face(self.bm, (4, 3, 3))
        edges = list(top.edges)
        geom.erase_faces(self.bm, [top])
        geom.erase_edges(self.bm, edges)
        self.assertEqual(counts(self.bm), (8, 8, 1))
        self.assertIsNotNone(find_face(self.bm, (4, 3, 0)))

    def test_erase_face_with_hole_removes_bridges(self):
        rect(self.bm, 0, 0, 3, 3)
        rect(self.bm, 1, 1, 2, 2)
        inner = next(f for f in self.bm.faces
                     if all(1 - 1e-6 <= c <= 2 + 1e-6 for v in f.verts for c in v.co.xy))
        outer = next(f for f in self.bm.faces if f is not inner)      # a piece of the ring
        geom.erase_faces(self.bm, [outer])
        self.assertEqual(bridges(self.bm), 0)
        self.assertEqual(counts(self.bm), (8, 8, 1))
        self.assertAlmostEqual(first(self.bm.faces).calc_area(), 1.0, places=6)

    def test_erase_divider_merges_ac_apg_1(self):
        rect(self.bm, 0, 0, 4, 2)
        geom.add_edge(self.bm, V((2, 0, 0)), V((2, 2, 0)))
        self.assertEqual(counts(self.bm), (6, 7, 2))
        geom.erase_edges(self.bm, [find_edge(self.bm, (2, 0, 0), (2, 2, 0))])
        self.assertEqual(counts(self.bm), (4, 4, 1))
        self.assertAlmostEqual(first(self.bm.faces).calc_area(), 8.0, places=6)
        self.assertNormal(first(self.bm.faces).normal, (0, 0, -1))

    def test_erase_wire_edge_removes_loose_vertex(self):
        geom.add_edge(self.bm, V((0, 0, 0)), V((1, 0, 0)))
        geom.erase_edges(self.bm, list(self.bm.edges))
        self.assertEqual(counts(self.bm), (0, 0, 0))

    def test_merge_coplanar(self):
        rect(self.bm, 0, 0, 4, 2)
        geom.add_edge(self.bm, V((2, 0, 0)), V((2, 2, 0)))
        geom.merge_coplanar(self.bm, list(self.bm.edges))
        self.assertEqual(counts(self.bm), (4, 4, 1))


class TestBridgeCrossing(KernelCase):
    """Bug from E: add_edge split su_bridge edges and left stray vertices. Bridges are not geometry:
    only visible edges split; the crossed logical face is rebuilt with new bridges."""

    def assertNoStrayVertex(self):
        lay = geom.layers(self.bm)
        for v in self.bm.verts:
            vis = [e for e in v.link_edges if not e[lay.bridge]]
            self.assertGreaterEqual(len(vis), 1, "vertex only on bridges: {}".format(v.co))
            if len(vis) == 2:
                d1 = vis[0].other_vert(v).co - v.co
                d2 = vis[1].other_vert(v).co - v.co
                self.assertGreater(d1.cross(d2).length, 1e-6 * d1.length * d2.length,
                                   "stray collinear vertex at {}".format(v.co))

    def test_line_through_face_with_inner_face(self):
        rect(self.bm, 0, 0, 3, 3)
        rect(self.bm, 1, 1, 2, 2)
        self.assertGreaterEqual(bridges(self.bm), 2)
        geom.add_edge(self.bm, V((0, 1.5, 0)), V((3, 1.5, 0)))
        self.assertEqual(counts(self.bm), (12, 15, 4))
        self.assertEqual(bridges(self.bm), 0)            # both halves of the ring are simple
        self.assertEqual([a for a, _n in logical(self.bm)], [0.5, 0.5, 4.0, 4.0])
        for _a, n in logical(self.bm):
            self.assertNormal(n, (0, 0, -1))
        self.assertNoStrayVertex()

    def test_line_through_hole_region(self):
        geom.rebuild_face(self.bm, [V((0, 0, 0)), V((3, 0, 0)), V((3, 3, 0)), V((0, 3, 0))],
                          [[V((1, 1, 0)), V((2, 1, 0)), V((2, 2, 0)), V((1, 2, 0))]],
                          V((0, 0, -1)), 2, 1, through_holes={0})
        geom.add_edge(self.bm, V((0, 1.5, 0)), V((3, 1.5, 0)))
        # the ring splits in 2 (material kept); each half of the hole is now a closed loop through
        # a new edge, so it gets a new default face (SketchUp healing rule)
        self.assertEqual(counts(self.bm), (12, 15, 4))
        self.assertEqual(bridges(self.bm), 0)
        self.assertEqual([a for a, _n in logical(self.bm)], [0.5, 0.5, 4.0, 4.0])
        self.assertEqual(sorted(f.material_index for f in self.bm.faces), [0, 0, 2, 2])
        self.assertNoStrayVertex()

    def test_line_through_ring_only(self):
        rect(self.bm, 0, 0, 6, 6)
        rect(self.bm, 2, 2, 4, 4)
        geom.add_edge(self.bm, V((0, 1, 0)), V((6, 1, 0)))          # below the inner square
        self.assertEqual(counts(self.bm)[:2], (10, 11))
        self.assertGreaterEqual(bridges(self.bm), 2)                   # the upper part keeps a hole
        self.assertEqual([a for a, _n in logical(self.bm)], [4.0, 6.0, 26.0])
        self.assertNoStrayVertex()

    def test_offset_like_inner_loop(self):
        geom.rebuild_face(self.bm, [V((0, 0, 0)), V((6, 0, 0)), V((6, 6, 0)), V((0, 6, 0))],
                          [[V((2, 2, 0)), V((4, 2, 0)), V((4, 4, 0)), V((2, 4, 0))]],
                          V((0, 0, 1)), 0, 1, through_holes={0})
        rect(self.bm, 1, 1, 5, 5)                    # loop between the border and the hole
        self.assertEqual(counts(self.bm), (12, 12, len(self.bm.faces)))
        self.assertEqual([a for a, _n in logical(self.bm)], [12.0, 20.0])
        for _a, n in logical(self.bm):
            self.assertNormal(n, (0, 0, 1))
        self.assertNoStrayVertex()

    def test_endpoint_on_a_bridge_does_not_split_it(self):
        rect(self.bm, 0, 0, 3, 3)
        rect(self.bm, 1, 1, 2, 2)
        lay = geom.layers(self.bm)
        br = next(e for e in self.bm.edges if e[lay.bridge])
        mid = (br.verts[0].co + br.verts[1].co) * 0.5
        n_before = len(self.bm.verts)
        v = geom.weld_point(self.bm, mid)
        self.assertEqual(len(self.bm.verts), n_before + 1)
        self.assertEqual(len(v.link_edges), 0)        # a free vertex, the bridge is untouched
        self.bm.verts.remove(v)


class TestHelpers(unittest.TestCase):
    def test_circle_and_arcs(self):
        pts = geom.circle_points(V((0, 0, 0)), UP, 2.0, 24)
        self.assertEqual(len(pts), 24)
        self.assertTrue(all(abs(p.length - 2.0) < 1e-5 for p in pts))
        arc = geom.arc_from_bulge(V((0, 0, 0)), V((2, 0, 0)), 1.0, UP, 12)     # AC-ARC-1 semicircle
        self.assertEqual(len(arc), 13)
        self.assertAlmostEqual((arc[-1] - V((2, 0, 0))).length, 0.0, places=6)
        self.assertAlmostEqual((arc[6] - V((1, 1, 0))).length, 0.0, places=6)
        self.assertTrue(all(abs((p - V((1, 0, 0))).length - 1.0) < 1e-5 for p in arc))

    def test_is_planar(self):
        bm = new_bm()
        vs = [bm.verts.new(c) for c in ((0, 0, 0), (1, 0, 0), (1, 1, 0.2), (0, 1, 0))]
        f = bm.faces.new(vs)
        f.normal_update()
        self.assertFalse(geom.is_planar(f))
        vs[2].co.z = 0.0
        self.assertTrue(geom.is_planar(f))
        bm.free()


if __name__ == "__main__":
    unittest.main()
