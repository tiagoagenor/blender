# SPDX-License-Identifier: GPL-2.0-or-later
"""Tool controller base (owner: A). Contract: PLANO.md §2.4 (frozen at M-A).

A0 skeleton: ToolMeta, Ev, Result, BaseTool (no-op methods), the @tool registry and
active_tool_id/controller. `su.tool_event`, the hover gizmo and click counting arrive in the slice (M-A).

EVENT SEMANTICS (contract):
 * keymap of every TOOL: LEFTMOUSE PRESS and RELEASE → su.tool_event (never ANY).
 * su.tool_event handles PRESS/RELEASE (DOUBLE_CLICK = PRESS; clicks counted in Python with clock+distance);
   returns PASS_THROUGH for CLICK, CLICK_DRAG and for PRESS with Ctrl (with or without Cmd/Shift) — on the
   Mac Ctrl+click = context menu and Ctrl+Cmd+drag = orbit/pan (Window keymap items).
 * NAV tools (Orbit/Pan/Zoom) do not use su.tool_event: keymap LEFTMOUSE PRESS → meta.operator.
 * In the modal: MMB/wheel/trackpad/NDOF → PASS_THROUGH; event outside the 3D region → PASS_THROUGH;
   another tool's key with empty VCB buffer → cancel + PASS_THROUGH; Cmd+Z → cancel; RIGHTMOUSE → ignored.
 * Exception in a controller → cancel() + perf.error + one-line report; the modal ends.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, ClassVar

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
    shortcut: str = ''
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
        return None             # C's QueryCtx once inference exists

    def draw_3d(self, dc):
        pass

    def draw_2d(self, dc):
        pass

    def update_status(self):
        pass


clock: Callable[[], float] = time.monotonic

TOOLS = {}           # id -> BaseTool subclass
_instances = {}      # id -> controller instance


def tool(meta):
    """Class decorator: declares a tool controller (`meta.id` must be unique)."""
    def deco(cls):
        if meta.id in TOOLS and TOOLS[meta.id] is not cls:
            raise KeyError("tool id registered twice: {!r}".format(meta.id))
        cls.meta = meta
        TOOLS[meta.id] = cls
        _instances.pop(meta.id, None)
        return cls
    return deco


def active_tool_id(context=None):
    import bpy
    context = context or bpy.context
    ws = getattr(context, "workspace", None)
    if ws is None:
        return ''
    t = ws.tools.from_space_view3d_mode('OBJECT', create=False)
    return t.idname if t is not None else ''


def controller(tool_id=None):
    """Singleton controller instance of `tool_id` (default: active tool), or None."""
    tool_id = tool_id or active_tool_id()
    cls = TOOLS.get(tool_id)
    if cls is None:
        return None
    inst = _instances.get(tool_id)
    if inst is None:
        inst = _instances[tool_id] = cls()
    return inst


def unregister():
    _instances.clear()
