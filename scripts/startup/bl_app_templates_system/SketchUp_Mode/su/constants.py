# SPDX-License-Identifier: GPL-2.0-or-later
"""Global constants (owner: A). Contract: PLANO.md §2.4. Pixel values are LOGICAL px (→ viewutil.ui_px)."""

ORDER = 1

PRODUCT_NAME = "SketchUp Mode"
TEMPLATE_ID = "SketchUp_Mode"
GEOM_TOL = 1e-5

# Inference snap radii (logical px) and hysteresis.
SNAP_PX_POINT = 12
SNAP_PX_EDGE = 7
SNAP_PX_AXIS = 9
SNAP_PX_GUIDE = 7
SNAP_RELEASE_FACTOR = 1.5

HOVER_ACQUIRE_S = 0.3
MAX_REF_POINTS = 2
DRAG_THRESHOLD_PX = 6
DOUBLE_CLICK_S = 0.35
MULTI_CLICK_DIST_PX = 4

CIRCLE_SIDES = 24
POLYGON_SIDES = 6
ARC_SEGMENTS = 12
ANGLE_SNAP_DEG = 15.0
DEFAULT_FOV_V_DEG = 35.0

# Material slots of every document object (F): 0 = "Padrão", 1 = "Padrão (verso)".
SLOT_DEFAULT_FRONT = 0
SLOT_DEFAULT_BACK = 1
