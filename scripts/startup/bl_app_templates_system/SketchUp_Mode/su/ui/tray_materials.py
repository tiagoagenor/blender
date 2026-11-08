# SPDX-License-Identifier: GPL-2.0-or-later
"""Tray section "Materiais" (owner: F). PLANO.md §4.4, §6.1 (Materiais P0: 24 colours + Padrão, create a colour).

Active material swatch + name; "Cores" grid (Padrão + 24); "Em uso no modelo"; "Criar material"
(colour picker + button). Clicking a swatch makes it the Paint bucket's material and activates
Pintura (as SketchUp does). Swatches are solid-colour preview icons (bpy.utils.previews).
"""

import bpy
from bpy.props import IntProperty, StringProperty

from .. import i18n, perf, registry

ORDER = 560

STRINGS = {
    "mat.tray.colors": {"pt_BR": "Cores", "en": "Colors"},
    "mat.tray.in_model": {"pt_BR": "Em uso no modelo", "en": "In Model"},
    "mat.tray.none_in_model": {"pt_BR": "Nenhum material pintado", "en": "No painted material"},
    "mat.tray.create": {"pt_BR": "Criar material", "en": "Create Material"},
    "mat.tray.pick": {"pt_BR": "Usar este material na Pintura", "en": "Use this material with Paint Bucket"},
}

_pcoll = {"c": None}
SWATCH_PX = 32


def _materials():
    return registry.optional("core.materials")


def _icon(key, rgb01):
    """icon_id of a solid swatch (cached by key + colour)."""
    pc = _pcoll["c"]
    if pc is None:
        import bpy.utils.previews
        pc = _pcoll["c"] = bpy.utils.previews.new()
    rgb01 = tuple(round(float(c), 4) for c in rgb01)
    name = "{}|{:.4f},{:.4f},{:.4f}".format(key, *rgb01)
    p = pc.get(name)
    if p is None:
        p = pc.new(name)
        n = SWATCH_PX
        px = []
        for y in range(n):
            for x in range(n):
                border = x in (0, n - 1) or y in (0, n - 1)
                if border:
                    px += [0.55, 0.55, 0.58, 1.0]
                else:
                    px += [rgb01[0], rgb01[1], rgb01[2], 1.0]
        p.icon_size = (n, n)
        p.icon_pixels_float = px
        p.image_size = (n, n)
        p.image_pixels_float = px
    return p.icon_id


def _rgb_of(mat):
    M = _materials()
    if mat is None:
        return (1.0, 1.0, 1.0)
    if getattr(mat, "su_mat", None) is not None and mat.su_mat.kind:
        return tuple(mat.su_mat.rgb)
    # linear diffuse → sRGB
    def s(x):
        return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
    return tuple(s(c) for c in mat.diffuse_color[:3])


class SU_OT_material_pick(bpy.types.Operator):
    """Usar este material na Pintura"""
    bl_idname = "su.material_pick"
    bl_label = "Escolher material"
    bl_options = {'INTERNAL'}

    name: StringProperty()          # material name ("" = Padrão)
    palette_index: IntProperty(default=-1)

    @classmethod
    def description(cls, context, props):
        return props.name or i18n.t("mat.default")

    def execute(self, context):
        M = _materials()
        if M is None:
            return {'CANCELLED'}
        if self.palette_index >= 0:
            mat = M.palette_material(self.palette_index)
        else:
            mat = bpy.data.materials.get(self.name) if self.name else None
        M.set_active(mat)
        _activate_paint()
        return {'FINISHED'}


class SU_OT_material_new(bpy.types.Operator):
    """Criar um material de cor sólida com a cor escolhida"""
    bl_idname = "su.material_new"
    bl_label = "Criar material"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        M = _materials()
        if M is None:
            return {'CANCELLED'}
        c = context.window_manager.su_paint.new_color
        mat = M.new_color(tuple(x * 255.0 for x in c))
        M.set_active(mat)
        _activate_paint()
        return {'FINISHED'}


def _activate_paint():
    try:
        from ..tools import base
        if base.DISPATCH.tool_id != "su.paint" and "su.paint" in base.TOOLS and not bpy.app.background:
            base.set_workspace_tool("su.paint")
    except Exception:
        perf.exception("tray materials: activate Paint")


def _swatch(layout, text, rgb, active, **props):
    col = layout.column(align=True)
    col.scale_y = 1.4
    op = col.operator("su.material_pick", text="", icon_value=_icon(text, rgb), depress=active,
                      emboss=active)
    for k, v in props.items():
        setattr(op, k, v)


def draw(layout, context):
    M = _materials()
    if M is None:
        layout.label(text=i18n.t("tray.placeholder.materials"))
        return
    act = M.active()
    row = layout.row(align=False)
    big = row.column()
    big.scale_y = 2.0
    big.template_icon(icon_value=_icon("active", _rgb_of(act)), scale=2.0)
    info = row.column()
    info.label(text=act.name if act is not None else i18n.t("mat.default"))
    layout.separator(factor=0.5)
    layout.label(text=i18n.t("mat.tray.colors"))
    grid = layout.grid_flow(row_major=True, columns=5, even_columns=True, even_rows=True, align=True)
    _swatch(grid, i18n.t("mat.default"), (1.0, 1.0, 1.0), act is None, name="")
    for i, (name, rgb) in enumerate(M.palette_rgb()):
        rgb01 = tuple(c / 255.0 for c in rgb)
        _swatch(grid, name, rgb01, act is not None and act.name == name, palette_index=i)
    layout.separator(factor=0.5)
    layout.label(text=i18n.t("mat.tray.in_model"))
    used = M.in_model()
    if used:
        g2 = layout.grid_flow(row_major=True, columns=5, even_columns=True, even_rows=True, align=True)
        for m in used:
            _swatch(g2, m.name, _rgb_of(m), act == m, name=m.name)
    else:
        layout.label(text=i18n.t("mat.tray.none_in_model"))
    layout.separator(factor=0.5)
    row = layout.row(align=True)
    row.prop(context.window_manager.su_paint, "new_color", text="")
    row.operator("su.material_new", text=i18n.t("mat.tray.create"))


_classes = (SU_OT_material_pick, SU_OT_material_new)


def register():
    i18n.register_strings(STRINGS)
    registry.register_classes(_classes)
    tray = registry.optional("ui.tray")
    if tray is not None:
        tray.register_section(20, "materials", "tray.materials", draw)


def unregister():
    registry.unregister_classes(_classes)
    pc = _pcoll["c"]
    if pc is not None:
        import bpy.utils.previews
        bpy.utils.previews.remove(pc)
        _pcoll["c"] = None
    i18n.unregister_strings(STRINGS)
