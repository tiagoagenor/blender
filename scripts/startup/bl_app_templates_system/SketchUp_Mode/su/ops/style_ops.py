# SPDX-License-Identifier: GPL-2.0-or-later
"""Display-style operators (owner: D): menu Visualizar › Geometria oculta / Eixos / Guias / Estilo de
aresta, Estilo de face (Raio X…). They change `Scene.su_style` (core/style.py) and push one undo step."""

import bpy
from bpy.props import EnumProperty, StringProperty

from .. import registry
from ..core import style

ORDER = 460

TOGGLES = ("show_axes", "show_guides", "show_hidden_geometry", "show_edges", "show_profiles", "show_back_edges")


class SU_OT_style_toggle(bpy.types.Operator):
    bl_idname = "su.style_toggle"
    bl_label = "Alternar estilo"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    prop: StringProperty()

    def execute(self, context):
        if self.prop not in TOGGLES:
            return {'CANCELLED'}
        style.toggle(self.prop)
        return {'FINISHED'}


class SU_OT_face_style(bpy.types.Operator):
    bl_idname = "su.face_style"
    bl_label = "Estilo de face"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    style: EnumProperty(items=style.FACE_STYLES, default='TEXTURED')

    def execute(self, context):
        context.scene.su_style.face_style = self.style
        return {'FINISHED'}


_classes = (SU_OT_style_toggle, SU_OT_face_style)


def register():
    registry.register_classes(_classes)


def unregister():
    registry.unregister_classes(_classes)
