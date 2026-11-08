# SPDX-License-Identifier: GPL-2.0-or-later
"""View / camera operators (owner: G). PLANO.md §2.4, §4.5 (Câmera menu), §5.2 (mouse and trackpad), §6.3.

  su.view_orbit         modal orbit (turntable, pivot = geometry under the PRESS point; Shift held = pan;
                        a second press within the double-click time = recentre). MMB, Ctrl+Cmd+drag, Órbita.
  su.view_pan           modal pan (the grabbed point stays under the cursor). Shift+MMB, Ctrl+Cmd+Shift+drag,
                        Panorâmica.
  su.view_zoom          wheel notch at the cursor (`steps`, + = in), or modal drag (Aplicar zoom tool:
                        up = in about the centre, Shift+drag = field of view).
  su.view_trackpad      Mac trackpad: pinch = zoom at the cursor; two-finger scroll = zoom at the cursor
                        ("sketchup" mode, settings.trackpad_invert_zoom flips it), Shift = pan;
                        "blender" mode: scroll = orbit, Shift = pan, pinch = zoom.
  su.view_recenter      the point under the cursor goes to the screen centre (double MMB).
  su.zoom_extents_cmd   Extensões de zoom (Shift+Z).    su.view_standard(view)   Exibições padrão.
  su.set_projection(persp)    su.view_previous / su.view_next    su.delete_guides (Editar ▸ Excluir guias)
No operator here has the UNDO flag: navigation is never an undo step (SketchUp).

KEYMAP (Window, via A's keymap.finalize): Ctrl+Cmd(+Option) drag = orbit, +Shift = pan (PLANO §5.2).
KEYMAP_VIEW3D: the "3D View" region items A must add (region handlers run before Window ones, and a
double click falls back to PRESS inside the same keymap): see `KEYMAP_VIEW3D` below.
"""

import math
import time

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty

from .. import constants, i18n, perf, registry, settings
from ..core import camera
from ..core.camera import View

ORDER = 410

MOVE = frozenset({'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'})
WHEEL_IN = frozenset({'WHEELUPMOUSE', 'WHEELINMOUSE'})
WHEEL_OUT = frozenset({'WHEELDOWNMOUSE', 'WHEELOUTMOUSE'})
TRACKPAD_ZOOM_K = 0.01          # distance factor exp(-k · px) for pinch / two-finger zoom
DRAG_ZOOM_K = 0.01              # Aplicar zoom drag (logical px)
DRAG_FOV_DEG_PER_PX = 0.2       # Shift + drag with Aplicar zoom

# Window keymap (A's keymap.finalize appends module KEYMAP lists): PLANO §5.2.
KEYMAP = [
    ("su.view_orbit", {"type": 'LEFTMOUSE', "value": 'CLICK_DRAG', "ctrl": True, "oskey": True}, None),
    ("su.view_orbit", {"type": 'LEFTMOUSE', "value": 'CLICK_DRAG', "ctrl": True, "oskey": True, "alt": True}, None),
    ("su.view_pan", {"type": 'LEFTMOUSE', "value": 'CLICK_DRAG', "ctrl": True, "oskey": True, "shift": True}, None),
]

# "3D View" keymap items (region level, before Blender's view3d.rotate/move/zoom) — for A to install.
KEYMAP_VIEW3D = [
    ("su.view_recenter", {"type": 'MIDDLEMOUSE', "value": 'DOUBLE_CLICK'}, None),
    ("su.view_orbit", {"type": 'MIDDLEMOUSE', "value": 'PRESS'}, None),
    ("su.view_orbit", {"type": 'MIDDLEMOUSE', "value": 'PRESS', "alt": True}, None),
    ("su.view_pan", {"type": 'MIDDLEMOUSE', "value": 'PRESS', "shift": True}, None),
    ("su.view_zoom", {"type": 'WHEELUPMOUSE', "value": 'PRESS', "any": True}, {"properties": [("steps", 1)]}),
    ("su.view_zoom", {"type": 'WHEELDOWNMOUSE', "value": 'PRESS', "any": True}, {"properties": [("steps", -1)]}),
    ("su.view_zoom", {"type": 'WHEELINMOUSE', "value": 'PRESS', "any": True}, {"properties": [("steps", 1)]}),
    ("su.view_zoom", {"type": 'WHEELOUTMOUSE', "value": 'PRESS', "any": True}, {"properties": [("steps", -1)]}),
    ("su.view_trackpad", {"type": 'TRACKPADPAN', "value": 'ANY', "any": True}, None),
    ("su.view_trackpad", {"type": 'TRACKPADZOOM', "value": 'ANY', "any": True}, None),
]

