# SPDX-License-Identifier: GPL-2.0-or-later
"""Mover (owner: F). PLANO.md §6.1 (AC-MOV-1..10), §3.8.

With a selection: click anywhere (start point, inferred) → move → click (or press-drag-release) →
the selection moves and stays selected. Without a selection: hovering highlights the entity under
the cursor (endpoint → that vertex, edge/curve, face/surface, group) and the click grabs it.
Option toggles copy (also during the move); the copy becomes the selection. Medidas: a distance
along the current direction while moving or after it ("Ajustar"), `5x` (5 copies) / `/5` (4 copies
between) after a copy. Vertex/edge moves fold faces that bend (dobra automática); a face move
rejects only positions that would bend a face (shear allowed). Groups move by matrix.
"""

import bpy
from mathutils import Matrix, Vector

from .. import colors, constants, i18n, modifiers, registry
from ..core.state import STATE, LastAction, Locks
from . import select as sel_tool
from .base import BaseTool, Result, ToolMeta, fmt_length, kind_of, make_query, tool, value_of

TOOL_ID = "su.move"

STRINGS = {
    "tool.su.move.label": {"pt_BR": "Mover", "en": "Move"},
    "tool.su.move.hint_pick": {
        "pt_BR": "Selecione os objetos a mover. {opt} = Alternar cópia.",
        "en": "Select objects to move. {opt} = Toggle copy."},
    "tool.su.move.hint_dest": {
        "pt_BR": "Selecione o ponto de destino. {opt} = Alternar cópia.",
        "en": "Select destination point. {opt} = Toggle copy."},
    "tool.su.move.undo": {"pt_BR": "Mover", "en": "Move"},
    "tool.su.move.undo_copy": {"pt_BR": "Copiar", "en": "Copy"},
}

LINEAR_COLOR = {"AXIS_X": colors.AXIS_X, "AXIS_Y": colors.AXIS_Y, "AXIS_Z": colors.AXIS_Z}
AXIS_DIRS = {"AXIS_X": Vector((1, 0, 0)), "AXIS_Y": Vector((0, 1, 0)), "AXIS_Z": Vector((0, 0, 1))}


def _mods():
    from ..core import document, geom_transform, selection
    return document, geom_transform, selection


def hover_target(tc, xy, inf):
    """(refs, verts) the Move tool grabs under the cursor without a selection: endpoint → the vertex
    ({doc_key: {vi}}), else the entity (edge/curve, face/surface, group)."""
    document, gt, selection = _mods()
    if inf is not None and inf.kind == "ENDPOINT" and inf.elem and inf.elem[0] == "VERT" and inf.doc_key:
        ref = sel_tool.resolve(inf.doc_key, 'EDGE', 0)
        if ref is not None and ref.kind != selection.OBJECT:
            return [], {inf.doc_key: {int(inf.elem[1])}}
        if ref is not None:
            return [ref], {}
    p = sel_tool.pick(tc, xy, inf)
    if p is None:
        return [], {}
    ref = sel_tool.resolve(*p)
    if ref is None:
        return [], {}
    return sel_tool.entity_refs(ref), {}


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.move.label", icon="ops.transform.translate", shortcut="M",
               cursor='SCROLL_XY', vcb_label_key="vcb.distance", vcb_schema="distance"))
