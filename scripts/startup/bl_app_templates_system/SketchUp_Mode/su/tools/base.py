# SPDX-License-Identifier: GPL-2.0-or-later
"""Tool controller base and event dispatcher (owner: A). Contract: PLANO.md §2.4 (frozen at M-A).

A tool is a BaseTool subclass declared with `@tool(ToolMeta(...))`. The platform turns every TOOL/NAV
meta into a Blender WorkSpaceTool (`register_workspace_tools`, called by tools/catalog.py after all
tool modules registered their strings) whose keymap is LEFTMOUSE PRESS/RELEASE → `su.tool_event`, plus
MOUSEMOVE → `su.tool_event` for the idle hover (`tool.hover`; always PASS_THROUGH — see hover_from_event).

EVENT SEMANTICS (contract):
 * keymap of every TOOL: LEFTMOUSE PRESS and RELEASE → su.tool_event (never ANY).
 * su.tool_event handles PRESS/RELEASE (DOUBLE_CLICK = PRESS; clicks counted in Python with clock+distance);
   returns PASS_THROUGH for CLICK, CLICK_DRAG and for PRESS with Ctrl (with or without Cmd/Shift) — on the
   Mac Ctrl+click = context menu and Ctrl+Cmd+drag = orbit/pan (Window keymap items).
 * NAV tools (Orbit/Pan/Zoom) do not use su.tool_event: keymap LEFTMOUSE PRESS → meta.operator.
 * In the modal: MMB/wheel/trackpad/NDOF → PASS_THROUGH; event outside the 3D region → PASS_THROUGH;
   another tool's key with empty VCB buffer → cancel + PASS_THROUGH; Cmd+Z → cancel + PASS_THROUGH
   (the undo then runs); RIGHTMOUSE → ignored.
 * Exception in a controller → cancel() + perf.error + one-line report; the modal ends.

Results: a controller method returns Result.RUNNING (operation in progress: the modal keeps running),
Result.IDLE (nothing in progress: the modal ends) or Result.PASS (event not used: passed on, state unchanged).

The same `DISPATCH.handle(tc, ev, inf)` routes events for the real modal (ops/tool_ops.py) and for
headless tests (`testing.dispatch`), so unit tests exercise the real routing.
"""

import math
import time
from dataclasses import dataclass
from enum import Enum
from types import SimpleNamespace
from typing import Callable, ClassVar

import bpy
from mathutils import Vector, geometry

from .. import constants, events, perf, registry
from ..core import state as _state

ORDER = 300


class Result(Enum):
    IDLE = 0
    RUNNING = 1
    PASS = 2


@dataclass(frozen=True)
class ToolMeta:
    id: str
    label_key: str
    icon: str
    kind: str = 'TOOL'          # 'TOOL' | 'COMMAND' | 'NAV'
    operator: str = ''          # COMMAND: operator executed; NAV: LEFTMOUSE operator (view3d.rotate, ...)
    shortcut: str = ''          # Blender event type with optional modifiers: "L", "SPACE", "shift+Z"
    cursor: str = 'DEFAULT'
    vcb_label_key: str = ''
    vcb_schema: str = ''
    priority: str = 'P0'
    enabled: bool = True
    search_synonyms: tuple = ()


@dataclass
class Ev:
    type: str
    value: str
    x: int
    y: int
    unicode: str = ''
    shift: bool = False
    copy: bool = False           # modifiers.is_copy (Option on the Mac)
    alt_action: bool = False     # modifiers.is_alt_action (Cmd on the Mac)
    ctrl: bool = False
    clicks: int = 1
    is_drag_release: bool = False
    t: float = 0.0
    press_x: int = 0
    press_y: int = 0


@dataclass
class ToolContext:
    """What a controller gets as `tc`. In headless tests context/region/rv3d are None."""
    context: object = None
    window: object = None
    area: object = None
    region: object = None        # the 3D view WINDOW region (physical px coordinates)
    rv3d: object = None
    depsgraph: object = None
    scene: object = None
    xy: tuple = (0, 0)


