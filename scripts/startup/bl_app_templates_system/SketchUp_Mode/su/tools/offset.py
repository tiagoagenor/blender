# SPDX-License-Identifier: GPL-2.0-or-later
"""Equidistância (owner: E). PLANO.md §6.2 (AC-EQD-1..3), ROTEIRO_CASA passo 10 e B2.

Hover a face (blue stipple), click it and move: the offset copy of its boundary follows the cursor (the
loops pass at the cursor's distance from the boundary: inside = shrink, outside = grow); click, or type
the distance + Enter ("Distância"; the sign follows the current side, negative reverses; with no movement
a positive value goes inside). The new loops are edges added through B's kernel, which splits the face
(ring + inner face; a hole grows into the material). Double click on a face repeats the last distance.
Idle retype re-applies the last offset ("Ajustar"). One undo step per offset. Surfaces are refused.
"""

from mathutils import Vector

from .. import colors, constants, i18n, registry
from ..core.state import STATE, LastAction, Locks
from .base import BaseTool, Result, ToolMeta, fmt_length, kind_of, make_query, tool, value_of
from .pushpull import _face_target

TOOL_ID = "su.offset"
LENGTH_KINDS = frozenset({"LENGTH", "DISTANCE", "NUMBER"})

STRINGS = {
    "tool.su.offset.label": {"pt_BR": "Equidistância", "en": "Offset"},
    "tool.su.offset.hint_start": {"pt_BR": "Selecione a face para criar a equidistância.",
                                  "en": "Select a face to offset."},
    "tool.su.offset.hint_next": {"pt_BR": "Mova para definir a distância ou digite-a.",
                                 "en": "Move to set the distance or enter it."},
    "tool.su.offset.undo": {"pt_BR": "Equidistância", "en": "Offset"},
}


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.offset.label", icon="ops.mesh.inset", shortcut="F",
               cursor='CROSSHAIR', vcb_label_key="vcb.distance", vcb_schema="length"))
