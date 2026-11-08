# SPDX-License-Identifier: GPL-2.0-or-later
"""C: units (formatting/parsing, decimal separator) and Medidas (vcb.parse table AC-VCB-1, feed rules §3.5)."""

import math
import unittest

import bpy

from su.core import units, vcb
from su.core.state import STATE
from su.tools.base import Ev

COMMA = units.Units(decimal='COMMA')
PERIOD = units.Units(decimal='PERIOD')


class TestSeparators(unittest.TestCase):
    def test_locale_table(self):
        f = units._sep_from_locale
        self.assertEqual(f("pt_BR"), ",")
        self.assertEqual(f("pt-BR"), ",")
        self.assertEqual(f("en_US"), ".")
        self.assertEqual(f("en_BR"), ",")              # region wins over language
        self.assertEqual(f("en_US@rg=brzzzz"), ",")    # region override
        self.assertEqual(f("de_DE"), ",")
        self.assertEqual(f("ja_JP"), ".")
        self.assertEqual(f("fr"), ",")
        self.assertIsNone(f(""))

    def test_system_cached(self):
        units._reset_system_cache()
        a = units.system_decimal_sep()
        self.assertIn(a, (",", "."))
        units._reset_system_cache("#")
        self.assertEqual(units.system_decimal_sep(), "#")
        units._reset_system_cache()

    def test_list_sep(self):
        self.assertEqual(units.list_sep(COMMA), ";")
        self.assertEqual(units.list_sep(PERIOD), ",")
        units._reset_system_cache(",")
        try:
            self.assertEqual(units.decimal_sep(units.Units()), ",")
        finally:
            units._reset_system_cache()

    def test_scene_property(self):
        u = bpy.context.scene.su_units
        self.assertEqual(u.length_unit, 'M')
        self.assertEqual(u.length_precision, 2)
        self.assertEqual(units.current(), u)


class TestFormat(unittest.TestCase):
    def test_length(self):
        self.assertEqual(units.format_length(2.5, COMMA), "2,50m")
        self.assertEqual(units.format_length(2.5, PERIOD), "2.50m")
        self.assertEqual(units.format_length(3.0, COMMA), "3,00m")
        self.assertEqual(units.format_length(-0.001, COMMA), "0,00m")
        self.assertEqual(units.format_length(2.5, units.Units(length_unit='CM', decimal='COMMA')), "250,00cm")
        self.assertEqual(units.format_length(0.3048, units.Units(length_unit='IN', decimal='COMMA')), '12,00"')
        self.assertEqual(units.format_length(0.9144, units.Units(length_unit='FT', decimal='COMMA')), "3,00'")
        self.assertEqual(units.format_length(1.0, units.Units(length_unit='MM', length_precision=0,
                                                              decimal='COMMA')), "1000mm")

    def test_area_angle(self):
        self.assertEqual(units.format_area(6.0, COMMA), "6,00m²")
        self.assertEqual(units.format_angle(math.pi / 2, COMMA), "90,0°")
        self.assertEqual(units.format_angle(math.radians(22.5), PERIOD), "22.5°")


class TestParse(unittest.TestCase):
    def test_length(self):
        p = units.parse_length
        self.assertAlmostEqual(p("2,5", COMMA), 2.5)
        self.assertAlmostEqual(p("2.5", COMMA), 2.5)          # point always accepted
        self.assertAlmostEqual(p("250cm", COMMA), 2.5)
        self.assertAlmostEqual(p("25 mm", COMMA), 0.025)
        self.assertAlmostEqual(p("3M", COMMA), 3.0)
        self.assertAlmostEqual(p("-1,5", COMMA), -1.5)
        self.assertAlmostEqual(p("3'", COMMA), 0.9144)
        self.assertAlmostEqual(p('12"', COMMA), 0.3048)
        self.assertAlmostEqual(p("5'6\"", COMMA), 1.6764)
        self.assertAlmostEqual(p('1/2"', COMMA), 0.0127)
        self.assertAlmostEqual(p('3 1/2"', COMMA), 3.5 * 0.0254)
        self.assertAlmostEqual(p("25", units.Units(length_unit='CM', decimal='COMMA')), 0.25)
        for bad in ("", "abc", "2,,5", "m", "1/0"):
            with self.assertRaises(ValueError, msg=bad):
                p(bad, COMMA)
        with self.assertRaises(ValueError):
            p("2,5", PERIOD)

    def test_angle(self):
        a = units.parse_angle
        self.assertAlmostEqual(a("30", COMMA), math.radians(30))
        self.assertAlmostEqual(a("90°", COMMA), math.pi / 2)
        self.assertAlmostEqual(a("-45,5", COMMA), math.radians(-45.5))
        self.assertAlmostEqual(a("3:12", COMMA), math.atan(3 / 12))
        with self.assertRaises(ValueError):
            a("abc", COMMA)


