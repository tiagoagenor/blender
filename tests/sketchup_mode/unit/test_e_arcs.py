# SPDX-License-Identifier: GPL-2.0-or-later
"""E: Arco de dois pontos through testing.dispatch — AC-ARC-1, typed chord, radius `Nr`, segments `Ns`,
retype, arc + line closes a face, Esc."""

import math
import unittest

from su import testing
from su.core import document, entities, geom
from su.tools import base

from test_e_rectangle import ToolCase

ARC = "su.arc2"


class TestArc2(ToolCase):
    TOOL = ARC

    def test_status(self):
        d = testing.state_dump()
        self.assertEqual(d["hint_key"], "tool.su.arc2.hint_start")

    def test_ac_arc_1_semicircle(self):
        testing.click((0, 0, 0))
        testing.click((2, 0, 0))
        self.assertEqual(testing.state_dump()["hint_key"], "tool.su.arc2.hint_bulge")
        testing.move((1, 0.4, 0))
        testing.type_text("1")
        self.assertFalse(base.DISPATCH.running)
        st = self.stats()
        self.assertEqual((st["verts"], st["edges"], st["faces"]), (13, 12, 0))
        bb = st["bbox"]
        self.assertAlmostEqual(bb[1][1], 1.0, places=5)
        self.assertAlmostEqual(bb[0][1], 0.0, places=5)
        bm = document.root().bm
        lay = geom.layers(bm)
        cids = {e[lay.curve] for e in bm.edges}
        self.assertEqual(len(cids), 1)
        meta = entities.get_curve_meta(document.root(), cids.pop())
        self.assertEqual(meta["kind"], "arc")
        self.assertAlmostEqual(meta["radius"], 1.0, places=5)
        self.assertEqual([round(c, 5) for c in meta["center"]], [1.0, 0.0, 0.0])
        self.assertEqual(self.steps(), 1)

    def test_typed_chord_radius_segments(self):
        testing.click((0, 0, 0))
        testing.move((1, 0, 0))
        testing.type_text("4")                       # chord length along the cursor direction
        testing.move((2, -0.5, 0))
        testing.type_text("6s")
        self.assertTrue(base.DISPATCH.running)
        testing.type_text("2r")                      # radius 2 = half chord → semicircle below
        st = self.stats()
        self.assertEqual(st["edges"], 6)
        self.assertAlmostEqual(st["bbox"][0][1], -2.0, places=5)
        testing.type_text("1")                       # retype bulge
        self.assertAlmostEqual(self.stats()["bbox"][0][1], -1.0, places=5)
        self.assertEqual(self.steps(), 2)

    def test_arc_and_line_close_a_face(self):
        testing.click((0, 0, 0))
        testing.click((2, 0, 0))
        testing.move((1, 1, 0))
        testing.type_text("1")
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), "su.line", testing.pt(0, 0, 0))
        testing.click((0, 0, 0))
        testing.click((2, 0, 0))
        st = self.stats()
        self.assertEqual(st["faces"] - 0 >= 1, True)
        self.assertAlmostEqual(st["area"], 0.5 * 12 * math.sin(math.pi / 12), places=4)

    def test_esc(self):
        testing.click((0, 0, 0))
        testing.click((2, 0, 0))
        testing.move((1, 1, 0))
        testing.dispatch(testing.ev('ESC', 'PRESS'))
        self.assertFalse(base.DISPATCH.running)
        self.assertEqual(testing.doc_stats()["edges"], 0)


if __name__ == "__main__":
    unittest.main()
