# SPDX-License-Identifier: GPL-2.0-or-later
"""E: Círculo / Polígono through testing.dispatch — AC-CIR-1..4, AC-EMP-7, curve entity + metadata,
retype radius / `Ns`, soft cylinder sides vs hard polygon prism."""

import math
import unittest

import bpy
from mathutils import Vector

from su import testing
from su.core import document, entities, geom
from su.tools import base

from test_e_pushpull import PPCase, face_inf

CIRCLE = "su.circle"
POLY = "su.polygon"


class ShapeCase(PPCase):
    TOOL = CIRCLE

    def shape(self, tool, center, toward, text, sides=None, start=None):
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), tool, testing.pt(*center))
        if sides:
            testing.type_text(sides)
        testing.click(start if start is not None else testing.pt(*center))
        testing.move(toward)
        return testing.type_text(text)


class TestCircle(ShapeCase):
    def test_status(self):
        d = testing.state_dump()
        self.assertEqual(d["hint_key"], "tool.su.circle.hint_start")
        self.assertEqual(d["vcb_label_key"], "vcb.sides")
        self.assertEqual(d["vcb_value"], "24")

    def test_ac_cir_1_twelve_sides(self):
        self.shape(CIRCLE, (0, 0, 0), (1, 0, 0), "1", sides="12")
        st = self.stats()
        self.assertEqual(self.counts(), (12, 12, 1))
        self.assertAlmostEqual(st["area"], 3.0, places=4)
        self.assertEqual(st["normals"], [[0.0, 0.0, -1.0]])
        bm = document.root().bm
        lay = geom.layers(bm)
        cids = {e[lay.curve] for e in bm.edges}
        self.assertEqual(len(cids), 1)
        cid = cids.pop()
        self.assertNotEqual(cid, 0)
        meta = entities.get_curve_meta(document.root(), cid)
        self.assertEqual(meta["kind"], "circle")
        self.assertEqual(meta["sides"], 12)
        self.assertAlmostEqual(meta["radius"], 1.0, places=5)
        self.assertEqual([round(c, 6) for c in meta["center"]], [0.0, 0.0, 0.0])
        self.assertEqual(self.steps(), 1)

    def test_default_24_and_click_radius(self):
        testing.click((2, 2, 0))
        testing.move((3, 2, 0))
        testing.click((4, 2, 0))
        self.assertEqual(self.counts(), (24, 24, 1))
        self.assertAlmostEqual(self.stats()["area"], 0.5 * 24 * 4 * math.sin(2 * math.pi / 24), places=4)

    def test_sides_while_drawing_and_retype(self):
        testing.click((0, 0, 0))
        testing.move((1, 0, 0))
        testing.type_text("8s")
        self.assertTrue(base.DISPATCH.running)
        testing.type_text("2")
        self.assertEqual(self.counts(), (8, 8, 1))
        testing.type_text("1")                         # retype radius → Ajustar
        self.assertEqual(self.stats()["bbox"][1][0], 1.0)
        testing.type_text("6s")                        # retype sides
        self.assertEqual(self.counts(), (6, 6, 1))
        self.assertEqual(self.steps(), 3)

    def test_ac_cir_3_on_vertical_face(self):
        self.TOOL = PPCase.TOOL
        self.box(4, 4, "3")
        inf = face_inf((2, 0, 1.5))
        self.shape(CIRCLE, (2, 0, 1.5), (2.5, 0, 1.5), "0,5", start=inf)
        bm = document.root().bm
        lay = geom.layers(bm)
        circ = [e for e in bm.edges if e[lay.curve]]
        self.assertEqual(len(circ), 24)
        self.assertTrue(all(abs(v.co.y) < 1e-6 for e in circ for v in e.verts))

    def test_ac_cir_4_arrows_lock_the_normal(self):
        testing.dispatch(testing.ev('RIGHT_ARROW', 'PRESS'))          # → normal red → plane YZ
        self.shape(CIRCLE, (0, 0, 0), (0, 0, 1), "1")
        bb = self.stats()["bbox"]
        self.assertAlmostEqual(bb[0][0], 0.0, places=6)
        self.assertAlmostEqual(bb[1][0], 0.0, places=6)
        testing.reset_model()
        testing.dispatch(testing.ev('LEFT_ARROW', 'PRESS'))           # ← normal green → plane XZ
        self.shape(CIRCLE, (0, 0, 0), (1, 0, 0), "1")
        bb = self.stats()["bbox"]
        self.assertAlmostEqual(bb[1][1] - bb[0][1], 0.0, places=6)
        testing.reset_model()
        testing.dispatch(testing.ev('UP_ARROW', 'PRESS'))             # ↑ normal blue → horizontal
        self.shape(CIRCLE, (0, 0, 0), (1, 0, 0), "1")
        bb = self.stats()["bbox"]
        self.assertAlmostEqual(bb[1][2] - bb[0][2], 0.0, places=6)

    def test_ac_cir_2_cylinder_is_smooth_and_ac_emp_7(self):
        self.shape(CIRCLE, (0, 0, 0), (1, 0, 0), "1", sides="12")
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), "su.pushpull", testing.pt(0, 0, 0))
        self.pull((0.1, 0.1, 0), (0.1, 0.1, 0.5), "2", side=-1)
        st = self.stats()
        self.assertEqual(st["soft"], 12)
        self.assertEqual(st["surfaces"], 3)                # top, bottom, one smooth lateral surface
        bm = document.root().bm
        lay = geom.layers(bm)
        top = {e[lay.curve] for e in bm.edges if e[lay.curve] and all(abs(v.co.z - 2) < 1e-6 for v in e.verts)}
        bot = {e[lay.curve] for e in bm.edges if e[lay.curve] and all(abs(v.co.z) < 1e-6 for v in e.verts)}
        self.assertEqual(len(top), 1)
        self.assertEqual(len(bot), 1)
        self.assertNotEqual(top, bot)                      # the top circle is its own curve
        meta = entities.get_curve_meta(document.root(), top.pop())
        self.assertAlmostEqual(meta["center"][2], 2.0, places=5)
        sides = [f for f in bm.faces if abs(f.normal.z) < 1e-3]
        self.assertTrue(sides and all(f.smooth for f in sides))
        # AC-EMP-7: Empurrar/puxar on the lateral surface does nothing
        before = self.counts()
        p = sides[0].calc_center_median()
        inf = face_inf(tuple(p))
        r = testing.click(inf)
        self.assertIs(r, base.Result.IDLE)
        self.assertFalse(base.DISPATCH.running)
        self.assertEqual(base.controller("su.pushpull").hover_polys, [])
        self.assertEqual(self.counts(), before)


class TestPolygon(ShapeCase):
    TOOL = POLY

    def test_default_six_and_hard_prism(self):
        self.assertEqual(testing.state_dump()["vcb_value"], "6")
        self.shape(POLY, (0, 0, 0), (1, 0, 0), "1")
        self.assertEqual(self.counts(), (6, 6, 1))
        self.assertAlmostEqual(self.stats()["area"], 1.5 * math.sqrt(3), places=4)
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), "su.pushpull", testing.pt(0, 0, 0))
        self.pull((0.1, 0.1, 0), (0.1, 0.1, 0.5), "1", side=-1)
        st = self.stats()
        self.assertEqual(st["soft"], 0)
        self.assertEqual(self.counts(), (12, 18, 8))


if __name__ == "__main__":
    unittest.main()
