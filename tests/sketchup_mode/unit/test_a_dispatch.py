# SPDX-License-Identifier: GPL-2.0-or-later
"""A: event semantics of tools.base.DISPATCH (PLANO §2.4 contract), Measurements routing, keymap, session."""

import unittest

import bpy

import fakes
from su import keymap, perf, session, testing
from su.core import state, undo
from su.tools import base

PROBE = "su.test_probe"
OTHER = "su.test_other"


class Probe(base.BaseTool):
    def __init__(self):
        self.calls = []
        self.running = False
        self.boom = False

    def _log(self, name, *a):
        self.calls.append((name,) + a)

    def activate(self, tc):
        self._log("activate")

    def deactivate(self, tc):
        self._log("deactivate")

    def hover(self, tc, inf):
        self._log("hover", inf.kind)

    def press(self, tc, ev, inf):
        if self.boom:
            raise RuntimeError("boom")
        self._log("press", ev.clicks)
        self.running = True
        return base.Result.RUNNING

    def release(self, tc, ev, inf):
        self._log("release", ev.is_drag_release, ev.clicks)
        return base.Result.RUNNING if self.running else base.Result.IDLE

    def move(self, tc, ev, inf):
        self._log("move")
        return base.Result.RUNNING

    def vcb(self, tc, values):
        self._log("vcb", [v.value for v in values])
        return base.Result.RUNNING if self.running else base.Result.IDLE

    def cancel(self, tc):
        self._log("cancel")
        self.running = False


class FakeClock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def _names(calls):
    return [c[0] for c in calls]


class DispatchCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.installed = fakes.install("su", only={"core.vcb"})
        base.tool(base.ToolMeta(id=PROBE, label_key="tool.su.test_probe.label", icon="", vcb_schema="length"))(Probe)
        base.tool(base.ToolMeta(id=OTHER, label_key="tool.su.test_other.label", icon="", shortcut="L"))(
            type("Other", (base.BaseTool,), {}))

    @classmethod
    def tearDownClass(cls):
        base.DISPATCH.reset()
        for tid in (PROBE, OTHER):
            base.TOOLS.pop(tid, None)
            base._instances.pop(tid, None)
        fakes.uninstall()
        testing.set_clock(None)

    def setUp(self):
        self.clock = FakeClock()
        testing.set_clock(self.clock)
        base.DISPATCH.reset()
        base._instances.pop(PROBE, None)
        state.STATE.reset()
        self.n_err = perf.errors()
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), PROBE, testing.pt(0, 0))
        self.p = base.controller(PROBE)
        self.p.calls.clear()

    def tearDown(self):
        del perf._errors[self.n_err:]
        base.DISPATCH.set_tool(base.ToolContext(), '')

    def press(self, x=10, y=10, **kw):
        return testing.dispatch(testing.ev('LEFTMOUSE', 'PRESS', x, y, **kw), None, testing.pt(x, y))

    def release(self, x=10, y=10, **kw):
        return testing.dispatch(testing.ev('LEFTMOUSE', 'RELEASE', x, y, **kw), None, testing.pt(x, y))


