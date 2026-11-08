# SPDX-License-Identifier: GPL-2.0-or-later
"""Selecionar (owner: F). PLANO.md §6.1 (AC-SEL-1..5), §3.8.

Click: an edge within 7 px wins over the face under the cursor; the clicked ENTITY is selected
(entities.pick_entity: curve / surface / logical face). 2 clicks: face → face + its edges, edge →
edge + its faces, group → enter (edit context). 3 clicks: everything connected. Modifiers (Mac):
Option = add, Shift = add/subtract (toggle), Shift+Option = subtract. Drag: left→right = window
(entities completely inside), right→left = crossing (entities touching). Click on empty space
(no modifier) clears. Inside a group only the group's geometry (and its child groups) is
selectable; outside geometry is still inferable by drawing tools. Esc (ops/edit_ops) clears the
selection, then leaves the group.

Guides, dimensions and texts (G) are picked too (an edge wins, then the annotation, then the face) and
kept in ANNOT (Excluir deletes them).

Shared helpers for F's other tools (Apagar, Pintura, Mover...):
    pick(tc, xy, inf) -> (doc_key, 'EDGE'|'FACE', index) | None     element under the cursor
    resolve(doc_key, kind, index) -> Ref | None                     selectable ref in the context
    entity_refs(ref) -> [Ref]                                       the clicked entity's refs
    apply(refs, op)                                                 'SET' 'ADD' 'TOGGLE' 'REMOVE'
"""

import bpy
from mathutils import Vector

from .. import colors, constants, i18n, modifiers, registry
from ..core.state import STATE
from .base import BaseTool, Result, ToolMeta, _ui_scale, make_query, tool

TOOL_ID = "su.select"

STRINGS = {
    "tool.su.select.label": {"pt_BR": "Selecionar", "en": "Select"},
    "tool.su.select.hint": {
        "pt_BR": "Clique ou arraste para selecionar objetos. Shift = Adicionar/Subtrair. {opt} = Adicionar. "
                 "Shift + {opt} = Subtrair.",
        "en": "Click or drag to select objects. Shift = Add/Subtract. {opt} = Add. Shift + {opt} = Subtract."},
}


# ---------------------------------------------------------------------------------------------- helpers

def _mods():
    from ..core import document, edit_context, entities, selection, spatial
    return document, edit_context, entities, selection, spatial


def _edge_radius():
    from ..core import viewutil
    r = viewutil.ui_px(constants.SNAP_PX_EDGE)
    return r if r > 0 else constants.SNAP_PX_EDGE


def pick(tc, xy, inf=None, *, edges=True, faces=True):
    """(doc_key, 'EDGE'|'FACE', mesh index) under region pixel `xy`, or None.
    GUI: own screen pick (edge ≤ 7 px in front of the face wins). Headless (no region): from the
    inference element (`inf.elem` = ('EDGE'|'FACE'|'VERT', i), `inf.doc_key`)."""
    document, _ec, _ent, _sel, spatial = _mods()
    if tc is None or tc.region is None or tc.rv3d is None:
        if inf is None or not inf.elem or not inf.doc_key:
            return None
        k, i = inf.elem[0], inf.elem[1]
        if k == 'VERT':
            obj = bpy.data.objects.get(inf.doc_key)
            if obj is None or obj.type != 'MESH' or not edges:
                return None
            e = next((e for e in obj.data.edges if i in e.vertices), None)
            return (inf.doc_key, 'EDGE', e.index) if e is not None else None
        if k == 'EDGE' and edges or k == 'FACE' and faces:
            return (inf.doc_key, k, int(i))
        return None
    from ..core import viewutil
    o, d = viewutil.mouse_ray(tc.region, tc.rv3d, xy)
    hit = spatial.ray_cast(tc, o, d) if faces or edges else spatial.Hit.miss()
    if edges:
        proj = spatial.projection(tc.region, tc.rv3d)
        for eh in spatial.edges_near(proj, xy, _edge_radius()):
            depth = (eh.co - o).dot(d)
            if not hit.ok or depth <= hit.distance + max(1e-4, 1e-3 * hit.distance):
                return (eh.doc_key, 'EDGE', eh.index)
    if faces and hit.ok:
        return (hit.doc_key, 'FACE', hit.face_idx_orig)
    return None


def resolve(doc_key, kind, index):
    """Selectable Ref for an element of document `doc_key` in the current edit context:
    geometry of the edited document → Ref(EDGE/FACE); geometry of a group inside the context → the
    group's OBJECT ref (outermost in context); anything outside the context → None."""
    document, edit_context, _ent, selection, _sp = _mods()
    obj = bpy.data.objects.get(doc_key)
    if obj is None:
        return None
    adoc = document.active()
    if adoc is not None and doc_key == adoc.key:
        return selection.Ref(doc_key, kind, index)
    top = edit_context.top_level_pick(obj)
    if top is None or document.kind(top) == document.KIND_MODEL:
        return None
    return selection.Ref(top.name, selection.OBJECT, 0)


