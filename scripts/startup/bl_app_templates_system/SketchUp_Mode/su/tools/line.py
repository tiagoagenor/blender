# SPDX-License-Identifier: GPL-2.0-or-later
"""Linha (owner: A during the vertical slice → E after M-A). PLANO.md §6.2.

Click-move-click (or press-drag-release) chain of segments. Each segment = one undo step
(Document.write). Measurements: length along the rubber band direction while drawing; after the chain
ends, typing a length re-sizes the last segment ("Ajustar"). A segment that creates a face (closing a
loop or splitting a face) ends the chain; clicking the anchor point again (double click) ends it; Esc
cancels the pending segment. Inference comes from C (anchor passed for axis/linear inference).

Consumes: B document.active()/root(), geom.add_edge/auto_faces, Document.write; C via base helpers.
"""

import bpy
from mathutils import Vector

from .. import colors, constants, i18n, registry
from ..core.state import STATE, LastAction
from .base import BaseTool, Result, ToolMeta, fmt_length, kind_of, make_query, tool, value_of

TOOL_ID = "su.line"
LENGTH_KINDS = frozenset({"LENGTH", "DISTANCE", "NUMBER"})

STRINGS = {
    "tool.su.line.label": {"pt_BR": "Linha", "en": "Line"},
    "tool.su.line.hint_start": {"pt_BR": "Selecione o ponto inicial.", "en": "Select start point."},
    "tool.su.line.hint_next": {"pt_BR": "Selecione o ponto final.", "en": "Select end point."},
    "tool.su.line.undo": {"pt_BR": "Linha", "en": "Line"},
}

LINEAR_COLOR = {
    "AXIS_X": colors.AXIS_X, "AXIS_Y": colors.AXIS_Y, "AXIS_Z": colors.AXIS_Z,
}


def _document():
    document = registry.optional("core.document")
    if document is None:
        raise RuntimeError("core.document (B) not available")
    doc = document.active() if hasattr(document, "active") else None
    return doc if doc is not None else document.root()


def _point(inf):
    if inf is None or inf.kind == "NONE":
        return None
    return Vector(inf.point)


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.line.label", icon="ops.gpencil.primitive_line", shortcut="L",
               cursor='PAINT_CROSS', vcb_label_key="vcb.length", vcb_schema="length"))