class TestEvents(DispatchCase):
    def test_activation_and_tool_event(self):
        self.assertEqual(base.DISPATCH.tool_id, PROBE)
        self.assertEqual(self.press(), base.Result.RUNNING)
        self.assertTrue(base.DISPATCH.running)
        testing.dispatch(testing.ev('LEFTMOUSE', 'PRESS'), OTHER, testing.pt(0, 0))
        self.assertIn("cancel", _names(self.p.calls))
        self.assertIn("deactivate", _names(self.p.calls))
        self.assertFalse(base.DISPATCH.running)

    def test_ctrl_press_and_click_values_pass(self):
        self.assertIs(self.press(ctrl=True), base.Result.PASS)
        self.assertIs(testing.dispatch(testing.ev('LEFTMOUSE', 'CLICK'), None, testing.pt(0, 0)), base.Result.PASS)
        self.assertIs(testing.dispatch(testing.ev('LEFTMOUSE', 'CLICK_DRAG'), None, testing.pt(0, 0)), base.Result.PASS)
        self.assertEqual(self.p.calls, [])

    def test_double_click_counts_and_value(self):
        self.press()
        self.release()
        self.clock.t += 0.2
        testing.dispatch(testing.ev('LEFTMOUSE', 'DOUBLE_CLICK', 11, 10), None, testing.pt(0, 0))
        self.clock.t += 0.2
        self.press(11, 11)
        presses = [c[1] for c in self.p.calls if c[0] == "press"]
        self.assertEqual(presses, [1, 2, 3])
        self.clock.t += 1.0
        self.press()
        self.assertEqual(self.p.calls[-1], ("press", 1))
        self.clock.t += 0.1
        self.press(200, 200)             # far away: not a double click
        self.assertEqual(self.p.calls[-1], ("press", 1))

    def test_drag_release(self):
        self.press(10, 10)
        self.release(11, 10)
        self.assertEqual(self.p.calls[-1][:2], ("release", False))
        self.press(10, 10)
        self.release(100, 10)
        self.assertEqual(self.p.calls[-1][:2], ("release", True))

    def test_move_hover_vs_running(self):
        testing.move((1, 1, 0))
        self.assertEqual(self.p.calls[-1][0], "hover")
        self.press()
        testing.move((2, 2, 0))
        self.assertEqual(self.p.calls[-1][0], "move")

    def test_navigation_and_rmb(self):
        self.press()
        for t in ('MIDDLEMOUSE', 'WHEELUPMOUSE', 'TRACKPADPAN', 'TRACKPADZOOM', 'NDOF_MOTION', 'TIMER'):
            self.assertIs(testing.dispatch(testing.ev(t, 'PRESS')), base.Result.PASS, t)
        self.assertIs(testing.dispatch(testing.ev('RIGHTMOUSE', 'PRESS')), base.Result.RUNNING)
        self.assertTrue(base.DISPATCH.running)
        self.assertNotIn("cancel", _names(self.p.calls))

    def test_esc_cancels(self):
        self.press()
        self.assertIs(testing.dispatch(testing.ev('ESC', 'PRESS')), base.Result.IDLE)
        self.assertFalse(base.DISPATCH.running)
        self.assertIn("cancel", _names(self.p.calls))
        # idle Esc is not ours (keymap: exit group)
        self.assertIs(testing.dispatch(testing.ev('ESC', 'PRESS')), base.Result.PASS)

    def test_other_tool_shortcut_cancels_and_passes(self):
        self.press()
        self.assertIs(testing.dispatch(testing.ev('L', 'PRESS', unicode='l')), base.Result.PASS)
        self.assertIn("cancel", _names(self.p.calls))
        self.assertFalse(base.DISPATCH.running)

    def test_non_tool_letter_passes_without_cancel(self):
        self.press()
        self.assertIs(testing.dispatch(testing.ev('K', 'PRESS', unicode='k')), base.Result.PASS)
        self.assertTrue(base.DISPATCH.running)
        self.assertNotIn("cancel", _names(self.p.calls))

    def test_cmd_z_cancels_and_passes(self):
        self.press()
        self.assertIs(testing.dispatch(testing.ev('Z', 'PRESS', alt_action=True, unicode='z')), base.Result.PASS)
        self.assertFalse(base.DISPATCH.running)
        self.assertIn("cancel", _names(self.p.calls))

    def test_exception_policy(self):
        self.p.boom = True
        n = perf.errors()
        r = self.press()
        self.assertIs(r, base.Result.IDLE)
        self.assertEqual(perf.errors(), n + 1)
        self.assertIn("cancel", _names(self.p.calls))
        self.assertTrue(base.DISPATCH.last_error.startswith("RuntimeError"))
        base.DISPATCH.last_error = ''

    def test_arrow_lock_while_idle(self):
        self.assertFalse(base.DISPATCH.running)
        r = testing.dispatch(testing.ev('UP_ARROW', 'PRESS'))
        self.assertIs(r, base.Result.IDLE)            # consumed, tool still idle
        self.assertEqual(state.STATE.locks.axis, "AXIS_Z")
        testing.dispatch(testing.ev('UP_ARROW', 'PRESS'))
        self.assertEqual(state.STATE.locks.axis, "")
        items = [it for it in keymap.window_items() if it[0] == "su.tool_key"]
        self.assertEqual(sorted(it[1]["type"] for it in items),
                         ['DOWN_ARROW', 'LEFT_ARROW', 'RIGHT_ARROW', 'UP_ARROW'])

    def test_locks_reset_when_operation_ends(self):
        self.press()
        state.STATE.locks.axis = "AXIS_Z"
        testing.dispatch(testing.ev('ESC', 'PRESS'))
        self.assertEqual(state.STATE.locks.axis, "")
        # also when the tool itself finishes (press/vcb returning IDLE)
        self.press()
        state.STATE.locks.axis = "AXIS_X"
        self.p.running = False
        self.p.calls.clear()
        base.DISPATCH.handle(base.ToolContext(), testing.ev('LEFTMOUSE', 'RELEASE', 10, 10), testing.pt(0, 0))
        self.assertFalse(base.DISPATCH.running)
        self.assertEqual(state.STATE.locks.axis, "")

    def test_shift_lock(self):
        self.press()
        state.STATE.inference = testing.pt(1, 0, 0, kind="ENDPOINT")
        testing.dispatch(testing.ev('LEFT_SHIFT', 'PRESS', shift=True))
        self.assertIsNotNone(state.STATE.locks.shift)
        testing.dispatch(testing.ev('LEFT_SHIFT', 'RELEASE'))
        self.assertIsNone(state.STATE.locks.shift)


