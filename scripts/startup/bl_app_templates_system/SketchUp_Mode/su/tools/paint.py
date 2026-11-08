# SPDX-License-Identifier: GPL-2.0-or-later
"""Pintura (owner: F). PLANO.md §6.1 (AC-PNT-1..4).

Click a face: the SIDE seen (spatial.ray_cast Hit.side: +1 front → material_index, -1 back →
su_back_mat) of the face ENTITY (logical face / whole smooth surface) gets the active material
(WindowManager.su_paint.active; "" = Padrão). Clicking a selected entity paints the whole
selection (selected faces on the clicked side, selected groups). Clicking a group paints its
default faces (both sides, nested groups too). Option = adjacent faces with the same material,
Shift = every face of the model with the same material, Shift+Option = same object only.
Cmd = eyedropper (the active material becomes the clicked side's material).
"""

import bpy

from .. import i18n, modifiers
from ..core.state import STATE
from . import select as sel_tool
from .base import BaseTool, Result, ToolMeta, make_query, tool

TOOL_ID = "su.paint"

STRINGS = {
    "tool.su.paint.label": {"pt_BR": "Pintura", "en": "Paint Bucket"},
    "tool.su.paint.hint": {
        "pt_BR": "Selecione o objeto para pintar. Shift = Pintar todos correspondentes. {opt} = Pintar adjacentes. "
                 "Shift + {opt} = Pintar o mesmo objeto. {cmd} = Conta-gotas.",
        "en": "Select object to paint. Shift = Paint all matching. {opt} = Paint adjacent. "
              "Shift + {opt} = Paint same object. {cmd} = Sample material."},
    "tool.su.paint.undo": {"pt_BR": "Pintura", "en": "Paint"},
}


def _mods():
    from ..core import document, entities, geom, materials, selection
    return document, entities, geom, materials, selection


def pick_face(tc, xy, inf):
    """(doc_key, face_idx, side) of the face under the cursor, or None. GUI: ray cast (side of the
    ORIGINAL face as seen); headless: inf.elem FACE + inf.side (0 → front)."""
    from ..core import spatial
    if tc is None or tc.region is None or tc.rv3d is None:
        if inf is None or not inf.elem or inf.elem[0] != 'FACE' or not inf.doc_key:
            return None
        if sel_tool.is_hidden_face(inf.doc_key, int(inf.elem[1])):
            return None
        return inf.doc_key, int(inf.elem[1]), (-1 if inf.side < 0 else 1)
    from ..core import viewutil
    o, d = viewutil.mouse_ray(tc.region, tc.rv3d, xy)
    hit = spatial.ray_cast(tc, o, d, skip=sel_tool.hidden_skip())
    if not hit.ok:
        return None
    return hit.doc_key, hit.face_idx_orig, hit.side


def _slot_material(obj, slot):
    mats = obj.data.materials
    return mats[slot] if 0 <= slot < len(mats) else None


def _face_slot(f, lay, side):
    return f.material_index if side >= 0 else f[lay.back]


def _same_material_faces(doc, side, mat, restrict=None):
    """Indices of faces of doc whose material on `side` is `mat` (None = default)."""
    document, entities, geom, materials, selection = _mods()
    bm = doc.bm
    lay = geom.ensure_layers(bm)
    out = []
    for f in bm.faces:
        if restrict is not None and f.index not in restrict:
            continue
        m = _slot_material(doc.obj, _face_slot(f, lay, side))
        if (materials.is_default(m) and materials.is_default(mat)) or m == mat:
            out.append(f.index)
    return out


def _adjacent_same(doc, start, side, mat):
    document, entities, geom, materials, selection = _mods()
    bm = doc.bm
    bm.faces.ensure_lookup_table()
    ok = set(_same_material_faces(doc, side, mat))
    seen = {start}
    stack = [start]
    while stack:
        i = stack.pop()
        for e in bm.faces[i].edges:
            for g in e.link_faces:
                if g.index in ok and g.index not in seen:
                    seen.add(g.index)
                    stack.append(g.index)
    return sorted(seen)


def _group_docs(obj):
    document = _mods()[0]
    out = []
    stack = [obj]
    while stack:
        o = stack.pop()
        if o.type == 'MESH':
            out.append(document.get(o))
        stack.extend(o.children)
    return out


