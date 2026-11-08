# SPDX-License-Identifier: GPL-2.0-or-later
"""Navigation tools (owner: G). PLANO.md §4.3 rows 16–18, §5.3, §6.3, Apêndice A.

  Órbita (O), Panorâmica (H), Aplicar zoom (Z): kind NAV — the tool keymap's LEFTMOUSE PRESS runs
  `meta.operator` (ops/view_ops.py) directly, without su.tool_event. Aplicar zoom also takes a typed
  field of view in the Measurements box ("Campo de visão": `35` = degrees, `50mm` = focal length).
  Extensões de zoom (Shift+Z) and Anterior: kind COMMAND (toolbar/menu/shortcut run the operator).
When a COMMAND id becomes the workspace tool (Large Tool Set button), its controller runs the
command and gives the previous tool back (SketchUp: Zoom Extents does not change the tool).
"""

import math

from .. import events, i18n, registry
from ..core import camera
from ..core.state import STATE
from .base import BaseTool, Result, ToolMeta, kind_of, tool

STRINGS = {
    "tool.su.orbit.label": {"pt_BR": "Órbita", "en": "Orbit"},
    "tool.su.orbit.hint": {"pt_BR": "Arraste para orbitar. Shift = Panorâmica. Clique duplo = centralizar.",
                           "en": "Drag to orbit. Shift = Pan. Double-click = center."},
    "tool.su.pan.label": {"pt_BR": "Panorâmica", "en": "Pan"},
    "tool.su.pan.hint": {"pt_BR": "Arraste para fazer uma panorâmica.", "en": "Drag to pan."},
    "tool.su.zoom.label": {"pt_BR": "Aplicar zoom", "en": "Zoom"},
    "tool.su.zoom.hint": {"pt_BR": "Arraste para cima ou para baixo para aplicar zoom. Shift = Campo de visão.",
                          "en": "Drag up or down to zoom. Shift = Field of view."},
    "tool.su.zoom_extents.label": {"pt_BR": "Extensões de zoom", "en": "Zoom Extents"},
    "tool.su.previous.label": {"pt_BR": "Anterior", "en": "Previous"},
}


@tool(ToolMeta(id="su.orbit", label_key="tool.su.orbit.label", icon="draw.orbit", kind='NAV',
               operator="su.view_orbit", shortcut="O", cursor='HAND_CLOSED', search_synonyms=("Orbitar",)))
class OrbitTool(BaseTool):
    def activate(self, tc):
        self.update_status()

    def update_status(self):
        STATE.set_hint("tool.su.orbit.hint")


@tool(ToolMeta(id="su.pan", label_key="tool.su.pan.label", icon="draw.pan", kind='NAV',
               operator="su.view_pan", shortcut="H", cursor='HAND', search_synonyms=("Pan",)))
class PanTool(BaseTool):
    def activate(self, tc):
        self.update_status()

    def update_status(self):
        STATE.set_hint("tool.su.pan.hint")


def fov_from_text(text, value):
    """Typed field of view: '50mm' → focal length on a 35 mm film (24 mm high), else degrees."""
    t = (text or "").strip().lower().replace(" ", "")
    if t.endswith("mm"):
        try:
            mm = float(t[:-2].replace(",", "."))
        except ValueError:
            return None
        return math.degrees(2.0 * math.atan(12.0 / mm)) if mm > 0 else None
    try:
        deg = float(t.replace(",", ".")) if t else float(value)
    except (TypeError, ValueError):
        return None
    return deg if 1.0 <= deg <= 120.0 else None


@tool(ToolMeta(id="su.zoom", label_key="tool.su.zoom.label", icon="draw.zoom", kind='NAV',
               operator="su.view_zoom", shortcut="Z", cursor='ZOOM_IN', vcb_label_key="vcb.fov",
               vcb_schema="length", search_synonyms=("Zoom",)))
class ZoomTool(BaseTool):
    def activate(self, tc):
        self.update_status()

    def update_status(self):
        STATE.set_hint("tool.su.zoom.hint")
        STATE.set_vcb(self.meta.vcb_label_key, _fov_text(camera.fov_v()))

    def vcb(self, tc, values):
        if not values:
            return Result.PASS
        v = values[0]
        deg = fov_from_text(getattr(v, "text", ""), getattr(v, "value", None)) if kind_of(v) in {
            "LENGTH", "NUMBER"} else None
        if deg is None:
            STATE.vcb_error = True
            return Result.IDLE
        camera.set_fov_v(deg)
        STATE.set_vcb(self.meta.vcb_label_key, _fov_text(deg))
        return Result.IDLE


def _fov_text(deg):
    units = registry.optional("core.units")
    if units is not None and hasattr(units, "format_angle"):
        return units.format_angle(math.radians(deg))
    return "{:.1f}°".format(deg).replace(".", ",")


_last_tool = ["su.select"]


class _Command(BaseTool):
    """COMMAND kind: when it becomes the workspace tool (LTS button), run it and go back."""

    def run(self):
        pass

    def activate(self, tc):
        self.run()
        back = _last_tool[0]
        from . import base
        registry.deferred(lambda: base.set_workspace_tool(back), 0.0)


@tool(ToolMeta(id="su.zoom_extents", label_key="tool.su.zoom_extents.label", icon="draw.zoom_extents",
               kind='COMMAND', operator="su.zoom_extents_cmd", shortcut="shift+Z",
               search_synonyms=("Zoom estendido",)))
class ZoomExtentsCommand(_Command):
    def run(self):
        camera.zoom_extents()


@tool(ToolMeta(id="su.previous", label_key="tool.su.previous.label", icon="draw.previous", kind='COMMAND',
               operator="su.view_previous", priority='P1'))
class PreviousCommand(_Command):
    def run(self):
        camera.previous()


def _on_tool(old='', new='', **_kw):
    from . import base
    cls = base.TOOLS.get(new)
    if cls is not None and cls.meta.kind != 'COMMAND':
        _last_tool[0] = new


def register():
    i18n.register_strings(STRINGS)
    events.subscribe("tool", _on_tool)


def unregister():
    events.unsubscribe("tool", _on_tool)
