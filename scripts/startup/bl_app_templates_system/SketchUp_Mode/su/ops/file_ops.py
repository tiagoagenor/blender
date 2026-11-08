# SPDX-License-Identifier: GPL-2.0-or-later
"""File operators (owner: D). Arquivo › Exportar ▸ OBJ / glTF / STL (P1, §9.2-D item 10).

Exports run WITHOUT modifiers: every document carries the "SU_Display" GN back copy (draw/display_gn),
which would otherwise duplicate every face in the exported file (risk R14).
"""

import os

import bpy
from bpy.props import EnumProperty, StringProperty
from bpy_extras.io_utils import ExportHelper

from .. import i18n, perf, registry

ORDER = 470

FORMATS = (('OBJ', "OBJ", ".obj"), ('GLTF', "glTF", ".glb"), ('STL', "STL", ".stl"))
EXT = {k: e for k, _l, e in FORMATS}

STRINGS = {
    "ui.export.title": "Exportar",
    "ui.export.done": "Exportado: {path}",
    "ui.export.failed": "Falha ao exportar ({fmt})",
}


def export(fmt, filepath):
    """Export the whole model without modifiers. Returns True on success."""
    if fmt == 'OBJ':
        r = bpy.ops.wm.obj_export(filepath=filepath, apply_modifiers=False, export_materials=True)
    elif fmt == 'STL':
        r = bpy.ops.wm.stl_export(filepath=filepath, apply_modifiers=False)
    elif fmt == 'GLTF':
        r = bpy.ops.export_scene.gltf(filepath=filepath, export_format='GLB', export_apply=False)
    else:
        return False
    return 'FINISHED' in r


class SU_OT_export(bpy.types.Operator, ExportHelper):
    bl_idname = "su.export"
    bl_label = "Exportar"
    bl_options = {'REGISTER'}
    fmt: EnumProperty(items=[(k, l, "") for k, l, _e in FORMATS], default='OBJ')
    filename_ext = ".obj"
    filter_glob: StringProperty(default="*.obj;*.glb;*.stl", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return context.window is not None

    def invoke(self, context, event):
        self.filename_ext = EXT[self.fmt]
        if not self.filepath:
            base = os.path.splitext(bpy.path.basename(bpy.data.filepath))[0] or "modelo"
            self.filepath = base + self.filename_ext
        return ExportHelper.invoke(self, context, event)

    def execute(self, context):
        path = bpy.path.ensure_ext(self.filepath, EXT[self.fmt])
        try:
            ok = export(self.fmt, path)
        except Exception:
            perf.exception("export {:s}".format(self.fmt))
            ok = False
        if not ok:
            self.report({'ERROR'}, i18n.t("ui.export.failed", fmt=self.fmt))
            return {'CANCELLED'}
        self.report({'INFO'}, i18n.t("ui.export.done", path=path))
        return {'FINISHED'}


_classes = (SU_OT_export,)


def register():
    i18n.register_strings(STRINGS)
    registry.register_classes(_classes)


def unregister():
    registry.unregister_classes(_classes)
    i18n.unregister_strings(STRINGS)
