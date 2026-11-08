# SPDX-License-Identifier: GPL-2.0-or-later
"""Guides and annotations (owner: G). Contract: PLANO.md §2.4 (core/guides.py), §6.3.

Model data lives in `Scene.su_guides` (saved in the .blend and in the memfile undo, so Cmd+Z removes a
guide or a dimension like any other step; the tools call `undo.push`):
  guides  LINE (infinite, through `co` along `direction`) | POINT (at `co`, created from `anchor`)
  dims    LINEAR dimensions a–b drawn at `offset`
  texts   leader texts (anchor → text at `leader_end`)
All coordinates are world space; `ctx_obj` records the group being edited when the guide was made.

API:
  add_guide_line(co, direction, ctx_obj='') -> int     add_guide_point(co, anchor, ctx_obj='') -> int
  delete_guides(indices=None)  (None = all)            count() -> int
  guides_arrays() -> {'points': [Vector], 'lines': [(co, dir)]}   visible guides, for C's inference
  add_dimension(a, b, offset, kind='LINEAR') -> int    add_text(anchor, leader_end, text) -> int
  dimension_text(i) -> str (current length, model units)   delete_annotations(dims=(), texts=())
  pick(region, rv3d, xy) -> ('GUIDE'|'DIM'|'TEXT', index) | None      (Selecionar/Apagar, F)
C's engine reads guides through `inference.set_guides_provider(guides_arrays)` (registered here).
"""

import bpy
from bpy.props import CollectionProperty, EnumProperty, FloatVectorProperty, PointerProperty, StringProperty
from mathutils import Vector

from .. import i18n, perf, registry

ORDER = 140

PICK_PX = 7


class SU_Guide(bpy.types.PropertyGroup):
    kind: EnumProperty(items=[('LINE', "Linha-guia", ""), ('POINT', "Ponto-guia", "")], default='LINE')
    co: FloatVectorProperty(size=3)
    direction: FloatVectorProperty(size=3, default=(1.0, 0.0, 0.0))
    anchor: FloatVectorProperty(size=3)
    ctx_obj: StringProperty()


class SU_Dimension(bpy.types.PropertyGroup):
    kind: EnumProperty(items=[('LINEAR', "Linear", "")], default='LINEAR')
    a: FloatVectorProperty(size=3)
    b: FloatVectorProperty(size=3)
    offset: FloatVectorProperty(size=3)
    ctx_obj: StringProperty()


class SU_Text(bpy.types.PropertyGroup):
    anchor: FloatVectorProperty(size=3)
    leader_end: FloatVectorProperty(size=3)
    text: StringProperty()
    ctx_obj: StringProperty()


class SU_Guides(bpy.types.PropertyGroup):
    guides: CollectionProperty(type=SU_Guide)
    dims: CollectionProperty(type=SU_Dimension)
    texts: CollectionProperty(type=SU_Text)


STRINGS = {
    "guide.line": {"pt_BR": "Linha-guia", "en": "Guide Line"},
    "guide.point": {"pt_BR": "Ponto-guia", "en": "Guide Point"},
    "guide.dimension": {"pt_BR": "Dimensão", "en": "Dimension"},
    "guide.text": {"pt_BR": "Texto", "en": "Text"},
}


def data(scene=None):
    scene = scene or getattr(bpy.context, "scene", None)
    return getattr(scene, "su_guides", None) if scene is not None else None


def _ctx_name():
    ec = registry.optional("core.edit_context")
    try:
        obj = ec.current_object() if ec is not None else None
    except Exception:
        obj = None
    return obj.name if obj is not None else ""


def _changed():
    from .state import STATE
    try:
        STATE.redraw_viewport()
    except Exception:
        pass


def add_guide_line(co, direction, ctx_obj=None):
    d = Vector(direction)
    if d.length < 1e-12:
        raise ValueError("guide line without direction")
    g = data().guides.add()
    g.kind = 'LINE'
    g.co = Vector(co)
    g.direction = d.normalized()
    g.anchor = Vector(co)
    g.ctx_obj = _ctx_name() if ctx_obj is None else ctx_obj
    _changed()
    return len(data().guides) - 1


def add_guide_point(co, anchor, ctx_obj=None):
    g = data().guides.add()
    g.kind = 'POINT'
    g.co = Vector(co)
    g.anchor = Vector(anchor)
    g.ctx_obj = _ctx_name() if ctx_obj is None else ctx_obj
    _changed()
    return len(data().guides) - 1


def count():
    d = data()
    return len(d.guides) if d is not None else 0


def delete_guides(indices=None):
    d = data()
    if d is None:
        return 0
    if indices is None:
        n = len(d.guides)
        d.guides.clear()
    else:
        idx = sorted({int(i) for i in indices if 0 <= int(i) < len(d.guides)}, reverse=True)
        for i in idx:
            d.guides.remove(i)
        n = len(idx)
    _changed()
    return n


