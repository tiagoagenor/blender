# SPDX-License-Identifier: GPL-2.0-or-later
"""C: spatial queries + inference engine with a synthetic camera (AC-INF-1..6, hover_plane, locks)."""

import math
import unittest

import bpy
from mathutils import Vector

import test_c_fakes as F
from su import constants as K
from su.core import inference, spatial
from su.core.inference import InferenceEngine, QueryCtx
from su.core.state import Inference, Locks, STATE

# box x∈[1,3] y∈[1,3] z∈[0,1]; the camera looks at it from (+x, -y, +z)
MN, MX = (1.0, 1.0, 0.0), (3.0, 3.0, 1.0)


def setUpModule():
    F.isolate_scene()


def tearDownModule():
    F.cleanup()


class _Base(unittest.TestCase):
    def setUp(self):
        F.cleanup()
        F.isolate_scene()
        self.box = F.box("box", MN, MX)
        self.key = spatial.doc_key_of(self.box)
        self.region, self.rv3d = F.camera()
        self.engine = InferenceEngine()
        STATE.ref_points.clear()

    def tearDown(self):
        STATE.ref_points.clear()

    def xy(self, co, dx=0.0, dy=0.0):
        s = F.project(self.region, self.rv3d, co)
        self.assertIsNotNone(s)
        return (s[0] + dx, s[1] + dy)

    def q(self, xy, **kw):
        kw.setdefault("locks", Locks())
        return QueryCtx(self.region, self.rv3d, xy, **kw)

    def query(self, xy, **kw):
        return self.engine.query(self.q(xy, **kw))

    def assertVec(self, a, b, tol=1e-4):
        self.assertLess((Vector(a) - Vector(b)).length, tol, "{} != {}".format(tuple(a), tuple(b)))


class TestSpatial(_Base):
    def test_projection_and_points(self):
        p = spatial.projection(self.region, self.rv3d)
        d = p.doc(self.key)
        self.assertEqual(len(d.edges), 12)
        self.assertEqual(len(d.faces), 6)
        hits = spatial.points_near(p, self.xy((3, 1, 1), 2, 1), 10)
        self.assertEqual(len(hits), 1)
        self.assertVec(hits[0].co, (3, 1, 1))
        vi = hits[0].index
        self.assertEqual(spatial.points_near(p, self.xy((3, 1, 1)), 10, exclude={(self.key, vi)}), [])
        p2 = spatial.projection(self.region, self.rv3d, exclude={self.key})
        self.assertIsNone(p2.doc(self.key))

    def test_hidden_edges_not_inferable(self):
        me = self.box.data
        a = me.attributes.new("su_hidden", 'BOOLEAN', 'EDGE')
        a.data[0].value = True
        p = spatial.projection(self.region, self.rv3d)
        self.assertEqual(len(p.doc(self.key).edges), 11)
        self.assertNotIn(0, set(p.doc(self.key).edge_ids))

    def test_edges_near(self):
        p = spatial.projection(self.region, self.rv3d)
        hits = spatial.edges_near(p, self.xy((3, 1.5, 1)), 5)
        self.assertTrue(hits)
        self.assertVec(hits[0].co, (3, 1.5, 1), 1e-3)

    def test_ray_cast_skip(self):
        top = F.face_index(self.box, (0, 0, 1))
        bottom = F.face_index(self.box, (0, 0, -1))
        h = spatial.ray_cast(None, (2, 2, 10), (0, 0, -1))
        self.assertTrue(h.ok)
        self.assertEqual((h.doc_key, h.face_idx_orig, h.side), (self.key, top, 1))
        self.assertVec(h.point, (2, 2, 1))
        self.assertAlmostEqual(h.distance, 9.0, places=4)
        h = spatial.ray_cast(None, (2, 2, 10), (0, 0, -1), skip={self.key: {top}})
        self.assertEqual((h.face_idx_orig, h.side), (bottom, -1))
        self.assertVec(h.normal_orig, (0, 0, -1))
        self.assertFalse(spatial.ray_cast(None, (2, 2, 10), (0, 0, 1)).ok)

    def test_ray_cast_back_copy(self):
        quad = F.mesh_object("quad", [(5, 5, 0), (6, 5, 0), (6, 6, 0), (5, 6, 0)], faces=[(0, 1, 2, 3)])
        F.add_back_copy_gn(quad)
        dg = bpy.context.evaluated_depsgraph_get()
        self.assertEqual(len(quad.evaluated_get(dg).data.polygons), 2)
        for origin, d, side in (((5.5, 5.5, -3), (0, 0, 1), -1), ((5.5, 5.5, 3), (0, 0, -1), 1)):
            h = spatial.ray_cast(None, origin, d)
            self.assertTrue(h.ok)
            self.assertEqual(h.face_idx_orig, 0)
            self.assertVec(h.normal_orig, (0, 0, 1))
            self.assertEqual(h.side, side)

    def test_rect_query(self):
        p = spatial.projection(self.region, self.rv3d)
        pts = [self.xy(c) for c in [(x, y, z) for x in (1, 3) for y in (1, 3) for z in (0, 1)]]
        x0 = min(s[0] for s in pts) - 5
        x1 = max(s[0] for s in pts) + 5
        y0 = min(s[1] for s in pts) - 5
        y1 = max(s[1] for s in pts) + 5
        r = spatial.rect_query(p, x0, y0, x1, y1, 'WINDOW')
        self.assertEqual((len(r[self.key]['EDGE']), len(r[self.key]['FACE'])), (12, 6))
        c = self.xy((3, 1, 1))
        r = spatial.rect_query(p, c[0] - 4, c[1] - 4, c[0] + 4, c[1] + 4, 'CROSSING')
        self.assertEqual(len(r[self.key]['EDGE']), 3)
        adjacent = {F.face_index(self.box, n) for n in ((0, 0, 1), (0, -1, 0), (1, 0, 0))}
        self.assertTrue(adjacent <= r[self.key]['FACE'])     # crossing also takes faces seen through
        self.assertEqual(spatial.rect_query(p, c[0] - 4, c[1] - 4, c[0] + 4, c[1] + 4, 'WINDOW'), {})


