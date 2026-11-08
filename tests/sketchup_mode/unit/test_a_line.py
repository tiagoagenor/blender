# SPDX-License-Identifier: GPL-2.0-or-later
"""A (slice): Linha through testing.dispatch — AC-LIN-1 (Measurements), AC-LIN-7 (retype), chain rules.
Uses B/C fakes (tests/sketchup_mode/unit/fakes.py) when the real modules are not merged yet."""

import unittest

import bpy

import fakes
from su import perf, registry, testing
from su.core import state
from su.tools import base

LINE = "su.line"


class LineCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fakes.install("su")

    @classmethod
    def tearDownClass(cls):
        base.DISPATCH.set_tool(base.ToolContext(), '')
        fakes.uninstall()

    def setUp(self):
        self.n_err = perf.errors()
        base.DISPATCH.reset()
        base._instances.pop(LINE, None)
        state.STATE.reset()
        testing.reset_model()
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), LINE, testing.pt(0, 0))
        self.serial0 = bpy.context.scene.su_undo_serial

    def tearDown(self):
        self.assertEqual(perf.errors(), self.n_err, perf.messages()[self.n_err:])

    def steps(self):
        return bpy.context.scene.su_undo_serial - self.serial0

    def seg(self, toward, text):
        testing.move(toward)
        return testing.type_text(text)


class TestLine(LineCase):
    def test_status_on_activate(self):
        d = testing.state_dump()
        self.assertEqual(d["tool"], LINE)
        self.assertEqual(d["hint_key"], "tool.su.line.hint_start")
        self.assertEqual(d["vcb_label_key"], "vcb.length")

    def test_ac_lin_1_rectangle_by_measurements(self):
        testing.click((0, 0, 0))
        self.assertTrue(base.DISPATCH.running)
        self.assertEqual(testing.state_dump()["hint_key"], "tool.su.line.hint_next")
        self.seg((1, 0, 0), "3")
        self.seg((3, 1, 0), "2")
        self.seg((2, 2, 0), "3")
        r = self.seg((0, 1, 0), "2")
        self.assertIs(r, base.Result.IDLE)          # the face ends the chain
        self.assertFalse(base.DISPATCH.running)
        st = testing.doc_stats()
        self.assertEqual((st["verts"], st["edges"], st["faces"]), (4, 4, 1))
        self.assertAlmostEqual(st["area"], 6.0, places=5)
        self.assertEqual(st["normals"], [[0.0, 0.0, -1.0]])
        self.assertEqual(st["non_planar"], 0)
        self.assertEqual(st["bbox"], [[0.0, 0.0, 0.0], [3.0, 2.0, 0.0]])
        self.assertEqual(self.steps(), 4)            # one undo step per segment

    def test_clicks_and_double_click_ends(self):
        testing.click((0, 0, 0))
        testing.click((1, 0, 0))
        self.assertTrue(base.DISPATCH.running)
        self.assertEqual(self.steps(), 1)
        r = testing.click((1, 0, 0))                 # same point again = double click
        self.assertIs(r, base.Result.IDLE)
        self.assertFalse(base.DISPATCH.running)
        self.assertEqual(testing.doc_stats()["edges"], 1)

    def test_drag_draws_segment(self):
        testing.dispatch(testing.ev('LEFTMOUSE', 'PRESS', 0, 0), None, testing.pt(0, 0))
        testing.dispatch(testing.ev('LEFTMOUSE', 'RELEASE', 200, 0), None, testing.pt(2, 0))
        self.assertEqual(testing.doc_stats()["edges"], 1)
        self.assertTrue(base.DISPATCH.running)

    def test_esc_leaves_no_garbage(self):
        testing.click((0, 0, 0))
        testing.move((5, 5, 0))
        testing.dispatch(testing.ev('ESC', 'PRESS'))
        self.assertFalse(base.DISPATCH.running)
        self.assertEqual(testing.doc_stats()["edges"], 0)
        self.assertEqual(self.steps(), 0)
        self.assertEqual(testing.state_dump()["hint_key"], "tool.su.line.hint_start")

    def test_ac_lin_7_retype_after_finish(self):
        testing.click((0, 0, 0))
        testing.click((1, 0, 0))
        testing.dispatch(testing.ev('ESC', 'PRESS'))
        self.assertEqual(testing.state_dump()["last_action"], LINE)
        testing.type_text("4")
        st = testing.doc_stats()
        self.assertEqual(st["bbox"], [[0.0, 0.0, 0.0], [4.0, 0.0, 0.0]])
        self.assertEqual(self.steps(), 2)            # segment + "Ajustar"

    def test_absolute_and_relative_points(self):
        testing.click((0, 0, 0))
        testing.move((1, 0, 0))
        sep = ";" if testing.registry.optional("core.units") is None or \
            testing.registry.optional("core.units").list_sep(None) == ";" else ","
        testing.type_text("[2{0}1{0}0]".format(sep))
        testing.type_text("<0{0}0{0}3>".format(sep))
        st = testing.doc_stats()
        self.assertEqual(st["edges"], 2)
        self.assertEqual(st["bbox"], [[0.0, 0.0, 0.0], [2.0, 1.0, 3.0]])

    def test_tool_change_clears_last_action(self):
        testing.click((0, 0, 0))
        testing.click((1, 0, 0))
        testing.dispatch(testing.ev('ESC', 'PRESS'))
        base.DISPATCH.set_tool(base.ToolContext(), '')
        self.assertIsNone(state.STATE.last_action)


if __name__ == "__main__":
    unittest.main()
