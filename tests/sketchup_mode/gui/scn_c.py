# SPDX-License-Identifier: GPL-2.0-or-later
"""C scenario: inference engine on the real viewport + inference_draw (markers, axis lines, ScreenTips).

Builds a 2×2×1 box in the root document, aims the view at it, queries ENGINE on the real region/RegionView3D and shows
each result through STATE.inference (the tool dispatcher of A does this on hover later). Writes
full screenshots plus <out_dir>/c_inferencia.png: a 2×2 grid of crops around the markers.
"""

import hashlib
import importlib
import os

import bpy
from mathutils import Vector

CROP_W, CROP_H = 900, 600


def _look(rv3d, eye, target):
    d = (Vector(target) - Vector(eye))
    rv3d.view_location = Vector(target)
    rv3d.view_distance = d.length
    rv3d.view_rotation = d.to_track_quat('-Z', 'Y')
    rv3d.view_perspective = 'PERSP'


def _crop(path, cx, cy):
    """Crop (CROP_W × CROP_H) of a screenshot around window px (cx, cy) → numpy array."""
    import numpy as np
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    bpy.data.images.remove(img)
    x0 = int(min(max(cx - CROP_W * 0.35, 0), w - CROP_W))
    y0 = int(min(max(cy - CROP_H * 0.6, 0), h - CROP_H))
    return px[y0:y0 + CROP_H, x0:x0 + CROP_W].copy()


def _grid(crops, path):
    import numpy as np
    rows = [np.concatenate(crops[i:i + 2], axis=1) for i in range(0, len(crops), 2)]
    rows.reverse()                                   # image rows start at the bottom
    out = np.concatenate(rows, axis=0)
    h, w = out.shape[:2]
    img = bpy.data.images.new("su_c_grid", w, h, alpha=True)
    img.pixels.foreach_set(out.reshape(-1))
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def run(h):
    su = h.su
    inference = importlib.import_module(su.__name__ + ".core.inference")
    state = importlib.import_module(su.__name__ + ".core.state")
    handlers = importlib.import_module(su.__name__ + ".draw.handlers")
    idraw = importlib.import_module(su.__name__ + ".draw.inference_draw")
    STATE = state.STATE
    names = [n for _o, n in handlers.layers('POST_PIXEL')]
    h.check("inference layers registered", "inference_marker" in names and "inference_tooltip" in names, names)

    # scene: a box in the root document "Modelo" (B's Document), nothing else visible
    import bmesh
    document = importlib.import_module(su.__name__ + ".core.document")
    doc = document.root()
    for obj in bpy.context.scene.objects:
        obj.hide_viewport = obj.name != doc.key
    bm = doc.bm
    v = [bm.verts.new(c) for c in ((1, 1, 0), (3, 1, 0), (3, 3, 0), (1, 3, 0),
                                   (1, 1, 1), (3, 1, 1), (3, 3, 1), (1, 3, 1))]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[i] for i in f])
    doc.write(undo_key=None)
    h.check("box written to the root document", len(doc.obj.data.polygons) == 6, len(doc.obj.data.polygons))
    bpy.context.view_layer.objects.active = None
    win, area, R = h.area_regions()
    region = R['WINDOW']
    rv3d = area.spaces.active.region_3d
    _look(rv3d, (8.0, -5.5, 5.0), (2.2, 1.6, 0.6))
    area.tag_redraw()
    h.park_mouse()
    yield 0.6

    def xy(co, dx=0.0, dy=0.0):
        from bpy_extras import view3d_utils
        s = view3d_utils.location_3d_to_region_2d(region, rv3d, Vector(co))
        return (s[0] + dx, s[1] + dy)

    def show(inf, name):
        STATE.inference = inf
        area.tag_redraw()
        return name

    shots = []
    eng = inference.ENGINE
    eng.reset()

    def q(p, **kw):
        kw.setdefault("locks", state.Locks())
        return inference.QueryCtx(region, rv3d, p, **kw)

    # 1. endpoint
    inf = eng.query(q(xy((3, 1, 1), 4, 3)))
    h.check("endpoint on the real viewport", inf.kind == "ENDPOINT" and (inf.point - Vector((3, 1, 1))).length < 1e-6,
            (inf.kind, tuple(inf.point)))
    shots.append((show(inf, "c_endpoint"), inf))
    yield 0.6
    # 2. red axis from the corner
    a = Vector((3, 1, 1))
    inf = eng.query(q(xy((4.6, 1, 1)), anchor=a))
    h.check("red axis from anchor", inf.linear == "AXIS_X" and abs(inf.point.y - 1) < 1e-3 and abs(inf.point.z - 1) < 1e-3,
            (inf.kind, inf.linear, tuple(inf.point)))
    shots.append((show(inf, "c_axis_x"), inf))
    yield 0.6
    # 3. blue axis locked with ↑ (thick)
    locks = state.Locks()
    inference.lock_from_arrow('UP_ARROW', locks)
    inf = eng.query(q(xy((3, 1, 2.1)), anchor=a, locks=locks))
    h.check("↑ locks the blue axis", inf.linear == "AXIS_Z" and inf.locked, (inf.linear, inf.locked))
    shots.append((show(inf, "c_axis_z_locked"), inf))
    yield 0.6
    # 4. midpoint, shown as geometry of a group (magenta + 2nd line)
    inf = eng.query(q(xy((2, 1, 1), 2, 3)))
    h.check("midpoint", inf.kind == "MIDPOINT", inf.kind)
    inf.in_context = 'GROUP'
    shots.append((show(inf, "c_midpoint_group"), inf))
    yield 0.6

    # screenshots (one redraw per shot)
    crops = []
    for name, inf in shots:
        STATE.inference = inf
        path = os.path.join(h.out_dir, name + ".png")
        # the screenshot may show an older frame: repeat until two consecutive captures are equal
        last = None
        for _attempt in range(6):
            area.tag_redraw()
            h.park_mouse()
            yield 0.5
            with bpy.context.temp_override(window=win, area=area, region=region):
                bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=3)     # flush swap buffers
            h.screenshot(path)
            yield 0.2
            with open(path, "rb") as fh:
                digest = hashlib.md5(fh.read()).hexdigest()
            if digest == last:
                break
            last = digest
        h.check("screenshot " + name, os.path.isfile(path), path)
        seen = idraw.last_drawn()
        h.check("drawn " + name, seen["marker"] is inf, (seen["marker"].kind if seen["marker"] else None,
                                                         seen["tooltip"]))
        s = xy(inf.point)
        try:
            crops.append(_crop(path, region.x + s[0], region.y + s[1]))
        except Exception as ex:
            h.check("crop " + name, False, repr(ex))
    if len(crops) == 4:
        grid = os.path.join(h.out_dir, "c_inferencia.png")
        _grid(crops, grid)
        h.check("grid written", os.path.isfile(grid), grid)
    STATE.inference = state.Inference.none()
    area.tag_redraw()
    yield 0.3
