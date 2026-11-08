# SPDX-License-Identifier: GPL-2.0-or-later
"""Palette (owner: A). All values are sRGB 0–255 tuples (RESEARCH_SKETCHUP.md §4.2, §5.1; spike colours).

`rgba(c, a)` → sRGB 0–1 tuple (GPU drawing, theme: the view transform is Standard, so POST_VIEW
colours are written 1:1); `lin(c)` → linear 0–1 (material `diffuse_color`).
"""

ORDER = 2

# Viewport (Simple Style)
SKY = (30, 166, 221)              # #1EA6DD top of the default view (2023); 2027 view shows #40B3E2
HORIZON = (191, 229, 245)         # #BFE5F5
BACKGROUND = (191, 191, 198)      # #BFBFC6 below the horizon (ground off)
GROUND = (191, 191, 198)
FACE_FRONT = (255, 255, 255)
FACE_BACK = (164, 178, 187)       # #A4B2BB
EDGE = (0, 0, 0)
SELECTION = (0, 0, 255)
AXIS_X = (178, 0, 0)
AXIS_Y = (0, 178, 0)
AXIS_Z = (0, 0, 178)
GUIDE = (0, 0, 0)
LOCKED = (255, 0, 0)

# Inference markers / lines
INF_ENDPOINT = (95, 149, 64)
INF_MIDPOINT = (49, 192, 200)
INF_ON_EDGE = (187, 31, 37)
INF_ON_FACE = (17, 95, 159)
INF_INTERSECTION = (187, 31, 37)
INF_CENTER = (17, 96, 160)
INF_GUIDE_POINT = (53, 52, 70)
INF_ON_GUIDE = (187, 31, 37)
INF_ORIGIN = (60, 60, 60)
INF_IN_CONTEXT = (115, 90, 165)
INF_PARALLEL = (255, 0, 255)      # parallel / perpendicular (magenta)
INF_TANGENT = (0, 255, 255)
INF_FROM_POINT = (0, 0, 0)

# ScreenTip
TOOLTIP_BG = (255, 255, 220)      # #FFFFDC
TOOLTIP_TEXT = (0, 0, 0)
TOOLTIP_BORDER = (0, 0, 0)

# UI chrome (spike values)
UI_CHROME = (241, 241, 246)       # #F1F1F6
UI_PANEL_HEADER = (224, 225, 233) # #E0E1E9
UI_TRAY_BODY = (244, 247, 252)    # #F4F7FC
UI_TEXT = (30, 30, 36)
UI_BORDER = (200, 200, 208)
UI_TOOL_ACTIVE_FILL = (214, 232, 250)   # #D6E8FA
UI_TOOL_ACTIVE_LINE = (0, 120, 215)     # #0078D7

# Icons
ICON_NAVY = (0, 66, 110)          # #00426E
ICON_CYAN = (0, 150, 220)         # #0096DC
ICON_RED = (220, 40, 40)


def rgba(c, a=1.0):
    """sRGB 0–255 → sRGB 0–1 RGBA tuple."""
    return (c[0] / 255.0, c[1] / 255.0, c[2] / 255.0, a)


def _to_linear(x):
    return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4


def lin(c, a=1.0):
    """sRGB 0–255 → linear 0–1 RGBA tuple (for Material.diffuse_color)."""
    return (_to_linear(c[0] / 255.0), _to_linear(c[1] / 255.0), _to_linear(c[2] / 255.0), a)