STRINGS = {
    "view.orbit": {"pt_BR": "Órbita", "en": "Orbit"},
    "view.pan": {"pt_BR": "Panorâmica", "en": "Pan"},
    "view.zoom": {"pt_BR": "Aplicar zoom", "en": "Zoom"},
    "view.zoom_extents": {"pt_BR": "Extensões de zoom", "en": "Zoom Extents"},
    "view.recenter": {"pt_BR": "Recentralizar", "en": "Recenter"},
    "view.standard": {"pt_BR": "Exibições padrão", "en": "Standard Views"},
    "view.projection": {"pt_BR": "Projeção", "en": "Projection"},
    "view.previous": {"pt_BR": "Anterior", "en": "Previous"},
    "view.next": {"pt_BR": "Próxima", "en": "Next"},
    "view.trackpad": {"pt_BR": "Trackpad", "en": "Trackpad"},
    "view.iso": {"pt_BR": "Iso", "en": "Iso"},
    "view.top": {"pt_BR": "Superior", "en": "Top"},
    "view.bottom": {"pt_BR": "Inferior", "en": "Bottom"},
    "view.front": {"pt_BR": "Frontal", "en": "Front"},
    "view.back": {"pt_BR": "Traseira", "en": "Back"},
    "view.left": {"pt_BR": "Esquerda", "en": "Left"},
    "view.right": {"pt_BR": "Direita", "en": "Right"},
    "guide.delete_all": {"pt_BR": "Excluir guias", "en": "Delete Guides"},
}

_last_press = [None]      # (t, x, y, button) of the last orbit press (double click → recentre)


def _pixel_size():
    try:
        return max(0.5, bpy.context.preferences.system.pixel_size)
    except Exception:
        return 1.0


def region_at(context, event):
    """(area, WINDOW region, rv3d, (x, y) region px) of the 3D view under the event, else Nones."""
    region = getattr(context, "region", None)
    area = getattr(context, "area", None)
    mx, my = event.mouse_x, event.mouse_y
    if region is not None and region.type == 'WINDOW' and area is not None and area.type == 'VIEW_3D':
        return area, region, context.region_data, (mx - region.x, my - region.y)
    win = getattr(context, "window", None)
    if win is None:
        return None, None, None, None
    for a in win.screen.areas:
        if a.type != 'VIEW_3D':
            continue
        for r in a.regions:
            if r.type == 'WINDOW' and r.x <= mx < r.x + r.width and r.y <= my < r.y + r.height:
                return a, r, a.spaces.active.region_3d, (mx - r.x, my - r.y)
    return None, None, None, None


def _main_view(context):
    _w, area, region, rv3d = camera.view3d(context)
    return area, region, rv3d


def _poll_view(context):
    return getattr(context, "window", None) is not None and camera.view3d(context)[3] is not None


