# SPDX-License-Identifier: GPL-2.0-or-later
"""F tests: Selecionar through testing.dispatch (AC-SEL-1..4 headless: picks come from the inference
element) and Excluir (ROTEIRO_CASA AF-1, AF-2, AF-5, AF-6; AC-APG kernel part is B's)."""

import unittest

import bpy
from mathutils import Vector as V

from su import perf, testing
from su.core import document, edit_context, geom, materials, selection, state
from su.core.selection import EDGE, FACE, OBJECT, Ref
from su.ops import edit_ops
from su.tools import base

from test_b_document import _fresh_root
from test_b_geom import box, counts, find_edge, find_face, rect

SELECT = "su.select"


def drop_groups():
    for obj in [o for o in bpy.data.objects if o.type == 'MESH' and o.su_doc.kind != document.KIND_MODEL]:
        me = obj.data
        bpy.data.objects.remove(obj)
        if me.users == 0:
            bpy.data.meshes.remove(me)
    document.invalidate_all()


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


class FCase(unittest.TestCase):
    """Root document with a fresh 8×6×3 box; Selecionar active; injectable clock."""
    TOOL = SELECT
    BOX = True

    def setUp(self):
        self.n_err = perf.errors()
        edit_context.exit_all()
        drop_groups()
        self.doc = _fresh_root()
        selection.clear()
        if self.BOX:
            box(self.doc.bm)
        self.doc.write(undo_key=None)
        self.key = self.doc.key
        self.clock = Clock()
        testing.set_clock(self.clock)
        base.DISPATCH.reset()
        state.STATE.reset()
        testing.dispatch(testing.ev('MOUSEMOVE', 'NOTHING'), self.TOOL, state.Inference.none())

    def tearDown(self):
        testing.set_clock(None)
        base.DISPATCH.set_tool(base.ToolContext(), '')
        edit_context.exit_all()
        selection.clear()
        self.assertEqual(perf.errors(), self.n_err, perf.messages()[self.n_err:])

    # -- helpers ----------------------------------------------------------------------------------
    def face(self, center, doc=None):
        return find_face((doc or self.doc).bm, center).index

    def edge(self, a, b, doc=None):
        return find_edge((doc or self.doc).bm, a, b).index

    def inf_face(self, idx, key=None, point=(0, 0, 0)):
        return testing.pt(*point, kind="ON_FACE", elem=("FACE", idx), doc_key=key or self.key)

    def inf_edge(self, idx, key=None, point=(0, 0, 0)):
        return testing.pt(*point, kind="ON_EDGE", elem=("EDGE", idx), doc_key=key or self.key)

    def click(self, inf, wait=1.0, **mods):
        self.clock.t += wait
        testing.dispatch(testing.ev('LEFTMOUSE', 'PRESS', **mods), None, inf)
        self.clock.t += 0.05
        return testing.dispatch(testing.ev('LEFTMOUSE', 'RELEASE', **mods), None, inf)

    def multi(self, inf, n, **mods):
        self.click(inf, 1.0, **mods)
        for _ in range(n - 1):
            self.click(inf, 0.1, **mods)

    def kinds(self):
        refs = selection.get()
        return sum(r.kind == FACE for r in refs), sum(r.kind == EDGE for r in refs), \
            sum(r.kind == OBJECT for r in refs)


