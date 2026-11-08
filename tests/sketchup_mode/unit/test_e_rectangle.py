# SPDX-License-Identifier: GPL-2.0-or-later
"""E: Retângulo through testing.dispatch — AC-RET-1, 2, 3 (kernel part), 5; ROTEIRO passo 1; retype,
negative values, arrow plane locks (AC-CIR-4 rule), Esc, drag."""

import unittest

import bpy
from mathutils import Vector

from su import perf, testing
from su.core import state
from su.tools import base

RECT = "su.rectangle"


class ToolCase(unittest.TestCase):
    TOOL = RECT

    def setUp(self):
        self.n_err = perf.errors()
        base.DISPATCH.set_tool(base.ToolContext(), '')
        base.DISPATCH.reset()
        base._instances.pop(self.TOOL, None)
        state.STATE.reset()
        bpy.context.scene.su_units.decimal = 'COMMA'
        testing.reset_model()
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), self.TOOL, testing.pt(0, 0))
        self.serial0 = bpy.context.scene.su_undo_serial

    def tearDown(self):
        base.DISPATCH.set_tool(base.ToolContext(), '')
        self.assertEqual(perf.errors(), self.n_err, perf.messages()[self.n_err:])

    def steps(self):
        return bpy.context.scene.su_undo_serial - self.serial0

    def stats(self):
        st = testing.doc_stats()
        self.assertEqual(st.get("validate"), [], st.get("validate"))
        self.assertEqual(st["non_planar"], 0)
        return st

    def counts(self):
        st = self.stats()
        return st["verts"], st["edges"] - st["bridges"], st["logical_faces"] or 0