class _OrbitPan:
    """Shared modal of su.view_orbit / su.view_pan (a plain mixin: registering a subclass of a REGISTERED
    operator class would replace the parent's operator type)."""
    bl_options = {'INTERNAL', 'BLOCKING'}

    pan_mode = False

    @classmethod
    def poll(cls, context):
        return _poll_view(context)

    def invoke(self, context, event):
        area, region, rv3d, xy = region_at(context, event)
        if region is None:
            return {'PASS_THROUGH'}
        if event.value == 'CLICK_DRAG':             # pivot under the PRESS, not where the drag was detected
            xy = (event.mouse_prev_press_x - region.x, event.mouse_prev_press_y - region.y)
        self.area, self.region, self.rv3d = area, region, rv3d
        self.button = event.type if event.type in {'LEFTMOUSE', 'MIDDLEMOUSE', 'RIGHTMOUSE'} else 'MIDDLEMOUSE'
        t = time.monotonic()
        lp = _last_press[0]
        lim = constants.MULTI_CLICK_DIST_PX * _pixel_size()
        if (not self.pan_mode and event.value != 'CLICK_DRAG' and lp is not None and lp[3] == self.button
                and t - lp[0] <= constants.DOUBLE_CLICK_S and math.hypot(xy[0] - lp[1], xy[1] - lp[2]) <= lim):
            _last_press[0] = None
            camera.recenter(region, rv3d, xy)       # double click: centre the view on the point
            area.tag_redraw()
            return {'FINISHED'}
        _last_press[0] = (t, xy[0], xy[1], self.button)
        v = View.from_rv3d(region, rv3d)
        camera.push_history(v)
        self.center = v.loc.copy()                   # orbit target over empty space (screen centre)
        self.pivot = camera.hit_point(region, rv3d, xy)
        self.last = xy
        self.mode = 'PAN' if (self.pan_mode or event.shift) else 'ORBIT'
        if self.mode == 'PAN':
            self._grab(v, xy)
        self.moved = False
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _grab(self, v, xy):
        p = camera.hit_point(self.region, self.rv3d, xy)
        if p is None or v.depth(p) <= 1e-6:
            p = v.point_at_depth(xy, v.depth(v.loc) if v.persp else 0.0)
        self.grab = p
        self.grab_depth = v.depth(p)

    def modal(self, context, event):
        try:
            return self._modal(context, event)
        except ReferenceError:
            return {'CANCELLED'}
        except Exception:
            perf.exception("su.view_orbit modal")
            return {'CANCELLED'}

    def _modal(self, context, event):
        t = event.type
        if t == self.button and event.value == 'RELEASE':
            camera.push_history()
            return {'FINISHED'}
        if t == 'ESC' and event.value == 'PRESS':
            return {'FINISHED'}
        if t in MOVE:
            r = self.region
            xy = (event.mouse_x - r.x, event.mouse_y - r.y)
            v = View.from_rv3d(r, self.rv3d)
            mode = 'PAN' if (self.pan_mode or event.shift) else 'ORBIT'
            if mode != self.mode:
                self.mode = mode
                if mode == 'PAN':
                    self._grab(v, self.last)
            if self.mode == 'PAN':
                camera.pan_to(v, self.grab, xy, depth=self.grab_depth if v.persp else None)
            else:
                ps = _pixel_size()
                dx, dy = (xy[0] - self.last[0]) / ps, (xy[1] - self.last[1]) / ps
                camera.orbit_about(v, self.pivot if self.pivot is not None else self.center, dx, dy)
            v.apply(self.rv3d)
            self.area.tag_redraw()
            self.last = xy
            self.moved = True
            return {'RUNNING_MODAL'}
        if t in {'LEFTMOUSE', 'MIDDLEMOUSE', 'RIGHTMOUSE'} or t.startswith("WHEEL") or t.startswith("TRACKPAD"):
            return {'RUNNING_MODAL'}
        return {'PASS_THROUGH'}


class SU_OT_view_orbit(_OrbitPan, bpy.types.Operator):
    bl_idname = "su.view_orbit"
    bl_label = "Órbita"
    bl_description = "Orbitar a câmera (o eixo azul fica sempre vertical)"
    pan_mode = False


class SU_OT_view_pan(_OrbitPan, bpy.types.Operator):
    bl_idname = "su.view_pan"
    bl_label = "Panorâmica"
    bl_description = "Panorâmica (o ponto agarrado fica sob o cursor)"
    pan_mode = True