class TestMeasurements(DispatchCase):
    def test_running_goes_to_tool(self):
        self.press()
        self.assertIs(testing.type_text("2,5"), base.Result.RUNNING)
        self.assertEqual(self.p.calls[-1], ("vcb", [2.5]))
        self.assertEqual(state.STATE.vcb_buffer, "")

    def test_letters_pass_with_empty_buffer_backspace_edits(self):
        self.assertIs(testing.dispatch(testing.ev('X', 'PRESS', unicode='x')), base.Result.PASS)
        testing.dispatch(testing.ev('ONE', 'PRESS', unicode='1'))
        testing.dispatch(testing.ev('TWO', 'PRESS', unicode='2'))
        self.assertEqual(state.STATE.vcb_buffer, "12")
        testing.dispatch(testing.ev('BACK_SPACE', 'PRESS'))
        self.assertEqual(state.STATE.vcb_buffer, "1")
        testing.dispatch(testing.ev('ESC', 'PRESS'))
        self.assertEqual(state.STATE.vcb_buffer, "")
        self.assertIs(testing.dispatch(testing.ev('BACK_SPACE', 'PRESS')), base.Result.PASS)

    def test_idle_reapply_pushes_adjust(self):
        got = []
        state.STATE.last_action = state.LastAction(PROBE, "length", lambda vals: got.append(vals[0].value) or True)
        s0 = bpy.context.scene.su_undo_serial
        testing.type_text("4")
        self.assertEqual(got, [4.0])
        self.assertEqual(bpy.context.scene.su_undo_serial, s0 + 1)
        self.assertNotIn("vcb", _names(self.p.calls))

    def test_idle_without_action_goes_to_tool(self):
        testing.type_text("8")
        self.assertEqual(self.p.calls[-1], ("vcb", [8.0]))

    def test_parse_error_marks_error(self):
        self.press()
        testing.type_text("1;2")
        self.assertTrue(state.STATE.vcb_error)
        self.assertTrue(base.DISPATCH.running)


