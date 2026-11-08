# SPDX-License-Identifier: GPL-2.0-or-later
"""Polígono (owner: E). PLANO.md §6.2 (AC-CIR-*): the Círculo controller with 6 sides by default; the
curve metadata kind is "polygon", so Empurrar/puxar keeps its side edges hard."""

from .. import constants, i18n
from .base import ToolMeta, tool
from .circle import ShapeTool

TOOL_ID = "su.polygon"

STRINGS = {
    "tool.su.polygon.label": {"pt_BR": "Polígono", "en": "Polygon"},
    "tool.su.polygon.hint_start": {"pt_BR": "Selecione o ponto central.", "en": "Select center point."},
    "tool.su.polygon.hint_next": {"pt_BR": "Selecione o raio ou digite-o.", "en": "Select radius or enter it."},
    "tool.su.polygon.undo": {"pt_BR": "Polígono", "en": "Polygon"},
}


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.polygon.label", icon="ops.gpencil.primitive_polyline",
               cursor='PAINT_CROSS', vcb_label_key="vcb.radius", vcb_schema="radius"))
class PolygonTool(ShapeTool):
    DEFAULT_SIDES = constants.POLYGON_SIDES
    KIND = "polygon"
    PREFIX = "tool.su.polygon"


def register():
    i18n.register_strings(STRINGS)
