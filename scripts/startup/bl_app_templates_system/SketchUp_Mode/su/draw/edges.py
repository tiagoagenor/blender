# SPDX-License-Identifier: GPL-2.0-or-later
"""Edge renderer (owner: D, layer EDGES=20). Ported from visual_spike `draw_edges`; contract PLANO.md §2.4.

Which edges are drawn is decided by ATTRIBUTES, never by angle (CRITICA_R3_SKETCHUP §2: a line the user
draws on a flat face has 0° and must show):
  * `su_bridge` (CDT bridge) or `su_hidden` → never;
  * `su_soft` → only as a SILHOUETTE: the two faces lie on opposite sides w.r.t. the camera (the outline
    of a cylinder, as in SketchUp) — always drawn, 1 pt, like any edge; a soft edge with < 2 faces is drawn;
  * everything else → always. Meshes without these attributes draw all their edges.
  * hidden FACES (`su_hidden_face`, collapsed by the GN) keep their edges, as in SketchUp; a soft edge
    next to a hidden face is drawn always (it borders the visible surface).
  * Perfis (Estilos, OFF in the default Simple Style): when ON, the OUTLINE of every object (silhouette
    edges of any kind + border edges) is drawn again PROFILE_WIDTH thick.
Black 1 pt `POLYLINE_UNIFORM_COLOR`, depth LESS_EQUAL with the spike's polygon-offset projection.
Uses the ORIGINAL mesh (`obj.original.data`), not the evaluated one (the GN back copy doubles faces).
Groups/instances: every depsgraph object instance, drawn with its `matrix_world` (batches are in local
space and shared). While a group is open (B `edit_context.current_object`), edges outside it are grey.

Cache: per mesh (pointer + element counts + dirty serial). `mark_dirty(doc_key)` runs on the "geometry"
event; a depsgraph handler also marks meshes whose geometry was updated (Document.preview_write).
"""

import sys

import bpy
import gpu
import numpy as np
from gpu_extras.batch import batch_for_shader

from .. import colors, events, registry
from . import handlers, shaders

ORDER = 222

GREY_OUT_OF_CONTEXT = (150, 150, 150)
_style = {"show_edges": True, "show_profiles": False, "color_override": {}, "back_edges": False, "xray": False}
BACK_EDGE_COLOR = (60, 60, 60)
PROFILE_WIDTH = 2.0        # pt — Perfis: outline of objects (SketchUp's default profile thickness 3 px)
_cache = {}          # mesh pointer -> entry dict
_serial = {}         # mesh name -> int (bumped by mark_dirty / depsgraph)
MAX_SIL_KEYS = 32


# ------------------------------------------------------------------------------------------- API
def mark_dirty(doc_key=None, **_kw):
    """Rebuild the batches of `doc_key` (object or mesh name) on the next draw; None = everything."""
    if doc_key is None:
        _cache.clear()
        _serial.clear()
        _tag_redraw()
        return
    names = {doc_key}
    ob = bpy.data.objects.get(doc_key) if isinstance(doc_key, str) else None
    if ob is not None and ob.type == 'MESH':
        names.add(ob.data.name)
    for n in names:
        _serial[n] = _serial.get(n, 0) + 1
    _tag_redraw()


def set_style(show_edges, show_profiles_of_soft=False, color_override=None):
    """Perfis (`show_profiles_of_soft`, name kept for the frozen contract): thick object outlines.
    Silhouettes of smooth surfaces are always drawn. `color_override`: {"edge": rgb255,
    "out_of_context": rgb255} (Estilos, Raio X… P1)."""
    _style["show_edges"] = bool(show_edges)
    _style["show_profiles"] = bool(show_profiles_of_soft)
    _style["color_override"] = dict(color_override or {})
    _tag_redraw()


def set_back_edges(on):
    """Arestas traseiras (K, P1): edges hidden behind faces drawn dashed."""
    _style["back_edges"] = bool(on)
    _tag_redraw()


def set_xray(on):
    """Raio X (P1): edges drawn without depth test (faces are see-through)."""
    _style["xray"] = bool(on)
    _tag_redraw()


def _tag_redraw():
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return
    for win in wm.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


# ------------------------------------------------------------------------------------------- mesh analysis
def _edge_bool(me, name, n):
    out = np.zeros(n, dtype=bool)
    a = me.attributes.get(name)
    if a is not None and a.domain == 'EDGE' and a.data_type == 'BOOLEAN' and n:
        a.data.foreach_get("value", out)
    return out