class TestPoints(_Base):
    """AC-INF-1."""

    def test_endpoint(self):
        inf = self.query(self.xy((3, 1, 1), 3, 2))
        self.assertEqual(inf.kind, "ENDPOINT")
        self.assertVec(inf.point, (3, 1, 1), 1e-6)
        self.assertEqual(inf.tooltip_key, "inf.endpoint")
        self.assertEqual(inf.doc_key, self.key)
        self.assertEqual(inf.elem[0], "VERT")
        self.assertVec((*inf.screen, 0), (*self.xy((3, 1, 1)), 0), 1e-3)

    def test_midpoint(self):
        inf = self.query(self.xy((3, 2, 1), -2, 2))
        self.assertEqual(inf.kind, "MIDPOINT")
        self.assertVec(inf.point, (3, 2, 1), 1e-6)

    def test_on_edge(self):
        inf = self.query(self.xy((3, 1.4, 1), 1, 1))
        self.assertEqual(inf.kind, "ON_EDGE")
        self.assertAlmostEqual(inf.point.x, 3.0, places=4)
        self.assertAlmostEqual(inf.point.z, 1.0, places=4)
        self.assertAlmostEqual(inf.point.y, 1.4, delta=0.02)
        self.assertEqual(inf.tooltip_key, "inf.on_edge")

    def test_on_face(self):
        inf = self.query(self.xy((2.3, 2.4, 1)))
        self.assertEqual(inf.kind, "ON_FACE")
        self.assertVec(inf.point, (2.3, 2.4, 1), 1e-3)
        self.assertVec(inf.normal, (0, 0, 1))
        self.assertEqual(inf.side, 1)
        self.assertEqual(inf.elem, ("FACE", F.face_index(self.box, (0, 0, 1))))

    def test_occluded_endpoint(self):
        hidden = (1, 3, 0)                 # back-bottom corner, behind the box
        self.assertFalse(spatial.is_visible(None, self.region, self.rv3d, hidden))
        inf = self.query(self.xy(hidden))
        self.assertFalse(inf.kind == "ENDPOINT" and (inf.point - Vector(hidden)).length < 1e-6)

    def test_origin_and_free(self):
        inf = self.query(self.xy((0, 0, 0), 2, -2))
        self.assertEqual(inf.kind, "ORIGIN")
        self.assertEqual(inf.tooltip_key, "inf.origin")
        inf = self.query(self.xy((-1.5, 4, 0)))
        self.assertEqual(inf.kind, "FREE")              # empty space → ground plane
        self.assertVec(inf.point, (-1.5, 4, 0), 1e-3)
        self.assertEqual(inf.tooltip_key, "")

    def test_flags(self):
        inf = self.query(self.xy((3, 1, 1), 3, 2), flags=frozenset({"FACES"}))
        self.assertNotEqual(inf.kind, "ENDPOINT")


