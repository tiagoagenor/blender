# SPDX-License-Identifier: GPL-2.0-or-later
"""Small shell operators and dialogs (owner: D).

* `su.ui_placeholder(name)` — "Em breve": a shell button whose feature does not exist yet; shows
  "<name>: em breve" in the status bar hint (A's `su.coming_soon(tool_id)` covers tools).
* `su.about` — "Sobre o SketchUp Mode".
"""

import bpy
from bpy.props import StringProperty

from .. import constants, i18n, registry
from ..core.state import STATE

ORDER = 505

STRINGS = {
    "ui.coming_soon": "Em breve",
    "ui.coming_soon_named": "{name}: em breve",
    "ui.about.title": "Sobre o {product}",
    "ui.about.line1": "Modo de modelagem no estilo SketchUp para o Blender.",
    "ui.about.line2": "Projeto independente, com ícones e textos próprios.",
}


class SU_OT_ui_placeholder(bpy.types.Operator):
    bl_idname = "su.ui_placeholder"
    bl_label = "Em breve"
    bl_options = {'INTERNAL'}
    name: StringProperty()

    @classmethod
    def description(cls, context, props):
        return i18n.t("ui.coming_soon_named", name=props.name) if props.name else i18n.t("ui.coming_soon")

    def execute(self, context):
        STATE.set_hint("ui.coming_soon_named", name=self.name or "")
        return {'FINISHED'}


class SU_OT_about(bpy.types.Operator):
    bl_idname = "su.about"
    bl_label = "Sobre"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=360)

    def draw(self, context):
        col = self.layout.column()
        col.label(text=i18n.t("ui.about.title", product=constants.PRODUCT_NAME))
        col.label(text=i18n.t("ui.about.line1"))
        col.label(text=i18n.t("ui.about.line2"))
        col.label(text="Blender " + bpy.app.version_string)

    def execute(self, context):
        return {'FINISHED'}


_classes = (SU_OT_ui_placeholder, SU_OT_about)


def register():
    i18n.register_strings(STRINGS)
    registry.register_classes(_classes)


def unregister():
    registry.unregister_classes(_classes)
    i18n.unregister_strings(STRINGS)