class OffsetTool(BaseTool):

    def __init__(self):
        self.last = None
        self.last_distance = None
        self.reset()

    def reset(self):
        self.doc = None
        self.face_idx = None
        self.n = None              # world normal of the face
        self.loops = None          # world loops (material on the left)
        self.distance = 0.0
        self.preview = None        # world offset loops
        self.hover_key = None
        self.hover_polys = []

    # -- status --------------------------------------------------------------------------------------
    def update_status(self):
        STATE.set_hint("tool.su.offset.hint_start" if self.doc is None else "tool.su.offset.hint_next")
        if self.doc is not None:
            STATE.set_vcb(self.meta.vcb_label_key, fmt_length(self.distance))
        else:
            STATE.set_vcb(self.meta.vcb_label_key, STATE.vcb_value)

    def activate(self, tc):
        self.reset()
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)
        self._drop_last()

    def cancel(self, tc):
        self.reset()
        self.update_status()

    def _drop_last(self):
        if self.last is not None:
            from ..core import geom_extrude
            geom_extrude.release(self.last["snap"])
            self.last = None

    # -- hover ---------------------------------------------------------------------------------------
    def _highlight(self, inf):
        doc, idx = _face_target(inf)
        if doc is None:
            self.hover_key, self.hover_polys = None, []
            return None, None
        from ..core import entities
        bm = doc.bm
        bm.faces.ensure_lookup_table()
        kind, ids = entities.pick_entity(bm, 'FACE', idx)
        if kind == 'SURFACE':
            self.hover_key, self.hover_polys = None, []
            return None, None
        key = (doc.key, idx, doc.version)
        if key != self.hover_key:
            mw = doc.world()
            self.hover_polys = [[mw @ v.co for v in bm.faces[i].verts] for i in ids]
            self.hover_key = key
        return doc, idx

    def hover(self, tc, inf):
        self._highlight(inf)

    def query_ctx(self, tc, xy):
        if self.doc is None:
            return make_query(tc, xy, locks=Locks())
        return make_query(tc, xy, plane=(self.loops[0][0].copy(), self.n.copy()), locks=Locks())

    # -- operation -----------------------------------------------------------------------------------
    def _start(self, inf):
        doc, idx = self._highlight(inf)
        if doc is None:
            return False
        from ..core import geom_extrude
        n, loops = geom_extrude.face_loops(doc.bm, idx)
        mw = doc.world()
        self.n = (mw.to_3x3().inverted().transposed() @ n).normalized()
        self.loops = [[mw @ p for p in loop] for loop in loops]
        self.doc, self.face_idx = doc, idx
        self.distance = 0.0
        self.preview = None
        return True

    def _set(self, d):
        from ..core import geom_extrude
        self.distance = d
        self.preview = None
        if abs(d) > constants.GEOM_TOL:
            self.preview = [geom_extrude.offset_loop(loop, self.n, d) for loop in self.loops]
            if any(p is None for p in self.preview):
                self.preview = None

    def _track(self, inf):
        if inf is None or inf.kind == "NONE":
            return
        from ..core import geom_extrude
        p = Vector(inf.point)
        p = p - self.n * (p - self.loops[0][0]).dot(self.n)
        self._set(geom_extrude.boundary_distance(self.loops, self.n, p))

    def move(self, tc, ev, inf):
        if self.doc is None:
            self._highlight(inf)
            return Result.IDLE
        self._track(inf)
        self.update_status()
        return Result.RUNNING

    def press(self, tc, ev, inf):
        if self.doc is None:
            if not self._start(inf):
                return Result.IDLE
            self.update_status()
            return Result.RUNNING
        if ev.clicks >= 2 and self.last_distance is not None and self.preview is None:
            return self._commit(self.last_distance)
        self._track(inf)
        if self.preview is None:
            return Result.RUNNING
        return self._commit(self.distance)

    def release(self, tc, ev, inf):
        if self.doc is None:
            return Result.IDLE
        if ev.is_drag_release:
            self._track(inf)
            if self.preview is not None:
                return self._commit(self.distance)
        return Result.RUNNING

    def vcb(self, tc, values):
        if self.doc is None:
            return Result.PASS
        if not values or values[0] is None or kind_of(values[0]) not in LENGTH_KINDS:
            STATE.vcb_error = True
            return Result.RUNNING
        v = value_of(values[0])
        d = v * (-1.0 if self.distance < -constants.GEOM_TOL else 1.0)
        return self._commit(d)

    def _reapply(self, values):
        last = self.last
        if last is None or not values or values[0] is None or kind_of(values[0]) not in LENGTH_KINDS:
            return False
        from ..core import geom_extrude
        document = registry.optional("core.document")
        doc = document.active()
        if doc.key != last["doc_key"]:
            return False
        d = value_of(values[0]) * (-1.0 if last["distance"] < 0 else 1.0)
        geom_extrude.restore(doc, last["snap"])
        if geom_extrude.offset_faces(doc.bm, last["face_idx"], d / last["k"]) is None:
            doc.invalidate()             # back to the written mesh (the last offset)
            return False
        doc.write(undo_key=None)
        last["distance"] = d
        self.last_distance = d
        STATE.set_vcb(self.meta.vcb_label_key, fmt_length(abs(d)))
        return True

    def _commit(self, d):
        from ..core import geom_extrude
        doc = self.doc
        sc = doc.world().to_scale()
        k = ((abs(sc.x) + abs(sc.y) + abs(sc.z)) / 3.0) or 1.0
        snap = geom_extrude.snapshot(doc)
        res = geom_extrude.offset_faces(doc.bm, self.face_idx, d / k)
        if res is None:
            geom_extrude.release(snap)
            STATE.vcb_error = True
            return Result.RUNNING
        doc.write(undo_key="tool.su.offset.undo")
        self._drop_last()
        self.last = {"doc_key": doc.key, "face_idx": self.face_idx, "distance": d, "snap": snap, "k": k}
        self.last_distance = d
        STATE.last_action = LastAction(tool_id=TOOL_ID, schema=self.meta.vcb_schema, reapply=self._reapply)
        self.reset()
        self.update_status()
        STATE.set_vcb(self.meta.vcb_label_key, fmt_length(abs(d)))
        return Result.IDLE

    # -- drawing -------------------------------------------------------------------------------------
    def draw_3d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None:
            return
        if self.doc is None:
            for poly in self.hover_polys:
                prims.polygon(dc, poly, colors.rgba(colors.SELECTION, 0.55), stipple=True)
            return
        if self.preview:
            rgba = colors.rgba(colors.EDGE, 1.0)
            for loop in self.preview:
                k = len(loop)
                prims.lines(dc, [(loop[i], loop[(i + 1) % k]) for i in range(k)], rgba)


def register():
    i18n.register_strings(STRINGS)