class TestLinear(_Base):
    def test_axis_from_anchor(self):
        """AC-INF-2: red axis from the anchor; ↑ forces blue; Shift keeps the inference."""
        a = Vector((3, 1, 1))
        inf = self.query(self.xy((4.2, 1, 1)), anchor=a)
        self.assertEqual((inf.kind, inf.linear), ("FREE", "AXIS_X"))
        self.assertVec(inf.point, (4.2, 1, 1), 1e-3)
        self.assertEqual(inf.tooltip_key, "inf.axis_x")
        self.assertVec(inf.ref_point, a)
        self.assertFalse(inf.locked)
        for target, lin in (((3, -0.5, 1), "AXIS_Y"), ((3, 1, 2.2), "AXIS_Z")):
            i2 = self.query(self.xy(target), anchor=a)
            self.assertEqual(i2.linear, lin, target)
        locks = Locks()
        self.assertTrue(inference.lock_from_arrow('UP_ARROW', locks))
        self.assertEqual(locks.axis, "AXIS_Z")
        up = self.query(self.xy((4.2, 1, 1)), anchor=a, locks=locks)
        self.assertEqual(up.linear, "AXIS_Z")
        self.assertTrue(up.locked)
        self.assertAlmostEqual(up.point.x, 3.0, places=6)
        self.assertAlmostEqual(up.point.y, 1.0, places=6)
        self.assertTrue(inference.lock_from_arrow('UP_ARROW', locks))
        self.assertEqual(locks.axis, "")
        self.assertFalse(inference.lock_from_arrow('A', locks))
        shift = Locks(shift=inf)
        held = self.query(self.xy((4.0, 1.6, 1.3)), anchor=a, locks=shift)
        self.assertEqual(held.linear, "AXIS_X")
        self.assertTrue(held.locked)
        self.assertAlmostEqual(held.point.y, 1.0, places=6)
        self.assertAlmostEqual(held.point.z, 1.0, places=6)

    def test_locked_line_snaps_to_point(self):
        """A point inference under a locked axis is projected onto the axis (AC-EMP-3 pattern)."""
        tall = F.box("tall", (5, 1, 0), (6, 2, 2))
        locks = Locks(axis="AXIS_Z")
        inf = self.query(self.xy((5, 1, 2), 2, 2), anchor=Vector((3, 1, 1)), locks=locks)
        self.assertEqual(inf.kind, "ENDPOINT")
        self.assertVec(inf.point, (3, 1, 2), 1e-6)
        line = self.query(self.xy((5.5, 1.5, 2)), line=(Vector((2, 2, 1)), Vector((0, 0, 1))))
        self.assertEqual(line.kind, "ON_FACE")             # top of the tall box → z = 2 exactly
        self.assertVec(line.point, (2, 2, 2), 1e-6)
        self.assertTrue(tall)

    def test_priority_endpoint_over_axis(self):
        """AC-INF-3: near an endpoint AND the red axis → Ponto de extremidade."""
        a = Vector((-1, 1, 1))
        inf = self.query(self.xy((1, 1, 1), 2, 1), anchor=a)
        self.assertEqual(inf.kind, "ENDPOINT")
        self.assertVec(inf.point, (1, 1, 1), 1e-6)
        self.assertEqual(inf.linear, "AXIS_X")             # still colours the rubber band
        self.assertEqual(inf.tooltip_key, "inf.endpoint")

    def test_on_face_constant_z(self):
        """AC-INF-4: Linha on the top of the box keeps z constant."""
        a = Vector((1.5, 1.5, 1))
        for p in ((2.5, 2.2, 1), (2.2, 2.6, 1), (1.3, 2.7, 1)):
            inf = self.query(self.xy(p), anchor=a)
            self.assertEqual(inf.kind, "ON_FACE", p)
            self.assertAlmostEqual(inf.point.z, 1.0, places=6)

    def test_parallel_perpendicular(self):
        e = F.mesh_object("diag", [(5, 5, 0), (7, 6, 0)], edges=[(0, 1)])
        hov = self.query(self.xy((5.6, 5.3, 0)))
        self.assertEqual(hov.kind, "ON_EDGE")
        self.assertIsNotNone(self.engine.last_edge)
        a = Vector((5, 8, 0))
        u = Vector((2, 1, 0)).normalized()
        par = self.query(self.xy(a + u * 1.5), anchor=a)
        self.assertEqual(par.linear, "PARALLEL")
        self.assertEqual(par.tooltip_key, "inf.parallel")
        self.assertVec(par.point, a + u * 1.5, 1e-3)
        w = Vector((-1, 2, 0)).normalized()
        per = self.query(self.xy(a + w * 1.2), anchor=a)
        self.assertEqual(per.linear, "PERPENDICULAR")
        self.assertTrue(e)

    def test_perp_face(self):
        n = Vector((1, 1, 0)).normalized()
        a = Vector((6, -2, 0.5))
        inf = self.query(self.xy(a + n * 1.0), anchor=a, anchor_normal=n)
        self.assertEqual(inf.linear, "PERP_FACE")