class TestVCBParse(unittest.TestCase):
    """AC-VCB-1."""

    def one(self, text, schema, units_=COMMA):
        v = vcb.parse(text, schema, units_)
        self.assertEqual(len(v), 1)
        return v[0]

    def test_table(self):
        v = self.one("2,5", "length")
        self.assertEqual((v.kind, round(v.value, 9)), ('LENGTH', 2.5))
        self.assertAlmostEqual(self.one("250cm", "length").value, 2.5)
        v = vcb.parse("2;3", "length2", COMMA)
        self.assertEqual([(x.kind, x.value) for x in v], [('LENGTH', 2.0), ('LENGTH', 3.0)])
        v = self.one("[1;2;0]", "line")
        self.assertEqual((v.kind, v.vector), ('POINT_ABS', (1.0, 2.0, 0.0)))
        v = self.one("<1;0;0>", "distance")
        self.assertEqual((v.kind, v.vector), ('POINT_REL', (1.0, 0.0, 0.0)))
        for t in ("5x", "x5", "*5", "5X"):
            v = self.one(t, "distance")
            self.assertEqual((v.kind, v.count), ('MULTIPLY', 5), t)
        for t in ("/5", "5/"):
            v = self.one(t, "distance")
            self.assertEqual((v.kind, v.count), ('DIVIDE', 5), t)
        v = self.one("12s", "radius")
        self.assertEqual((v.kind, v.count), ('SIDES', 12))
        v = self.one("12", "sides")
        self.assertEqual((v.kind, v.count), ('SIDES', 12))
        v = self.one("1r", "arc")
        self.assertEqual((v.kind, v.value), ('RADIUS', 1.0))
        v = self.one("12s", "arc")
        self.assertEqual((v.kind, v.count), ('SEGMENTS', 12))
        v = self.one("0,5", "arc")
        self.assertEqual((v.kind, v.value), ('LENGTH', 0.5))
        v = self.one("3:12", "angle")
        self.assertEqual(v.kind, 'ANGLE')
        self.assertAlmostEqual(v.value, math.atan(0.25))
        v = self.one("90", "angle")
        self.assertAlmostEqual(v.value, math.pi / 2)
        v = self.one("3x", "angle")
        self.assertEqual((v.kind, v.count), ('MULTIPLY', 3))
        self.assertAlmostEqual(self.one("0,4", "radius").value, 0.4)

    def test_scale(self):
        v = vcb.parse("2;1;1", "scale", COMMA)
        self.assertEqual([(x.kind, x.value) for x in v], [('NUMBER', 2.0), ('NUMBER', 1.0), ('NUMBER', 1.0)])
        self.assertEqual(self.one("-1", "scale").value, -1.0)
        self.assertEqual(self.one("1,5", "scale").value, 1.5)
        v = self.one("3m", "scale")
        self.assertEqual((v.kind, v.value), ('LENGTH', 3.0))

    def test_period_locale(self):
        self.assertEqual(self.one("2.5", "length", PERIOD).value, 2.5)
        v = vcb.parse("2,3", "length2", PERIOD)
        self.assertEqual([x.value for x in v], [2.0, 3.0])
        v = self.one("[1,2,0]", "line", PERIOD)
        self.assertEqual(v.vector, (1.0, 2.0, 0.0))

    def test_partial_rectangle(self):
        v = vcb.parse(";3", "length2", COMMA)
        self.assertEqual([x.value for x in v], [None, 3.0])
        v = vcb.parse("2,5", "length2", COMMA)
        self.assertEqual([x.value for x in v], [2.5])
        v = self.one("<;;1>", "distance")
        self.assertEqual(v.vector, (None, None, 1.0))

    def test_errors(self):
        bad = [("", "length"), ("abc", "length"), ("2;3;4", "length2"), ("0x", "distance"), ("2s", "sides"),
               ("[1;2]", "line"), ("[1;;2]", "line"), ("1;2;3;4", "scale"), ("0", "scale"), ("1", "nope"),
               ("5x", "length")]
        for text, schema in bad:
            with self.assertRaises(ValueError, msg=(text, schema)):
                vcb.parse(text, schema, COMMA)


