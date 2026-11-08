# SPDX-License-Identifier: GPL-2.0-or-later
"""Tool operators (owner: A). Contract: PLANO.md §2.4, §3.5, §3.6.

  su.tool_event      LEFTMOUSE PRESS/RELEASE of every TOOL (tool keymap) → tools.base.DISPATCH; becomes the
                     tool's modal while the controller returns Result.RUNNING.
  su.tool_activate   activate a tool by id (Window keymap shortcuts, menus, toolbar); COMMAND kinds run
                     their operator; unknown / disabled ids → su.coming_soon.
  su.vcb_key         Window keymap TEXTINPUT/RET/NUMPAD_ENTER/BACK_SPACE/ESC (idle): feeds C's vcb.feed;
                     the first consumed character starts su.vcb_capture. PASS_THROUGH when not for it.
  su.vcb_capture     window modal that owns text/RET/NUMPAD_ENTER/BACK_SPACE/ESC until APPLY/CANCEL (it runs
                     before region/UI handlers, so Enter never presses the button under the mouse).
  su.vcb_field_apply apply a text as if typed in the Measurements box.
  su.coming_soon     "Em breve" for tools that are not implemented yet.
WindowManager.su_vcb (PointerProperty): `field` = text shown in the Measurements box (get: buffer or
value; set: apply, as typed + Enter). D's status bar draws `prop(wm.su_vcb, "field")`.
"""

import bpy
from bpy.props import PointerProperty, StringProperty

from .. import i18n, perf, registry
from ..core.state import STATE
from ..tools import base

ORDER = 400

TEMPLATE_ID = "SketchUp_Mode"
KEY_AREAS = frozenset({'VIEW_3D', 'STATUSBAR', 'TOPBAR'})
VCB_KEYS = frozenset({'RET', 'NUMPAD_ENTER', 'BACK_SPACE', 'ESC'})


def mode_active(context):
    prefs = getattr(context, "preferences", None)
    return prefs is not None and prefs.app_template == TEMPLATE_ID


def keymap_poll(context):
    """Main window + area VIEW_3D/STATUSBAR/TOPBAR + SketchUp mode (PLANO §3.5-1)."""
    win = getattr(context, "window", None)
    area = getattr(context, "area", None)
    if win is None or area is None or area.type not in KEY_AREAS:
        return False
    if getattr(win, "parent", None) is not None or win.screen.is_temporary:
        return False
    return mode_active(context)


def _view3d_region(context):
    r = getattr(context, "region", None)
    if r is not None and r.type == 'WINDOW' and context.area is not None and context.area.type == 'VIEW_3D':
        return r
    return None


def _inside(region, event):
    x, y = event.mouse_x - region.x, event.mouse_y - region.y
    return 0 <= x < region.width and 0 <= y < region.height


def _report_error(op):
    if base.DISPATCH.last_error:
        op.report({'ERROR'}, base.DISPATCH.last_error.splitlines()[0][:200])
        base.DISPATCH.last_error = ''
        return True
    return False


class SU_OT_tool_event(bpy.types.Operator):
    bl_idname = "su.tool_event"
    bl_label = "SketchUp Mode: tool event"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return _view3d_region(context) is not None

    def invoke(self, context, event):
        if event.ctrl or event.value not in {'PRESS', 'DOUBLE_CLICK', 'RELEASE'}:
            return {'PASS_THROUGH'}
        region = context.region
        tc = base.tool_context(context)
        base.DISPATCH.sync(tc)
        self.tool_id = base.DISPATCH.tool_id
        r = base.DISPATCH.handle(tc, base.event_from_bpy(event, region), None)
        if _report_error(self):
            return {'CANCELLED'}
        if r is base.Result.RUNNING:
            self.region = region
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        if r is base.Result.PASS:
            return {'PASS_THROUGH'}
        return {'FINISHED'}

    def modal(self, context, event):
        d = base.DISPATCH
        region = self.region
        try:
            tc = base.tool_context(context, region=region, rv3d=context.region_data)
            if base.active_tool_id(context) != self.tool_id or d.tool_id != self.tool_id:
                d.sync(tc)                      # another tool was picked in the toolbar: cancel ours
                return {'FINISHED', 'PASS_THROUGH'}
            if not d.running:
                return {'FINISHED', 'PASS_THROUGH'}
            t = event.type
            is_mouse = t in base.MOVE_EVENTS or t in {'LEFTMOUSE', 'RIGHTMOUSE'}
            if is_mouse and not _inside(region, event):
                return {'PASS_THROUGH'}
            r = d.handle(tc, base.event_from_bpy(event, region), None)
        except Exception:
            perf.exception("su.tool_event modal")
            d.cancel(base.tool_context(context))
            return {'CANCELLED'}
        if _report_error(self):
            return {'CANCELLED'}
        if r is base.Result.PASS:
            return {'PASS_THROUGH'} if d.running else {'FINISHED', 'PASS_THROUGH'}
        if r is base.Result.IDLE or not d.running:
            return {'FINISHED'}
        return {'RUNNING_MODAL'}


class SU_OT_tool_activate(bpy.types.Operator):
    bl_idname = "su.tool_activate"
    bl_label = "SketchUp Mode: activate tool"
    bl_options = {'INTERNAL'}

    tool_id: StringProperty()

    @classmethod
    def poll(cls, context):
        return keymap_poll(context)

    def execute(self, context):
        tid = self.tool_id
        cls = base.TOOLS.get(tid)
        if cls is None or not cls.meta.enabled:
            bpy.ops.su.coming_soon(tool_id=tid)
            return {'FINISHED'}
        meta = cls.meta
        if meta.kind == 'COMMAND':
            if base.DISPATCH.running:
                base.DISPATCH.cancel(base.tool_context(context))
            return _call_operator(meta.operator)
        return {'FINISHED'} if base.set_workspace_tool(tid) else {'CANCELLED'}