class TestHysteresis(_Base):
    """AC-INF-5: the endpoint holds at 1.2× the snap radius and is released at 1.6×."""

    def _free_direction(self, corner, neighbours):
        c = Vector(self.xy(corner) + (0.0,))
        angs = []
        for nb in neighbours:
            d = Vector(self.xy(nb) + (0.0,)) - c
            angs.append(math.atan2(d.y, d.x))

        def gap(t):
            return min(abs((t - a + math.pi) % (2 * math.pi) - math.pi) for a in angs)
        best = max((math.radians(k) for k in range(0, 360, 5)), key=gap)
        return math.cos(best), math.sin(best)

    def test_hysteresis(self):
        corner = (3, 1, 1)
        ux, uy = self._free_direction(corner, [(1, 1, 1), (3, 3, 1), (3, 1, 0), (3, 2, 1), (2, 1, 1)])
        rp = inference._px(K.SNAP_PX_POINT)
        held = self.query(self.xy(corner, 2, 0))
        self.assertEqual(held.kind, "ENDPOINT")
        at12 = self.xy(corner, ux * rp * 1.2, uy * rp * 1.2)
        at16 = self.xy(corner, ux * rp * 1.6, uy * rp * 1.6)
        self.assertEqual(self.query(at12, previous=held).kind, "ENDPOINT")
        self.assertNotEqual(self.query(at16, previous=held).kind, "ENDPOINT")
        fresh = InferenceEngine()
        self.assertNotEqual(fresh.query(self.q(at12)).kind, "ENDPOINT")
        # the engine's own last result is the default "previous"
        self.engine.query(self.q(self.xy(corner)))
        self.assertEqual(self.engine.query(self.q(at12)).kind, "ENDPOINT")


class TestFromPoint(_Base):
    """AC-INF-6."""

    def test_acquire_and_from_point(self):
        ep = self.query(self.xy((3, 1, 1), 1, 1))
        self.assertEqual(ep.kind, "ENDPOINT")
        self.assertFalse(self.engine.acquire_tick(ep, 10.0))
        self.assertFalse(self.engine.acquire_tick(ep, 10.2))
        self.assertTrue(self.engine.acquire_tick(ep, 10.0 + K.HOVER_ACQUIRE_S + 0.01))
        self.assertFalse(self.engine.acquire_tick(ep, 11.0))          # only once
        self.assertEqual(len(STATE.ref_points), 1)
        self.assertVec(STATE.ref_points[0], (3, 1, 1))
        inf = self.query(self.xy((3, -1.0, 1)))
        self.assertEqual((inf.linear, inf.tooltip_key), ("FROM_POINT", "inf.from_point"))
        self.assertVec(inf.point, (3, -1, 1), 1e-3)
        self.assertVec(inf.ref_point, (3, 1, 1))
        a = Vector((6, -1, 1))                                       # red axis from the anchor ∩ green from the ref
        both = self.query(self.xy((3, -1, 1), 3, 0), anchor=a)
        self.assertEqual(both.linear, "FROM_POINT")
        self.assertVec(both.point, (3, -1, 1), 1e-6)

    def test_ref_points_capped(self):
        for p in ((0, 0, 0), (1, 0, 0), (2, 0, 0), (2, 0, 0)):
            inference.add_ref_point(p)
        self.assertEqual([tuple(v) for v in STATE.ref_points], [(1, 0, 0), (2, 0, 0)])

    def test_tick_resets_on_non_point(self):
        ep = self.query(self.xy((3, 1, 1)))
        self.engine.acquire_tick(ep, 0.0)
        self.engine.acquire_tick(Inference.none(), 0.2)
        self.assertFalse(self.engine.acquire_tick(ep, 0.35))


