# SPDX-License-Identifier: GPL-2.0-or-later
"""Back-face copy by Geometry Nodes (owner: D). Contract PLANO.md §2.4, §3.3.

Every document object gets the modifier "SU_Display" with the node group "SU_Display":
    Join(original, Set Material Index(Flip Faces(original), su_back_mat))
`su_back_mat` = face INT attribute (default slot 1 = "Padrão (verso)" when the attribute is missing).
Workbench draws it with `show_backface_culling=True` and `color_type='MATERIAL'` (core/style.py), so the
back side shows its own material, lit, without a blue tint (verified R2). The edge renderer and every
query use the ORIGINAL mesh; exports/intersections must skip modifiers.

`ensure(obj)` runs on the "load" event (all mesh objects) and on "doc" (new document objects: groups,
copies, 3D text, imports). `set_back_copy(False)` hides the copy (Raio X).

Until F's core/materials.py exists, `ensure()` also gives slot-less objects the two default materials
("Padrão" white, "Padrão (verso)" #A4B2BB) so the slice shows the right colours; once F is loaded,
`ensure()` calls F's `materials.ensure_slots(obj)` instead (F owns the slots).

Back faces are UNLIT (layer BACKFACES=15, `draw_back_faces`): Workbench lights the flipped copy with the
camera-relative light, which made a ground face seen from above as dark as a box top (≈101,110,116).
In SketchUp a back face keeps its colour (#A4B2BB → ≈164,178,187). The layer redraws the back-facing
triangles of every document flat in their back material colour (sRGB of `diffuse_color`), depth-tested
over the GN copy (which still provides depth, culling and the Raio X switch).
"""

import sys

import bpy
from mathutils import Vector

from .. import colors, constants, events
from . import handlers

LAYER_BACKFACES = 15        # between AXES (10) and EDGES (20)
_back_cache = {}            # mesh pointer -> (key, batch)

ORDER = 230

MODIFIER = "SU_Display"
GROUP = "SU_Display"
ATTR_BACK = "su_back_mat"
MAT_FRONT = "Padrão"
MAT_BACK = "Padrão (verso)"
ATTR_HIDDEN_FACE = "su_hidden_face"          # face BOOL, Ocultar (F)
HIDDEN_LOOK = (120, 120, 130)               # dotted look of hidden faces when Geometria oculta is on
_state = {"back_copy": True, "show_hidden": False}


def _new_node(nodes, type_, x, y, **props):
    n = nodes.new(type_)
    n.location = (x, y)
    for k, v in props.items():
        setattr(n, k, v)
    return n


GROUP_VERSION = 2
SOCKET_SHOW_HIDDEN = "Mostrar ocultas"


