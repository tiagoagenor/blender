# SPDX-License-Identifier: GPL-2.0-or-later
"""A0 platform tests (owner: A): discovery, events, i18n, registry, colors, base, state, undo serial."""

import unittest

import bpy

import su
from su import colors, constants, events, i18n, perf, registry
from su.core import state, undo
from su.tools import base


class _PerfGuard:
    """Tests that provoke perf.error restore the counter afterwards."""

    def setUp(self):
        self._n = perf.errors()

    def tearDown(self):
        del perf._errors[self._n:]


class TestDiscovery(unittest.TestCase):
    def test_registered_without_failures(self):
        self.assertTrue(su.is_registered())
        self.assertEqual(su.failed_modules(), [])

    def test_order_and_no_draw_in_background(self):
        names = su.loaded_modules()
        self.assertIn("perf", names)
        self.assertIn("tools.base", names)
        self.assertIn("i18n", su.active_modules())
        self.assertIn("core.undo", names)
        self.assertFalse(any(n.startswith("draw.") for n in names))
        orders = [o for o, _r, _m in su.discover()]
        self.assertEqual(orders, sorted(orders))


class TestEvents(_PerfGuard, unittest.TestCase):
    def test_order_and_exception_isolation(self):
        seen = []

        def late(**kw):
            seen.append(("late", kw["doc_key"]))

        def boom(**kw):
            raise RuntimeError("boom")

        def early(**kw):
            seen.append(("early", kw["doc_key"]))

        events.subscribe("doc", late, order=900)
        events.subscribe("doc", boom, order=500)
        events.subscribe("doc", early, order=10)
        try:
            n = perf.errors()
            events.emit("doc", doc_key="k")
            self.assertEqual(seen, [("early", "k"), ("late", "k")])
            self.assertEqual(perf.errors(), n + 1)
        finally:
            for fn in (late, boom, early):
                events.unsubscribe("doc", fn)

    def test_unknown_topic(self):
        with self.assertRaises(ValueError):
            events.subscribe("nope", lambda **kw: None)


class TestI18n(unittest.TestCase):
    def test_lookup_fallback_format(self):
        self.assertEqual(i18n.t("undo.init"), "Início")
        self.assertEqual(i18n.t("missing.key"), "missing.key")
        i18n.register_strings({"app.test_fmt": {"pt_BR": "{n} lados", "en": "{n} sides"}})
        try:
            self.assertEqual(i18n.t("app.test_fmt", n=6), "6 lados")
            i18n.set_language("en")
            self.assertEqual(i18n.t("app.test_fmt", n=6), "6 sides")
            self.assertEqual(i18n.t("undo.adjust"), "Adjust")
        finally:
            i18n.set_language("pt_BR")
            i18n.unregister_strings(["app.test_fmt"])

    def test_duplicate_and_prefix(self):
        with self.assertRaises(KeyError):
            i18n.register_strings({"undo.init": "x"})
        with self.assertRaises(ValueError):
            i18n.register_strings({"nopefix": "x"})
        self.assertFalse(i18n.has("nopefix"))


class TestRegistry(unittest.TestCase):
    def test_override_restore(self):
        class Owner:
            def f(self):
                return 1
        registry.override(Owner, "f", lambda self: 2)
        registry.override(Owner, "g", lambda self: 3)
        self.assertEqual(Owner().f(), 2)
        # restore only these two (pop from the end, as restore_all does)
        saved = registry._overrides[:-2]
        mine = registry._overrides[-2:]
        registry._overrides[:] = mine
        registry.restore_all()
        registry._overrides[:] = saved
        self.assertEqual(Owner().f(), 1)
        self.assertFalse(hasattr(Owner, "g"))


class TestColors(unittest.TestCase):
    def test_conversions(self):
        self.assertEqual(colors.rgba(colors.FACE_FRONT), (1.0, 1.0, 1.0, 1.0))
        r, g, b, a = colors.lin((188, 188, 188))
        self.assertAlmostEqual(r, 0.5029, places=3)
        self.assertEqual(colors.rgba(colors.EDGE, 0.5)[3], 0.5)
        self.assertEqual(constants.TEMPLATE_ID, "SketchUp_Mode")


class TestBase(unittest.TestCase):
    def test_tool_decorator(self):
        meta = base.ToolMeta(id="su.test_dummy", label_key="tool.su.test_dummy.label", icon="")

        @base.tool(meta)
        class Dummy(base.BaseTool):
            pass

        try:
            self.assertIs(base.controller("su.test_dummy"), base.controller("su.test_dummy"))
            self.assertEqual(base.controller("su.test_dummy").press(None, None, None), base.Result.IDLE)
            with self.assertRaises(KeyError):
                @base.tool(meta)
                class Other(base.BaseTool):
                    pass
        finally:
            base.TOOLS.pop("su.test_dummy", None)
            base._instances.pop("su.test_dummy", None)
        self.assertIsNone(base.controller("su.test_dummy"))


class TestState(unittest.TestCase):
    def test_defaults(self):
        inf = state.Inference.none()
        self.assertEqual(inf.kind, "NONE")
        self.assertEqual(inf.side, 0)
        self.assertIsNone(state.STATE.last_action)


class TestUndoSerial(unittest.TestCase):
    def test_push_increments_serial(self):
        scene = bpy.context.scene
        s0 = scene.su_undo_serial
        undo.before_change()
        undo.push("undo.init")
        self.assertEqual(scene.su_undo_serial, s0 + 1)
        self.assertIn(s0, undo._SEL)
        self.assertIn(s0 + 1, undo._SEL)


if __name__ == "__main__":
    unittest.main()
