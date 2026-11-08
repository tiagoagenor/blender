# SPDX-License-Identifier: GPL-2.0-or-later
"""Texto (leader text) and Texto em 3D (owner: G, P1). PLANO.md §1.2, §6.3; RESEARCH_SKETCHUP §6.

Texto: click an entity (face → its area, edge → its length, point → its coordinates), move, click to
place the text at the end of the leader; the text can then be edited (su.text_edit dialog). Screen text
(click in empty space) is P2.
Texto em 3D: a dialog (text, height, extruded + depth) and then a click places a NEW GROUP with the
letters (faces, holes and soft curved sides like SketchUp), lying on the face under the cursor or on
the ground. The group is a document of its own (emits "doc": back faces GN + material slots).
"""

import math

import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty
from mathutils import Matrix, Vector

from .. import colors, constants, events, i18n, perf, registry
from ..core import guides, undo
from ..core.state import STATE
from .base import BaseTool, Result, ToolMeta, tool

STRINGS = {
    "tool.su.text.label": {"pt_BR": "Texto", "en": "Text"},
    "tool.su.text.hint": {"pt_BR": "Clique numa entidade para anexar o texto.", "en": "Click an entity to attach the text."},
    "tool.su.text.hint_place": {"pt_BR": "Mova e clique para posicionar o texto.", "en": "Move and click to place the text."},
    "tool.su.text.undo": {"pt_BR": "Texto", "en": "Text"},
    "tool.su.text3d.label": {"pt_BR": "Texto em 3D", "en": "3D Text"},
    "tool.su.text3d.hint": {"pt_BR": "Clique para posicionar o texto em 3D.", "en": "Click to place the 3D text."},
    "tool.su.text3d.undo": {"pt_BR": "Texto em 3D", "en": "3D Text"},
    "tool.su.text3d.default": {"pt_BR": "Digite o texto", "en": "Enter text"},
}

SOFT_ANGLE_DEG = 25.0           # side facets of curved letters below this dihedral angle → soft


def _units():
    return registry.optional("core.units")


def entity_text(inf):
    """Default leader text of SketchUp: face area, edge length, point coordinates."""
    u = _units()
    us = getattr(bpy.context.scene, "su_units", None)
    document = registry.optional("core.document")
    try:
        if inf.kind == "ON_FACE" and inf.elem and document is not None:
            doc = document.get_by_key(inf.doc_key)
            if doc is not None:
                entities = registry.optional("core.entities")
                bm = doc.bm
                bm.faces.ensure_lookup_table()
                f = bm.faces[inf.elem[1]]
                faces = entities.logical_face(bm, f).faces if entities is not None else [f]
                m = doc.world()
                area = sum(_world_area(m, x) for x in faces)
                return u.format_area(area, us) if u is not None else "{:.2f}m²".format(area)
        if inf.kind in ("ON_EDGE", "MIDPOINT") and inf.ref_edge and document is not None:
            doc = document.get_by_key(inf.ref_edge[0])
            if doc is not None:
                me = doc.obj.data
                e = me.edges[inf.ref_edge[1]]
                m = doc.world()
                L = (m @ me.vertices[e.vertices[1]].co - m @ me.vertices[e.vertices[0]].co).length
                return u.format_length(L, us) if u is not None else "{:.2f}m".format(L)
    except Exception:
        perf.exception("text: entity text")
    p = inf.point
    if u is not None:
        sep = u.list_sep(us) if hasattr(u, "list_sep") else ";"
        return "[{:s}]".format((sep + " ").join(u.format_length(c, us) for c in p))
    return "[{:.2f}; {:.2f}; {:.2f}]".format(*p)


def _world_area(m, f):
    pts = [m @ v.co for v in f.verts]
    n = Vector()
    for i in range(len(pts)):
        n += pts[i].cross(pts[(i + 1) % len(pts)])
    return n.length * 0.5