def node_group():
    """The shared "SU_Display" node group (created once per file; older versions are replaced).

    v2: hidden faces (face BOOL `su_hidden_face`, F) collapse on the ORIGINAL branch before the
    Join/Flip — Split Edges (selection) → Scale Elements (faces, scale 0) — so they vanish while the
    face COUNT and ORDER stay (C relies on idx % n_orig). Group input "Mostrar ocultas" (Visualizar ›
    Geometria oculta) disables the collapse."""
    ng = bpy.data.node_groups.get(GROUP)
    if ng is not None and ng.bl_idname == 'GeometryNodeTree' and ng.get("su_version") == GROUP_VERSION:
        return ng
    if ng is not None:
        ng.name = GROUP + ".old"
    ng = bpy.data.node_groups.new(GROUP, 'GeometryNodeTree')
    ng["su_version"] = GROUP_VERSION
    ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket(SOCKET_SHOW_HIDDEN, in_out='INPUT', socket_type='NodeSocketBool')
    ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, L = ng.nodes, ng.links
    gi = _new_node(N, 'NodeGroupInput', -1400, 0)
    go = _new_node(N, 'NodeGroupOutput', 400, 0)
    # hidden faces collapse (selection = hidden AND NOT show-hidden)
    hid = _new_node(N, 'GeometryNodeInputNamedAttribute', -1400, -250, data_type='BOOLEAN')
    hid.inputs["Name"].default_value = ATTR_HIDDEN_FACE
    sel = _new_node(N, 'FunctionNodeBooleanMath', -1150, -250, operation='NIMPLY')
    split = _new_node(N, 'GeometryNodeSplitEdges', -950, 0)
    scale = _new_node(N, 'GeometryNodeScaleElements', -750, 0, domain='FACE')
    scale.inputs["Scale"].default_value = 0.0
    L.new(hid.outputs["Attribute"], sel.inputs[0])
    L.new(gi.outputs[1], sel.inputs[1])
    L.new(gi.outputs[0], split.inputs["Mesh"])
    L.new(sel.outputs[0], split.inputs["Selection"])
    L.new(split.outputs["Mesh"], scale.inputs["Geometry"])
    L.new(sel.outputs[0], scale.inputs["Selection"])
    base = scale.outputs["Geometry"]
    # back copy
    flip = _new_node(N, 'GeometryNodeFlipFaces', -500, -150)
    attr = _new_node(N, 'GeometryNodeInputNamedAttribute', -800, -350, data_type='INT')
    attr.inputs["Name"].default_value = ATTR_BACK
    sw = _new_node(N, 'GeometryNodeSwitch', -500, -350, input_type='INT')
    setm = _new_node(N, 'GeometryNodeSetMaterialIndex', -200, -150)
    join = _new_node(N, 'GeometryNodeJoinGeometry', 150, 0)
    L.new(base, flip.inputs["Mesh"])
    L.new(attr.outputs["Exists"], sw.inputs["Switch"])
    sw.inputs["False"].default_value = constants.SLOT_DEFAULT_BACK
    L.new(attr.outputs["Attribute"], sw.inputs["True"])
    L.new(flip.outputs["Mesh"], setm.inputs["Geometry"])
    L.new(sw.outputs["Output"], setm.inputs["Material Index"])
    # Join keeps the order of its inputs: original first (face index i < n = original face i)
    L.new(setm.outputs["Geometry"], join.inputs["Geometry"])
    L.new(base, join.inputs["Geometry"])
    L.new(join.outputs["Geometry"], go.inputs[0])
    return ng


def _show_hidden_identifier(ng):
    item = ng.interface.items_tree.get(SOCKET_SHOW_HIDDEN)
    return item.identifier if item is not None else None


def set_show_hidden(on):
    """Visualizar › Geometria oculta: hidden faces drawn (with a dotted look) instead of collapsed."""
    on = bool(on)
    changed = _state["show_hidden"] != on
    _state["show_hidden"] = on
    for obj in bpy.data.objects:
        mod = obj.modifiers.get(MODIFIER)
        if mod is not None and mod.type == 'NODES' and mod.node_group is not None:
            _apply_show_hidden(obj, mod)
    if changed:
        _back_cache.clear()


def _apply_show_hidden(obj, mod):
    ident = _show_hidden_identifier(mod.node_group)
    if ident is None:
        return
    want = _state["show_hidden"]
    props = getattr(mod, "properties", None)          # 5.x: modifier.properties.inputs.<Socket_N>.value
    sock = getattr(getattr(props, "inputs", None), ident, None) if props is not None else None
    try:
        if sock is not None:
            if bool(sock.value) != want:
                sock.value = want
                obj.update_tag()
        elif mod.get(ident) != want:                  # older API: IDProperties on the modifier
            mod[ident] = want
            obj.update_tag()
    except Exception:
        from .. import perf
        perf.exception("display_gn: set {:s} on {:s}".format(SOCKET_SHOW_HIDDEN, obj.name))


def _materials_module():
    """F's core/materials.py (any package name: `su` in unit tests, the template package in the GUI)."""
    for name in (__package__.rsplit(".", 1)[0] + ".core.materials", "su.core.materials"):
        mod = sys.modules.get(name)
        if mod is not None and hasattr(mod, "ensure_slots"):
            return mod
    return None