def _call_operator(idname):
    try:
        mod, name = idname.split(".", 1)
        return getattr(getattr(bpy.ops, mod), name)('INVOKE_DEFAULT')
    except Exception:
        perf.exception("command operator {!r}".format(idname))
        return {'CANCELLED'}


def _feed(context, event):
    vcb = registry.optional("core.vcb")
    if vcb is None:
        return None, 'PASS'
    ev = base.event_from_bpy(event)
    return ev, vcb.feed(ev)


class SU_OT_vcb_key(bpy.types.Operator):
    bl_idname = "su.vcb_key"
    bl_label = "SketchUp Mode: Measurements key"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return keymap_poll(context)

    def invoke(self, context, event):
        if event.ctrl or event.oskey or event.value != 'PRESS':
            return {'PASS_THROUGH'}
        tc = base.tool_context(context)
        if _view3d_region(context) is not None:
            base.DISPATCH.sync(tc)
        _ev, fed = _feed(context, event)
        if fed == 'PASS':
            return {'PASS_THROUGH'}
        if fed == 'APPLY':
            base.DISPATCH.apply_vcb(tc, STATE.vcb_buffer)
        elif fed == 'CONSUMED' and STATE.vcb_buffer and not base.DISPATCH.running and not _capture_running[0]:
            bpy.ops.su.vcb_capture('INVOKE_DEFAULT')
        STATE.redraw_statusbar()
        return {'FINISHED'}


_capture_running = [False]


class SU_OT_vcb_capture(bpy.types.Operator):
    bl_idname = "su.vcb_capture"
    bl_label = "SketchUp Mode: Measurements capture"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        _capture_running[0] = True
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _end(self, extra=()):
        _capture_running[0] = False
        return {'FINISHED', *extra}

    def modal(self, context, event):
        try:
            if not STATE.vcb_buffer or base.DISPATCH.running:
                return self._end(('PASS_THROUGH',))
            t = event.type
            if t in base.MOVE_EVENTS or t in base.PASS_MOUSE or t.endswith("MOUSE") or t.startswith(("TIMER", "NDOF", "WINDOW")):
                return {'PASS_THROUGH'}
            if event.ctrl or event.oskey:
                return {'PASS_THROUGH'}
            if event.value != 'PRESS':
                # swallow the release of the keys we own (a button could react to it)
                return {'RUNNING_MODAL'} if t in VCB_KEYS or event.unicode else {'PASS_THROUGH'}
            _ev, fed = _feed(context, event)
            if fed == 'PASS':
                return {'PASS_THROUGH'}
            if fed == 'APPLY':
                base.DISPATCH.apply_vcb(base.tool_context(context), STATE.vcb_buffer)
                STATE.redraw_statusbar()
                return self._end()
            STATE.redraw_statusbar()
            if fed == 'CANCEL' or not STATE.vcb_buffer:
                return self._end()
            return {'RUNNING_MODAL'}
        except Exception:
            perf.exception("su.vcb_capture")
            return self._end()


class SU_OT_vcb_field_apply(bpy.types.Operator):
    bl_idname = "su.vcb_field_apply"
    bl_label = "SketchUp Mode: apply Measurements text"
    bl_options = {'INTERNAL'}

    text: StringProperty()

    def execute(self, context):
        base.DISPATCH.apply_vcb(base.tool_context(context), self.text)
        return {'FINISHED'}


class SU_OT_coming_soon(bpy.types.Operator):
    bl_idname = "su.coming_soon"
    bl_label = "SketchUp Mode: coming soon"
    bl_options = {'INTERNAL'}

    tool_id: StringProperty()

    def execute(self, context):
        catalog = registry.optional("tools.catalog")
        name = catalog.label(self.tool_id) if catalog is not None else self.tool_id
        STATE.set_hint("app.coming_soon", name=name)
        self.report({'INFO'}, i18n.t("app.coming_soon", name=name))
        return {'FINISHED'}


_field_guard = [False]


def _field_get(_self):
    return STATE.vcb_buffer or STATE.vcb_value


def _field_set(_self, value):
    if _field_guard[0]:
        return
    _field_guard[0] = True
    try:
        if value.strip() and value != STATE.vcb_value:
            base.DISPATCH.apply_vcb(base.tool_context(bpy.context), value)
    except Exception:
        perf.exception("Measurements field")
    finally:
        _field_guard[0] = False


class SU_PG_vcb(bpy.types.PropertyGroup):
    field: StringProperty(name="Medidas", get=_field_get, set=_field_set, options={'SKIP_SAVE'})


_classes = (SU_OT_tool_event, SU_OT_tool_activate, SU_OT_vcb_key, SU_OT_vcb_capture, SU_OT_vcb_field_apply,
            SU_OT_coming_soon, SU_PG_vcb)

STRINGS = {
    "app.coming_soon": {"pt_BR": "Em breve: {name}", "en": "Coming soon: {name}"},
}


def register():
    i18n.register_strings(STRINGS)
    registry.register_classes(_classes)
    bpy.types.WindowManager.su_vcb = PointerProperty(type=SU_PG_vcb)


def unregister():
    _capture_running[0] = False
    if hasattr(bpy.types.WindowManager, "su_vcb"):
        del bpy.types.WindowManager.su_vcb
    registry.unregister_classes(_classes)
