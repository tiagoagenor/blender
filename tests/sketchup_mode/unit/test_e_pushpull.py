# SPDX-License-Identifier: GPL-2.0-or-later
"""E: Empurrar/puxar through testing.dispatch — AC-EMP-1, 2, 4, 5, 6, AC-RET-3/4 (rebaixo, porta
passante), ROTEIRO_CASA Parte 1 passos 1–2 e 6–9, Parte 2 B1/B3–B6 (anel feito à mão: a Equidistância
ainda não existe), Esc, undo."""

import unittest

import bpy
from mathutils import Vector

from su import testing
from su.core import document, geom, geom_extrude
from su.tools import base

from test_e_rectangle import ToolCase

PP = "su.pushpull"
RECT = "su.rectangle"


def face_inf(p, side=1, kind="ON_FACE"):
    """ON_FACE inference on the root face containing world point p (root = identity matrix)."""
    doc = document.root()
    bm = doc.bm
    bm.faces.index_update()
    fs = geom_extrude.faces_at(bm, Vector(p))
    assert fs, "no face at {}".format(p)
    f = fs[0]
    f.normal_update()
    return testing.pt(*p, kind=kind, elem=("FACE", f.index), doc_key=doc.key, normal=f.normal.copy(), side=side,
                      plane=(Vector(p), f.normal.copy()))


class PPCase(ToolCase):
    TOOL = PP

    def rect(self, p1, toward, text, start=None):
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), RECT, testing.pt(*p1))
        testing.click(start if start is not None else testing.pt(*p1))
        testing.move(toward)
        testing.type_text(text)
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), PP, testing.pt(*p1))

    def pull(self, p, toward, text, side=1, **kw):
        """P: click the face at p, move to `toward` (a point on the normal line), type `text`."""
        inf = face_inf(p, side)
        testing.click(inf, **kw)
        testing.move(toward)
        return testing.type_text(text)

    def box(self, w=8, d=6, h="3"):
        self.rect((0, 0, 0), (1, 1, 0), "{};{}".format(w, d))
        self.pull((w / 2, d / 2, 0), (w / 2, d / 2, 0.5), h, side=-1)

    def assert_closed_out(self):
        """Every face of a closed solid points away from the solid's centre (boxes)."""
        bm = document.root().bm
        c = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
        for f in bm.faces:
            f.normal_update()
            self.assertGreater(f.normal.dot(f.calc_center_median() - c), 0.0, f.calc_center_median())

    def logical_areas(self):
        from su.core import entities
        bm = document.root().bm
        bm.faces.ensure_lookup_table()
        out, seen = [], set()
        for f in bm.faces:
            if f.index in seen:
                continue
            lf = entities.logical_face(bm, f)
            seen.update(g.index for g in lf.faces)
            out.append(round(sum(g.calc_area() for g in lf.faces), 4))
        return sorted(out)