def guides_visible():
    style = getattr(getattr(bpy.context, "scene", None), "su_style", None)
    return bool(getattr(style, "show_guides", True))


def guides_arrays():
    """Visible guides in world space: {'points': [Vector], 'lines': [(co, unit dir)]}."""
    d = data()
    if d is None or not guides_visible():
        return {"points": [], "lines": []}
    pts, lines = [], []
    for g in d.guides:
        if g.kind == 'POINT':
            pts.append(Vector(g.co))
        else:
            lines.append((Vector(g.co), Vector(g.direction).normalized()))
    return {"points": pts, "lines": lines}


def add_dimension(a, b, offset, kind='LINEAR'):
    dim = data().dims.add()
    dim.kind = kind
    dim.a, dim.b, dim.offset = Vector(a), Vector(b), Vector(offset)
    dim.ctx_obj = _ctx_name()
    _changed()
    return len(data().dims) - 1


def dimension_text(i):
    d = data().dims[i]
    length = (Vector(d.b) - Vector(d.a)).length
    units = registry.optional("core.units")
    if units is not None and hasattr(units, "format_length"):
        return units.format_length(length, getattr(bpy.context.scene, "su_units", None))
    return "{:.2f}m".format(length).replace(".", ",")


def add_text(anchor, leader_end, text):
    t = data().texts.add()
    t.anchor, t.leader_end, t.text = Vector(anchor), Vector(leader_end), text
    t.ctx_obj = _ctx_name()
    _changed()
    return len(data().texts) - 1


def delete_annotations(dims=(), texts=()):
    d = data()
    for i in sorted({int(i) for i in dims}, reverse=True):
        if 0 <= i < len(d.dims):
            d.dims.remove(i)
    for i in sorted({int(i) for i in texts}, reverse=True):
        if 0 <= i < len(d.texts):
            d.texts.remove(i)
    _changed()


# ------------------------------------------------------------------------------------------ picking

def _dist_point_segment_2d(p, a, b):
    ab = b - a
    L2 = ab.length_squared
    if L2 < 1e-12:
        return (p - a).length
    t = max(0.0, min(1.0, (p - a).dot(ab) / L2))
    return (p - (a + ab * t)).length


def pick(region, rv3d, xy, radius_px=None):
    """Guide / dimension / text under region pixel xy (closest within PICK_PX logical px)."""
    from bpy_extras import view3d_utils
    d = data()
    if d is None:
        return None
    try:
        scale = bpy.context.preferences.system.ui_scale or 1.0
    except Exception:
        scale = 1.0
    r = (radius_px if radius_px is not None else PICK_PX) * scale
    p = Vector((xy[0], xy[1]))
    best = None

    def proj(co):
        return view3d_utils.location_3d_to_region_2d(region, rv3d, Vector(co))

    def consider(kind, i, dist):
        nonlocal best
        if dist <= r and (best is None or dist < best[0]):
            best = (dist, (kind, i))

    if guides_visible():
        o, dirv = None, None
        for i, g in enumerate(d.guides):
            if g.kind == 'POINT':
                s = proj(g.co)
                if s is not None:
                    consider('GUIDE', i, (s - p).length)
                continue
            # closest point of the infinite line to the mouse ray, then its screen distance
            if o is None:
                o = view3d_utils.region_2d_to_origin_3d(region, rv3d, xy)
                dirv = view3d_utils.region_2d_to_vector_3d(region, rv3d, xy).normalized()
            c, u = Vector(g.co), Vector(g.direction).normalized()
            w0 = c - o
            b = u.dot(dirv)
            den = 1.0 - b * b
            if den < 1e-9:
                continue
            s_line = (b * dirv.dot(w0) - u.dot(w0)) / den
            q = proj(c + u * s_line)
            if q is not None:
                consider('GUIDE', i, (q - p).length)
    for i, dm in enumerate(d.dims):
        a2, b2 = proj(Vector(dm.a) + Vector(dm.offset)), proj(Vector(dm.b) + Vector(dm.offset))
        if a2 is not None and b2 is not None:
            consider('DIM', i, _dist_point_segment_2d(p, a2, b2))
    for i, t in enumerate(d.texts):
        s = proj(t.leader_end)
        if s is not None:
            consider('TEXT', i, (s - p).length)
    return best[1] if best else None


# ------------------------------------------------------------------------------------------ register

CLASSES = (SU_Guide, SU_Dimension, SU_Text, SU_Guides)


def register():
    i18n.register_strings(STRINGS)
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.su_guides = PointerProperty(type=SU_Guides)
    inference = registry.optional("core.inference")
    if inference is not None and hasattr(inference, "set_guides_provider"):
        inference.set_guides_provider(guides_arrays)
    else:
        perf.error("guides: core.inference has no set_guides_provider")


def unregister():
    inference = registry.optional("core.inference")
    if inference is not None and hasattr(inference, "set_guides_provider"):
        inference.set_guides_provider(None)
    del bpy.types.Scene.su_guides
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
