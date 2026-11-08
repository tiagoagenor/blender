# SPDX-License-Identifier: GPL-2.0-or-later
"""Display style of the 3D viewport (owner: D). Contract PLANO.md §2.4 (`apply()`, `toggle(prop)`), §3.3.

`Scene.su_style` (saved with the file) holds the SketchUp style switches; `apply()` pushes them to every
3D viewport (Workbench solid, MATERIAL colours with back-face culling for the GN back copy, the camera-
relative "sketchup.sl" studio light, no Blender overlays) and to the draw layers (axes, edges).
View transform Standard (colours are written 1:1). Runs on "load" and after `toggle()`; emits "style".
"""

import sys

import bpy
from bpy.props import BoolProperty, EnumProperty

from .. import events, registry

ORDER = 180

FACE_STYLES = (
    ('XRAY', "Raio X", ""),
    ('WIREFRAME', "Grade de linhas", ""),
    ('HIDDEN_LINE', "Linha oculta", ""),
    ('SHADED', "Sombreado", ""),
    ('TEXTURED', "Sombreado com texturas", ""),
    ('MONOCHROME', "Monocromático", ""),
)


def _on_change(self, context):
    apply(context)


class SU_PG_style(bpy.types.PropertyGroup):
    show_axes: BoolProperty(name="Eixos", default=True, update=_on_change)
    show_guides: BoolProperty(name="Guias", default=True, update=_on_change)
    show_hidden_geometry: BoolProperty(name="Geometria oculta", default=False, update=_on_change)
    show_edges: BoolProperty(name="Arestas", default=True, update=_on_change)
    show_profiles: BoolProperty(name="Perfis", default=False, update=_on_change)   # off in Simple Style
    show_back_edges: BoolProperty(name="Arestas traseiras", default=False, update=_on_change)
    face_style: EnumProperty(name="Estilo de face", items=FACE_STYLES, default='TEXTURED', update=_on_change)


def _sib(name):
    return sys.modules.get(__package__.rsplit(".", 1)[0] + "." + name)


def configure_space(space, studio_light=""):
    """SketchUp look of one SpaceView3D (no layout changes: region visibility is ui.startup's)."""
    sh = space.shading
    sh.type = 'SOLID'
    sh.light = 'STUDIO'
    if studio_light:
        try:
            sh.studio_light = studio_light
        except TypeError:
            pass
    try:
        sh.use_world_space_lighting = False
    except Exception:
        pass
    sh.color_type = 'MATERIAL'
    sh.show_specular_highlight = False
    sh.show_cavity = False
    sh.show_shadows = False
    sh.show_object_outline = False
    sh.show_backface_culling = True
    sh.background_type = 'THEME'
    ov = space.overlay
    ov.show_floor = False
    ov.show_axis_x = ov.show_axis_y = ov.show_axis_z = False
    ov.show_cursor = False
    ov.show_object_origins = False
    ov.show_text = False
    ov.show_stats = False
    ov.show_relationship_lines = False
    ov.show_extras = False
    ov.show_outline_selected = False
    ov.show_wireframes = False
    ov.show_face_orientation = False
    for a in ("show_viewer_attribute", "show_bones", "show_motion_paths"):
        try:
            setattr(ov, a, False)
        except Exception:
            pass
    space.show_gizmo = False
    space.clip_start = 0.05
    space.clip_end = 20000.0


def _apply_face_style(sh, face):
    """Estilo de face (P1): Raio X (faces 50 % transparent), Grade de linhas (faces hidden, only edges),
    Linha oculta (unlit white faces hiding edges), Sombreado / Sombreado com texturas (materials, lit),
    Monocromático (lit, materials ignored)."""
    sh.show_xray = face in ('XRAY', 'WIREFRAME')
    sh.xray_alpha = 0.0 if face == 'WIREFRAME' else 0.5
    sh.light = 'FLAT' if face == 'HIDDEN_LINE' else 'STUDIO'
    if face in ('HIDDEN_LINE', 'MONOCHROME'):
        sh.color_type = 'SINGLE'
        sh.single_color = (1.0, 1.0, 1.0)
    else:
        sh.color_type = 'MATERIAL'


def _studio_light_name():
    theme = _sib("theme")
    if theme is None or bpy.app.background:
        return ""
    for sl in bpy.context.preferences.studio_lights:
        if sl.name == theme.STUDIO_LIGHT_NAME:
            return sl.name
    return theme.ensure_studio_light()


def apply(context=None):
    """Push Scene.su_style to all 3D viewports and draw layers."""
    context = context or bpy.context
    scene = getattr(context, "scene", None)
    if scene is None:
        return
    vs = scene.view_settings
    if vs.view_transform != 'Standard':
        vs.view_transform = 'Standard'
    vs.look = 'None'
    vs.exposure = 0.0
    vs.gamma = 1.0
    st = getattr(scene, "su_style", None)
    face = st.face_style if st is not None else 'TEXTURED'
    see_through = face in ('XRAY', 'WIREFRAME')       # edges without depth test, no back copy
    if not bpy.app.background:
        light = _studio_light_name()
        for win in context.window_manager.windows:
            for area in win.screen.areas:
                if area.type != 'VIEW_3D':
                    continue
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        configure_space(space, light)
                        _apply_face_style(space.shading, face)
                area.tag_redraw()
    axes = _sib("draw.axes")
    if axes is not None and st is not None:
        axes.set_enabled(st.show_axes)
    edges = _sib("draw.edges")
    if edges is not None and st is not None:
        edges.set_style(st.show_edges, st.show_profiles)
        edges.set_back_edges(st.show_back_edges)
        edges.set_xray(see_through)
    gn = _sib("draw.display_gn")
    if gn is not None:
        gn.set_back_copy(not see_through)
        if st is not None:
            gn.set_show_hidden(st.show_hidden_geometry)
    events.emit("style")


def toggle(prop):
    """Flip a boolean of Scene.su_style (menu Visualizar)."""
    st = bpy.context.scene.su_style
    setattr(st, prop, not getattr(st, prop))       # update callback → apply()


def get(prop):
    st = getattr(bpy.context.scene, "su_style", None)
    return getattr(st, prop) if st is not None else None


def _on_load(**_kw):
    apply()


def register():
    registry.register_classes([SU_PG_style])
    bpy.types.Scene.su_style = bpy.props.PointerProperty(type=SU_PG_style)
    events.subscribe("load", _on_load, order=400)


def unregister():
    del bpy.types.Scene.su_style
    registry.unregister_classes([SU_PG_style])
