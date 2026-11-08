# SPDX-License-Identifier: GPL-2.0-or-later
"""Fita métrica (T) (owner: G). PLANO.md §6.3 AC-FIT-1..4; RESEARCH_SKETCHUP §6 (Tape Measure).

Click-move-click (press-drag-release also works):
  * first click ON AN EDGE (or on a guide line) → a guide line PARALLEL to it follows the cursor at the
    perpendicular offset; second click (or a typed distance + Enter) places it;
  * first click on a point/face/anywhere else → measuring tape from that point; the second click creates
    a GUIDE POINT there (with a dashed leader while measuring), a typed length puts it at that distance;
  * Option toggles guide creation ↔ measure only (tap it while measuring, or click with Option held):
    in measure mode nothing is created and Medidas keeps the length (AC-FIT-2).
Each guide = one undo step. Idle retype ("Ajustar") moves the last guide to the new distance.
"""

from mathutils import Vector

from .. import colors, constants, i18n, registry
from ..core import guides, undo
from ..core.state import STATE, LastAction
from .base import BaseTool, Result, ToolMeta, fmt_length, kind_of, make_query, tool, value_of

TOOL_ID = "su.tape"
LENGTH_KINDS = frozenset({"LENGTH", "DISTANCE", "NUMBER"})
OPTION_KEYS = frozenset({'LEFT_ALT', 'RIGHT_ALT'})

STRINGS = {
    "tool.su.tape.label": {"pt_BR": "Fita métrica", "en": "Tape Measure"},
    "tool.su.tape.hint_start": {"pt_BR": "Selecione o ponto inicial. Option = alternar criação de guia.",
                                "en": "Select start point. Option = toggle guide creation."},
    "tool.su.tape.hint_start_measure": {"pt_BR": "Selecione o ponto inicial (só medir). Option = criar guias.",
                                        "en": "Select start point (measure only). Option = create guides."},
    "tool.su.tape.hint_next": {"pt_BR": "Selecione o ponto final. Option = alternar criação de guia.",
                               "en": "Select end point. Option = toggle guide creation."},
    "tool.su.tape.hint_offset": {"pt_BR": "Mova para posicionar a linha-guia e clique, ou digite a distância.",
                                 "en": "Move to place the guide line and click, or type the distance."},
    "tool.su.tape.undo": {"pt_BR": "Guia", "en": "Guide"},
}


def _point(inf):
    if inf is None or inf.kind == "NONE":
        return None
    return Vector(inf.point)


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.tape.label", icon="draw.tape", shortcut="T",
               cursor='CROSSHAIR', vcb_label_key="vcb.length", vcb_schema="length",
               search_synonyms=("Trena",)))
