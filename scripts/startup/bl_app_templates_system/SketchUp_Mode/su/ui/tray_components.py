# SPDX-License-Identifier: GPL-2.0-or-later
"""Tray section "Componentes" (owner: F, P1). PLANO.md §4.4.

"Em uso no modelo": every component definition (B's document.definitions()) with its instance count;
clicking one starts placing a new instance (`su.place_component`, a modal operator driving
tools/move.py's ComponentPlacer: the instance follows the inferred point, a click places it, Esc cancels).
"""

import bpy
from bpy.props import StringProperty

from .. import i18n, perf, registry

ORDER = 562

STRINGS = {
    "edit.comp.in_model": {"pt_BR": "Em uso no modelo", "en": "In Model"},
    "edit.comp.none": {"pt_BR": "Nenhum componente no modelo. Selecione geometria e tecle G.",
                      "en": "No components in the model. Select geometry and press G."},
    "edit.comp.count": {"pt_BR": "{name}  ({n})", "en": "{name}  ({n})"},
    "edit.comp.place": {"pt_BR": "Inserir uma instância de {name}", "en": "Place an instance of {name}"},
}


class SU_OT_place_component(bpy.types.Operator):
    """Inserir uma instância deste componente"""
    bl_idname = "su.place_component"
    bl_label = "Inserir componente"
    bl_options = {'INTERNAL'}

    definition: StringProperty()

    @classmethod
    def description(cls, context, props):
        return i18n.t("edit.comp.place", name=props.definition)

    def invoke(self, context, event):
        move = registry.optional("tools.move")
        if move is None or not hasattr(move, "ComponentPlacer"):
            return {'CANCELLED'}
        from ..tools import base
        if base.DISPATCH.running:
            base.DISPATCH.cancel(base.tool_context(context))
        self.placer = move.ComponentPlacer(self.definition)
        if not self.placer.start():
            return {'CANCELLED'}
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        return self.invoke(context, None)

    def _inference(self, event):
        from ..core.state import STATE
        from ..tools import base
        win, area, region, rv3d = base.find_view3d()
        if region is None:
            return None, None
        x, y = event.mouse_x - region.x, event.mouse_y - region.y
        if not (0 <= x < region.width and 0 <= y < region.height):
            return None, region
        tc = base.tool_context(bpy.context, region=region, rv3d=rv3d, xy=(x, y))
        inf = base.run_query(base.make_query(tc, (x, y), exclude=self.placer.exclude()))
        STATE.inference = inf
        return inf, region

    def modal(self, context, event):
        try:
            t = event.type
            if t in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
                self.placer.cancel()
                return {'CANCELLED'}
            if t in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
                inf, region = self._inference(event)
                if inf is not None:
                    self.placer.follow(inf)
                    region.tag_redraw()
                return {'PASS_THROUGH'}
            if t == 'LEFTMOUSE' and event.value == 'PRESS' and not event.ctrl:
                inf, region = self._inference(event)
                if inf is None:
                    return {'PASS_THROUGH'}
                self.placer.place(inf)
                return {'FINISHED'}
        except Exception:
            perf.exception("place component")
            self.placer.cancel()
            return {'CANCELLED'}
        return {'PASS_THROUGH'}


def rows():
    """[(definition name, instance count)] for the section (and tests)."""
    document = registry.optional("core.document")
    if document is None or not hasattr(document, "definitions"):
        return []
    return [(me.name, len(document.instances(me))) for me in document.definitions()]


def draw(layout, context):
    items = rows()
    layout.label(text=i18n.t("edit.comp.in_model"))
    if not items:
        layout.label(text=i18n.t("edit.comp.none"))
        return
    col = layout.column(align=True)
    for name, n in items:
        col.operator("su.place_component", text=i18n.t("edit.comp.count", name=name, n=n),
                     icon='MESH_CUBE').definition = name


_classes = (SU_OT_place_component,)


def register():
    i18n.register_strings(STRINGS)
    registry.register_classes(_classes)
    tray = registry.optional("ui.tray")
    if tray is not None:
        tray.register_section(30, "components", "tray.components", draw, 'P1')


def unregister():
    registry.unregister_classes(_classes)
    i18n.unregister_strings(STRINGS)