def _zoom_point(region, rv3d, v, xy):
    p = camera.hit_point(region, rv3d, xy)
    if p is None or (v.persp and v.depth(p) <= 1e-6):
        p = v.point_at_depth(xy, v.depth(v.loc)) if v.persp else v.point_at_depth(xy, 0.0)
        if not v.persp:
            p = p - v.fwd * (p - v.loc).dot(v.fwd)
    return p


def zoom_steps(region, rv3d, xy, steps):
    v = View.from_rv3d(region, rv3d)
    p = _zoom_point(region, rv3d, v, xy)
    camera.zoom_at(v, p, camera.wheel_factor(steps))
    v.apply(rv3d)
    camera.push_history(v, debounce=0.6)
    return v


class SU_OT_view_zoom(bpy.types.Operator):
    bl_idname = "su.view_zoom"
    bl_label = "Aplicar zoom"
    bl_description = "Aproximar/afastar (roda: no cursor; arrastar: no centro; Shift+arrastar: campo de visão)"
    bl_options = {'INTERNAL', 'BLOCKING'}

    steps: IntProperty(default=0, options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        return _poll_view(context)

    def execute(self, context):
        area, region, rv3d = _main_view(context)
        if region is None:
            return {'CANCELLED'}
        zoom_steps(region, rv3d, (region.width * 0.5, region.height * 0.5), self.steps or 1)
        area.tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        area, region, rv3d, xy = region_at(context, event)
        if region is None:
            return {'PASS_THROUGH'}
        steps = self.steps
        if event.type in WHEEL_IN:
            steps = steps or 1
        elif event.type in WHEEL_OUT:
            steps = steps or -1
        if steps:
            zoom_steps(region, rv3d, xy, steps)
            area.tag_redraw()
            return {'FINISHED'}
        if event.type != 'LEFTMOUSE':
            return self.execute(context)
        self.area, self.region, self.rv3d = area, region, rv3d
        self.last = xy
        camera.push_history(View.from_rv3d(region, rv3d))
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        try:
            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                camera.push_history()
                return {'FINISHED'}
            if event.type == 'ESC':
                return {'FINISHED'}
            if event.type in MOVE:
                r = self.region
                xy = (event.mouse_x - r.x, event.mouse_y - r.y)
                dy = (xy[1] - self.last[1]) / _pixel_size()
                self.last = xy
                if event.shift and self.rv3d.is_perspective:
                    camera.set_fov_v(camera.fov_v() - dy * DRAG_FOV_DEG_PER_PX, context)
                else:
                    v = View.from_rv3d(r, self.rv3d)
                    camera.zoom_at(v, v.loc, math.exp(-dy * DRAG_ZOOM_K))
                    v.apply(self.rv3d)
                self.area.tag_redraw()
                return {'RUNNING_MODAL'}
        except ReferenceError:
            return {'CANCELLED'}
        return {'RUNNING_MODAL'} if event.type in {'MIDDLEMOUSE', 'RIGHTMOUSE'} else {'PASS_THROUGH'}


def trackpad_action(event_type, dx, dy, shift, mode=None, invert=None):
    """('ZOOM', factor) | ('PAN', dx, dy) | ('ORBIT', dx, dy) for a trackpad event (pure; unit tested).
    dx, dy = event delta in px (mouse - mouse_prev, Blender's convention: content follows it)."""
    mode = mode or settings.get("trackpad_mode")
    invert = settings.get("trackpad_invert_zoom") if invert is None else invert
    if event_type == 'TRACKPADZOOM':
        return ('ZOOM', math.exp(-dx * TRACKPAD_ZOOM_K))
    if shift:
        return ('PAN', dx, dy)
    if mode == 'blender':
        return ('ORBIT', dx, dy)
    k = -dy if not invert else dy
    return ('ZOOM', math.exp(k * TRACKPAD_ZOOM_K))


class SU_OT_view_trackpad(bpy.types.Operator):
    bl_idname = "su.view_trackpad"
    bl_label = "Trackpad"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return _poll_view(context)

    def invoke(self, context, event):
        area, region, rv3d, xy = region_at(context, event)
        if region is None:
            return {'PASS_THROUGH'}
        dx = event.mouse_x - event.mouse_prev_x
        dy = event.mouse_y - event.mouse_prev_y
        act = trackpad_action(event.type, dx, dy, event.shift)
        v = View.from_rv3d(region, rv3d)
        if act[0] == 'ZOOM':
            camera.zoom_at(v, _zoom_point(region, rv3d, v, xy), act[1])
            camera.push_history(v, debounce=0.6)
        elif act[0] == 'PAN':
            camera.pan_pixels(v, act[1], act[2])
        else:
            ps = _pixel_size()
            camera.orbit_about(v, v.loc, act[1] / ps, act[2] / ps)
        v.apply(rv3d)
        area.tag_redraw()
        return {'FINISHED'}


class SU_OT_view_recenter(bpy.types.Operator):
    bl_idname = "su.view_recenter"
    bl_label = "Recentralizar"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return _poll_view(context)

    def invoke(self, context, event):
        area, region, rv3d, xy = region_at(context, event)
        if region is None:
            return {'PASS_THROUGH'}
        _last_press[0] = None
        camera.recenter(region, rv3d, xy)
        area.tag_redraw()
        return {'FINISHED'}


class SU_OT_zoom_extents_cmd(bpy.types.Operator):
    bl_idname = "su.zoom_extents_cmd"
    bl_label = "Extensões de zoom"
    bl_description = "Enquadrar o modelo inteiro"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return _poll_view(context)

    def execute(self, context):
        camera.zoom_extents()
        return {'FINISHED'}


class SU_OT_view_standard(bpy.types.Operator):
    bl_idname = "su.view_standard"
    bl_label = "Exibições padrão"
    bl_options = {'INTERNAL'}

    view: EnumProperty(items=[(n, n.title(), "") for n in camera.STANDARD_VIEWS], default='ISO')

    @classmethod
    def poll(cls, context):
        return _poll_view(context)

    def execute(self, context):
        camera.standard_view(self.view)
        return {'FINISHED'}


class SU_OT_set_projection(bpy.types.Operator):
    bl_idname = "su.set_projection"
    bl_label = "Projeção"
    bl_options = {'INTERNAL'}

    persp: BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        return _poll_view(context)

    def execute(self, context):
        camera.set_projection(self.persp)
        return {'FINISHED'}


class SU_OT_view_previous(bpy.types.Operator):
    bl_idname = "su.view_previous"
    bl_label = "Anterior"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return _poll_view(context)

    def execute(self, context):
        camera.previous()
        return {'FINISHED'}


class SU_OT_view_next(bpy.types.Operator):
    bl_idname = "su.view_next"
    bl_label = "Próxima"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return _poll_view(context)

    def execute(self, context):
        camera.next()
        return {'FINISHED'}


class SU_OT_delete_guides(bpy.types.Operator):
    bl_idname = "su.delete_guides"
    bl_label = "Excluir guias"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        guides = registry.optional("core.guides")
        return guides is not None and guides.count() > 0

    def execute(self, context):
        from ..core import guides, undo
        guides.delete_guides()
        undo.push("guide.delete_all")
        return {'FINISHED'}


CLASSES = (SU_OT_view_orbit, SU_OT_view_pan, SU_OT_view_zoom, SU_OT_view_trackpad, SU_OT_view_recenter,
           SU_OT_zoom_extents_cmd, SU_OT_view_standard, SU_OT_set_projection, SU_OT_view_previous,
           SU_OT_view_next, SU_OT_delete_guides)


def register():
    i18n.register_strings(STRINGS)
    registry.register_classes(CLASSES)


def unregister():
    registry.unregister_classes(CLASSES)