class TestRectangle(ToolCase):
    def test_status(self):
        d = testing.state_dump()
        self.assertEqual(d["tool"], RECT)
        self.assertEqual(d["hint_key"], "tool.su.rectangle.hint_start")
        self.assertEqual(d["vcb_label_key"], "vcb.dimensions")

    def test_ac_ret_1_typed_dimensions(self):
        testing.click((0, 0, 0))
        self.assertTrue(base.DISPATCH.running)
        self.assertEqual(testing.state_dump()["hint_key"], "tool.su.rectangle.hint_next")
        testing.move((1, 1, 0))
        r = testing.type_text("2;3")
        self.assertIs(r, base.Result.IDLE)
        self.assertFalse(base.DISPATCH.running)
        st = self.stats()
        self.assertEqual((st["verts"], st["edges"], st["faces"]), (4, 4, 1))
        self.assertAlmostEqual(st["area"], 6.0, places=5)
        self.assertEqual(st["normals"], [[0.0, 0.0, -1.0]])
        self.assertEqual(st["bbox"], [[0.0, 0.0, 0.0], [2.0, 3.0, 0.0]])
        self.assertEqual(self.steps(), 1)

    def test_roteiro_1_floor_8x6(self):
        testing.click(testing.pt(0, 0, 0, kind="ORIGIN"))
        testing.move((3, 2, 0))
        testing.type_text("8;6")
        st = self.stats()
        self.assertEqual(self.counts(), (4, 4, 1))
        self.assertAlmostEqual(st["area"], 48.0, places=4)
        self.assertEqual(st["normals"], [[0.0, 0.0, -1.0]])
        v = testing.state_dump()["vcb_value"]
        self.assertIn("8", v)
        self.assertIn("6", v)
        self.assertEqual(self.steps(), 1)

    def test_click_click(self):
        testing.click((0, 0, 0))
        testing.move((1, 1, 0))
        r = testing.click((4, 2, 0))
        self.assertIs(r, base.Result.IDLE)
        st = self.stats()
        self.assertAlmostEqual(st["area"], 8.0, places=5)
        self.assertEqual(self.steps(), 1)

    def test_drag(self):
        testing.dispatch(testing.ev('LEFTMOUSE', 'PRESS', 0, 0), None, testing.pt(0, 0))
        testing.dispatch(testing.ev('LEFTMOUSE', 'RELEASE', 200, 100), None, testing.pt(2, 1))
        self.assertAlmostEqual(self.stats()["area"], 2.0, places=5)
        self.assertFalse(base.DISPATCH.running)

    def test_negative_values_and_quadrant(self):
        testing.click((0, 0, 0))
        testing.move((-1, 1, 0))
        testing.type_text("2;3")
        self.assertEqual(self.stats()["bbox"], [[-2.0, 0.0, 0.0], [0.0, 3.0, 0.0]])
        testing.reset_model()
        testing.click((0, 0, 0))
        testing.move((1, 1, 0))
        testing.type_text("-2;-3")
        self.assertEqual(self.stats()["bbox"], [[-2.0, -3.0, 0.0], [0.0, 0.0, 0.0]])

    def test_ac_ret_2_standing_rectangle(self):
        testing.click(testing.pt(0, 0, 0, kind="ORIGIN"))
        testing.move((2, 0, 3))
        testing.click((2, 0, 3))
        st = self.stats()
        self.assertEqual(st["bbox"], [[0.0, 0.0, 0.0], [2.0, 0.0, 3.0]])
        self.assertAlmostEqual(st["area"], 6.0, places=5)
        self.assertAlmostEqual(abs(st["normals"][0][1]), 1.0, places=5)

    def test_ac_ret_5_on_vertical_face(self):
        # a free-standing wall face in the plane y = 0 (x 0..4, z 0..3)
        testing.click((0, 0, 0))
        testing.click((4, 0, 3))
        self.assertEqual(self.counts(), (4, 4, 1))
        n = Vector(testing.doc_stats()["normals"][0])
        start = testing.pt(1, 0, 1, kind="ON_FACE", normal=n, side=1, plane=(Vector((1, 0, 1)), n))
        testing.click(start)
        testing.move((2, 0.7, 2))          # cursor off the plane: projected onto the face plane
        testing.type_text("1;1")
        st = self.stats()
        self.assertEqual(st["bbox"], [[0.0, 0.0, 0.0], [4.0, 0.0, 3.0]])
        self.assertEqual(self.counts()[2], 2)                  # wall with a hole + inner face
        areas = self._logical_areas()
        self.assertEqual(sorted(round(a, 4) for a in areas), [1.0, 11.0])

    def _logical_areas(self):
        from su.core import document, entities, geom
        bm = document.root().bm
        bm.faces.ensure_lookup_table()
        out, seen = [], set()
        for f in bm.faces:
            if f.index in seen:
                continue
            lf = entities.logical_face(bm, f)
            seen.update(g.index for g in lf.faces)
            out.append(sum(g.calc_area() for g in lf.faces))
        return out

    def test_ac_ret_3_inner_rectangle_makes_hole(self):
        testing.click((0, 0, 0))
        testing.move((1, 1, 0))
        testing.type_text("3;3")
        inner = testing.pt(1, 1, 0, kind="ON_FACE", normal=Vector((0, 0, -1)), side=-1)
        testing.click(inner)
        testing.move((1.5, 1.5, 0))
        testing.type_text("1;1")
        self.assertEqual(self.counts(), (8, 8, 2))
        self.assertEqual(sorted(round(a, 4) for a in self._logical_areas()), [1.0, 8.0])
        self.assertEqual(self.steps(), 2)

    def test_door_on_edge_makes_u(self):
        # wall y = 0, x 0..8, z 0..3; door from the midpoint of the bottom edge → U face, no visible bridge
        testing.click((0, 0, 0))
        testing.click((8, 0, 3))
        mid = testing.pt(4, 0, 0, kind="MIDPOINT")
        testing.click(mid)
        n = Vector(testing.doc_stats()["normals"][0])
        testing.move(testing.pt(4.5, 0, 1, kind="ON_FACE", normal=n, side=1))
        testing.type_text("1;2,1")
        self.assertEqual(self.counts(), (8, 9, 2))
        self.assertEqual(sorted(round(a, 4) for a in self._logical_areas()), [2.1, 21.9])

    def test_retype_after_finish(self):
        testing.click((0, 0, 0))
        testing.move((1, 1, 0))
        testing.type_text("2;3")
        self.assertEqual(testing.state_dump()["last_action"], RECT)
        testing.type_text("4;5")
        st = self.stats()
        self.assertEqual(st["bbox"], [[0.0, 0.0, 0.0], [4.0, 5.0, 0.0]])
        self.assertEqual(self.counts(), (4, 4, 1))
        self.assertEqual(self.steps(), 2)          # rectangle + "Ajustar"

    def test_arrow_locks_plane_normal(self):
        testing.dispatch(testing.ev('LEFT_ARROW', 'PRESS'))         # ← = green normal → XZ plane
        testing.click((0, 0, 0))
        testing.move((2, 5, 3))
        testing.click((2, 5, 3))
        st = self.stats()
        self.assertEqual(st["bbox"], [[0.0, 0.0, 0.0], [2.0, 0.0, 3.0]])
        self.assertEqual(state.STATE.locks.axis, '')
        testing.reset_model()
        testing.click((0, 0, 0))
        testing.dispatch(testing.ev('UP_ARROW', 'PRESS'))           # ↑ = blue normal → horizontal
        testing.move((2, 0, 3))
        self.assertTrue(base.DISPATCH.running)                      # (2, 0, 0): degenerate, keeps drawing
        testing.click((2, 0, 3))
        self.assertTrue(base.DISPATCH.running)
        testing.type_text("2;1")
        self.assertEqual(self.stats()["bbox"], [[0.0, 0.0, 0.0], [2.0, 1.0, 0.0]])

    def test_esc_leaves_nothing(self):
        testing.click((0, 0, 0))
        testing.move((5, 5, 0))
        testing.dispatch(testing.ev('ESC', 'PRESS'))
        self.assertFalse(base.DISPATCH.running)
        self.assertEqual(testing.doc_stats()["edges"], 0)
        self.assertEqual(self.steps(), 0)

    def test_degenerate_click_keeps_drawing(self):
        testing.click((0, 0, 0))
        r = testing.click((3, 0, 0))
        self.assertIs(r, base.Result.RUNNING)
        self.assertEqual(testing.doc_stats()["edges"], 0)


if __name__ == "__main__":
    unittest.main()