class TestHoverPlane(_Base):
    def test_planes(self):
        co, n, ax = inference.hover_plane(self.q(self.xy((2.2, 2.4, 1))))
        self.assertEqual(ax, "Z")
        self.assertAlmostEqual(co.z, 1.0, places=6)
        _co, n, ax = inference.hover_plane(self.q(self.xy((2.2, 1, 0.4))))     # front face (normal −Y)
        self.assertEqual(ax, "Y")
        self.assertVec(n, (0, -1, 0))
        _co, n, ax = inference.hover_plane(self.q(self.xy((3, 2.3, 0.4))))     # side face (normal +X)
        self.assertEqual(ax, "X")
        co, n, ax = inference.hover_plane(self.q(self.xy((-1, 4, 0))))         # empty → ground
        self.assertEqual(ax, "Z")
        self.assertAlmostEqual(co.z, 0.0, places=6)
        co, n, ax = inference.hover_plane(self.q(self.xy((2.2, 2.4, 1)), locks=Locks(axis="AXIS_X")))
        self.assertEqual(ax, "X")
        self.assertVec(n, (1, 0, 0))


class TestContext(unittest.TestCase):
    def test_context_label(self):
        class Doc:
            def __init__(self, kind):
                self.kind = kind

        class Obj:
            def __init__(self, kind):
                self.su_doc = Doc(kind)
        self.assertEqual(inference.context_label(None), "")
        self.assertEqual(inference.context_label(Obj('MODEL')), "")
        self.assertEqual(inference.context_label(Obj('GROUP')), "GROUP")
        self.assertEqual(inference.context_label(Obj('COMPONENT')), "COMPONENT")
        self.assertEqual(inference.context_label(Obj('')), "GROUP")          # B: '' = group
        self.assertEqual(inference.context_label(object()), "")

    def test_axis_of(self):
        self.assertEqual(inference.axis_of(Vector((0, 0, -2))), "AXIS_Z")
        self.assertEqual(inference.axis_of(Vector((1, 1, 0))), "")
        self.assertEqual(inference.axis_of(None), "")

    def test_strings(self):
        from su import i18n
        self.assertEqual(i18n.t("inf.endpoint"), "Ponto de extremidade")
        self.assertEqual(i18n.t("inf.axis_z"), "No eixo azul")
        self.assertEqual(i18n.t("vcb.length"), "Comprimento")


class TestCenter(_Base):
    """Centro: hovering a curve (B: su_curve + su_doc.curves meta) makes its centre inferable."""

    def _circle(self, cid=7, n=12, c=(6.0, 6.0, 0.0), r=1.0):
        import json
        verts = [(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n), c[2])
                 for i in range(n)]
        obj = F.mesh_object("circle", verts, edges=[(i, (i + 1) % n) for i in range(n)])
        a = obj.data.attributes.new("su_curve", 'INT', 'EDGE')
        for e in a.data:
            e.value = cid
        obj.su_doc.curves = json.dumps({str(cid): {"kind": "CIRCLE", "center": list(c), "radius": r}})
        obj.location = (0.0, 0.0, 0.5)
        bpy.context.view_layer.update()
        return obj

    def test_center_after_hover(self):
        if not hasattr(bpy.types.Object, "su_doc"):
            self.skipTest("B's su_doc not registered")
        obj = self._circle()
        center = Vector((6, 6, 0.5))
        self.assertNotEqual(self.query(self.xy(center, 2, 1)).kind, "CENTER")
        rim = obj.matrix_world @ obj.data.vertices[0].co.lerp(obj.data.vertices[1].co, 0.4)
        hov = self.query(self.xy(rim))
        self.assertIn(hov.kind, ("ON_EDGE", "ENDPOINT", "MIDPOINT"))
        inf = self.query(self.xy(center, 2, 1))
        self.assertEqual((inf.kind, inf.tooltip_key), ("CENTER", "inf.center"))
        self.assertVec(inf.point, center, 1e-5)
        self.assertEqual(inf.elem, ("CURVE", 7))