class BaseTool:
    meta: ClassVar[ToolMeta]
    inference_flags: ClassVar[frozenset] = frozenset()

    def activate(self, tc):
        pass

    def deactivate(self, tc):
        pass

    def hover(self, tc, inf):
        pass

    def press(self, tc, ev, inf):
        return Result.IDLE

    def release(self, tc, ev, inf):
        return Result.IDLE

    def move(self, tc, ev, inf):
        return Result.IDLE

    def key(self, tc, ev):
        return Result.PASS

    def vcb(self, tc, values):
        return Result.PASS

    def cancel(self, tc):
        pass

    def query_ctx(self, tc, xy):
        """QueryCtx for the inference engine at `xy` (default: make_query(tc, xy))."""
        return None

    def draw_3d(self, dc):
        pass

    def draw_2d(self, dc):
        pass

    def update_status(self):
        pass


clock: Callable[[], float] = time.monotonic


def now():
    """Current time from the (injectable) clock. Use base.now(), never time.*, in controllers."""
    return clock()


TOOLS = {}           # id -> BaseTool subclass
_instances = {}      # id -> controller instance


def tool(meta):
    """Class decorator: declares a tool controller (`meta.id` must be unique)."""
    def deco(cls):
        if meta.id in TOOLS and TOOLS[meta.id].__qualname__ != cls.__qualname__:
            raise KeyError("tool id registered twice: {!r}".format(meta.id))
        cls.meta = meta
        TOOLS[meta.id] = cls
        _instances.pop(meta.id, None)
        return cls
    return deco


def active_tool_id(context=None):
    context = context or bpy.context
    ws = getattr(context, "workspace", None)
    if ws is None:
        return ''
    try:
        t = ws.tools.from_space_view3d_mode('OBJECT', create=False)
    except Exception:
        return ''
    return t.idname if t is not None else ''


def controller(tool_id=None):
    """Singleton controller instance of `tool_id` (default: the dispatcher's tool), or None."""
    tool_id = tool_id or DISPATCH.tool_id or active_tool_id()
    cls = TOOLS.get(tool_id)
    if cls is None:
        return None
    inst = _instances.get(tool_id)
    if inst is None:
        inst = _instances[tool_id] = cls()
    return inst


# ---------------------------------------------------------------------------------------------- context

def find_view3d(context=None):
    """(window, area, WINDOW region, rv3d) of the largest 3D view of the main window, or Nones."""
    context = context or bpy.context
    wm = getattr(context, "window_manager", None)
    if wm is None or not wm.windows:
        return None, None, None, None
    win = wm.windows[0]
    areas = [a for a in win.screen.areas if a.type == 'VIEW_3D']
    if not areas:
        return win, None, None, None
    area = max(areas, key=lambda a: a.width * a.height)
    region = next((r for r in area.regions if r.type == 'WINDOW'), None)
    return win, area, region, area.spaces.active.region_3d


def set_workspace_tool(tool_id):
    """Make `tool_id` the workspace's active tool (GUI) and follow it."""
    win, area, region, _rv3d = find_view3d()
    if area is None:
        return False
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.wm.tool_set_by_id(name=tool_id, space_type='VIEW_3D')
    DISPATCH.sync(tool_context())
    return True


def tool_context(context=None, region=None, rv3d=None, xy=(0, 0)):
    """ToolContext for `context` (region defaults to the 3D view WINDOW region of the main window)."""
    context = context or bpy.context
    win = getattr(context, "window", None)
    area = getattr(context, "area", None)
    if region is None or rv3d is None:
        r = getattr(context, "region", None)
        if r is not None and r.type == 'WINDOW' and area is not None and area.type == 'VIEW_3D':
            region, rv3d = r, context.region_data
        elif not bpy.app.background:
            win2, area, region, rv3d = find_view3d(context)
            win = win or win2
    try:
        depsgraph = context.evaluated_depsgraph_get() if region is not None else None
    except Exception:
        depsgraph = None
    return ToolContext(context=context, window=win, area=area, region=region, rv3d=rv3d,
                       depsgraph=depsgraph, scene=getattr(context, "scene", None), xy=tuple(xy))


