# SPDX-License-Identifier: GPL-2.0-or-later
"""G: navigation math (core/camera.py) with a synthetic camera — AC-NAV-1/2/6/8 at the math level,
turntable (blue axis vertical), pan, recentre, standard views, lens/FOV, trackpad mapping, typed FOV."""

import math
import unittest

from mathutils import Vector

import test_c_fakes as F
from su.core import camera
from su.core.camera import View
from su.ops import view_ops
from su.tools import nav


def view_from(eye=(9.0, -7.0, 6.0), target=(2.0, 2.0, 0.5), size=(1000, 800), fov=35.0):
    region, rv3d = F.camera(eye, target, size)
    v = View(rv3d.view_location, rv3d.view_rotation, rv3d.view_distance, width=size[0], height=size[1],
             fov_v_deg=fov)
    return region, rv3d, v


class TestView(unittest.TestCase):
    def test_projection_matches_blender(self):
        region, rv3d, v = view_from()
        for p in ((0, 0, 0), (2, 2, 0.5), (3, -1, 2), (-4, 5, 1)):
            a = F.project(region, rv3d, p)
            b = v.project(p)
            self.assertLess((a - b).length, 1e-3, (p, a, b))

    def test_ray_through_projection(self):
        _r, _rv, v = view_from()
        p = Vector((1.0, 3.0, 0.7))
        s = v.project(p)
        o, d = v.ray(s)
        self.assertLess(((p - o).normalized() - d).length, 1e-6)

    def test_from_rv3d_reads_fov(self):
        region, rv3d = F.camera()
        v = View.from_rv3d(region, rv3d)
        self.assertAlmostEqual(v.fov_v_deg, 35.0, places=4)
        self.assertLess((v.eye() - Vector((9.0, -7.0, 6.0))).length, 1e-5)


class TestOrbit(unittest.TestCase):
    def test_pivot_stays_under_cursor(self):            # AC-NAV-2 (math)
        _r, _rv, v = view_from()
        pivot = Vector((3.0, 1.0, 1.0))
        s0 = v.project(pivot)
        for dx, dy in ((40, 0), (0, 25), (-60, -30), (15, 80)):
            camera.orbit_about(v, pivot, dx, dy)
            s1 = v.project(pivot)
            self.assertLess((s1 - s0).length, 1e-3, (dx, dy, s0, s1))

    def test_blue_axis_vertical(self):
        _r, _rv, v = view_from()
        for dx, dy in ((100, 30), (-250, -60), (30, 200)):
            camera.orbit_about(v, Vector((0, 0, 0)), dx, dy)
            self.assertAlmostEqual(v.right.z, 0.0, places=6)     # no roll
            self.assertGreaterEqual(v.up.z, -1e-6)              # never upside down

    def test_clamped_at_top(self):
        _r, _rv, v = view_from()
        camera.orbit_about(v, v.loc, 0, -10000)                 # mouse far down → camera to the top
        self.assertAlmostEqual(v.fwd.z, -1.0, places=5)
        camera.orbit_about(v, v.loc, 0, 30000)
        self.assertAlmostEqual(v.fwd.z, 1.0, places=5)

    def test_direction_grab_metaphor(self):
        _r, _rv, v = view_from()
        eye0 = v.eye()
        camera.orbit_about(v, v.loc, 0, -20)                    # mouse down → camera goes up
        self.assertGreater(v.eye().z, eye0.z)
        _r, _rv, v = view_from(eye=(0, -10, 0), target=(0, 0, 0))
        camera.orbit_about(v, v.loc, 30, 0)                     # mouse right → camera moves left (−X)
        self.assertLess(v.eye().x, 0.0)


class TestPanZoom(unittest.TestCase):
    def test_pan_point_follows_cursor(self):
        _r, _rv, v = view_from()
        p = Vector((2.5, 1.5, 0.0))
        d = v.depth(p)
        for xy in ((300, 200), (720, 640), (510, 395)):
            camera.pan_to(v, p, xy, depth=d)
            self.assertLess((v.project(p) - Vector(xy)).length, 1e-3)
        self.assertAlmostEqual(v.right.z, 0.0, places=6)

    def test_zoom_keeps_point_under_cursor(self):        # AC-NAV-1 (math): 5 wheel notches
        _r, _rv, v = view_from()
        p = Vector((3.0, 1.0, 1.0))
        s0 = v.project(p)
        d0 = (v.eye() - p).length
        for _ in range(5):
            camera.zoom_at(v, p, camera.wheel_factor(1))
        self.assertLess((v.project(p) - s0).length, 1e-3)
        self.assertAlmostEqual((v.eye() - p).length, d0 * camera.WHEEL_FACTOR ** 5, places=5)
        for _ in range(5):
            camera.zoom_at(v, p, camera.wheel_factor(-1))
        self.assertAlmostEqual((v.eye() - p).length, d0, places=5)

    def test_zoom_ortho(self):
        _r, _rv, v = view_from()
        v.persp = False
        p = Vector((3.0, 1.0, 1.0))
        s0 = v.project(p)
        camera.zoom_at(v, p, 0.5)
        self.assertLess((v.project(p) - s0).length, 1e-3)

    def test_recenter(self):                              # AC-NAV-3 (math)
        _r, _rv, v = view_from()
        p = Vector((3.0, 1.0, 1.0))
        camera.recenter_at(v, p)
        self.assertLess((v.project(p) - Vector(v.center_xy())).length, 1e-3)
        self.assertLess((v.loc - p).length, 1e-9)

    def test_pan_pixels(self):
        _r, _rv, v = view_from()
        s0 = v.project(v.loc)
        loc0 = v.loc.copy()
        camera.pan_pixels(v, 30, -10)
        self.assertLess((v.project(loc0) - (s0 + Vector((30, -10)))).length, 1e-3)


