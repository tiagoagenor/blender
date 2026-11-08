# SPDX-License-Identifier: GPL-2.0-or-later
"""Desenho à mão livre (owner: E; promoted from P2). SketchUp behaviour: press, drag, release.

The stroke lies on the plane of the press point: the face under it, else the horizontal plane through it.
Points are kept every few pixels (world spacing from the view; 5 cm headless); releasing near the start
closes the loop (→ a face, by B's kernel). The polyline is one curve entity (kind "freehand"). Esc while
dragging cancels. One undo step.
"""

from mathutils import Vector

from .. import colors, constants, i18n, registry
from ..core.state import STATE, Locks
from .base import BaseTool, Result, ToolMeta, make_query, tool

TOOL_ID = "su.freehand"
SPACING_PX = 6.0
SPACING_HEADLESS = 0.05

STRINGS = {
    "tool.su.freehand.label": {"pt_BR": "Desenho à mão livre", "en": "Freehand"},
    "tool.su.freehand.hint": {"pt_BR": "Clique e arraste para desenhar.", "en": "Click and drag to draw."},
    "tool.su.freehand.undo": {"pt_BR": "Desenho à mão livre", "en": "Freehand"},
}


def _document():
    return registry.optional("core.document").active()


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.freehand.label", icon="ops.gpencil.draw", cursor='PAINT_CROSS',
               priority='P1'))
class FreehandTool(BaseTool):

    def __init__(self):
        self.reset()

    def reset(self):
        self.pts = []
        self.plane = None          # (co, n)
        self.spacing = SPACING_HEADLESS

    def update_status(self):
        STATE.set_hint("tool.su.freehand.hint")
        STATE.set_vcb("", "")

    def activate(self, tc):
        self.reset()
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)

    def cancel(self, tc):
        self.reset()
        self.update_status()

    def query_ctx(self, tc, xy):
        if self.plane is None:
            return make_query(tc, xy, locks=Locks())
        return make_query(tc, xy, plane=(self.plane[0].copy(), self.plane[1].copy()), locks=Locks(),
                          flags=frozenset())

    def _on_plane(self, inf):
        if inf is None or inf.kind == "NONE":
            return None
        p = Vector(inf.point)
        co, n = self.plane
        return p - n * (p - co).dot(n)

    def press(self, tc, ev, inf):
        if inf is None or inf.kind == "NONE":
            return Result.IDLE
        p = Vector(inf.point)
        n = Vector(inf.normal).normalized() if inf.kind == "ON_FACE" and inf.normal is not None else Vector((0, 0, 1))
        self.plane = (p.copy(), n)
        self.pts = [p]
        self.spacing = SPACING_HEADLESS
        if tc is not None and tc.region is not None and tc.rv3d is not None:
            from ..core import viewutil
            k = viewutil.pixel_size_at(tc.region, tc.rv3d, p)
            if k > 0.0:
                self.spacing = k * viewutil.ui_px(SPACING_PX)
        return Result.RUNNING

    def move(self, tc, ev, inf):
        if not self.pts:
            return Result.IDLE
        q = self._on_plane(inf)
        if q is not None and (q - self.pts[-1]).length >= self.spacing:
            self.pts.append(q)
        return Result.RUNNING

    def release(self, tc, ev, inf):
        if not self.pts:
            return Result.IDLE
        q = self._on_plane(inf)
        if q is not None and (q - self.pts[-1]).length > constants.GEOM_TOL:
            self.pts.append(q)
        if len(self.pts) < 2:
            self.reset()                      # a plain click: nothing drawn
            return Result.IDLE
        return self._commit()

    def _commit(self):
        from ..core import entities, geom
        pts = self.pts
        closed = len(pts) >= 4 and (pts[-1] - pts[0]).length <= self.spacing * 2.0
        if closed:
            pts = pts[:-1]
        doc = _document()
        inv = doc.world().inverted()
        cid = entities.new_curve_id(doc)
        geom.add_polyline(doc.bm, [inv @ p for p in pts], closed, curve_id=cid)
        entities.set_curve_meta(doc, cid, {"kind": "freehand"})
        doc.write(undo_key="tool.su.freehand.undo")
        self.reset()
        self.update_status()
        return Result.IDLE

    def draw_3d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None or len(self.pts) < 2:
            return
        prims.lines(dc, list(zip(self.pts, self.pts[1:])), colors.rgba(colors.EDGE, 1.0))


def register():
    i18n.register_strings(STRINGS)