class MoveTool(BaseTool):

    def __init__(self):
        self.session = None
        self.start = None
        self.current = None
        self.linear = ""
        self.copy = False
        self.targets = ([], {})
        self.hover_refs = ([], {})
        self.last = None             # finished session (for Ajustar / arrays)
        self.last_vec = None

    # -- status ------------------------------------------------------------------------------------
    def update_status(self):
        opt = modifiers.label("copy")
        STATE.set_hint("tool.su.move.hint_pick" if self.session is None else "tool.su.move.hint_dest", opt=opt)
        if self.session is not None and self.current is not None:
            STATE.set_vcb(self.meta.vcb_label_key, fmt_length((self.current - self.start).length))
        else:
            STATE.set_vcb(self.meta.vcb_label_key, STATE.vcb_value)

    def activate(self, tc):
        self.session = None
        self.hover_refs = ([], {})
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)

    def cancel(self, tc):
        if self.session is not None:
            self.session.cancel()
        self.session = None
        self.start = self.current = None
        self.linear = ""
        self.update_status()

    # -- inference -----------------------------------------------------------------------------------
    def query_ctx(self, tc, xy):
        if self.session is None:
            return make_query(tc, xy)
        return make_query(tc, xy, anchor=self.start, exclude=self.session.exclude,
                          skip=self.session.moving_faces)

    def hover(self, tc, inf):
        _d, _g, selection = _mods()
        if selection.is_empty():
            self.hover_refs = hover_target(tc, tc.xy, inf)
        else:
            self.hover_refs = ([], {})

    # -- session -------------------------------------------------------------------------------------
    def _targets(self, tc, ev, inf):
        _d, _g, selection = _mods()
        if not selection.is_empty():
            return list(selection.get()), {}
        return hover_target(tc, (ev.x, ev.y), inf)

    def _fold_of(self, refs, verts):
        _d, _g, selection = _mods()
        if verts:
            return 'AUTO'
        return 'RESTRICT' if any(r.kind == selection.FACE for r in refs) else 'AUTO'

    def _start(self, refs, verts, copy):
        _d, gt, _s = _mods()
        self.session = gt.TransformSession(refs, copy=copy, fold=self._fold_of(refs, verts), verts=verts)
        self.copy = copy

    def press(self, tc, ev, inf):
        p = Vector(inf.point) if inf is not None and inf.kind != "NONE" else None
        if self.session is None:
            if p is None:
                return Result.IDLE
            refs, verts = self._targets(tc, ev, inf)
            if not refs and not verts:
                return Result.IDLE
            self.targets = (refs, verts)
            self._start(refs, verts, ev.copy)
            if self.session.is_empty():
                self.session.cancel()
                self.session = None
                return Result.IDLE
            self.start = p
            self.current = p
            self.hover_refs = ([], {})
            self.update_status()
            return Result.RUNNING
        if p is None:
            return Result.RUNNING
        return self._finish(p)

    def release(self, tc, ev, inf):
        if self.session is None:
            return Result.IDLE
        p = Vector(inf.point) if inf is not None and inf.kind != "NONE" else None
        if ev.is_drag_release and p is not None and (p - self.start).length > constants.GEOM_TOL:
            return self._finish(p)
        return Result.RUNNING

    def move(self, tc, ev, inf):
        if self.session is None:
            return Result.IDLE
        if inf is not None and inf.kind != "NONE":
            self.current = Vector(inf.point)
            self.linear = inf.linear
            self.session.set_matrix(Matrix.Translation(self.current - self.start))
        self.update_status()
        return Result.RUNNING

    def key(self, tc, ev):
        if ev.type in {'LEFT_ALT', 'RIGHT_ALT'} and ev.value == 'PRESS' and self.session is not None:
            m = self.session.matrix.copy()
            self.session.cancel()
            refs, verts = self.targets
            self._start(refs, verts, not self.copy)
            self.session.set_matrix(m)
            STATE.redraw_viewport(tc.region)
            return Result.RUNNING
        return Result.PASS

    def vcb(self, tc, values):
        if not values:
            return Result.PASS
        v = values[0]
        if self.session is None:
            return Result.PASS
        if kind_of(v) in {"POINT_ABS", "POINT_REL"} and getattr(v, "vector", None) is not None:
            a = self.start
            if kind_of(v) == "POINT_ABS":
                p = Vector([a[i] if c is None else c for i, c in enumerate(v.vector)])
            else:
                p = Vector([a[i] + (c or 0.0) for i, c in enumerate(v.vector)])
            return self._finish(p)
        if kind_of(v) not in {"LENGTH", "NUMBER", "DISTANCE"}:
            return Result.PASS
        d = (self.current - self.start) if self.current is not None else Vector()
        if d.length <= constants.GEOM_TOL and STATE.locks.axis in AXIS_DIRS:
            d = AXIS_DIRS[STATE.locks.axis].copy()      # arrow-locked axis, mouse not moved yet
        if d.length <= constants.GEOM_TOL:
            STATE.vcb_error = True
            return Result.RUNNING
        return self._finish(self.start + d.normalized() * value_of(v))

    # -- commit --------------------------------------------------------------------------------------
    def _finish(self, p):
        s = self.session
        vec = p - self.start
        s.set_matrix(Matrix.Translation(vec))
        if s.fold == 'RESTRICT':
            vec = s.matrix.to_translation()
        s.finish("tool.su.move.undo_copy" if self.copy else "tool.su.move.undo")
        self.last, self.last_vec = s, vec.copy()
        STATE.last_action = LastAction(tool_id=TOOL_ID, schema=self.meta.vcb_schema, reapply=self._reapply)
        STATE.locks = Locks()                 # arrow/Shift locks end with the operation
        STATE.set_vcb(self.meta.vcb_label_key, fmt_length(vec.length))
        self.session = None
        self.start = self.current = None
        self.update_status()
        return Result.IDLE

    def _reapply(self, values):
        s, vec = self.last, self.last_vec
        if s is None or vec is None or not values:
            return False
        v = values[0]
        k = kind_of(v)
        if k in {"MULTIPLY", "DIVIDE"} and s.copy:
            n = v.count
            if not n or n < 1:
                return False
            return s.array(n, k == "DIVIDE", lambda t: Matrix.Translation(vec * t))
        if k in {"LENGTH", "NUMBER", "DISTANCE"} and vec.length > constants.GEOM_TOL:
            new = vec.normalized() * value_of(v)
            if s.copy:
                ok = s.array(1, False, lambda t: Matrix.Translation(new * t))
            else:
                s.reapply_matrix(Matrix.Translation(new))
                ok = True
            if ok:
                self.last_vec = new
                STATE.set_vcb(self.meta.vcb_label_key, fmt_length(new.length))
            return ok
        return False

    # -- drawing -------------------------------------------------------------------------------------
    def draw_3d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None:
            return
        if self.session is not None and self.start is not None and self.current is not None:
            rgb = LINEAR_COLOR.get(self.linear, colors.EDGE)
            prims.dashed(dc, self.start, self.current, colors.rgba(rgb), 1.0)
            return
        refs, verts = self.hover_refs
        blue = colors.rgba(colors.SELECTION)
        segs = []
        for r in refs:
            obj = bpy.data.objects.get(r.doc_key)
            if obj is None or obj.type != 'MESH':
                continue
            me, M = obj.data, obj.matrix_world
            if r.kind == 'EDGE' and r.index < len(me.edges):
                a, b = me.edges[r.index].vertices
                segs.append((M @ me.vertices[a].co, M @ me.vertices[b].co))
            elif r.kind == 'FACE' and r.index < len(me.polygons):
                prims.polygon(dc, [M @ me.vertices[i].co for i in me.polygons[r.index].vertices], blue, stipple=True)
            elif r.kind == 'OBJECT':
                bb = [Vector(c) for c in obj.bound_box]
                mn = Vector((min(c.x for c in bb), min(c.y for c in bb), min(c.z for c in bb)))
                mx = Vector((max(c.x for c in bb), max(c.y for c in bb), max(c.z for c in bb)))
                prims.box(dc, mn, mx, M, blue)
        if segs:
            prims.lines(dc, segs, blue, 1.0, depth=True)
        for key, vs in verts.items():
            obj = bpy.data.objects.get(key)
            if obj is not None:
                pts = [obj.matrix_world @ obj.data.vertices[i].co for i in vs if i < len(obj.data.vertices)]
                prims.points(dc, pts, blue, 6)


def register():
    i18n.register_strings(STRINGS)