def event_from_bpy(event, region=None):
    """tools.base.Ev from a bpy event; x/y are coordinates of `region` (default: event's region)."""
    if region is not None:
        x, y = event.mouse_x - region.x, event.mouse_y - region.y
    else:
        x, y = event.mouse_region_x, event.mouse_region_y
    return Ev(type=event.type, value=event.value, x=int(x), y=int(y), unicode=event.unicode or '',
              shift=event.shift, copy=event.alt, alt_action=event.oskey, ctrl=event.ctrl, t=now())


# ---------------------------------------------------------------------------------------------- inference

def make_query(tc, xy, **kw):
    """C's inference.QueryCtx for `xy` (or a SimpleNamespace with the same fields while C is absent).
    Defaults: previous = STATE.inference, locks = STATE.locks."""
    kw.setdefault("previous", _state.STATE.inference)
    kw.setdefault("locks", _state.STATE.locks)
    inference = registry.optional("core.inference")
    if inference is not None and hasattr(inference, "QueryCtx"):
        return inference.QueryCtx(region=tc.region, rv3d=tc.rv3d, xy=tuple(xy), depsgraph=tc.depsgraph, **kw)
    q = SimpleNamespace(region=tc.region, rv3d=tc.rv3d, xy=tuple(xy), depsgraph=tc.depsgraph, anchor=None,
                        anchor_normal=None, plane=None, line=None, flags=None, exclude=frozenset(), skip=None,
                        locks=None, previous=None)
    for k, v in kw.items():
        setattr(q, k, v)
    return q


def _fallback_query(q):
    """Free point on the anchor's horizontal plane (or the ground) while C's engine is absent."""
    if q.region is None or q.rv3d is None:
        return _state.Inference.none()
    from ..core import viewutil
    origin, direction = viewutil.mouse_ray(q.region, q.rv3d, q.xy)
    if q.plane is not None:
        co, no = q.plane
    else:
        co = Vector(q.anchor) if q.anchor is not None else Vector((0.0, 0.0, 0.0))
        no = Vector((0.0, 0.0, 1.0))
    p = geometry.intersect_line_plane(origin, origin + direction, co, no)
    if p is None or (p - origin).dot(direction) < 0.0:
        return _state.Inference.none()
    return _state.Inference(kind="FREE", point=p, plane=(Vector(co), Vector(no)), screen=tuple(q.xy))


def run_query(q):
    inference = registry.optional("core.inference")
    if inference is not None and hasattr(inference, "ENGINE"):
        return inference.ENGINE.query(q)
    return _fallback_query(q)


def query(tc, xy, ctrl=None):
    """Inference under `xy` for the active controller (its query_ctx, else make_query)."""
    q = ctrl.query_ctx(tc, xy) if ctrl is not None else None
    if q is None:
        q = make_query(tc, xy)
    return run_query(q)


# ---------------------------------------------------------------------------------------------- VCB helpers

def units():
    scene = getattr(bpy.context, "scene", None)
    return getattr(scene, "su_units", None)


def fmt_length(m):
    """Length for the Measurements box (C's units.format_length; plain "1,23m" while C is absent)."""
    u = registry.optional("core.units")
    if u is not None and hasattr(u, "format_length"):
        return u.format_length(m, units())
    return "{:.2f}m".format(m).replace(".", ",")


def value_of(v):
    """Float of a parsed VCB value (C's VCBValue has `.value`; plain numbers accepted)."""
    return float(getattr(v, "value", v))


def kind_of(v):
    return getattr(v, "kind", "LENGTH")


# ---------------------------------------------------------------------------------------------- shortcuts

MODIFIER_KEYS = frozenset({'LEFT_SHIFT', 'RIGHT_SHIFT', 'LEFT_CTRL', 'RIGHT_CTRL', 'LEFT_ALT', 'RIGHT_ALT',
                           'OSKEY', 'APP', 'HYPER'})
