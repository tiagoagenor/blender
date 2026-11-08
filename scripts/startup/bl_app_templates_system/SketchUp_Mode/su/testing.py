# SPDX-License-Identifier: GPL-2.0-or-later
"""Test hooks (owner: A). Contract: PLANO.md §2.4, §8. Used by unit tests (headless) and GUI scenarios.

  dispatch(ev, tool_id=None, inf=None) -> Result   route one event through the REAL dispatcher
      (tool_id: make it the dispatcher's tool first; inf: the inference to use; None = STATE.inference
      headless, a real query under (ev.x, ev.y) in the GUI)
  hover(xy) -> Inference                            idle hover at region pixel xy (GUI: real query)
  set_clock(fn)                                     inject the clock (multi-click timing); None = monotonic
  state_dump() -> dict                              tool, hint, Measurements, inference, locks, selection,
                                                    edit context, toolbar/LTS order and separators
  doc_stats(doc_key=None) -> dict                   counts, logical faces, surfaces, areas, bbox, non-planar
Helpers: ev(type, value, x, y, **kw), pt(x, y, z, kind) → Inference, click(p), type_text(text).
"""

import time

import bpy
from mathutils import Vector

from . import i18n, perf, registry
from .core import state as _state
from .tools import base

ORDER = 95


# ---------------------------------------------------------------------------------------------- events

def ev(type, value='PRESS', x=0, y=0, **kw):
    return base.Ev(type=type, value=value, x=int(x), y=int(y), **kw)


def pt(x, y, z=0.0, kind="FREE", **kw):
    """Inference at world point (x, y, z)."""
    return _state.Inference(kind=kind, point=Vector((x, y, z)), **kw)


def _tc():
    if bpy.app.background:
        return base.ToolContext(context=bpy.context, scene=bpy.context.scene)
    return base.tool_context()


def dispatch(e, tool_id=None, inf=None):
    tc = _tc()
    if tool_id is not None and tool_id != base.DISPATCH.tool_id:
        base.DISPATCH.set_tool(tc, tool_id)
    if inf is None and tc.region is None:
        inf = _state.STATE.inference
    return base.DISPATCH.handle(tc, e, inf)


def click(p, tool_id=None, x=0, y=0, **kw):
    """PRESS + RELEASE at world point p (Inference or (x, y, z)) — one click."""
    inf = p if isinstance(p, _state.Inference) else pt(*p)
    dispatch(ev('LEFTMOUSE', 'PRESS', x, y, **kw), tool_id, inf)
    return dispatch(ev('LEFTMOUSE', 'RELEASE', x, y, **kw), None, inf)


def move(p, x=0, y=0):
    inf = p if isinstance(p, _state.Inference) else pt(*p)
    return dispatch(ev('MOUSEMOVE', 'NOTHING', x, y), None, inf)


_KEY_OF = {".": 'PERIOD', ",": 'COMMA', "-": 'MINUS', ";": 'SEMI_COLON', "/": 'SLASH', "*": 'NUMPAD_ASTERIX',
           "[": 'LEFT_BRACKET', "]": 'RIGHT_BRACKET', "<": 'COMMA', ">": 'PERIOD', " ": 'SPACE'}
_DIGITS = ("ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE")


def key_type(ch):
    if ch.isdigit():
        return _DIGITS[int(ch)]
    if ch.isalpha():
        return ch.upper()
    return _KEY_OF.get(ch, 'NONE')


def type_text(text, enter=True):
    """Type `text` (+ Enter) through the dispatcher, as the tool modal would receive it."""
    r = None
    for ch in text:
        r = dispatch(ev(key_type(ch), 'PRESS', unicode=ch))
    if enter:
        r = dispatch(ev('RET', 'PRESS'))
    return r


def hover(xy):
    tc = _tc()
    if tc.region is not None:
        base.DISPATCH.sync(tc)
    base.DISPATCH.hover(tc, xy)
    return _state.STATE.inference


def reset_model():
    """Empty the root document "Modelo" (no undo step). For tests and scenarios."""
    document = registry.optional("core.document")
    if document is None:
        return
    if hasattr(document, "reset") and getattr(document, "FAKE", False):
        document.reset()
        return
    doc = document.root()
    doc.bm.clear()
    doc.write(undo_key=None)


def set_clock(fn=None):
    base.clock = fn if fn is not None else time.monotonic


# ---------------------------------------------------------------------------------------------- dumps

def _vec(v):
    return None if v is None else [round(float(c), 6) for c in v]


def _tool_order():
    """Flattened LTS as Blender will draw it: [id | None] (None = separator)."""
    try:
        from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active as TA
    except Exception:
        return []
    out = []
    for item in TA._tools.get('OBJECT', []):
        if item is None:
            out.append(None)
        elif isinstance(item, tuple):
            out.append([getattr(t, "idname", None) for t in item if t is not None])
        elif callable(item):
            out.append("<dynamic>")
        else:
            out.append(getattr(item, "idname", None))
    return out


