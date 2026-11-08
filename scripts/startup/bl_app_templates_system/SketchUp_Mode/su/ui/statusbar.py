# SPDX-License-Identifier: GPL-2.0-or-later
"""Status bar (owner: D). PLANO.md §3.4; ported from the spike.

Left: pin + ⓘ icons, a LINE separator and the hint (`STATE.hint_key` through i18n; idle = the Selecionar
hint, with "Option" on the Mac by `modifiers.label()`). Right: the Measurements label
(`STATE.vcb_label_key`, idle "Medidas") and the field `wm.su_vcb.field` (A). `template_reports_banner`
is omitted on purpose (yellow banner). Redraw: `STATE.redraw_statusbar()` (status_text_set_internal(None)
keeps this override).
"""

import sys

import bpy

from .. import i18n, registry
from .. import icons
from ..core.state import STATE

ORDER = 540

VCB_UNITS_X = 11

STRINGS = {
    "ui.hint.idle": "Clique ou arraste para selecionar objetos. Shift = Adicionar/Subtrair. "
                    "{copy} = Adicionar. Shift + {copy} = Subtrair.",
    "ui.vcb.idle": "Medidas",
}


def _sib(name):
    return sys.modules.get(__package__.rsplit(".", 1)[0] + "." + name)


def copy_modifier_label():
    """'Option' on the Mac (A's modifiers.label), 'Ctrl' elsewhere."""
    mod = _sib("modifiers")
    if mod is not None and hasattr(mod, "label"):
        for name in ("copy", "COPY", "alt"):
            try:
                s = mod.label(name)
                if s:
                    return s
            except Exception:
                continue
    return "Option" if sys.platform == "darwin" else "Ctrl"


def hint_text():
    if STATE.hint_key:
        return i18n.t(STATE.hint_key, **(STATE.hint_fmt or {}))
    return i18n.t("ui.hint.idle", copy=copy_modifier_label())


def vcb_label():
    if STATE.vcb_label_key:
        return i18n.t(STATE.vcb_label_key)
    return i18n.t("ui.vcb.idle")


def _vcb_owner(context):
    """(data, prop) of the Measurements field: A's wm.su_vcb.field, else D's fallback string."""
    wm = context.window_manager
    vcb = getattr(wm, "su_vcb", None)
    if vcb is not None and hasattr(vcb, "field"):
        return vcb, "field"
    return wm.su_tray, "vcb_fallback"


def draw(self, context):
    layout = self.layout
    row = layout.row(align=True)
    row.label(text="", icon_value=icons.ui_icon("pin"))
    row.label(text="", icon_value=icons.ui_icon("info"))
    row.separator(factor=0.5, type='LINE')
    row.label(text=hint_text())
    layout.separator_spacer()
    layout.separator_spacer()
    r = layout.row(align=True)
    r.separator(factor=0.5, type='LINE')
    r.label(text=vcb_label())
    s = r.row(align=True)
    s.ui_units_x = VCB_UNITS_X
    data, prop = _vcb_owner(context)
    s.prop(data, prop, text="")


def register():
    i18n.register_strings(STRINGS)
    registry.override(bpy.types.STATUSBAR_HT_header, "draw", draw)
    # WorkSpace.status_text_set(None) restores `_draw_orig`: make it ours too (modal ops call it).
    registry.override(bpy.types.STATUSBAR_HT_header, "_draw_orig", draw)


def unregister():
    i18n.unregister_strings(STRINGS)