def paint_group(obj, material):
    """Group: its (and nested groups') default faces take the material on both sides."""
    document, entities, geom, materials, selection = _mods()
    changed = []
    for d in _group_docs(obj):
        bm = d.bm
        lay = geom.ensure_layers(bm)
        front = [f.index for f in bm.faces if materials.is_default(_slot_material(d.obj, f.material_index))]
        back = [f.index for f in bm.faces if materials.is_default(_slot_material(d.obj, f[lay.back]))]
        n = materials.paint(d, front, material, 1) + materials.paint(d, back, material, -1)
        if n:
            changed.append(d)
    return changed


def paint_at(tc, ev, inf, material=None, *, use_active=True):
    """Apply one Paint click. Returns True when something changed."""
    document, entities, geom, materials, selection = _mods()
    from ..ops import edit_ops
    if use_active:
        material = materials.active()
    hit = pick_face(tc, (ev.x, ev.y), inf)
    if hit is None:
        return False
    key, fidx, side = hit
    ref = sel_tool.resolve(key, 'FACE', fidx)
    if ref is None:
        return False
    if ref.kind == selection.OBJECT:
        obj = bpy.data.objects.get(ref.doc_key)
        targets = [obj] if obj is not None else []
        if ref in selection.get():
            targets = selection.objects()
        changed = [d for o in targets for d in paint_group(o, material)]
        if changed:
            edit_ops.commit(changed, "tool.su.paint.undo")
        return bool(changed)
    doc = document.get_by_key(key)
    ent = [r.index for r in selection.entity(ref)]
    jobs = {}               # doc_key -> set of face indices (on `side`)
    groups = []
    if ref in selection.get() and not (ev.shift or ev.copy):
        for r in selection.get():
            if r.kind == selection.FACE:
                jobs.setdefault(r.doc_key, set()).add(r.index)
            elif r.kind == selection.OBJECT:
                groups.append(bpy.data.objects.get(r.doc_key))
    else:
        bm = doc.bm
        lay = geom.ensure_layers(bm)
        bm.faces.ensure_lookup_table()
        cur = _slot_material(doc.obj, _face_slot(bm.faces[fidx], lay, side))
        if ev.shift and ev.copy:
            jobs[key] = set(_same_material_faces(doc, side, cur))
        elif ev.shift:
            for o in bpy.context.scene.objects:
                if o.type == 'MESH' and o.visible_get():
                    d = document.get(o)
                    jobs[d.key] = set(_same_material_faces(d, side, cur))
        elif ev.copy:
            jobs[key] = set(_adjacent_same(doc, fidx, side, cur))
        else:
            jobs[key] = set(ent)
    changed = []
    for k, idx in jobs.items():
        d = document.get_by_key(k)
        if d is not None and idx and materials.paint(d, sorted(idx), material, side):
            changed.append(d)
    for o in groups:
        if o is not None:
            changed += paint_group(o, material)
    if not changed:
        return False
    edit_ops.commit(changed, "tool.su.paint.undo")
    return True


def sample_at(tc, ev, inf):
    """Cmd+click: the active material becomes the clicked side's material. Returns it (None = default)."""
    document, entities, geom, materials, selection = _mods()
    hit = pick_face(tc, (ev.x, ev.y), inf)
    if hit is None:
        return None
    key, fidx, side = hit
    doc = document.get_by_key(key)
    m = materials.material_of(doc, fidx, side)
    materials.set_active(m)
    return m


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.paint.label", icon="brush.gpencil_draw.fill", shortcut="B",
               cursor='PAINT_BRUSH'))
class PaintTool(BaseTool):

    def update_status(self):
        STATE.set_hint("tool.su.paint.hint", opt=modifiers.label("copy"), cmd=modifiers.label("alt_action"))
        STATE.set_vcb("", "")

    def activate(self, tc):
        self.update_status()

    def query_ctx(self, tc, xy):
        return make_query(tc, xy, flags=frozenset())      # Pintura hits faces by itself: no markers

    def press(self, tc, ev, inf):
        if ev.alt_action:
            sample_at(tc, ev, inf)
        else:
            paint_at(tc, ev, inf)
        return Result.IDLE


def register():
    i18n.register_strings(STRINGS)
