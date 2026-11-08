# SPDX-License-Identifier: GPL-2.0-or-later
"""View helpers (owner: A). Coordinates are REGION coordinates in PHYSICAL pixels (Retina: 2× points),
the same space as event.mouse_region_x/y and region.width/height."""

import bpy
from bpy_extras import view3d_utils
from mathutils import Vector

ORDER = 120


def mouse_ray(region, rv3d, xy):
    """(origin, direction) of the view ray through region pixel `xy` (direction normalised)."""
    origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, xy)
    direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, xy).normalized()
    return origin, direction


def project(region, rv3d, co):
    """World point → region pixel Vector((x, y)), or None when behind the view."""
    return view3d_utils.location_3d_to_region_2d(region, rv3d, co)


def ui_px(v):
    """Logical px (sizes, radii, fonts) → physical px (UI scale × Retina)."""
    return v * bpy.context.preferences.system.ui_scale


def line_px(v):
    """Logical line width / point size → physical px."""
    return v * bpy.context.preferences.system.ui_line_width


def pixel_size_at(region, rv3d, co):
    """World length covered by one physical pixel at the depth of `co`."""
    p = project(region, rv3d, co)
    if p is None:
        return 0.0
    a = view3d_utils.region_2d_to_location_3d(region, rv3d, p, co)
    b = view3d_utils.region_2d_to_location_3d(region, rv3d, p + Vector((1.0, 0.0)), co)
    return (b - a).length