class LineTool(BaseTool):

    def __init__(self):
        self.reset()

    def reset(self):
        self.anchor = None          # world point the pending segment starts at
        self.current = None         # world point under the cursor (last inference)
        self.linear = ""
        self.last_seg = None        # (doc_key, start world, end world) of the last committed segment

    # -- status --------------------------------------------------------------------------------------
    def update_status(self):
        STATE.set_hint("tool.su.line.hint_start" if self.anchor is None else "tool.su.line.hint_next")
        if self.anchor is not None and self.current is not None:
            STATE.set_vcb(self.meta.vcb_label_key, fmt_length((self.current - self.anchor).length))
        else:
            STATE.set_vcb(self.meta.vcb_label_key, STATE.vcb_value)

    def activate(self, tc):
        self.anchor = None
        self.current = None
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)

    def cancel(self, tc):
        self.anchor = None
        self.current = None
        self.linear = ""
        self.update_status()

    # -- inference -----------------------------------------------------------------------------------
    def query_ctx(self, tc, xy):
        return make_query(tc, xy, anchor=self.anchor)

    def hover(self, tc, inf):
        self.current = _point(inf)
        self.linear = inf.linear if inf is not None else ""

    def move(self, tc, ev, inf):
        p = _point(inf)
        if p is not None:
            self.current = p
            self.linear = inf.linear
        self.update_status()
        return Result.RUNNING if self.anchor is not None else Result.IDLE

    # -- clicks --------------------------------------------------------------------------------------
    def press(self, tc, ev, inf):
        p = _point(inf)
        if p is None:
            return Result.RUNNING if self.anchor is not None else Result.IDLE
        self.current = p
        if self.anchor is None:
            self.anchor = p
            self.update_status()
            return Result.RUNNING
        if (p - self.anchor).length <= constants.GEOM_TOL:
            self.cancel(tc)              # second click on the same point (double click) ends the chain
            return Result.IDLE
        return self._commit(tc, p)

    def release(self, tc, ev, inf):
        if self.anchor is None:
            return Result.IDLE
        p = _point(inf)
        if ev.is_drag_release and p is not None and (p - self.anchor).length > constants.GEOM_TOL:
            return self._commit(tc, p)   # press-drag-release draws one segment
        return Result.RUNNING

    # -- Measurements --------------------------------------------------------------------------------
    def vcb(self, tc, values):
        if self.anchor is None or not values or kind_of(values[0]) not in LENGTH_KINDS:
            return Result.PASS
        length = value_of(values[0])
        d = (self.current - self.anchor) if self.current is not None else Vector()
        if length <= 0.0 or d.length <= constants.GEOM_TOL:
            STATE.vcb_error = True
            return Result.RUNNING
        return self._commit(tc, self.anchor + d.normalized() * length)

    def _reapply(self, values):
        """Re-size the last segment (idle retype): moves its end vertex when it is a dangling end."""
        if self.last_seg is None or not values or kind_of(values[0]) not in LENGTH_KINDS:
            return False
        length = value_of(values[0])
        _key, a, b = self.last_seg
        if length <= 0.0 or (b - a).length <= constants.GEOM_TOL:
            return False
        doc = _document()
        inv = doc.world().inverted()
        old = inv @ b
        new_world = a + (b - a).normalized() * length
        vert = None
        for v in doc.bm.verts:
            if (v.co - old).length <= constants.GEOM_TOL * 10:
                vert = v
                break
        if vert is None or len(vert.link_edges) != 1 or vert.link_faces:
            return False
        vert.co = inv @ new_world
        doc.write(undo_key=None)
        self.last_seg = (_key, a, new_world)
        STATE.set_vcb(self.meta.vcb_label_key, fmt_length(length))
        return True

    # -- geometry ------------------------------------------------------------------------------------
    def _commit(self, tc, p):
        from ..core import geom
        doc = _document()
        inv = doc.world().inverted()
        a, b = inv @ self.anchor, inv @ p
        res = geom.add_edge(doc.bm, a, b)
        faces = list(getattr(res, "new_faces", None) or [])
        if not faces and hasattr(geom, "auto_faces"):
            faces = list(geom.auto_faces(doc.bm, getattr(res, "new_edges", None) or []) or [])
        doc.write(undo_key="tool.su.line.undo")
        self.last_seg = (doc.key, Vector(self.anchor), Vector(p))
        STATE.last_action = LastAction(tool_id=TOOL_ID, schema=self.meta.vcb_schema, reapply=self._reapply)
        STATE.set_vcb(self.meta.vcb_label_key, fmt_length((p - self.anchor).length))
        if faces:
            self.anchor = None           # a new face ends the chain (SketchUp)
            self.current = p
            self.update_status()
            return Result.IDLE
        self.anchor = p
        self.update_status()
        return Result.RUNNING

    # -- drawing -------------------------------------------------------------------------------------
    def draw_3d(self, dc):
        if self.anchor is None or self.current is None:
            return
        rgb = LINEAR_COLOR.get(self.linear, colors.EDGE)
        rgba = colors.rgba(rgb, 1.0)
        prims = registry.optional("draw.prims")
        if prims is not None and hasattr(prims, "line"):
            prims.line(dc, self.anchor, self.current, rgba, width=1.0)
        else:
            _fallback_line(dc, self.anchor, self.current, rgba)


def _fallback_line(dc, a, b, rgba):
    """Plain 1 pt line while D's prims.py is absent."""
    import gpu
    from gpu_extras.batch import batch_for_shader
    sh = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
    batch = batch_for_shader(sh, 'LINES', {"pos": [tuple(a), tuple(b)]})
    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.blend_set('ALPHA')
    sh.uniform_float("viewportSize", (dc.region.width, dc.region.height))
    sh.uniform_float("lineWidth", bpy.context.preferences.system.ui_line_width * 1.5)
    sh.uniform_float("color", rgba)
    batch.draw(sh)
    gpu.state.depth_test_set('NONE')
    gpu.state.blend_set('NONE')


def register():
    i18n.register_strings(STRINGS)