class TestPushPull(PPCase):
    def test_status(self):
        d = testing.state_dump()
        self.assertEqual(d["tool"], PP)
        self.assertEqual(d["hint_key"], "tool.su.pushpull.hint_start")
        self.assertEqual(d["vcb_label_key"], "vcb.distance")

    def test_ac_emp_1_box(self):
        self.rect((0, 0, 0), (1, 1, 0), "2;3")
        s0 = bpy.context.scene.su_undo_serial
        inf = face_inf((1, 1, 0), side=-1)
        testing.click(inf)
        self.assertTrue(base.DISPATCH.running)
        self.assertEqual(testing.state_dump()["hint_key"], "tool.su.pushpull.hint_next")
        testing.move((1, 1, 0.4))
        self.assertEqual(self.counts(), (8, 12, 6))              # live preview
        testing.type_text("1")
        self.assertFalse(base.DISPATCH.running)
        st = self.stats()
        self.assertEqual(self.counts(), (8, 12, 6))
        self.assertEqual(st["bbox"], [[0.0, 0.0, 0.0], [2.0, 3.0, 1.0]])
        self.assertAlmostEqual(st["area"], 2 * (6 + 2 + 3), places=4)
        self.assert_closed_out()
        self.assertEqual(bpy.context.scene.su_undo_serial - s0, 1)

    def test_roteiro_2_volume(self):
        self.box()
        st = self.stats()
        self.assertEqual(self.counts(), (8, 12, 6))
        self.assertEqual(st["bbox"], [[0.0, 0.0, 0.0], [8.0, 6.0, 3.0]])
        self.assert_closed_out()
        self.assertEqual(self.steps(), 2)

    def test_ac_emp_2_pull_top_again_and_push_down(self):
        self.box()
        self.pull((4, 3, 3), (4, 3, 3.5), "1")
        self.assertEqual(self.counts(), (8, 12, 6))
        self.assertEqual(self.stats()["bbox"][1], [8.0, 6.0, 4.0])
        self.assert_closed_out()
        self.pull((4, 3, 4), (4, 3, 3.5), "2")                    # push the top down 2
        self.assertEqual(self.counts(), (8, 12, 6))
        self.assertEqual(self.stats()["bbox"][1], [8.0, 6.0, 2.0])
        self.assert_closed_out()

    def test_click_move_click_and_drag(self):
        self.rect((0, 0, 0), (1, 1, 0), "2;2")
        testing.click(face_inf((1, 1, 0), side=-1))
        testing.move((1, 1, 0.7))
        testing.click((1, 1, 0.7))
        self.assertAlmostEqual(self.stats()["bbox"][1][2], 0.7, places=5)
        testing.reset_model()
        self.rect((0, 0, 0), (1, 1, 0), "2;2")
        testing.dispatch(testing.ev('LEFTMOUSE', 'PRESS', 0, 0), None, face_inf((1, 1, 0), side=-1))
        testing.dispatch(testing.ev('LEFTMOUSE', 'RELEASE', 0, 200), None, testing.pt(1, 1, 0.25))
        self.assertAlmostEqual(self.stats()["bbox"][1][2], 0.25, places=5)
        self.assertFalse(base.DISPATCH.running)

    def test_ac_emp_4_retype(self):
        self.box()
        testing.type_text("1,5")
        self.assertEqual(self.stats()["bbox"][1], [8.0, 6.0, 1.5])
        self.assertEqual(self.counts(), (8, 12, 6))
        self.assertEqual(self.steps(), 3)

    def test_ac_emp_5_double_click_repeats(self):
        self.rect((0, 0, 0), (1, 1, 0), "2;2")
        self.rect((5, 0, 0), (6, 1, 0), "2;2")
        self.pull((1, 1, 0), (1, 1, 0.5), "1,25", side=-1)
        testing.click(face_inf((6, 1, 0), side=-1), x=300, y=300)
        testing.click(face_inf((6, 1, 0), side=-1), x=300, y=300)
        self.assertFalse(base.DISPATCH.running)
        bb = self.stats()["bbox"]
        self.assertAlmostEqual(bb[1][2], 1.25, places=5)
        self.assertEqual(self.counts(), (16, 24, 12))

    def test_ac_emp_6_option_keeps_face(self):
        self.box()
        inf = face_inf((4, 3, 3))
        testing.click(inf, copy=True)
        testing.move((4, 3, 3.5))
        testing.type_text("1")
        st = self.stats()
        self.assertEqual(st["bbox"][1], [8.0, 6.0, 4.0])
        self.assertEqual(self.counts()[2], 11)                 # original top kept + new top + 4 sides
        self.assertIn(48.0, self.logical_areas())

    def test_esc_restores(self):
        self.box()
        before = self.counts()
        testing.click(face_inf((4, 3, 3)))
        testing.move((4, 3, 5))
        testing.dispatch(testing.ev('ESC', 'PRESS'))
        self.assertFalse(base.DISPATCH.running)
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.stats()["bbox"][1], [8.0, 6.0, 3.0])
        self.assertEqual(self.steps(), 2)

    def test_click_on_nothing(self):
        r = testing.click((1, 1, 0))
        self.assertIs(r, base.Result.IDLE)
        self.assertFalse(base.DISPATCH.running)

    def test_ac_ret_3_recess(self):
        self.rect((0, 0, 0), (1, 1, 0), "3;3")
        self.pull((1.5, 1.5, 0), (1.5, 1.5, 0.5), "1", side=-1)
        self.rect((1, 1, 1), (1.5, 1.5, 1), "1;1", start=face_inf((1, 1, 1)))
        self.pull((1.5, 1.5, 1), (1.5, 1.5, 0.8), "0,5")
        self.assertEqual(self.counts(), (16, 24, 11))
        bm = document.root().bm
        self.assertTrue(any(abs(f.calc_center_median().z - 0.5) < 1e-6 and f.normal.z > 0.99 for f in bm.faces))