PASS_MOUSE = frozenset({'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'WHEELINMOUSE', 'WHEELOUTMOUSE',
                        'TRACKPADPAN', 'TRACKPADZOOM', 'MOUSEROTATE', 'MOUSESMARTZOOM', 'BUTTON4MOUSE',
                        'BUTTON5MOUSE', 'BUTTON6MOUSE', 'BUTTON7MOUSE', 'PEN', 'ERASER'})
MOVE_EVENTS = frozenset({'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'})
PRESS_VALUES = frozenset({'PRESS', 'DOUBLE_CLICK'})


def parse_shortcut(s):
    """"shift+Z" -> ('Z', frozenset({'shift'})). Modifier names: shift ctrl alt oskey."""
    parts = [p.strip() for p in s.split("+") if p.strip()]
    if not parts:
        return None
    return parts[-1].upper(), frozenset(p.lower() for p in parts[:-1])


def shortcut_tool(ev):
    """Id of the TOOL/NAV whose shortcut is `ev` (PRESS), or ''."""
    mods = set()
    if ev.shift:
        mods.add("shift")
    if ev.ctrl:
        mods.add("ctrl")
    if ev.copy:
        mods.add("alt")
    if ev.alt_action:
        mods.add("oskey")
    for tid, cls in TOOLS.items():
        sc = parse_shortcut(cls.meta.shortcut) if cls.meta.shortcut else None
        if sc is not None and sc[0] == ev.type and sc[1] == mods:
            return tid
    return ''


# ---------------------------------------------------------------------------------------------- dispatcher