def entity_refs(ref):
    _d, _e, _ent, selection, _sp = _mods()
    if ref.kind == selection.OBJECT:
        return [ref]
    return selection.entity(ref)


# ---------------------------------------------------------------------------------------------- annotations
# Guides, dimensions and texts (G's core/guides, Scene.su_guides) are not mesh elements, so B's selection
# sets cannot hold them (refs are pruned by mesh counts). F keeps their selection here: a set of
# ('GUIDE'|'DIM'|'TEXT', index). Excluir deletes them; any 'SET' selection change clears them.
ANNOT = set()


def pick_annotation(tc, xy):
    """('GUIDE'|'DIM'|'TEXT', i) under region pixel xy (G's guides.pick), or None."""
    guides = registry.optional("core.guides")
    if guides is None or not hasattr(guides, "pick") or tc is None or tc.region is None or tc.rv3d is None:
        return None
    try:
        return guides.pick(tc.region, tc.rv3d, xy)
    except Exception:
        return None


def apply_annotation(item, op):
    if op == 'SET':
        _mods()[3].clear()
        ANNOT.clear()
        ANNOT.add(item)
    elif op == 'ADD':
        ANNOT.add(item)
    elif op == 'TOGGLE':
        ANNOT.symmetric_difference_update({item})
    elif op == 'REMOVE':
        ANNOT.discard(item)
    STATE.redraw_viewport()


def delete_annotations(items=None):
    """Delete the selected (or given) guides / dimensions / texts. Returns the number deleted."""
    guides = registry.optional("core.guides")
    items = set(ANNOT if items is None else items)
    if guides is None or not items:
        return 0
    g = [i for k, i in items if k == 'GUIDE']
    d = [i for k, i in items if k == 'DIM']
    t = [i for k, i in items if k == 'TEXT']
    if g:
        guides.delete_guides(g)
    if d or t:
        guides.delete_annotations(dims=d, texts=t)
    ANNOT.difference_update(items)
    return len(items)


def draw_annotations(dc):
    """Selected guides / dimensions / texts in the selection blue."""
    guides = registry.optional("core.guides")
    prims = registry.optional("draw.prims")
    if not ANNOT or guides is None or prims is None:
        return
    d = guides.data()
    if d is None:
        return
    blue = colors.rgba(colors.SELECTION)
    pts, segs = [], []
    for kind, i in list(ANNOT):
        if kind == 'GUIDE' and i < len(d.guides):
            g = d.guides[i]
            if g.kind == 'POINT':
                pts.append(Vector(g.co))
            else:
                c, u = Vector(g.co), Vector(g.direction).normalized()
                segs.append((c - u * 1000.0, c + u * 1000.0))
        elif kind == 'DIM' and i < len(d.dims):
            m = d.dims[i]
            segs.append((Vector(m.a) + Vector(m.offset), Vector(m.b) + Vector(m.offset)))
        elif kind == 'TEXT' and i < len(d.texts):
            t = d.texts[i]
            segs.append((Vector(t.anchor), Vector(t.leader_end)))
    if segs:
        prims.lines(dc, segs, blue, 2.0, depth=False)
    if pts:
        prims.points(dc, pts, blue, 7)


def apply(refs, op):
    _d, _e, _ent, selection, _sp = _mods()
    refs = list(refs)
    if op == 'SET':
        ANNOT.clear()
        selection.set(refs)
    elif op == 'ADD':
        selection.add(refs)
    elif op == 'TOGGLE':
        selection.toggle(refs)
    elif op == 'REMOVE':
        selection.remove(refs)


def op_of(ev):
    if ev.shift and ev.copy:
        return 'REMOVE'
    if ev.shift:
        return 'TOGGLE'
    if ev.copy:
        return 'ADD'
    return 'SET'


def rect_refs(tc, x0, y0, x1, y1, mode):
    """Refs selected by a window ('WINDOW') / crossing ('CROSSING') rectangle in the context."""
    document, edit_context, entities, selection, spatial = _mods()
    proj = spatial.projection(tc.region, tc.rv3d)
    hits = spatial.rect_query(proj, x0, y0, x1, y1, mode)
    adoc = document.active()
    out = set()
    objs = {}                # top object name -> [complete?]
    for d in proj.docs:
        h = hits.get(d.key)
        if d.key == adoc.key:
            if not h:
                continue
            for kind in ('EDGE', 'FACE'):
                got = h[kind]
                done = set()
                for i in sorted(got):
                    if i in done:
                        continue
                    ent = selection.entity(selection.Ref(d.key, kind, i))
                    idx = {r.index for r in ent}
                    done |= idx
                    if mode == 'CROSSING' or idx <= got:
                        out.update(ent)
            continue
        ref = resolve(d.key, 'FACE', 0)
        if ref is None:
            continue
        complete = bool(h) and len(h['EDGE']) == len(d.edge_ids) and len(h['FACE']) == len(d.faces)
        touched = bool(h)
        if len(d.edge_ids) == 0 and len(d.faces) == 0:
            continue                         # empty group mesh: decided by its children
        st = objs.setdefault(ref.doc_key, [True, False])
        st[0] = st[0] and complete
        st[1] = st[1] or touched
    for name, (complete, touched) in objs.items():
        if (mode == 'WINDOW' and complete) or (mode == 'CROSSING' and touched):
            out.add(selection.Ref(name, selection.OBJECT, 0))
    return out