class TestKeymapData(unittest.TestCase):
    def test_window_items_order(self):
        items = keymap.window_items()
        types = [it[1]["type"] for it in items[:5]]
        self.assertEqual(types, ['TEXTINPUT', 'RET', 'NUMPAD_ENTER', 'BACK_SPACE', 'ESC'])
        self.assertTrue(all(it[0] == "su.vcb_key" for it in items[:5]))
        line = [it for it in items if it[0] == "su.tool_activate" and it[2]["properties"] == [("tool_id", "su.line")]]
        self.assertEqual(len(line), 1)
        self.assertEqual(line[0][1]["type"], 'L')
        k = [it for it in items if it[1]["type"] == 'K']
        self.assertEqual([it[0] for it in k], ["su.style_toggle"])

    def test_tool_keymap_accepts_modifiers(self):
        meta = base.ToolMeta(id="su.x", label_key="tool.su.x.label", icon="")
        items = base.tool_keymap(meta)
        self.assertEqual([(it[1]["type"], it[1]["value"]) for it in items],
                         [('LEFTMOUSE', 'PRESS'), ('LEFTMOUSE', 'RELEASE'), ('MOUSEMOVE', 'ANY')])
        self.assertTrue(all(it[1].get("any") for it in items))

    def test_allow_list(self):
        data = {name: content for name, _args, content in keymap.keyconfig_data()}
        ids = {it[0] for name in keymap.FILTERED if name in data for it in data[name]["items"]}
        if keymap.view3d_items():          # G's su.view_* replace Blender's navigation
            self.assertTrue(keymap.BLENDER_NAV.isdisjoint(ids), keymap.BLENDER_NAV & ids)
            self.assertIn("view3d.ndof_orbit", ids)
            mmb = [it[0] for it in keymap.view3d_items() if it[1]["type"] == 'MIDDLEMOUSE']
            self.assertIn("su.view_orbit", mmb)
        else:
            self.assertIn("view3d.rotate", ids)
        self.assertIn("ed.undo", ids)
        win = [it[0] for it in keymap.window_items()]
        self.assertLessEqual(win.count("su.view_orbit"), 2)      # no duplicate Ctrl+Cmd items
        for banned in ("object.hide_collection", "screen.animation_play", "view3d.select", "object.delete",
                       "ui.reset_default_button", "wm.call_menu", "transform.translate", "wm.search_menu"):
            self.assertNotIn(banned, ids)
        self.assertTrue(data["View3D Rotate Modal"]["items"])     # modal keymaps untouched


class TestSession(unittest.TestCase):
    def test_hold_release(self):
        ns = bpy.app.driver_namespace
        session._loaded[0] = True
        session.hold("x")
        self.assertFalse(ns.get("su_ready"))
        session.release("x")
        self.assertTrue(ns.get("su_ready"))
        ns.pop("su_ready", None)

    def test_load_emits_and_clears_active(self):
        from su import events
        seen = []
        events.subscribe("load", lambda **kw: seen.append(1))
        ob = bpy.data.objects.new("su_test_active", None)
        bpy.context.scene.collection.objects.link(ob)
        bpy.context.view_layer.objects.active = ob
        try:
            session.on_load_post()
            self.assertEqual(seen, [1])
            self.assertIsNone(bpy.context.view_layer.objects.active)
        finally:
            events._subs["load"].pop()
            bpy.data.objects.remove(ob)


class TestTesting(unittest.TestCase):
    def test_state_dump_keys(self):
        d = testing.state_dump()
        for k in ("tool", "hint", "vcb_label", "vcb_buffer", "inference", "locks", "selection", "lts", "perf_errors"):
            self.assertIn(k, d)


if __name__ == "__main__":
    unittest.main()