class TapeTool(BaseTool):

    def __init__(self):
        self.guide_mode = True
        self.last_guide = None       # (index, kind, base, unit dir) of the last created guide
        self.reset()

    def reset(self):
        self.start = None            # first click point
        self.line_dir = None         # edge / guide direction (parallel guide mode)
        self.current = None
        self.offset = None           # parallel mode: perpendicular offset vector

    # -- status ----------------------------------------------------------------------------------
    def update_status(self):
        if self.start is None:
            STATE.set_hint("tool.su.tape.hint_start" if self.guide_mode else "tool.su.tape.hint_start_measure")
        elif self.line_dir is not None and self.guide_mode:
            STATE.set_hint("tool.su.tape.hint_offset")
        else:
            STATE.set_hint("tool.su.tape.hint_next")
        val = self.measure()
        STATE.set_vcb(self.meta.vcb_label_key, fmt_length(val) if val is not None else STATE.vcb_value)

    def measure(self):
        if self.start is None or self.current is None:
            return None
        if self.offset is not None:
            return self.offset.length
        return (self.current - self.start).length

    def activate(self, tc):
        self.reset()
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)

    def cancel(self, tc):
        self.reset()
        self.update_status()

    # -- inference ---------------------------------------------------------------------------------
    def query_ctx(self, tc, xy):
        return make_query(tc, xy, anchor=self.start)

    def hover(self, tc, inf):
        self.current = _point(inf)

    def _track(self, p):
        self.current = p
        if self.line_dir is not None:
            v = p - self.start
            self.offset = v - self.line_dir * v.dot(self.line_dir)
        self.update_status()

    def move(self, tc, ev, inf):
        p = _point(inf)
        if p is not None and self.start is not None:
            self._track(p)
        return Result.RUNNING if self.start is not None else Result.IDLE

    def key(self, tc, ev):
        if ev.type in OPTION_KEYS and ev.value == 'PRESS':
            self.guide_mode = not self.guide_mode
            self.update_status()
            return Result.RUNNING if self.start is not None else Result.IDLE
        return Result.PASS

    # -- clicks ------------------------------------------------------------------------------------
    def press(self, tc, ev, inf):
        p = _point(inf)
        if p is None:
            return Result.RUNNING if self.start is not None else Result.IDLE
        if self.start is None:
            if ev.copy:
                self.guide_mode = not self.guide_mode
            self.start = p
            self.current = p
            self.offset = None
            self.line_dir = None
            if inf.kind in ("ON_EDGE", "ON_GUIDE") and inf.direction is not None and inf.direction.length > 1e-9:
                self.line_dir = Vector(inf.direction).normalized()
                self.offset = Vector((0.0, 0.0, 0.0))
            self.update_status()
            return Result.RUNNING
        self._track(p)
        return self._commit()

    def release(self, tc, ev, inf):
        if self.start is None:
            return Result.IDLE
        p = _point(inf)
        if ev.is_drag_release and p is not None and (p - self.start).length > constants.GEOM_TOL:
            self._track(p)
            return self._commit()
        return Result.RUNNING

    def vcb(self, tc, values):
        if self.start is None or not values or kind_of(values[0]) not in LENGTH_KINDS:
            return Result.PASS
        L = value_of(values[0])
        if self.line_dir is not None:
            if self.offset is None or self.offset.length <= constants.GEOM_TOL:
                STATE.vcb_error = True
                return Result.RUNNING
            self.offset = self.offset.normalized() * L
            self.current = self.start + self.offset
        else:
            d = (self.current - self.start) if self.current is not None else Vector()
            if d.length <= constants.GEOM_TOL:
                STATE.vcb_error = True
                return Result.RUNNING
            self.current = self.start + d.normalized() * L
        return self._commit()

    # -- results -----------------------------------------------------------------------------------
    def _commit(self):
        length = self.measure() or 0.0
        STATE.set_vcb(self.meta.vcb_label_key, fmt_length(length))
        made = None
        if self.guide_mode and length > constants.GEOM_TOL:
            if self.line_dir is not None:
                i = guides.add_guide_line(self.start + self.offset, self.line_dir)
                made = (i, 'LINE', Vector(self.start), self.offset.normalized())
            else:
                i = guides.add_guide_point(self.current, self.start)
                made = (i, 'POINT', Vector(self.start), (self.current - self.start).normalized())
            undo.push("tool.su.tape.undo")
            self.last_guide = made
            STATE.last_action = LastAction(tool_id=TOOL_ID, schema=self.meta.vcb_schema, reapply=self._reapply)
        self.reset()
        self.update_status()
        STATE.set_vcb(self.meta.vcb_label_key, fmt_length(length))
        return Result.IDLE

    def _reapply(self, values):
        """Idle retype: the last guide moves to the typed distance from its base."""
        if self.last_guide is None or not values or kind_of(values[0]) not in LENGTH_KINDS:
            return False
        i, kind, base, u = self.last_guide
        d = guides.data()
        if d is None or i >= len(d.guides) or d.guides[i].kind != kind:
            return False
        L = value_of(values[0])
        d.guides[i].co = base + u * L
        STATE.set_vcb(self.meta.vcb_label_key, fmt_length(L))
        STATE.redraw_viewport()
        return True

    # -- drawing -----------------------------------------------------------------------------------
    def draw_3d(self, dc):
        if self.start is None or self.current is None:
            return
        prims = registry.optional("draw.prims")
        if prims is None:
            return
        black = colors.rgba(colors.GUIDE, 1.0)
        if self.line_dir is not None and self.offset is not None:
            base = self.start + self.offset
            ann = registry.optional("draw.annotations")
            seg = ann.clip_line(dc, base, self.line_dir) if ann is not None else None
            if seg is not None and self.guide_mode:
                prims.dashed(dc, seg[0], seg[1], black, 1.0, 6, 4)
            prims.line(dc, self.start, base, black, 1.0, depth=False)
        else:
            prims.dashed(dc, self.start, self.current, black, 1.0, 6, 4)
            if self.guide_mode:
                prims.points(dc, [self.current], black, 7, 'CROSS', outline=False)


def register():
    i18n.register_strings(STRINGS)