def state_dump():
    st = _state.STATE
    inf = st.inference
    d = {
        "tool": base.DISPATCH.tool_id,
        "workspace_tool": base.active_tool_id() if not bpy.app.background else "",
        "running": base.DISPATCH.running,
        "hint_key": st.hint_key,
        "hint": i18n.t(st.hint_key, **st.hint_fmt) if st.hint_key else "",
        "vcb_label_key": st.vcb_label_key,
        "vcb_label": i18n.t(st.vcb_label_key) if st.vcb_label_key else "",
        "vcb_value": st.vcb_value,
        "vcb_buffer": st.vcb_buffer,
        "vcb_error": st.vcb_error,
        "last_action": st.last_action.tool_id if st.last_action else "",
        "inference": {"kind": inf.kind, "point": _vec(inf.point), "linear": inf.linear,
                      "tooltip_key": inf.tooltip_key, "doc_key": inf.doc_key},
        "locks": {"axis": st.locks.axis, "shift": st.locks.shift is not None, "plane": st.locks.plane is not None},
        "active_object": None,
        "selection": None,
        "context": [],
        "lts": _tool_order(),
        "perf_errors": perf.errors(),
    }
    vl = getattr(bpy.context, "view_layer", None)
    if vl is not None and vl.objects.active is not None:
        d["active_object"] = vl.objects.active.name
    sel = registry.optional("core.selection")
    if sel is not None and hasattr(sel, "get"):
        try:
            refs = sel.get()
            d["selection"] = sorted([r.doc_key, r.kind, r.index] for r in refs)
        except Exception:
            perf.exception("state_dump selection")
    ec = registry.optional("core.edit_context")
    if ec is not None and hasattr(ec, "stack"):
        try:
            d["context"] = [getattr(o, "name", str(o)) for o in ec.stack()]
        except Exception:
            perf.exception("state_dump edit_context")
    catalog = registry.optional("tools.catalog")
    if catalog is not None:
        d["getting_started"] = catalog.GETTING_STARTED
    return d


def _planar(face, tol=1e-4):
    if len(face.verts) <= 3:
        return True
    n, c = face.normal, face.verts[0].co
    return all(abs((v.co - c).dot(n)) <= tol for v in face.verts)


def doc_stats(doc_key=None):
    """Statistics of a document (default: root). Areas in world units (matrix applied)."""
    document = registry.optional("core.document")
    if document is None:
        return {"ok": False, "error": "core.document not available"}
    if doc_key is None:
        doc = document.root()
    else:
        doc = next((x for x in document.visible_documents() if x.key == doc_key), None)
        if doc is None:
            return {"ok": False, "error": "no document " + str(doc_key)}
    bm = doc.bm
    bm.normal_update()
    mw = doc.world()
    lay = bm.edges.layers.bool if hasattr(bm.edges.layers, "bool") else None
    bridge = lay.get("su_bridge") if lay is not None else None
    soft = lay.get("su_soft") if lay is not None else None
    faces = list(bm.faces)
    pts = [mw @ v.co for v in bm.verts]
    lfaces, surfaces = None, None
    ent = registry.optional("core.entities")
    if ent is not None and faces:
        try:
            seen, n = set(), 0
            for f in faces:
                if f.index in seen:
                    continue
                lf = ent.logical_face(bm, f)
                seen.update(x.index for x in lf.faces)
                n += 1
            lfaces = n
            seen, n = set(), 0
            for f in faces:
                if f.index in seen:
                    continue
                s = ent.surface(bm, f)
                seen.update(x.index for x in s)
                n += 1
            surfaces = n
        except Exception:
            perf.exception("doc_stats entities")
    out = {
        "ok": True,
        "key": doc.key,
        "verts": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(faces),
        "logical_faces": lfaces,
        "surfaces": surfaces,
        "bridges": sum(1 for e in bm.edges if bridge is not None and e[bridge]),
        "soft": sum(1 for e in bm.edges if soft is not None and e[soft]),
        "face_areas": sorted(round(f.calc_area() * abs(mw.determinant()) ** (2.0 / 3.0), 6) for f in faces),
        "area": round(sum(f.calc_area() for f in faces) * abs(mw.determinant()) ** (2.0 / 3.0), 6),
        "normals": [_vec((mw.to_3x3() @ f.normal).normalized()) for f in faces],
        "non_planar": sum(1 for f in faces if not _planar(f)),
        "bbox": [_vec([min(p[i] for p in pts) for i in range(3)]),
                 _vec([max(p[i] for p in pts) for i in range(3)])] if pts else None,
        "version": getattr(doc, "version", None),
    }
    geom = registry.optional("core.geom")
    if geom is not None and hasattr(geom, "validate"):
        try:
            out["validate"] = geom.validate(bm)
        except Exception:
            perf.exception("doc_stats validate")
    return out
