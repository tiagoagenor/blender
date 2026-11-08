# SPDX-License-Identifier: GPL-2.0-or-later
"""Ordered draw layers for the 3D viewport (owner: A). Contract: PLANO.md §2.4.

One SpaceView3D draw handler per space ('POST_VIEW', 'POST_PIXEL') calls every layer in `order`:

    add_layer("edges", 'POST_VIEW', POST_VIEW["EDGES"], fn)   # fn(dc: DrawContext)

A layer that raises is reported once with perf.error and disabled (no error spam per frame).
Not imported in background mode (unit tests).
"""

from dataclasses import dataclass

import bpy

from .. import perf

ORDER = 200

POST_VIEW = {"SKY": 0, "AXES": 10, "EDGES": 20, "SELECTION": 30, "GUIDES": 40, "ANNOT_3D": 45,
             "TOOL": 50, "INFERENCE": 60}
POST_PIXEL = {"ANNOT_2D": 10, "TOOL_2D": 20, "TOOLTIP": 30}
SPACES = ('POST_VIEW', 'POST_PIXEL')


@dataclass
class DrawContext:
    context: object
    region: object
    rv3d: object
    space: object
    phase: str


_layers = {s: [] for s in SPACES}   # space -> [(order, name, fn)]
_disabled = set()
_handles = {}


def add_layer(name, space, order, fn):
    """Add (or replace, by name) a layer drawn in `space` at `order`."""
    if space not in SPACES:
        raise ValueError("unknown draw space {!r}".format(space))
    remove_layer(name)
    _layers[space].append((order, name, fn))
    _layers[space].sort(key=lambda l: (l[0], l[1]))
    _disabled.discard(name)


def remove_layer(name):
    for space in SPACES:
        _layers[space][:] = [l for l in _layers[space] if l[1] != name]


def layers(space):
    return [(o, n) for o, n, _fn in _layers[space]]


def _draw(space):
    ctx = bpy.context
    dc = DrawContext(context=ctx, region=ctx.region, rv3d=ctx.region_data, space=ctx.space_data, phase=space)
    for _order, name, fn in _layers[space]:
        if name in _disabled:
            continue
        try:
            fn(dc)
        except Exception:
            _disabled.add(name)
            perf.exception("draw layer {!r} ({:s}) disabled".format(name, space))


def register():
    for space in SPACES:
        _handles[space] = bpy.types.SpaceView3D.draw_handler_add(_draw, (space,), 'WINDOW', space)


def unregister():
    for space, h in list(_handles.items()):
        bpy.types.SpaceView3D.draw_handler_remove(h, 'WINDOW')
    _handles.clear()
    for space in SPACES:
        _layers[space].clear()
    _disabled.clear()