class TestShapes(_Base):
    """P1: Quadrado / Seção áurea (Retângulo) and Semicírculo (Arco de dois pontos)."""

    def test_square_and_golden(self):
        c = Vector((-2, 4, 0))
        u, v = Vector((1, 0, 0)), Vector((0, 1, 0))
        sq = inference.rect_shape(self.q(self.xy((-0.5, 5.5, 0), 2, -1)), c, (-0.5, 5.5, 0), u, v)
        self.assertIsNotNone(sq)
        self.assertEqual(sq.tooltip_key, "inf.square")
        d = sq.point - c
        self.assertAlmostEqual(abs(d.x), abs(d.y), places=6)
        g = c + Vector((inference.GOLDEN, 1.0, 0.0)) * 0.9
        gold = inference.rect_shape(self.q(self.xy(g)), c, g, u, v)
        self.assertEqual(gold.tooltip_key, "inf.golden")
        d = gold.point - c
        self.assertAlmostEqual(d.x / d.y, inference.GOLDEN, places=5)
        far = c + Vector((2.0, 0.4, 0.0))
        self.assertIsNone(inference.rect_shape(self.q(self.xy(far)), c, far, u, v))
        from su import i18n
        self.assertEqual(i18n.t("inf.golden"), "Seção áurea")

    def test_half_circle(self):
        a, b, n = Vector((-2, 4, 0)), Vector((0, 4, 0)), Vector((0, 0, 1))
        near = Vector((-1, 5.02, 0))
        bulge, key = inference.arc_semicircle(self.q(self.xy(near)), a, b, near, n)
        self.assertEqual(key, "inf.half_circle")
        self.assertAlmostEqual(abs(bulge), 1.0, places=9)
        low = Vector((-1, 4.4, 0))
        bulge, key = inference.arc_semicircle(self.q(self.xy(low)), a, b, low, n)
        self.assertEqual(key, "")
        self.assertAlmostEqual(abs(bulge), 0.4, places=6)


class TestLowCameraLine(_Base):
    """Regression (A): Linha started on the red axis at (4,0,0) — not on a vertex — with a near-horizontal
    camera (default view pitch ≈ 6.6°) got its next point off the ground (z ≈ 0.15): the free point used
    the vertical plane facing the camera. Free points after a click must stay on the anchor's horizontal
    plane; the start point and the red-axis point must be exact."""

    def setUp(self):
        super().setUp()
        self.region = F.FakeRegion(1000, 800)
        target = Vector((3.0, 1.0, 0.8))
        pitch, yaw, dist = math.radians(6.6), math.radians(33.0), 11.5
        back = Vector((math.sin(yaw), -math.cos(yaw), 0.0)) * math.cos(pitch) + Vector((0, 0, math.sin(pitch)))
        self.rv3d = F.FakeRV3D(target + back * dist, target, self.region)

    def test_start_and_free_point_on_ground(self):
        start = self.query(self.xy((4, 0, 0), 0.4, 0.3))
        self.assertEqual(start.kind, "FREE")
        self.assertAlmostEqual(start.point.z, 0.0, places=9)
        a = Vector((4, 0, 0))
        for target in ((6.0, 1.7, 0.0), (5.2, -2.5, 0.0), (6.5, 3.0, 0.0)):
            inf = self.query(self.xy(target), anchor=a)
            self.assertEqual(inf.linear, "", target)
            self.assertAlmostEqual(inf.point.z, 0.0, places=9, msg=target)
            self.assertVec(inf.point, target, 1e-3)

    def test_red_axis_exact(self):
        a = Vector((4, 0, 0))
        inf = self.query(self.xy((7, 0, 0), 1, 2), anchor=a)
        self.assertEqual(inf.linear, "AXIS_X")
        self.assertAlmostEqual(inf.point.y, 0.0, places=9)
        self.assertAlmostEqual(inf.point.z, 0.0, places=9)
        typed = a + inf.direction * 3.0            # what Linha does with "3"
        self.assertVec(typed, (7, 0, 0), 1e-9)

    def test_above_horizon_uses_vertical_plane(self):
        a = Vector((4, 0, 0))
        inf = self.query((500, 790), anchor=a)       # near the top edge: above the horizon
        self.assertEqual(inf.kind, "FREE")
        self.assertGreater(inf.point.z, 0.0)
        self.assertTrue(math.isfinite(inf.point.length))


class TestGroupContext(_Base):
    def test_point_in_group_is_labelled(self):
        try:
            from su.core import document
        except ImportError:
            self.skipTest("B's document not available")
        g = document.create_group(F.PREFIX + "grp")
        bm = g.bm
        vs = [bm.verts.new(c) for c in ((5, -2, 0), (6, -2, 0), (6, -1, 0), (5, -1, 0))]
        bm.faces.new(vs)
        g.write(undo_key=None)
        bpy.context.view_layer.update()
        inf = self.query(self.xy((6, -2, 0), 2, 1))
        self.assertEqual(inf.kind, "ENDPOINT")
        self.assertEqual(inf.in_context, "GROUP")