class TestHouse(PPCase):
    """ROTEIRO_CASA Parte 1: piso, volume, porta + rebaixo, janela + rebaixo — without the ridge of
    passos 3–4 (Linha/Mover), so every count is the ROTEIRO's minus V2 A3 F1."""

    def door(self):
        mid = testing.pt(4, 0, 0, kind="MIDPOINT")
        self.rect((4, 0, 0), face_inf((4.5, 0, 1)), "1;2,1", start=mid)

    def test_steps_1_2_6_7_door(self):
        self.box()
        self.door()
        self.assertEqual(self.counts(), (12, 17, 7))
        self.assertIn(2.1, self.logical_areas())
        self.pull((4.5, 0, 1), (4.5, 0.1, 1), "0,15")
        self.assertEqual(self.counts(), (16, 24, 10))
        self.assertEqual(self.stats()["bbox"][0][1], 0.0)          # the recess goes INTO the wall
        self.assertIn(47.85, self.logical_areas())                # floor with a notch
        bm = document.root().bm
        lay = geom.layers(bm)
        sill = [e for e in bm.edges if not e[lay.bridge] and all(abs(v.co.y) < 1e-6 and abs(v.co.z) < 1e-6
                                                                  and 4.0 - 1e-6 < v.co.x < 5.0 + 1e-6 for v in e.verts)]
        self.assertEqual(sill, [])                                 # no loose sill edge at y = 0
        door = [f for f in bm.faces if abs(f.calc_center_median().y - 0.15) < 1e-6]
        self.assertEqual(len(door), 1)
        self.assertLess(door[0].normal.y, -0.99)                  # door front still faces outside
        self.assertEqual(self.steps(), 4)

    def test_typed_value_follows_mouse_side_when_snapped(self):
        """The inference kept the distance at 0 (cursor snapped to a point of the door): the typed value
        follows the side of the cursor on screen (+Y = into the wall here), not the viewer side."""
        from mathutils import Vector as V2
        self.box()
        self.door()
        testing.click(face_inf((4.5, 0, 1)))
        ctrl = base.controller(PP)
        ctrl._s0, ctrl._sdir = (100.0, 100.0), V2((0.0, 1.0))      # +n (−Y) goes up on screen
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING', 100, 60), None, testing.pt(4.5, 0, 1))
        self.assertEqual(ctrl.screen_side, -1)                     # mouse went down = −n = +Y (inside)
        testing.type_text("0,15")
        bb = self.stats()["bbox"]
        self.assertEqual(bb[0][1], 0.0)                            # nothing outside the wall
        bm = document.root().bm
        self.assertEqual(len([f for f in bm.faces if abs(f.calc_center_median().y - 0.15) < 1e-6]), 1)

    def test_steps_8_9_window(self):
        self.box()
        self.door()
        self.pull((4.5, 0, 1), (4.5, 0.1, 1), "0,15")
        start = face_inf((1, 0, 0.9))
        start.kind = "INTERSECTION"
        self.rect((1, 0, 0.9), face_inf((1.5, 0, 1.5)), "1,2;1,2", start=start)
        self.assertEqual(self.counts(), (20, 28, 11))
        self.pull((1.6, 0, 1.5), (1.6, 0.05, 1.5), "0,1")
        self.assertEqual(self.counts(), (24, 36, 15))
        bm = document.root().bm
        glass = [f for f in bm.faces if abs(f.calc_center_median().y - 0.1) < 1e-6]
        self.assertEqual(len(glass), 1)
        self.assertLess(glass[0].normal.y, -0.99)


class TestHollowWalls(PPCase):
    """ROTEIRO_CASA Parte 2 (anel feito à mão até a Equidistância existir)."""

    def ring(self):
        self.rect((0, 0, 0), (1, 1, 0), "8;6")
        self.rect((0.15, 0.15, 0), (1, 1, 0), "7,7;5,7", start=face_inf((0.15, 0.15, 0), side=-1))
        doc = document.root()
        geom.erase_faces(doc.bm, geom_extrude.faces_at(doc.bm, Vector((4, 3, 0))))
        doc.write(undo_key="test")
        self.assertEqual(self.counts(), (8, 8, 1))

    def test_b4_walls(self):
        self.ring()
        self.pull((0.07, 3, 0), (0.07, 3, 1), "2,8", side=-1)
        self.assertEqual(self.counts(), (16, 24, 10))
        self.assertEqual(self.stats()["bbox"][1], [8.0, 6.0, 2.8])

    def test_ac_ret_4_b6_door_through(self):
        self.ring()
        self.pull((0.07, 3, 0), (0.07, 3, 1), "2,8", side=-1)
        mid = testing.pt(4, 0, 0, kind="MIDPOINT")
        self.rect((4, 0, 0), face_inf((4.5, 0, 1)), "1;2,1", start=mid)
        self.pull((4.5, 0, 1), (4.5, 0.05, 1), "0,15")
        bm = document.root().bm
        hit = [f for f in bm.faces if geom_extrude.point_in_face(f, Vector((4.5, 0.15, 1.0)))
               or geom_extrude.point_in_face(f, Vector((4.5, 0.0, 1.0)))]
        self.assertEqual(hit, [])                                  # door and inner wall region are open
        # a ray from (4.5, −1, 1) along +Y reaches the back inner wall at y = 5.85
        ys = sorted(f.calc_center_median().y for f in bm.faces
                    if geom_extrude.point_in_face(f, Vector((4.5, f.calc_center_median().y, 1.0)))
                    and abs(f.normal.y) > 0.99)
        self.assertAlmostEqual(ys[0], 5.85, places=4)
        floor = [a for a in self.logical_areas()]
        self.assertEqual(self.stats()["non_planar"], 0)
        self.assertTrue(floor)


if __name__ == "__main__":
    unittest.main()
