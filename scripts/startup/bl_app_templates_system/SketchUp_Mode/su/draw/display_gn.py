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
("Padrão" white, "Padrão (verso)" #A4B2BB) so the slice shows the right colours; once F is loaded this
fallback is skipped and F's `ensure_slots` (subscribed to the same events) owns the slots.
"""

import sys

import bpy

from .. import colors, constants, events

ORDER = 230

MODIFIER = "SU_Display"
GROUP = "SU_Display"
ATTR_BACK = "su_back_mat"
MAT_FRONT = "Padrão"
MAT_BACK = "Padrão (verso)"
_state = {"back_copy": True}


def _new_node(nodes, type_, x, y, **props):
    n = nodes.new(type_)
    n.location = (x, y)
    for k, v in props.items():
        setattr(n, k, v)
    return n


def node_group():
    """The shared "SU_Display" node group (created once per file)."""
    ng = bpy.data.node_groups.get(GROUP)
    if ng is not None and ng.bl_idname == 'GeometryNodeTree' and ng.get("su_version") == 1:
        return ng
    if ng is not None:
        ng.name = GROUP + ".old"
    ng = bpy.data.node_groups.new(GROUP, 'GeometryNodeTree')
    ng["su_version"] = 1
    ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, L = ng.nodes, ng.links
    gi = _new_node(N, 'NodeGroupInput', -800, 0)
    go = _new_node(N, 'NodeGroupOutput', 400, 0)
    flip = _new_node(N, 'GeometryNodeFlipFaces', -500, -150)
    attr = _new_node(N, 'GeometryNodeInputNamedAttribute', -800, -350, data_type='INT')
    attr.inputs["Name"].default_value = ATTR_BACK
    sw = _new_node(N, 'GeometryNodeSwitch', -500, -350, input_type='INT')
    setm = _new_node(N, 'GeometryNodeSetMaterialIndex', -200, -150)
    join = _new_node(N, 'GeometryNodeJoinGeometry', 150, 0)
    L.new(gi.outputs[0], flip.inputs["Mesh"])
    L.new(attr.outputs["Exists"], sw.inputs["Switch"])
    sw.inputs["False"].default_value = constants.SLOT_DEFAULT_BACK
    L.new(attr.outputs["Attribute"], sw.inputs["True"])
    L.new(flip.outputs["Mesh"], setm.inputs["Geometry"])
    L.new(sw.outputs["Output"], setm.inputs["Material Index"])
    # Join keeps the order of its inputs: original first (face index i < n = original face i)
    L.new(setm.outputs["Geometry"], join.inputs["Geometry"])
    L.new(gi.outputs[0], join.inputs["Geometry"])
    L.new(join.outputs["Geometry"], go.inputs[0])
    return ng


def _materials_owner_loaded():
    return sys.modules.get(__package__.rsplit(".", 1)[0] + ".core.materials") is not None


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
    if mod.show_viewport != _state["back_copy"]:
        mod.show_viewport = _state["back_copy"]
    mod.show_render = True
    if not _materials_owner_loaded():
        _fallback_slots(obj)
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


def register():
    events.subscribe("load", _on_load, order=300)
    events.subscribe("doc", _on_doc, order=300)


def unregister():
    pass