class TestSelect(FCase):
    def test_hint_mentions_option(self):
        d = testing.state_dump()
        self.assertEqual(d["tool"], SELECT)
        self.assertIn("Option", d["hint"])
        self.assertNotIn("Ctrl", d["hint"])

    def test_ac_sel_1_one_two_three_clicks(self):
        top = self.inf_face(self.face((4, 3, 3)))
        self.click(top)
        self.assertEqual(self.kinds(), (1, 0, 0))
        self.multi(top, 2)
        self.assertEqual(self.kinds(), (1, 4, 0))
        self.multi(top, 3)
        self.assertEqual(self.kinds(), (6, 12, 0))

    def test_click_edge_and_double_click_edge(self):
        e = self.inf_edge(self.edge((0, 0, 3), (8, 0, 3)))
        self.click(e)
        self.assertEqual(self.kinds(), (0, 1, 0))
        self.multi(e, 2)
        self.assertEqual(self.kinds(), (2, 1, 0))

    def test_modifiers_option_shift(self):
        top = self.inf_face(self.face((4, 3, 3)))
        front = self.inf_face(self.face((4, 0, 1.5)))
        self.click(top)
        self.click(front, copy=True)                 # Option = add
        self.assertEqual(self.kinds(), (2, 0, 0))
        self.click(front, shift=True)                # Shift = toggle (off)
        self.assertEqual(self.kinds(), (1, 0, 0))
        self.click(front, shift=True)                # Shift = toggle (on)
        self.assertEqual(self.kinds(), (2, 0, 0))
        self.click(top, shift=True, copy=True)       # Shift+Option = subtract
        self.assertEqual(selection.get(), {Ref(self.key, FACE, self.face((4, 0, 1.5)))})

    def test_click_empty_clears(self):
        self.click(self.inf_face(self.face((4, 3, 3))))
        self.click(state.Inference.none())
        self.assertTrue(selection.is_empty())
        self.click(self.inf_face(self.face((4, 3, 3))))
        self.click(state.Inference.none(), shift=True)     # modifier + empty: unchanged
        self.assertEqual(self.kinds(), (1, 0, 0))

    def test_ac_sel_2_curve(self):
        bm = self.doc.bm
        bm.clear()
        pts = geom.circle_points(V((0, 0, 0)), V((0, 0, 1)), 1.0, 24)
        geom.add_polyline(bm, pts, True, curve_id=7)
        self.doc.write(undo_key=None)
        e = next(e for e in self.doc.bm.edges)
        self.click(self.inf_edge(e.index))
        self.assertEqual(self.kinds(), (0, 24, 0))

    def test_ac_sel_3_surface(self):
        bm = self.doc.bm
        bm.clear()
        lay = geom.ensure_layers(bm)
        vs = [bm.verts.new(c) for c in ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (1, 0, 1), (1, 1, 1))]
        f1 = bm.faces.new((vs[0], vs[1], vs[2], vs[3]))
        bm.faces.new((vs[1], vs[4], vs[5], vs[2]))
        bm.edges.get((vs[1], vs[2]))[lay.soft] = True
        self.doc.write(undo_key=None)
        self.click(self.inf_face(0))
        self.assertEqual(self.kinds(), (2, 0, 0))

    def test_ac_sel_4_group_context(self):
        bm = self.doc.bm
        top = self.face((4, 3, 3))
        g = document.group_from(self.doc, [top], [])
        g.write(undo_key=None)
        self.doc.write(undo_key=None)
        gface = self.inf_face(0, key=g.key)
        self.click(gface)
        self.assertEqual(selection.get(), {Ref(g.key, OBJECT, 0)})
        self.multi(gface, 2)                              # double click enters the group
        self.assertEqual([o.name for o in edit_context.stack()], [g.key])
        self.assertTrue(selection.is_empty())
        self.click(gface)
        self.assertEqual(self.kinds(), (1, 0, 0))
        self.click(self.inf_face(self.face((4, 0, 1.5))))  # outside geometry: not selectable
        self.assertTrue(selection.is_empty())
        edit_ops.escape()                               # nothing selected → leaves the group
        self.assertEqual(edit_context.stack(), [])

    def test_escape_clears_selection_first(self):
        self.click(self.inf_face(self.face((4, 3, 3))))
        edit_ops.escape()
        self.assertTrue(selection.is_empty())

    def test_select_all_none_invert(self):
        bpy.ops.su.select_all()
        self.assertEqual(self.kinds(), (6, 12, 0))
        bpy.ops.su.select_none()
        self.assertTrue(selection.is_empty())
        self.click(self.inf_face(self.face((4, 3, 3))))
        bpy.ops.su.select_invert()
        self.assertEqual(self.kinds(), (5, 12, 0))

    def test_materials_slots_on_root(self):
        mats = self.doc.obj.data.materials
        self.assertGreaterEqual(len(mats), 2)
        self.assertEqual(mats[0].name, materials.MAT_FRONT)
        self.assertEqual(mats[1].name, materials.MAT_BACK)


class TestDelete(FCase):
    BOX = False

    def stats(self):
        return counts(self.doc.bm)

    def test_af1_rectangle_face(self):
        rect(self.doc.bm, 0, 0, 8, 6)
        self.doc.write(undo_key=None)
        self.click(self.inf_face(0))
        bpy.ops.su.delete_selected()
        self.assertEqual(self.stats(), (4, 4, 0))
        self.assertTrue(selection.is_empty())

    def test_af2_top_only(self):
        box(self.doc.bm)
        self.doc.write(undo_key=None)
        self.click(self.inf_face(self.face((4, 3, 3))))
        s0 = bpy.context.scene.su_undo_serial
        bpy.ops.su.delete_selected()
        self.assertEqual(self.stats(), (8, 12, 5))
        self.assertEqual(bpy.context.scene.su_undo_serial - s0, 1)
        self.assertEqual(geom.validate(self.doc.bm), [])

    def test_af5_double_click_top_then_delete(self):
        box(self.doc.bm)
        self.doc.write(undo_key=None)
        self.multi(self.inf_face(self.face((4, 3, 3))), 2)
        edit_ops.delete_selection()
        self.assertEqual(self.stats(), (8, 8, 1))

    def test_af6_undo_restores_counts_and_selection(self):
        box(self.doc.bm)
        self.doc.write(undo_key=None)
        bpy.ops.ed.undo_push(message="base")
        top = self.face((4, 3, 3))
        self.click(self.inf_face(top))
        before = selection.get()
        bpy.ops.su.delete_selected()
        self.assertEqual(self.stats(), (8, 12, 5))
        bpy.ops.ed.undo()
        self.assertEqual(counts(document.root().bm), (8, 12, 6))
        self.assertEqual(selection.get(), before)
        bpy.ops.ed.redo()
        self.assertEqual(counts(document.root().bm), (8, 12, 5))
        self.assertTrue(selection.is_empty())

    def test_delete_group_object(self):
        box(self.doc.bm)
        self.doc.write(undo_key=None)
        g = document.group_from(self.doc, [self.face((4, 3, 3))], [])
        g.write(undo_key=None)
        self.doc.write(undo_key=None)
        name = g.key
        self.click(self.inf_face(0, key=name))
        bpy.ops.su.delete_selected()
        self.assertIsNone(bpy.data.objects.get(name))
        self.assertTrue(selection.is_empty())

    def test_nothing_selected_no_undo_step(self):
        s0 = bpy.context.scene.su_undo_serial
        bpy.ops.su.delete_selected()
        self.assertEqual(bpy.context.scene.su_undo_serial, s0)


if __name__ == "__main__":
    unittest.main()