class Dispatcher:
    """Single router of tool events (GUI modal, hover gizmo, Window keymap, headless tests)."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.tool_id = ''
        self.running = False
        self.last_error = ''
        self.last_event = None
        self._press = None          # (t, x, y, clicks) of the last LEFTMOUSE press

    # -- tool switching ---------------------------------------------------------------------------
    def set_tool(self, tc, tool_id):
        """Make `tool_id` the dispatcher's tool: cancel/deactivate the old one, activate the new one."""
        old = self.tool_id
        if tool_id == old:
            return
        octrl = controller(old) if old else None
        if octrl is not None:
            if self.running:
                self._safe(octrl.cancel, tc)
            self._safe(octrl.deactivate, tc)
        self.running = False
        self._press = None
        self.tool_id = tool_id
        st = _state.STATE
        st.inference = _state.Inference.none()
        st.locks = _state.Locks()
        st.last_action = None
        st.vcb_buffer = ''
        st.vcb_error = False
        st.ref_points = []
        st.set_hint('')
        meta = TOOLS[tool_id].meta if tool_id in TOOLS else None
        st.set_vcb(meta.vcb_label_key if meta else '', '')
        nctrl = controller(tool_id) if tool_id else None
        if nctrl is not None:
            self._safe(nctrl.activate, tc)
            self._safe(nctrl.update_status)
        events.emit("tool", old=old, new=tool_id)

    def sync(self, tc):
        """Follow the workspace's active tool (GUI only: toolbar/LTS clicks bypass su.tool_activate)."""
        tid = active_tool_id(tc.context)
        if tid == self.tool_id:
            return
        back = self.tool_id if self.tool_id in TOOLS else ''
        if tid.startswith("su.") and tid not in TOOLS and back:
            # a disabled placeholder of the toolbar/LTS was clicked: "Em breve" and back to our tool
            catalog = registry.optional("tools.catalog")
            name = catalog.label(tid) if catalog is not None else tid
            _state.STATE.set_hint("app.coming_soon", name=name)
            registry.deferred(lambda: set_workspace_tool(back), 0.0)
            return
        self.set_tool(tc, tid)

    def _safe(self, fn, *args):
        try:
            return fn(*args)
        except Exception:
            perf.exception("tool {:s}.{:s}".format(self.tool_id, getattr(fn, "__name__", "?")))
            return None

    # -- events -----------------------------------------------------------------------------------
    def handle(self, tc, ev, inf=None):
        """Route one event to the controller. Returns Result (PASS = not used, pass it on)."""
        self.last_event = ev                     # diagnostics (GUI scenarios check modifiers arrive)
        ctrl = controller(self.tool_id) if self.tool_id else None
        if ctrl is None:
            return Result.PASS
        try:
            r = self._route(tc, ctrl, ev, inf)
        except Exception as ex:
            self.last_error = "{:s}: {:s}".format(type(ex).__name__, str(ex))
            perf.exception("tool {:s}: event {:s} {:s}".format(self.tool_id, ev.type, ev.value))
            try:
                ctrl.cancel(tc)
            except Exception:
                perf.exception("tool {:s}.cancel after error".format(self.tool_id))
            self.running = False
            _state.STATE.redraw_viewport(tc.region)
            return Result.IDLE
        if r is None:
            r = Result.RUNNING if self.running else Result.IDLE
        if r is not Result.PASS:
            was = self.running
            self.running = (r is Result.RUNNING)
            if was and not self.running and ev.type not in MOVE_EVENTS:
                _state.STATE.inference = _state.Inference.none()   # no stale marker/tooltip after the op
                _state.STATE.redraw_viewport(tc.region)
        return r

    def _inference(self, tc, ctrl, ev, inf):
        if inf is None:
            inf = query(tc, (ev.x, ev.y), ctrl)
        _state.STATE.inference = inf
        engine = getattr(registry.optional("core.inference"), "ENGINE", None)
        if engine is not None and hasattr(engine, "acquire_tick"):
            engine.acquire_tick(inf, ev.t or now())
        return inf

    def _route(self, tc, ctrl, ev, inf):
        st = _state.STATE
        t, v = ev.type, ev.value
        if not ev.t:
            ev.t = now()
        if t == 'LEFTMOUSE':
            if v in PRESS_VALUES:
                if ev.ctrl:
                    return Result.PASS
                ev.value = 'PRESS'
                self._count_click(ev)
                inf = self._inference(tc, ctrl, ev, inf)
                r = ctrl.press(tc, ev, inf)
            elif v == 'RELEASE':
                if self._press is None:
                    return Result.PASS
                ev.press_x, ev.press_y = self._press[1], self._press[2]
                ev.clicks = self._press[3]
                lim = constants.DRAG_THRESHOLD_PX * _ui_scale()
                ev.is_drag_release = math.hypot(ev.x - ev.press_x, ev.y - ev.press_y) > lim
                inf = self._inference(tc, ctrl, ev, inf)
                r = ctrl.release(tc, ev, inf)
            else:
                return Result.PASS          # CLICK, CLICK_DRAG, ...
            st.redraw_viewport(tc.region)
            return r
        if t in MOVE_EVENTS:
            inf = self._inference(tc, ctrl, ev, inf)
            if self.running:
                r = ctrl.move(tc, ev, inf)
            else:
                ctrl.hover(tc, inf)
                r = Result.IDLE
            st.redraw_viewport(tc.region)
            return r
        if t == 'RIGHTMOUSE':
            return Result.RUNNING if self.running else Result.PASS
        if t in PASS_MOUSE or t.startswith("NDOF") or t.startswith("TIMER") or t.startswith("WINDOW") \
                or t in {'NONE', 'ACTIONZONE_AREA', 'ACTIONZONE_REGION', 'ACTIONZONE_FULLSCREEN', 'XR_ACTION'}:
            return Result.PASS
        return self._key(tc, ctrl, ev)

    def _key(self, tc, ctrl, ev):
        st = _state.STATE
        if ev.type in MODIFIER_KEYS:
            if ev.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} and self.running:
                inf = st.inference
                if ev.value == 'PRESS' and inf.kind not in {"NONE", "FREE"} and st.locks.shift is None:
                    st.locks.shift = inf
                elif ev.value == 'RELEASE':
                    st.locks.shift = None
            r = ctrl.key(tc, ev)
            return Result.PASS if r is Result.PASS else r
        if ev.value != 'PRESS':
            return Result.PASS
        if ev.ctrl or ev.alt_action:
            if self.running and ev.alt_action and ev.type == 'Z':
                self.cancel(tc)
            return Result.PASS
        vcb = registry.optional("core.vcb")
        fed = vcb.feed(ev) if vcb is not None else 'PASS'
        if fed == 'CONSUMED':
            st.redraw_statusbar()
            return Result.RUNNING if self.running else Result.IDLE
        if fed == 'CANCEL':
            st.vcb_error = False
            st.redraw_statusbar()
            return Result.RUNNING if self.running else Result.IDLE
        if fed == 'APPLY':
            text = st.vcb_buffer
            r = self.apply_vcb(tc, text)
            return r
        # not for the Measurements box
        if ev.type == 'ESC':
            if self.running:
                self.cancel(tc)
                return Result.IDLE
            return Result.PASS
        if ev.type in {'UP_ARROW', 'DOWN_ARROW', 'LEFT_ARROW', 'RIGHT_ARROW'}:
            inference = registry.optional("core.inference")
            if inference is not None and hasattr(inference, "lock_from_arrow"):
                inference.lock_from_arrow(ev.type, st.locks)
                st.redraw_viewport(tc.region)
                r = ctrl.key(tc, ev)
                return (Result.RUNNING if self.running else Result.IDLE) if r is Result.PASS else r
        r = ctrl.key(tc, ev)
        if r is not Result.PASS:
            return r
        if self.running and not st.vcb_buffer and shortcut_tool(ev):
            self.cancel(tc)
            return Result.PASS
        return Result.PASS      # other keys (e.g. K = Arestas traseiras) reach the Window keymap; the op continues

    def _count_click(self, ev):
        p = self._press
        lim = constants.MULTI_CLICK_DIST_PX * _ui_scale()
        if p is not None and ev.t - p[0] <= constants.DOUBLE_CLICK_S and math.hypot(ev.x - p[1], ev.y - p[2]) <= lim:
            ev.clicks = p[3] + 1
        else:
            ev.clicks = 1
        self._press = (ev.t, ev.x, ev.y, ev.clicks)

    def cancel(self, tc):
        ctrl = controller(self.tool_id) if self.tool_id else None
        if ctrl is not None:
            self._safe(ctrl.cancel, tc)
        self.running = False
        _state.STATE.locks = _state.Locks()
        _state.STATE.inference = _state.Inference.none()
        _state.STATE.redraw_viewport(tc.region)

    def hover(self, tc, xy):
        """Idle mouse move (hover gizmo / testing.hover)."""
        ev = Ev(type='MOUSEMOVE', value='NOTHING', x=int(xy[0]), y=int(xy[1]), t=now())
        return self.handle(tc, ev)

    # -- Measurements box -------------------------------------------------------------------------
    def apply_vcb(self, tc, text):
        """APPLY of the Measurements box (PLANO §3.5-4): running → tool.vcb; idle with last_action →
        reapply + undo "undo.adjust"; idle without → tool.vcb (pre-click parameters)."""
        st = _state.STATE
        ctrl = controller(self.tool_id) if self.tool_id else None
        la = st.last_action
        if self.running and ctrl is not None:
            schema, target = ctrl.meta.vcb_schema, ("tool", ctrl)
        elif la is not None:
            schema, target = la.schema, ("reapply", la)
        elif ctrl is not None:
            schema, target = ctrl.meta.vcb_schema, ("tool", ctrl)
        else:
            return Result.PASS
        vcb = registry.optional("core.vcb")
        try:
            values = vcb.parse(text, schema or 'length', units()) if vcb is not None else [float(text.replace(",", "."))]
        except Exception:
            values = None
        if not values:
            st.vcb_error = True
            st.redraw_statusbar()
            return Result.RUNNING if self.running else Result.IDLE
        st.vcb_buffer = ''
        st.vcb_error = False
        if target[0] == "reapply":
            ok = False
            try:
                ok = la.reapply(values)
            except Exception:
                perf.exception("reapply {:s}".format(la.tool_id))
            if ok:
                from ..core import undo
                undo.push("undo.adjust")
            r = Result.IDLE
        else:
            r = target[1].vcb(tc, values)
            if r is Result.PASS:
                r = Result.RUNNING if self.running else Result.IDLE
        st.redraw_statusbar()
        st.redraw_viewport(tc.region)
        return r

    # -- drawing ----------------------------------------------------------------------------------
    def draw(self, dc, phase):
        ctrl = controller(self.tool_id) if self.tool_id else None
        if ctrl is None:
            return
        (ctrl.draw_3d if phase == 'POST_VIEW' else ctrl.draw_2d)(dc)