# ---------------------------------------------------------------------------------------------- tool

@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.select.label", icon="ops.generic.select", shortcut="SPACE",
               cursor='DEFAULT'))
class SelectTool(BaseTool):

    def __init__(self):
        self.press_xy = None
        self.cur_xy = None
        self.dragging = False
        self.pending = None          # ref picked at press (single click applied on release)
        self.press_ev = None

    def update_status(self):
        STATE.set_hint("tool.su.select.hint", opt=modifiers.label("copy"))
        STATE.set_vcb("", "")

    def activate(self, tc):
        self.cancel(tc)
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)

    def cancel(self, tc):
        self.press_xy = None
        self.cur_xy = None
        self.dragging = False
        self.pending = None

    def press(self, tc, ev, inf):
        _d, edit_context, _ent, selection, _sp = _mods()
        op = op_of(ev)
        p = pick(tc, (ev.x, ev.y), inf)
        ref = resolve(*p) if p is not None else None
        if ev.clicks >= 2:
            self.cancel(tc)
            if ref is None:
                return Result.IDLE
            if ev.clicks == 2:
                if ref.kind == selection.OBJECT:
                    obj = bpy.data.objects.get(ref.doc_key)
                    if obj is not None and obj.type == 'MESH':
                        edit_context.enter(obj)
                        STATE.redraw_viewport(tc.region)
                    return Result.IDLE
                refs = selection.expand_face(ref) if ref.kind == selection.FACE else selection.expand_edge(ref)
            else:
                refs = entity_refs(ref) if ref.kind == selection.OBJECT else selection.connected(ref)
            apply(refs, 'ADD' if op == 'TOGGLE' else op)
            return Result.IDLE
        self.press_xy = (ev.x, ev.y)
        self.cur_xy = (ev.x, ev.y)
        self.dragging = False
        self.pending = (ref, op)
        if p is None or p[1] == 'FACE':
            ann = pick_annotation(tc, (ev.x, ev.y))      # a guide / dimension / text over a face wins
            if ann is not None:
                self.pending = (("ANNOT",) + tuple(ann), op)
        return Result.RUNNING

    def move(self, tc, ev, inf):
        if self.press_xy is None:
            return Result.IDLE
        self.cur_xy = (ev.x, ev.y)
        lim = constants.DRAG_THRESHOLD_PX * _ui_scale()
        if abs(ev.x - self.press_xy[0]) > lim or abs(ev.y - self.press_xy[1]) > lim:
            self.dragging = True
        STATE.redraw_viewport(tc.region)
        return Result.RUNNING

    def release(self, tc, ev, inf):
        if self.press_xy is None:
            return Result.IDLE
        ref, op = self.pending if self.pending else (None, op_of(ev))
        if (ev.is_drag_release or self.dragging) and tc.region is not None:
            x0, y0 = self.press_xy
            mode = 'WINDOW' if ev.x >= x0 else 'CROSSING'
            refs = rect_refs(tc, x0, y0, ev.x, ev.y, mode)
            if refs or op == 'SET':
                apply(refs, op)
        elif isinstance(ref, tuple) and ref and ref[0] == "ANNOT":
            apply_annotation(ref[1:], op)
        elif ref is not None:
            apply(entity_refs(ref), op)
        elif op == 'SET':
            _d, _e, _ent, selection, _sp = _mods()
            ANNOT.clear()
            selection.clear()
        self.cancel(tc)
        return Result.IDLE

    def query_ctx(self, tc, xy):
        """Selecionar picks by itself: no inference markers / ScreenTips while hovering."""
        return make_query(tc, xy, flags=frozenset())

    def draw_3d(self, dc):
        draw_annotations(dc)

    def draw_2d(self, dc):
        if not self.dragging or self.press_xy is None or self.cur_xy is None:
            return
        prims = registry.optional("draw.prims")
        if prims is None:
            return
        (x0, y0), (x1, y1) = self.press_xy, self.cur_xy
        segs = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
        rgba = colors.rgba(colors.EDGE)
        if x1 >= x0:
            prims.lines(dc, segs, rgba, 1.0, depth=False)
        else:
            prims.dashed_many(dc, segs, rgba, 1.0, dash_px=4, gap_px=3, depth=False)


def register():
    i18n.register_strings(STRINGS)