def _ensure_slots(obj):
    """Slots 0/1 by F's materials.ensure_slots when F is loaded, else D's fallback materials."""
    mats = _materials_module()
    if mats is not None:
        mats.ensure_slots(obj)
    else:
        _fallback_slots(obj)


def _default_material(name, rgb):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.diffuse_color = colors.lin(rgb)
        m.roughness = 1.0
        m.specular_intensity = 0.0
    return m


def _fallback_slots(obj):
    me = obj.data
    if len(me.materials) >= 2:
        return
    if len(me.materials) == 0:
        me.materials.append(_default_material(MAT_FRONT, colors.FACE_FRONT))
    me.materials.append(_default_material(MAT_BACK, colors.FACE_BACK))


def is_document_object(obj):
    return obj is not None and obj.type == 'MESH' and obj.library is None


def ensure(obj):
    """Give `obj` the SU_Display modifier (idempotent). Returns the modifier or None."""
    if not is_document_object(obj):
        return None
    mod = obj.modifiers.get(MODIFIER)
    if mod is None or mod.type != 'NODES':
        if mod is not None:
            obj.modifiers.remove(mod)
        mod = obj.modifiers.new(MODIFIER, 'NODES')
    if mod.node_group is None or mod.node_group.name != GROUP:
        mod.node_group = node_group()
    _apply_show_hidden(obj, mod)
    if mod.show_viewport != _state["back_copy"]:
        mod.show_viewport = _state["back_copy"]
    mod.show_render = True
    _ensure_slots(obj)
    return mod


def ensure_all(scene=None):
    for obj in bpy.data.objects:
        if is_document_object(obj):
            ensure(obj)


def set_back_copy(enabled):
    _state["back_copy"] = bool(enabled)
    for obj in bpy.data.objects:
        mod = obj.modifiers.get(MODIFIER)
        if mod is not None and mod.show_viewport != _state["back_copy"]:
            mod.show_viewport = _state["back_copy"]


def back_copy_enabled():
    return _state["back_copy"]


def _on_load(**_kw):
    ensure_all()


def _on_doc(doc_key=None, **_kw):
    obj = bpy.data.objects.get(doc_key) if isinstance(doc_key, str) else None
    if obj is None:
        ensure_all()
    else:
        ensure(obj)


def _srgb(c):
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1.0 / 2.4) - 0.055


def _material_colors(me):
    out = []
    for m in me.materials:
        if m is None:
            out.append(colors.rgba(colors.FACE_BACK))
        else:
            d = m.diffuse_color
            out.append((_srgb(d[0]), _srgb(d[1]), _srgb(d[2]), 1.0))
    return out


def hidden_faces(me):
    """Face BOOL array of `su_hidden_face` (all False when missing)."""
    import numpy as np
    out = np.zeros(len(me.polygons), dtype=bool)
    a = me.attributes.get(ATTR_HIDDEN_FACE)
    if a is not None and a.domain == 'FACE' and a.data_type == 'BOOLEAN' and len(me.polygons):
        a.data.foreach_get("value", out)
    return out


def hidden_triangles(me):
    """Positions (3n,3) local of the triangles of hidden faces, or None."""
    import numpy as np
    hid = hidden_faces(me)
    if not hid.any():
        return None
    me.calc_loop_triangles()
    n = len(me.loop_triangles)
    tv = np.empty(n * 3, np.int32)
    me.loop_triangles.foreach_get("vertices", tv)
    tp = np.empty(n, np.int32)
    me.loop_triangles.foreach_get("polygon_index", tp)
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    keep = hid[tp]
    return co.reshape(-1, 3)[tv.reshape(-1, 3)[keep].reshape(-1)] if keep.any() else None