@tool(ToolMeta(id="su.text", label_key="tool.su.text.label", icon="draw.text", cursor='DEFAULT', priority='P1'))
class TextTool(BaseTool):
    def __init__(self):
        self.reset()

    def reset(self):
        self.anchor = None
        self.text = ""
        self.current = None

    def update_status(self):
        STATE.set_hint("tool.su.text.hint" if self.anchor is None else "tool.su.text.hint_place")

    def activate(self, tc):
        self.reset()
        self.update_status()

    def cancel(self, tc):
        self.reset()
        self.update_status()

    def press(self, tc, ev, inf):
        if inf is None or inf.kind == "NONE":
            return Result.RUNNING if self.anchor is not None else Result.IDLE
        if self.anchor is None:
            if inf.kind == "FREE":
                return Result.IDLE                  # screen text (empty space) is P2
            self.anchor = Vector(inf.point)
            self.current = self.anchor.copy()
            self.text = entity_text(inf)
            self.update_status()
            return Result.RUNNING
        return self._place(tc, Vector(inf.point))

    def move(self, tc, ev, inf):
        if self.anchor is not None and inf is not None and inf.kind != "NONE":
            self.current = Vector(inf.point)
        return Result.RUNNING if self.anchor is not None else Result.IDLE

    def release(self, tc, ev, inf):
        if self.anchor is None:
            return Result.IDLE
        if ev.is_drag_release and inf is not None and inf.kind != "NONE":
            return self._place(tc, Vector(inf.point))
        return Result.RUNNING

    def _place(self, tc, end):
        i = guides.add_text(self.anchor, end, self.text)
        undo.push("tool.su.text.undo")
        self.reset()
        self.update_status()
        if not bpy.app.background:
            registry.deferred(lambda: _invoke_in_view("su.text_edit", index=i), 0.0)
        return Result.IDLE

    def draw_3d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None or self.anchor is None or self.current is None:
            return
        black = colors.rgba(colors.EDGE, 1.0)
        prims.line(dc, self.anchor, self.current, black, 1.0, depth=False)

    def draw_2d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None or self.anchor is None or self.current is None:
            return
        prims.text(dc, self.current, self.text, 11, colors.rgba(colors.EDGE, 1.0), bg=(1, 1, 1, 0.9), align='CENTER')


def _invoke_in_view(idname, **props):
    from .base import find_view3d
    win, area, region, _rv = find_view3d()
    if area is None:
        return
    mod, name = idname.split(".")
    with bpy.context.temp_override(window=win, area=area, region=region):
        getattr(getattr(bpy.ops, mod), name)('INVOKE_DEFAULT', **props)


class SU_OT_text_edit(bpy.types.Operator):
    bl_idname = "su.text_edit"
    bl_label = "Editar texto"
    bl_options = {'INTERNAL'}

    index: IntProperty(default=-1)
    text: StringProperty(name="Texto")

    def invoke(self, context, event):
        d = guides.data()
        if d is None or not 0 <= self.index < len(d.texts):
            return {'CANCELLED'}
        self.text = d.texts[self.index].text
        return context.window_manager.invoke_props_dialog(self, width=320)

    def draw(self, context):
        self.layout.prop(self, "text", text="")

    def execute(self, context):
        d = guides.data()
        if d is None or not 0 <= self.index < len(d.texts):
            return {'CANCELLED'}
        if d.texts[self.index].text != self.text:
            d.texts[self.index].text = self.text
            undo.push("tool.su.text.undo")
        return {'FINISHED'}


# ---------------------------------------------------------------------------------------------- 3D text

_settings = {"text": "", "height": 0.25, "extruded": True, "depth": 0.05, "filled": True}


def text3d_bmesh(text, height, extruded=True, depth=0.05):
    """BMesh of the letters (local XY, baseline at y = 0, extruded towards +Z): coplanar triangles merged,
    remaining in-face edges marked su_bridge, curved side facets su_soft."""
    import bmesh
    from ..core import geom
    cu = bpy.data.curves.new("SU_text3d_tmp", 'FONT')
    cu.body = text or " "
    cu.size = height
    cu.fill_mode = 'BOTH'
    cu.resolution_u = 4
    if extruded:
        cu.extrude = depth * 0.5           # symmetric around z = 0; moved to z ≥ 0 below
    obj = bpy.data.objects.new("SU_text3d_tmp", cu)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new()
    try:
        dg = bpy.context.evaluated_depsgraph_get()
        ev = obj.evaluated_get(dg)
        me = ev.to_mesh()
        bm.from_mesh(me)
        ev.to_mesh_clear()
    finally:
        bpy.data.objects.remove(obj)
        bpy.data.curves.remove(cu)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    if extruded:
        zmin = min((v.co.z for v in bm.verts), default=0.0)
        for v in bm.verts:
            v.co.z -= zmin
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.1), verts=list(bm.verts), edges=list(bm.edges))
    bm.normal_update()
    lay = geom.ensure_layers(bm)
    soft = math.radians(SOFT_ANGLE_DEG)
    for e in bm.edges:
        if len(e.link_faces) == 2:
            a = e.calc_face_angle(0.0)
            if a < 1e-4:
                e[lay.bridge] = True
            elif a < soft:
                e[lay.soft] = True
                e.smooth = True
                for f in e.link_faces:
                    f.smooth = True
    return bm