def key(type_, ch="", **kw):
    return Ev(type=type_, value=kw.pop("value", 'PRESS'), x=0, y=0, unicode=ch, **kw)


CHAR_TYPES = {"2": 'TWO', ",": 'COMMA', "5": 'FIVE', "m": 'M', "l": 'L', "-": 'MINUS', "[": 'LEFT_BRACKET'}


def typed(ch):
    return key(CHAR_TYPES.get(ch, 'TEXTINPUT'), ch)


class TestVCBFeed(unittest.TestCase):
    def setUp(self):
        vcb.clear()
        STATE.vcb_error = False

    tearDown = setUp

    def test_typing_rules(self):
        self.assertEqual(vcb.feed(typed("l")), 'PASS')          # letter with empty buffer = shortcut
        self.assertEqual(vcb.buffer(), "")
        for ch in "2,5":
            self.assertEqual(vcb.feed(typed(ch)), 'CONSUMED')
        self.assertEqual(vcb.feed(typed("m")), 'CONSUMED')       # non-empty: letters go to the buffer
        self.assertEqual(vcb.buffer(), "2,5m")
        self.assertEqual(vcb.feed(key('BACK_SPACE')), 'CONSUMED')
        self.assertEqual(vcb.buffer(), "2,5")
        self.assertEqual(vcb.feed(key('RET')), 'APPLY')
        self.assertEqual([v.value for v in vcb.values("length", COMMA)], [2.5])
        self.assertEqual(vcb.take(), "2,5")
        self.assertEqual(vcb.buffer(), "")

    def test_start_chars(self):
        for ch in "0123456789.,-[</*":
            vcb.clear()
            self.assertEqual(vcb.feed(key('TEXTINPUT', ch)), 'CONSUMED', ch)

    def test_empty_buffer_passes(self):
        for t in ('RET', 'NUMPAD_ENTER', 'BACK_SPACE', 'ESC', 'UP_ARROW', 'DEL'):
            self.assertEqual(vcb.feed(key(t)), 'PASS', t)

    def test_esc_clears(self):
        vcb.feed(typed("2"))
        self.assertEqual(vcb.feed(key('ESC')), 'CANCEL')
        self.assertEqual(vcb.buffer(), "")
        self.assertEqual(vcb.feed(key('ESC')), 'PASS')

    def test_modifiers_and_release(self):
        vcb.feed(typed("2"))
        self.assertEqual(vcb.feed(key('Z', "z", alt_action=True)), 'PASS')   # Cmd+Z
        self.assertEqual(vcb.feed(key('Z', "z", ctrl=True)), 'PASS')
        self.assertEqual(vcb.feed(key('THREE', "3", value='RELEASE')), 'PASS')
        self.assertEqual(vcb.feed(key('UP_ARROW')), 'PASS')                   # arrows lock inference
        self.assertEqual(vcb.buffer(), "2")

    def test_invalid_sets_error(self):
        for ch in "2x":
            vcb.feed(typed(ch))
        self.assertIsNone(vcb.values("length", COMMA))
        self.assertTrue(STATE.vcb_error)
        vcb.feed(key('BACK_SPACE'))
        self.assertFalse(STATE.vcb_error)

    def test_apply_text(self):
        got = []
        vcb.set_applier(got.append)
        try:
            self.assertEqual(vcb.apply_text(" 4 "), 'APPLY')
            self.assertEqual(got, ["4"])
            self.assertEqual(vcb.apply_text(""), 'PASS')
        finally:
            vcb.set_applier(None)