def edge_classes(me):
    """Pure analysis of a mesh (unit-testable): returns dict with
    co (V,3) local, ev (E,2), f0/f1 (E,) face indices (-1 none), fn/fc (P,3) local normals/centres,
    always (E,) bool edges drawn regardless of the camera, profile (E,) bool soft edges drawn only as
    silhouettes."""
    V, E, P, L = len(me.vertices), len(me.edges), len(me.polygons), len(me.loops)
    co = np.empty(V * 3, np.float32)
    me.vertices.foreach_get("co", co)
    ev = np.empty(E * 2, np.int32)
    me.edges.foreach_get("vertices", ev)
    fn = np.empty(P * 3, np.float32)
    fc = np.empty(P * 3, np.float32)
    if P:
        me.polygons.foreach_get("normal", fn)
        me.polygons.foreach_get("center", fc)
    f0 = -np.ones(E, np.int64)
    f1 = -np.ones(E, np.int64)
    counts = np.zeros(E, np.int64)
    if L and E:
        le = np.empty(L, np.int32)
        me.loops.foreach_get("edge_index", le)
        tot = np.empty(P, np.int32)
        me.polygons.foreach_get("loop_total", tot)
        lf = np.repeat(np.arange(P, dtype=np.int64), tot)
        order = np.argsort(le, kind="stable")
        le_s, lf_s = le[order], lf[order]
        counts = np.bincount(le, minlength=E).astype(np.int64)
        start = np.concatenate(([0], np.cumsum(counts)[:-1]))
        has1, has2 = counts >= 1, counts >= 2
        f0[has1] = lf_s[start[has1]]
        f1[has2] = lf_s[start[has2] + 1]
    bridge = _edge_bool(me, "su_bridge", E)
    hidden = _edge_bool(me, "su_hidden", E)
    soft = _edge_bool(me, "su_soft", E)
    shown = ~(bridge | hidden)
    profile = shown & soft & (counts >= 2)
    hf = np.zeros(P, dtype=bool)                  # hidden faces (Ocultar, F): a soft edge next to one
    a = me.attributes.get("su_hidden_face")       # borders the visible surface → drawn always
    if a is not None and a.domain == 'FACE' and a.data_type == 'BOOLEAN' and P:
        a.data.foreach_get("value", hf)
        nxt = (f0 >= 0) & hf[np.maximum(f0, 0)] | (f1 >= 0) & hf[np.maximum(f1, 0)]
        profile &= ~nxt
    always = shown & ~profile
    outline = shown & (counts >= 1)               # Perfis candidates (silhouettes of any edge + borders)
    return dict(co=co.reshape(-1, 3), ev=ev.reshape(-1, 2), f0=f0, f1=f1, fn=fn.reshape(-1, 3),
                fc=fc.reshape(-1, 3), always=always, profile=profile, outline=outline)


def silhouette_mask(data, eye_local, ortho_dir_local=None, which="profile"):
    """Edges of `data[which]` whose two faces are on opposite sides of the eye (or of the view direction
    in ortho): which='profile' → soft edges; 'outline' → any edge (border edges always included)."""
    cand = np.nonzero(data[which])[0]
    if not len(cand):
        return cand
    border = cand[data["f1"][cand] < 0]
    idx = cand[data["f1"][cand] >= 0]
    if not len(idx):
        return border
    fn, fc, f0, f1 = data["fn"], data["fc"], data["f0"][idx], data["f1"][idx]
    if ortho_dir_local is not None:
        d = -np.asarray(ortho_dir_local, np.float32)
        s0 = fn[f0] @ d > 0
        s1 = fn[f1] @ d > 0
    else:
        eye = np.asarray(eye_local, np.float32)
        s0 = np.einsum("ij,ij->i", fn[f0], eye - fc[f0]) > 0
        s1 = np.einsum("ij,ij->i", fn[f1], eye - fc[f1]) > 0
    return np.concatenate((idx[s0 != s1], border))


# ------------------------------------------------------------------------------------------- batches
def _entry(me, sh):
    key = (len(me.vertices), len(me.edges), len(me.polygons), _serial.get(me.name, 0))
    ptr = me.as_pointer()
    e = _cache.get(ptr)
    if e is not None and e["key"] == key:
        return e
    data = edge_classes(me)
    ev = data["ev"][data["always"]]
    e = dict(key=key, name=me.name, data=data, sil={}, segs=data["co"][ev],
             static=batch_for_shader(sh, 'LINES', {"pos": data["co"]}, indices=ev) if len(ev) else None)
    _cache[ptr] = e
    return e


def _silhouette_batch(e, sh, eye_local, ortho_dir_local, which="profile"):
    k = (which,) + tuple(round(float(x), 3) for x in (ortho_dir_local if ortho_dir_local is not None else eye_local))
    b = e["sil"].get(k, False)
    if b is not False:
        return b
    if len(e["sil"]) > MAX_SIL_KEYS:
        e["sil"].clear()
    sel = silhouette_mask(e["data"], eye_local, ortho_dir_local, which)
    b = batch_for_shader(sh, 'LINES', {"pos": e["data"]["co"]}, indices=e["data"]["ev"][sel]) if len(sel) else None
    e["sil"][k] = b
    return b


