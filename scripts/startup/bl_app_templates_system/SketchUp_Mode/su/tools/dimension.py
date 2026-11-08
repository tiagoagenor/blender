# SPDX-License-Identifier: GPL-2.0-or-later
"""Dimensões (owner: G). PLANO.md §6.3 AC-DIM-1..3; RESEARCH_SKETCHUP §6 (Dimensions).

Linear dimensions: click the start point and the end point (or click an EDGE: its two ends), pull the
dimension out perpendicular to the measured line, click to place. Text = the length in the model units
("3,00m"), drawn in screen space (always legible, draw/annotations.py). One undo step per dimension.
"""

from mathutils import Vector, geometry

from .. import colors, constants, i18n, registry
from ..core import guides, undo, viewutil
from ..core.state import STATE
from .base import BaseTool, Result, ToolMeta, fmt_length, make_query, tool

TOOL_ID = "su.dimension"

STRINGS = {
    "tool.su.dimension.label": {"pt_BR": "Dimensões", "en": "Dimensions"},
    "tool.su.dimension.hint_start": {"pt_BR": "Selecione o ponto inicial da dimensão ou uma aresta.",
                                     "en": "Select the dimension start point or an edge."},
    "tool.su.dimension.hint_end": {"pt_BR": "Selecione o ponto final da dimensão.",
                                   "en": "Select the dimension end point."},
    "tool.su.dimension.hint_place": {"pt_BR": "Mova para posicionar a dimensão e clique.",
                                     "en": "Move to place the dimension and click."},
    "tool.su.dimension.undo": {"pt_BR": "Dimensão", "en": "Dimension"},
}


def _point(inf):
    if inf is None or inf.kind == "NONE":
        return None
    return Vector(inf.point)


def edge_ends(inf):
    """World end points of the edge of an ON_EDGE inference, or None."""
    if inf is None or inf.kind != "ON_EDGE" or not inf.ref_edge:
        return None
    document = registry.optional("core.document")
    if document is None:
        return None
    doc = document.get_by_key(inf.ref_edge[0])
    if doc is None:
        return None
    try:
        me = doc.obj.data
        e = me.edges[inf.ref_edge[1]]
        m = doc.obj.matrix_world
        return m @ Vector(me.vertices[e.vertices[0]].co), m @ Vector(me.vertices[e.vertices[1]].co)
    except (IndexError, AttributeError, ReferenceError):
        return None


def perpendicular_offset(a, b, p):
    """Component of (p − a) perpendicular to a–b."""
    u = (b - a).normalized()
    v = p - a
    return v - u * v.dot(u)


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.dimension.label", icon="draw.dimension", cursor='DEFAULT',
               vcb_label_key="vcb.length", search_synonyms=("Cotas",)))
class DimensionTool(BaseTool):

    def __init__(self):
        self.reset()

    def reset(self):
        self.a = None
        self.b = None
        self.current = None
        self.offset = Vector((0.0, 0.0, 0.0))

    @property
    def stage(self):
        return 0 if self.a is None else 1 if self.b is None else 2

    def update_status(self):
        STATE.set_hint(("tool.su.dimension.hint_start", "tool.su.dimension.hint_end",
                        "tool.su.dimension.hint_place")[self.stage])
        if self.a is not None and (self.b or self.current) is not None:
            STATE.set_vcb(self.meta.vcb_label_key, fmt_length(((self.b or self.current) - self.a).length))
        else:
            STATE.set_vcb(self.meta.vcb_label_key, STATE.vcb_value)

    def activate(self, tc):
        self.reset()
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)

    def cancel(self, tc):
        self.reset()
        self.update_status()

    def query_ctx(self, tc, xy):
        return make_query(tc, xy, anchor=self.a if self.b is None else None)

    def _offset_from(self, tc, ev, inf):
        a, b = self.a, self.b
        if tc is not None and tc.region is not None and ev is not None:
            o, d = viewutil.mouse_ray(tc.region, tc.rv3d, (ev.x, ev.y))
            r = geometry.intersect_line_line(a, b, o, o + d)
            if r is not None:
                on_line, on_ray = r
                return on_ray - on_line
        p = _point(inf)
        return perpendicular_offset(a, b, p) if p is not None else self.offset

    def move(self, tc, ev, inf):
        if self.stage == 1:
            self.current = _point(inf) or self.current
        elif self.stage == 2:
            self.offset = self._offset_from(tc, ev, inf)
        self.update_status()
        return Result.RUNNING if self.a is not None else Result.IDLE

    def press(self, tc, ev, inf):
        if self.stage == 0:
            ends = edge_ends(inf)
            if ends is not None:
                self.a, self.b = ends
                self.offset = Vector((0.0, 0.0, 0.0))
            else:
                p = _point(inf)
                if p is None:
                    return Result.IDLE
                self.a = self.current = p
            self.update_status()
            return Result.RUNNING
        if self.stage == 1:
            p = _point(inf)
            if p is None or (p - self.a).length <= constants.GEOM_TOL:
                return Result.RUNNING
            self.b = p
            self.offset = Vector((0.0, 0.0, 0.0))
            self.update_status()
            return Result.RUNNING
        self.offset = self._offset_from(tc, ev, inf)
        guides.add_dimension(self.a, self.b, self.offset)
        undo.push("tool.su.dimension.undo")
        length = (self.b - self.a).length
        self.reset()
        self.update_status()
        STATE.set_vcb(self.meta.vcb_label_key, fmt_length(length))
        return Result.IDLE

    def release(self, tc, ev, inf):
        return Result.RUNNING if self.a is not None else Result.IDLE

    def draw_3d(self, dc):
        prims = registry.optional("draw.prims")
        ann = registry.optional("draw.annotations")
        if prims is None or self.a is None:
            return
        black = colors.rgba(colors.EDGE, 1.0)
        if self.b is None:
            if self.current is not None:
                prims.line(dc, self.a, self.current, black, 1.0, depth=False)
            return
        if ann is not None:
            prims.lines(dc, ann.dimension_geometry(dc, self.a, self.b, self.offset), black, 1.0, depth=False)

    def draw_2d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None or self.a is None or self.b is None:
            return
        mid = (self.a + self.b) * 0.5 + self.offset
        s = viewutil.project(dc.region, dc.rv3d, mid)
        if s is not None:
            prims.text(dc, (s.x, s.y + viewutil.ui_px(3)), fmt_length((self.b - self.a).length), 11,
                       colors.rgba(colors.EDGE, 1.0), bg=(1.0, 1.0, 1.0, 0.75), align='CENTER')


def register():
    i18n.register_strings(STRINGS)