def place_matrix(point, normal=None):
    """Object matrix of the 3D text: on a face (its plane, letters upright along the slope) or the ground."""
    p = Vector(point)
    if normal is None or abs(Vector(normal).z) > 0.999:
        return Matrix.Translation(p)
    n = Vector(normal).normalized()
    x = Vector((0.0, 0.0, 1.0)).cross(n)
    x = x.normalized() if x.length > 1e-6 else Vector((1.0, 0.0, 0.0))
    y = n.cross(x).normalized()
    m = Matrix((x, y, n)).transposed().to_4x4()
    m.translation = p
    return m


def create_text3d(point, normal=None, settings=None):
    """New group "Texto em 3D" at `point` (emits "doc" through B's create_group). Returns the Document."""
    s = dict(_settings, **(settings or {}))
    document = registry.optional("core.document")
    bm = text3d_bmesh(s["text"] or i18n.t("tool.su.text3d.default"), s["height"], s["extruded"], s["depth"])
    doc = document.create_group(i18n.t("tool.su.text3d.label"))
    obj = doc.obj
    obj.matrix_world = place_matrix(point, normal)
    bm.to_mesh(obj.data)
    bm.free()
    doc.invalidate()
    events.emit("doc", doc_key=doc.key)
    doc.write(undo_key="tool.su.text3d.undo")
    return doc


@tool(ToolMeta(id="su.text3d", label_key="tool.su.text3d.label", icon="draw.text3d", cursor='CROSSHAIR',
               priority='P1'))
class Text3DTool(BaseTool):
    def update_status(self):
        STATE.set_hint("tool.su.text3d.hint")

    def activate(self, tc):
        self.update_status()
        if not bpy.app.background and not _settings.get("_asked"):
            registry.deferred(lambda: _invoke_in_view("su.text3d_dialog"), 0.0)

    def deactivate(self, tc):
        _settings["_asked"] = False

    def press(self, tc, ev, inf):
        if inf is None or inf.kind == "NONE":
            return Result.IDLE
        n = None
        if inf.kind == "ON_FACE" and inf.normal is not None:
            n = Vector(inf.normal) * (1 if inf.side >= 0 else -1)
        create_text3d(inf.point, n)
        _settings["_asked"] = False
        STATE.redraw_viewport()
        return Result.IDLE


class SU_OT_text3d_dialog(bpy.types.Operator):
    bl_idname = "su.text3d_dialog"
    bl_label = "Texto em 3D"
    bl_options = {'INTERNAL'}

    text: StringProperty(name="Texto")
    height: FloatProperty(name="Altura", default=0.25, min=0.001, unit='LENGTH')
    extruded: BoolProperty(name="Extrudado", default=True)
    depth: FloatProperty(name="Profundidade", default=0.05, min=0.0, unit='LENGTH')

    def invoke(self, context, event):
        for k in ("text", "height", "extruded", "depth"):
            setattr(self, k, _settings[k] if k != "text" or _settings[k] else i18n.t("tool.su.text3d.default"))
        return context.window_manager.invoke_props_dialog(self, width=360, confirm_text="Posicionar")

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "text", text="")
        col.prop(self, "height")
        row = col.row()
        row.prop(self, "extruded")
        sub = row.row()
        sub.active = self.extruded
        sub.prop(self, "depth", text="")

    def execute(self, context):
        _settings.update(text=self.text, height=self.height, extruded=self.extruded, depth=self.depth, _asked=True)
        from . import base
        if base.active_tool_id(context) != "su.text3d":
            base.set_workspace_tool("su.text3d")
        return {'FINISHED'}


CLASSES = (SU_OT_text_edit, SU_OT_text3d_dialog)


def register():
    i18n.register_strings(STRINGS)
    registry.register_classes(CLASSES)


def unregister():
    registry.unregister_classes(CLASSES)
