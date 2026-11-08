# SPDX-License-Identifier: GPL-2.0-or-later
"""Shared runtime state (owner: A). Contract: PLANO.md §2.4 (frozen at M-A)."""

from dataclasses import dataclass, field
from typing import Callable, Optional

import bpy
from mathutils import Vector

ORDER = 100

INFERENCE_KINDS = frozenset({
    "NONE", "ENDPOINT", "MIDPOINT", "ON_EDGE", "ON_FACE", "INTERSECTION", "CENTER", "ORIGIN",
    "GUIDE_POINT", "ON_GUIDE", "FREE",
})
LINEAR_KINDS = frozenset({
    "", "AXIS_X", "AXIS_Y", "AXIS_Z", "PARALLEL", "PERPENDICULAR", "PERP_FACE", "FROM_POINT", "TANGENT",
})


@dataclass
class Inference:
    kind: str                                   # one of INFERENCE_KINDS
    point: Vector
    linear: str = ""                            # one of LINEAR_KINDS
    direction: Optional[Vector] = None
    ref_point: Optional[Vector] = None
    ref_edge: Optional[tuple] = None
    normal: Optional[Vector] = None             # ALWAYS of the original face (idx % n_orig)
    side: int = 0                               # +1 front seen, -1 back seen (sign(-dot(ray_dir, normal)))
    plane: Optional[tuple] = None
    doc_key: str = ""
    elem: Optional[tuple] = None                # (kind, index)
    obj_name: str = ""
    in_context: str = ""
    locked: bool = False
    tooltip_key: str = ""
    screen: tuple = (0.0, 0.0)

    @classmethod
    def none(cls):
        return cls(kind="NONE", point=Vector((0.0, 0.0, 0.0)))


@dataclass
class Locks:
    axis: str = ""
    shift: Optional[Inference] = None
    plane: Optional[tuple] = None


@dataclass
class LastAction:
    tool_id: str
    schema: str
    reapply: Callable[[list], bool]


class State:
    def __init__(self):
        self.reset()

    def reset(self):
        self.inference = Inference.none()
        self.locks = Locks()
        self.hint_key = ""
        self.hint_fmt = {}
        self.vcb_label_key = ""
        self.vcb_value = ""
        self.vcb_buffer = ""
        self.vcb_error = False
        self.last_action = None
        self.ref_points = []

    def set_hint(self, key, **fmt):
        if key != self.hint_key or fmt != self.hint_fmt:
            self.hint_key = key
            self.hint_fmt = fmt
            self.redraw_statusbar()

    def set_vcb(self, label_key, value):
        if label_key != self.vcb_label_key or value != self.vcb_value:
            self.vcb_label_key = label_key
            self.vcb_value = value
            self.redraw_statusbar()

    def redraw_viewport(self, region=None):
        if region is not None:
            region.tag_redraw()
            return
        wm = getattr(bpy.context, "window_manager", None)
        if wm is None:
            return
        for win in wm.windows:
            for area in win.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

    def redraw_statusbar(self):
        # Calls the internal function directly: WorkSpace.status_text_set() would also swap
        # STATUSBAR_HT_header.draw back to its "_draw_orig" and could undo D's override.
        wm = getattr(bpy.context, "window_manager", None)
        if wm is None or bpy.app.background:
            return
        for win in wm.windows:
            try:
                with bpy.context.temp_override(window=win):
                    win.workspace.status_text_set_internal(None)
            except Exception:
                pass


STATE = State()
