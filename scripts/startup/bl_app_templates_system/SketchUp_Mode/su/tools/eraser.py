# SPDX-License-Identifier: GPL-2.0-or-later
"""Apagar (owner: F). PLANO.md §6.1 (AC-APG-1..4), ROTEIRO_CASA "Apagar uma face".

Click an edge (or drag over several: they are marked blue and erased on release, 1 undo step):
the edge ENTITY goes (a curve goes whole), faces bounded by it go too, two coplanar faces
separated by it merge (geom.erase_edges). A group hit (edge or face) → the group goes. Faces
are never erased by the Eraser. Shift = hide instead (su_hidden), Option = soften (su_soft +
smooth shading), Shift+Option = unsoften.
"""

import bpy

from .. import colors, i18n, modifiers, registry
from ..core.state import STATE
from . import select as sel_tool
from .base import BaseTool, Result, ToolMeta, tool

TOOL_ID = "su.eraser"

STRINGS = {
    "tool.su.eraser.label": {"pt_BR": "Apagar", "en": "Eraser"},
    "tool.su.eraser.hint": {
        "pt_BR": "Selecione os objetos para apagar. Shift = Ocultar. {opt} = Suavizar. Shift + {opt} = Não suavizar.",
        "en": "Select objects to erase. Shift = Hide. {opt} = Soften. Shift + {opt} = Unsoften."},
    "tool.su.eraser.undo": {"pt_BR": "Apagar", "en": "Erase"},
}


def mode_of(ev):
    if ev.shift and ev.copy:
        return 'UNSOFTEN'
    if ev.shift:
        return 'HIDE'
    if ev.copy:
        return 'SOFTEN'
    return 'ERASE'


def _target(tc, xy, inf):
    """Ref list (edge entity or [OBJECT ref]) under the cursor, or []."""
    p = sel_tool.pick(tc, xy, inf)
    if p is None:
        return []
    ref = sel_tool.resolve(*p)
    if ref is None or ref.kind == 'FACE':
        return []
    return sel_tool.entity_refs(ref)


def soften(bm, edges, on):
    """Soft edges + smooth shading across them (faces next to soft edges are smooth; their other,
    non-soft edges stay sharp)."""
    from ..core import geom
    lay = geom.ensure_layers(bm)
    faces = set()
    for e in edges:
        e[lay.soft] = on
        e.smooth = on
        faces.update(e.link_faces)
    for f in faces:
        f.smooth = any(x[lay.soft] for x in f.edges)
        for x in f.edges:
            if not x[lay.soft] and not x[lay.bridge]:
                x.smooth = False


def apply(refs, mode, undo_key="tool.su.eraser.undo"):
    """Erase / hide / soften the refs (edges and OBJECT refs). Returns True when something changed."""
    from ..core import document, geom
    from ..ops import edit_ops
    by_doc, objs = {}, []
    for r in refs:
        if r.kind == 'OBJECT':
            obj = bpy.data.objects.get(r.doc_key)
            if obj is not None and obj not in objs:
                objs.append(obj)
        elif r.kind == 'EDGE':
            by_doc.setdefault(r.doc_key, set()).add(r.index)
    changed = []
    for key, idx in by_doc.items():
        doc = document.get_by_key(key)
        if doc is None:
            continue
        bm = doc.bm
        bm.edges.ensure_lookup_table()
        edges = [bm.edges[i] for i in sorted(idx) if i < len(bm.edges)]
        if not edges:
            continue
        lay = geom.ensure_layers(bm)
        if mode == 'ERASE':
            geom.erase_edges(bm, edges)
        elif mode == 'HIDE':
            for e in edges:
                e[lay.hidden] = True
        else:
            soften(bm, edges, mode == 'SOFTEN')
        changed.append(doc)
    if mode == 'ERASE':
        names = {o.name for o in objs}
        for obj in objs:
            p = obj.parent
            nested = False
            while p is not None:
                nested = nested or p.name in names
                p = p.parent
            if not nested and bpy.data.objects.get(obj.name) is not None:
                edit_ops._remove_object_tree(obj)
    elif mode == 'HIDE':
        for obj in objs:
            obj.hide_set(True)
    else:
        objs = []
    if not changed and not objs:
        return False
    from ..core import selection
    gone = {r for r in selection.get() if r in set(refs)} if mode in ('ERASE', 'HIDE') else set()
    edit_ops.commit(changed, undo_key, select=(selection.get() - gone) if gone else None)
    return True


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.eraser.label", icon="brush.gpencil_draw.erase", shortcut="E",
               cursor='ERASER'))
class EraserTool(BaseTool):

    def __init__(self):
        self.marked = []
        self.hover_refs = []
        self.mode = 'ERASE'

    def update_status(self):
        STATE.set_hint("tool.su.eraser.hint", opt=modifiers.label("copy"))
        STATE.set_vcb("", "")

    def activate(self, tc):
        self.cancel(tc)
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)

    def cancel(self, tc):
        self.marked = []
        self.hover_refs = []

    def hover(self, tc, inf):
        self.hover_refs = _target(tc, tc.xy, inf)    # pre-highlight (blue) of what a click erases

    def _mark(self, tc, ev, inf):
        for r in _target(tc, (ev.x, ev.y), inf):
            if r not in self.marked:
                self.marked.append(r)

    def press(self, tc, ev, inf):
        self.marked = []
        self.mode = mode_of(ev)
        self._mark(tc, ev, inf)
        return Result.RUNNING

    def move(self, tc, ev, inf):
        self._mark(tc, ev, inf)
        return Result.RUNNING

    def release(self, tc, ev, inf):
        self._mark(tc, ev, inf)
        refs, self.marked, self.hover_refs = self.marked, [], []
        if refs:
            apply(refs, self.mode)
        return Result.IDLE

    def draw_3d(self, dc):
        refs = self.marked or self.hover_refs
        if not refs:
            return
        prims = registry.optional("draw.prims")
        if prims is None:
            return
        blue = colors.rgba(colors.SELECTION)
        segs = []
        for r in refs:
            obj = bpy.data.objects.get(r.doc_key)
            if obj is None or obj.type != 'MESH':
                continue
            if r.kind == 'EDGE' and r.index < len(obj.data.edges):
                me, M = obj.data, obj.matrix_world
                a, b = me.edges[r.index].vertices
                segs.append((M @ me.vertices[a].co, M @ me.vertices[b].co))
            elif r.kind == 'OBJECT':
                from mathutils import Vector
                bb = [Vector(c) for c in obj.bound_box]
                mn = Vector((min(c.x for c in bb), min(c.y for c in bb), min(c.z for c in bb)))
                mx = Vector((max(c.x for c in bb), max(c.y for c in bb), max(c.z for c in bb)))
                prims.box(dc, mn, mx, obj.matrix_world, blue)
        if segs:
            prims.lines(dc, segs, blue, 2.0, depth=True)


def register():
    i18n.register_strings(STRINGS)