class TestExtentsViews(unittest.TestCase):
    def box(self, mn=(0, 0, 0), mx=(8, 6, 3)):
        return [Vector((x, y, z)) for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])]

    def test_zoom_extents_90_percent(self):               # AC-NAV-6 (math)
        for persp in (True, False):
            _r, _rv, v = view_from()
            v.persp = persp
            pts = self.box()
            camera.fit_points(v, pts)
            e = camera._extent(v, pts)
            hx, hy = (e[1] - e[0]) / 2, (e[3] - e[2]) / 2
            self.assertAlmostEqual(max(hx, hy), 0.9, places=3)
            self.assertLess(abs(e[0] + e[1]), 1e-2)              # centred
            self.assertLess(abs(e[2] + e[3]), 1e-2)

    def test_standard_views(self):                       # AC-NAV-8
        expect = {"TOP": (0, 0, -1), "BOTTOM": (0, 0, 1), "FRONT": (0, 1, 0), "BACK": (0, -1, 0),
                  "LEFT": (1, 0, 0), "RIGHT": (-1, 0, 0)}
        for name, fwd in expect.items():
            _r, _rv, v = view_from()
            camera.standard_view_of(v, name)
            self.assertLess((v.fwd - Vector(fwd)).length, 1e-6, name)
        _r, _rv, v = view_from()
        camera.standard_view_of(v, "ISO")
        self.assertAlmostEqual(v.right.z, 0.0, places=6)
        x = v.project(v.loc + Vector((1, 0, 0))) - v.project(v.loc)
        y = v.project(v.loc + Vector((0, 1, 0))) - v.project(v.loc)
        self.assertTrue(x.x > 0 and x.y < 0, x)          # red to the lower right
        self.assertTrue(y.x > 0 and y.y > 0, y)          # green recedes to the upper right

    def test_lens_for_fov(self):
        tan_now = math.tan(math.radians(50.0) / 2)
        lens = camera.lens_for_fov(50.0, tan_now, 35.0)
        self.assertAlmostEqual(math.tan(math.radians(35.0) / 2), tan_now * 50.0 / lens, places=9)


class TestInputMapping(unittest.TestCase):
    def test_trackpad_sketchup_mode(self):
        k, f = view_ops.trackpad_action('TRACKPADPAN', 0, 20, False, mode='sketchup', invert=False)
        self.assertEqual(k, 'ZOOM')
        self.assertLess(f, 1.0)                               # fingers up = zoom in
        k, f2 = view_ops.trackpad_action('TRACKPADPAN', 0, 20, False, mode='sketchup', invert=True)
        self.assertGreater(f2, 1.0)                           # "inverter zoom do trackpad"
        self.assertEqual(view_ops.trackpad_action('TRACKPADPAN', 5, 6, True, mode='sketchup')[0], 'PAN')
        k, f3 = view_ops.trackpad_action('TRACKPADZOOM', 10, 0, False, mode='sketchup')
        self.assertLess(f3, 1.0)                              # pinch open = zoom in

    def test_trackpad_blender_mode(self):
        self.assertEqual(view_ops.trackpad_action('TRACKPADPAN', 5, 6, False, mode='blender'), ('ORBIT', 5, 6))
        self.assertEqual(view_ops.trackpad_action('TRACKPADPAN', 5, 6, True, mode='blender'), ('PAN', 5, 6))

    def test_typed_fov(self):
        self.assertAlmostEqual(nav.fov_from_text("35", 35.0), 35.0)
        self.assertAlmostEqual(nav.fov_from_text("50mm", 0.05), math.degrees(2 * math.atan(12 / 50)))
        self.assertIsNone(nav.fov_from_text("500", 500.0))

    def test_keymap_lists(self):
        ids = {it[0] for it in view_ops.KEYMAP + view_ops.KEYMAP_VIEW3D}
        import bpy
        for idname in ids:
            mod, name = idname.split(".")
            op = getattr(getattr(bpy.ops, mod), name)
            self.assertIsNotNone(op.get_rna_type(), idname)          # registered (hasattr is always True)


if __name__ == "__main__":
    unittest.main()