DISPATCH = Dispatcher()


def _ui_scale():
    try:
        s = bpy.context.preferences.system.ui_scale
    except Exception:
        s = 0.0
    return s if s > 0.0 else 1.0          # 0 in background (no window yet)


def is_running():
    return DISPATCH.running


# ---------------------------------------------------------------------------------------------- Blender tools

HOVER_CALLS = [0]      # idle hover events handled (diagnostics for GUI scenarios)


def hover_from_event(context, event):
    """Idle MOUSEMOVE over the 3D region: tool keymap MOUSEMOVE → su.tool_event → here.

    The hover rides on the tool keymap (the operator returns PASS_THROUGH) instead of a gizmo's
    test_select: gizmos are disabled in the mode's viewport (`space.show_gizmo = False`, D's style)."""
    HOVER_CALLS[0] += 1
    xy = (event.mouse_region_x, event.mouse_region_y)
    tc = tool_context(context, xy=xy)
    DISPATCH.sync(tc)
    if not DISPATCH.running:
        DISPATCH.hover(tc, xy)


_bl_tools = []       # registered WorkSpaceTool classes


def tool_keymap(meta):
    if meta.kind == 'NAV':
        return ((meta.operator, {"type": 'LEFTMOUSE', "value": 'PRESS'}, None),)
    # "any": True — Shift/Option/Cmd+click and drag must reach the tools (Ctrl is passed on by su.tool_event)
    return (("su.tool_event", {"type": 'LEFTMOUSE', "value": 'PRESS', "any": True}, None),
            ("su.tool_event", {"type": 'LEFTMOUSE', "value": 'RELEASE', "any": True}, None),
            ("su.tool_event", {"type": 'MOUSEMOVE', "value": 'ANY', "any": True}, None))