def back_triangles(me, skip_hidden=True):
    """(positions (3n,3) local, reversed winding; colours (3n,4) sRGB) of the mesh's back sides.
    Hidden faces (`su_hidden_face`) are left out unless `skip_hidden` is False."""
    import numpy as np
    me.calc_loop_triangles()
    n = len(me.loop_triangles)
    if not n:
        return None, None
    tv = np.empty(n * 3, np.int32)
    me.loop_triangles.foreach_get("vertices", tv)
    tp = np.empty(n, np.int32)
    me.loop_triangles.foreach_get("polygon_index", tp)
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    tv = tv.reshape(-1, 3)[:, (0, 2, 1)]                     # reversed winding = the back side
    if skip_hidden:
        keep = ~hidden_faces(me)[tp]
        if not keep.all():
            tv, tp = tv[keep], tp[keep]
            if not len(tp):
                return None, None
    pos = co[tv.reshape(-1)]
    slot = np.full(len(me.polygons), constants.SLOT_DEFAULT_BACK, np.int32)
    a = me.attributes.get(ATTR_BACK)
    if a is not None and a.domain == 'FACE' and a.data_type == 'INT' and len(me.polygons):
        a.data.foreach_get("value", slot)
    mats = _material_colors(me)
    palette = np.array(mats + [colors.rgba(colors.FACE_BACK)], np.float32)
    s = slot[tp]
    s = np.where((s >= 0) & (s < len(mats)), s, len(mats))
    col = np.repeat(palette[s], 3, axis=0)
    return pos, col


def draw_back_faces(dc):
    if not _state["back_copy"] or dc.rv3d is None:
        return
    import gpu
    from gpu_extras.batch import batch_for_shader
    from . import edges, shaders
    sh = shaders.builtin('FLAT_COLOR')
    visible = {o.name for o in dc.context.visible_objects if o.type == 'MESH'}
    items = []
    for inst in dc.context.view_layer.depsgraph.object_instances:
        ob = inst.object
        if ob.type != 'MESH':
            continue
        orig = ob.original
        if not inst.is_instance and orig.name not in visible:
            continue
        me = orig.data
        if me is None or not len(me.polygons):
            continue
        key = (len(me.vertices), len(me.polygons), edges._serial.get(me.name, 0), _state["show_hidden"],
               tuple(tuple(round(x, 4) for x in c) for c in _material_colors(me)))
        ent = _back_cache.get(me.as_pointer())
        if ent is None or ent[0] != key:
            pos, col = back_triangles(me, skip_hidden=not _state["show_hidden"])
            hpos = hidden_triangles(me) if _state["show_hidden"] else None
            ent = (key, batch_for_shader(sh, 'TRIS', {"pos": pos, "color": col}) if pos is not None else None,
                   hpos)
            _back_cache[me.as_pointer()] = ent
        if ent[1] is not None or ent[2] is not None:
            items.append((inst.matrix_world.copy(), ent))
    if not items:
        return
    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.depth_mask_set(False)
    gpu.state.face_culling_set('BACK')
    with shaders.offset_projection(dc.rv3d, 0.3):
        for M, ent in items:
            if ent[1] is not None:
                with gpu.matrix.push_pop():
                    gpu.matrix.multiply_matrix(M)
                    ent[1].draw(sh)
    gpu.state.face_culling_set('NONE')
    if _state["show_hidden"]:
        # Geometria oculta: hidden faces drawn (GN collapse off) with a dotted look, both sides
        from . import prims
        for M, ent in items:
            hpos = ent[2]
            if hpos is None:
                continue
            for i in range(0, len(hpos), 3):
                prims.polygon(dc, [M @ Vector(hpos[i + k]) for k in range(3)], colors.rgba(HIDDEN_LOOK),
                              stipple=True)
    gpu.state.depth_test_set('NONE')


def register():
    events.subscribe("load", _on_load, order=300)
    events.subscribe("doc", _on_doc, order=300)
    if not bpy.app.background:
        handlers.add_layer("backfaces", 'POST_VIEW', LAYER_BACKFACES, draw_back_faces)


def unregister():
    if not bpy.app.background:
        handlers.remove_layer("backfaces")
    _back_cache.clear()