def _context_test():
    """fn(obj) -> True when obj is drawn black: no group open, or obj is the open group / inside it."""
    ec = sys.modules.get(__package__.rsplit(".", 1)[0] + ".core.edit_context")
    cur_fn = getattr(ec, "current_object", None) if ec else None
    cur = cur_fn() if cur_fn else None
    if cur is None:
        return None

    def inside(obj):
        o = obj
        while o is not None:
            if o == cur:
                return True
            o = o.parent
        return False
    return inside


def draw(dc):
    if not _style["show_edges"] or dc.rv3d is None:
        return
    ctx, rv3d = dc.context, dc.rv3d
    sh = shaders.builtin('POLYLINE_UNIFORM_COLOR')
    view_inv = rv3d.view_matrix.inverted()
    eye = view_inv.translation
    view_dir = -(view_inv.col[2].xyz).normalized()
    persp = rv3d.is_perspective
    visible = {o.name for o in ctx.visible_objects if o.type == 'MESH'}
    in_ctx = _context_test()
    over = _style["color_override"]
    black = colors.rgba(over.get("edge", colors.EDGE))
    grey = colors.rgba(over.get("out_of_context", GREY_OUT_OF_CONTEXT))
    draws = []
    depsgraph = ctx.view_layer.depsgraph
    for inst in depsgraph.object_instances:
        ob = inst.object
        if ob.type != 'MESH':
            continue
        orig = ob.original
        if not inst.is_instance and orig.name not in visible:
            continue
        me = orig.data
        if me is None or not len(me.edges):
            continue
        M = inst.matrix_world.copy()
        e = _entry(me, sh)
        batches = [(e["static"], 1.0)]
        kinds = (["profile"] if e["data"]["profile"].any() else []) + (["outline"] if _style["show_profiles"] else [])
        if kinds:
            Minv = M.inverted_safe()
            eye_l = Minv @ eye if persp else None
            d = None if persp else (Minv.to_3x3() @ view_dir).normalized()
            for which in kinds:      # smooth-surface silhouettes always (1 pt); Perfis = thick outline
                batches.append((_silhouette_batch(e, sh, eye_l, d, which),
                                PROFILE_WIDTH if which == "outline" else 1.0))
        col = black
        if in_ctx is not None:
            try:
                if not in_ctx(orig):
                    col = grey
            except Exception:
                pass
        draws.append((M, col, [b for b in batches if b[0] is not None], e))
    if not draws:
        return
    ps = ctx.preferences.system.pixel_size
    gpu.state.depth_test_set('NONE' if _style["xray"] else 'LESS_EQUAL')
    gpu.state.depth_mask_set(False)
    gpu.state.blend_set('ALPHA')
    with shaders.offset_projection(rv3d):
        sh.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
        sh.uniform_float("lineWidth", 1.0 * ps)
        # 1 pt black: on a 1× display a smoothed 1 px line comes out grey — draw it crisp instead.
        _set_smooth(sh, ps >= 1.5)
        for M, col, batches, _e in draws:
            if not batches:
                continue
            with gpu.matrix.push_pop():
                gpu.matrix.multiply_matrix(M)
                sh.uniform_float("color", col)
                for b, w in batches:
                    sh.uniform_float("lineWidth", w * ps)
                    b.draw(sh)
    gpu.state.depth_test_set('NONE')
    gpu.state.blend_set('NONE')
    if _style["back_edges"] and not _style["xray"]:
        from . import prims
        segs = []
        for M, _col, _b, e in draws:
            M3 = np.array(M, np.float32)
            w = e["segs"].reshape(-1, 3) @ M3[:3, :3].T + M3[:3, 3]
            w = w.reshape(-1, 2, 3)
            segs.extend((tuple(s[0]), tuple(s[1])) for s in w)
        if segs:
            prims.dashed_many(dc, segs, colors.rgba(BACK_EDGE_COLOR), 1.0, 3, 3, depth='GREATER')


def _set_smooth(sh, on):
    try:
        sh.uniform_bool("lineSmooth", bool(on))
    except Exception:
        try:
            sh.uniform_int("lineSmooth", 1 if on else 0)
        except Exception:
            pass


def _on_depsgraph(scene, depsgraph):
    for u in depsgraph.updates:
        if not u.is_updated_geometry:
            continue
        idd = u.id
        try:
            orig = idd.original
        except Exception:
            continue
        if isinstance(orig, bpy.types.Object) and orig.type == 'MESH':
            mark_dirty(orig.name)
        elif isinstance(orig, bpy.types.Mesh):
            _serial[orig.name] = _serial.get(orig.name, 0) + 1


def register():
    handlers.add_layer("edges", 'POST_VIEW', handlers.POST_VIEW["EDGES"], draw)
    events.subscribe("geometry", mark_dirty, order=200)
    events.subscribe("load", lambda **kw: mark_dirty(None), order=200)
    registry.add_handler("depsgraph_update_post", _on_depsgraph)


def unregister():
    handlers.remove_layer("edges")
    _cache.clear()
    _serial.clear()