def make_workspace_tool(meta, label):
    attrs = {
        "bl_space_type": 'VIEW_3D',
        "bl_context_mode": 'OBJECT',
        "bl_idname": meta.id,
        "bl_label": label,
        "bl_description": label,
        "bl_icon": meta.icon or "ops.generic.select",
        "bl_cursor": meta.cursor or 'DEFAULT',
        "bl_keymap": tool_keymap(meta),
    }
    return type("SU_WST_" + meta.id.replace(".", "_"), (bpy.types.WorkSpaceTool,), attrs)


def register_workspace_tools():
    """WorkSpaceTool for every TOOL/NAV meta (called by catalog.register, after the tools' strings)."""
    from .. import i18n
    for tid in sorted(TOOLS):
        meta = TOOLS[tid].meta
        if meta.kind not in {'TOOL', 'NAV'} or not meta.enabled:
            continue
        cls = make_workspace_tool(meta, i18n.t(meta.label_key))
        try:
            bpy.utils.register_tool(cls)
        except Exception:
            perf.exception("register_tool {:s}".format(tid))
            continue
        _bl_tools.append(cls)


def unregister_workspace_tools():
    while _bl_tools:
        cls = _bl_tools.pop()
        try:
            bpy.utils.unregister_tool(cls)
        except Exception:
            perf.exception("unregister_tool {:s}".format(cls.bl_idname))


def bl_tool(tool_id):
    """The ToolDef Blender built for `tool_id` (for the Large Tool Set layout), or None."""
    for cls in _bl_tools:
        if cls.bl_idname == tool_id:
            return getattr(cls, "_bl_tool", None)
    return None


def register():
    pass       # WorkSpaceTools are created by catalog.register; register() puts us in su._active


def unregister():
    unregister_workspace_tools()
    DISPATCH.reset()
    _instances.clear()
