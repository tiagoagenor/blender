# SPDX-License-Identifier: GPL-2.0-or-later
"""Selection display (owner: D, layer SELECTION=30). PLANO.md §3.3, §9.2-D item 4.

Reads B's `core/selection` (sets of Ref(doc_key, kind, index); indices = mesh indices of the document):
  * selected EDGES  → blue (#0000FF) 1 pt lines over the black edges (depth-tested, offset);
  * selected FACES  → blue dot screen (stipple shader, SketchUp's selected-face look);
  * selected OBJECTS (groups/components) → blue bounding box of the object and its descendants, in
    the object's own axes;
  * the open group (edit context) → dashed grey bounding box.
Recomputed from the mesh on every draw (simple first; performance is deferred, PLANO §7).
"""

import sys

import bpy
from mathutils import Vector

from .. import colors
from . import handlers, prims

ORDER = 223

OPEN_GROUP_BOX = (110, 110, 110)


def _sib(name):
    return sys.modules.get(__package__.rsplit(".", 1)[0] + "." + name)


def _local_bounds(obj):
    """(min, max) in obj's local space over obj's mesh and all its descendants, or None."""
    inv = obj.matrix_world.inverted_safe()
    mn = Vector((1e30, 1e30, 1e30))
    mx = Vector((-1e30, -1e30, -1e30))
    found = False
    stack = [obj]
    while stack:
        o = stack.pop()
        stack.extend(o.children)
        if o.type != 'MESH' or o.data is None or not len(o.data.vertices):
            continue
        m = inv @ o.matrix_world
        for c in o.bound_box:
            p = m @ Vector(c)
            mn = Vector(map(min, mn, p))
            mx = Vector(map(max, mx, p))
            found = True
    return (mn, mx) if found else None


def _face_world(obj, me, fi):
    if fi >= len(me.polygons):
        return None
    M = obj.matrix_world
    return [M @ me.vertices[v].co for v in me.polygons[fi].vertices]


def draw(dc):
    sel = _sib("core.selection")
    if sel is None or dc.rv3d is None:
        return
    blue = colors.rgba(colors.SELECTION)
    refs = sel.get()
    by_doc = {}
    for r in refs:
        by_doc.setdefault(r.doc_key, []).append(r)
    for doc_key, rs in by_doc.items():
        obj = bpy.data.objects.get(doc_key)
        if obj is None or not obj.visible_get():
            continue
        if obj.type == 'MESH' and obj.data is not None:
            me = obj.data
            M = obj.matrix_world
            faces = [r.index for r in rs if r.kind == 'FACE']
            for fi in faces:
                pts = _face_world(obj, me, fi)
                if pts:
                    prims.polygon(dc, pts, blue, stipple=True)
            segs = []
            for r in rs:
                if r.kind == 'EDGE' and r.index < len(me.edges):
                    a, b = me.edges[r.index].vertices
                    segs.append((M @ me.vertices[a].co, M @ me.vertices[b].co))
            if segs:
                prims.lines(dc, segs, blue, 1.0, depth=True)
        if any(r.kind == 'OBJECT' for r in rs):
            bb = _local_bounds(obj)
            if bb is not None:
                prims.box(dc, bb[0], bb[1], obj.matrix_world, blue)
    ec = _sib("core.edit_context")
    cur = ec.current_object() if ec is not None and hasattr(ec, "current_object") else None
    if cur is not None:
        bb = _local_bounds(cur)
        if bb is not None:
            prims.box(dc, bb[0], bb[1], cur.matrix_world, colors.rgba(OPEN_GROUP_BOX), dashed=True)


def _on_selection(**_kw):
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return
    for win in wm.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def register():
    from .. import events
    handlers.add_layer("selection", 'POST_VIEW', handlers.POST_VIEW["SELECTION"], draw)
    events.subscribe("selection", _on_selection, order=200)


def unregister():
    handlers.remove_layer("selection")
