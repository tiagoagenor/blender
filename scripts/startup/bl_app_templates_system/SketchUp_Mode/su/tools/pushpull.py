# SPDX-License-Identifier: GPL-2.0-or-later
"""Empurrar/puxar (owner: E). PLANO.md §6.2 (AC-EMP-1..7), ROTEIRO_CASA passos 2, 7, 9, B4, B6.

Hover a face: the logical face is pre-highlighted (blue stipple); a smooth surface is refused (no
highlight, the click does nothing). Click (or press-drag-release) and move: live preview along the
face normal (the inference is constrained to that line, so hovering another face/point snaps the
distance to it — "encaixe"; the moving faces are skipped by the ray). Click again, or type a distance +
Enter ("Distância"; the sign follows the current direction, negative reverses; with no movement yet a
positive value pulls towards the viewer). Option (copy) keeps the original face (new starting face).
Double click on a face repeats the last distance. Idle retype re-applies the last push/pull with the
new distance ("Ajustar"). One undo step per push/pull. Kernel: core/geom_extrude.py.
"""

from mathutils import Vector

from .. import colors, constants, i18n, registry
from ..core.state import STATE, LastAction, Locks
from .base import BaseTool, Result, ToolMeta, fmt_length, kind_of, make_query, tool, value_of

TOOL_ID = "su.pushpull"
LENGTH_KINDS = frozenset({"LENGTH", "DISTANCE", "NUMBER"})

STRINGS = {
    "tool.su.pushpull.label": {"pt_BR": "Empurrar/puxar", "en": "Push/Pull"},
    "tool.su.pushpull.hint_start": {"pt_BR": "Selecione a face para empurrar ou puxar.",
                                    "en": "Select a face to push or pull."},
    "tool.su.pushpull.hint_next": {"pt_BR": "Mova para empurrar ou puxar, ou digite a distância.",
                                   "en": "Move to push or pull, or enter the distance."},
    "tool.su.pushpull.undo": {"pt_BR": "Empurrar/puxar", "en": "Push/Pull"},
}


def _documents():
    return registry.optional("core.document")


def _face_target(inf):
    """(doc, bmesh face index) of an editable face under `inf`, or (None, None)."""
    if inf is None or inf.kind == "NONE" or not inf.elem or inf.elem[0] != "FACE":
        return None, None
    document = _documents()
    if document is None:
        return None, None
    doc = document.active()
    key = inf.doc_key or doc.key
    if key != doc.key:
        return None, None                   # geometry of another context (group): not editable here
    try:
        bm = doc.bm
        bm.faces.ensure_lookup_table()
        idx = inf.elem[1]
        if idx < 0 or idx >= len(bm.faces):
            return None, None
    except Exception:
        return None, None
    return doc, idx


def face_pick(tc, xy, inf):
    """The face under the cursor as an ON_FACE inference: the inference itself when it already names a
    face, else a ray cast at `xy` (a point inference — midpoint, center… — over a face still picks the
    face, as in SketchUp). Headless (no region) the inference is returned unchanged."""
    if inf is not None and inf.elem and inf.elem[0] == "FACE":
        return inf
    if tc is None or tc.region is None or tc.rv3d is None or xy is None:
        return inf
    spatial = registry.optional("core.spatial")
    if spatial is None:
        return inf
    from ..core import viewutil
    from ..core.state import Inference
    o, d = viewutil.mouse_ray(tc.region, tc.rv3d, xy)
    hit = spatial.ray_cast(tc, o, d)
    if not hit.ok:
        return inf
    return Inference(kind="ON_FACE", point=hit.point.copy(), normal=hit.normal_orig.copy(), side=hit.side,
                     plane=(hit.point.copy(), hit.normal_orig.copy()), doc_key=hit.doc_key,
                     elem=("FACE", hit.face_idx_orig), obj_name=hit.obj.name if hit.obj else "")


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.pushpull.label", icon="ops.mesh.extrude_region_move", shortcut="P",
               cursor='SCROLL_Y', vcb_label_key="vcb.distance", vcb_schema="length"))
class PushPullTool(BaseTool):

    def __init__(self):
        self.reset()
        self.last = None             # dict of the last push/pull (retype / double click)
        self.last_distance = None    # signed distance along the face normal

    def reset(self):
        self.session = None
        self.doc = None
        self.face_idx = None
        self.p0 = None               # clicked point (world)
        self.n = None                # face normal (world)
        self.u_view = None           # normal towards the viewer (world)
        self.distance = 0.0          # signed, along self.n (world units)
        self.hover_key = None        # (doc_key, face_idx, version)
        self.hover_polys = []        # world polygons of the highlighted logical face
        self.copy = False
        self._snap = None
        self.screen_side = 0
        self._s0 = self._sdir = None

    # -- status --------------------------------------------------------------------------------------
    def _shown(self):
        if self.n is None:
            return 0.0
        return self.distance * (self.n.dot(self.u_view) if self.u_view is not None else 1.0)

    def update_status(self):
        STATE.set_hint("tool.su.pushpull.hint_start" if self.session is None else "tool.su.pushpull.hint_next")
        if self.session is not None:
            STATE.set_vcb(self.meta.vcb_label_key, fmt_length(self._shown()))
        else:
            STATE.set_vcb(self.meta.vcb_label_key, STATE.vcb_value)

    def activate(self, tc):
        self.reset()
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)
        self._drop_last()

    def cancel(self, tc):
        if self.session is not None:
            try:
                self.session.cancel()
            finally:
                self.session = None
        from ..core import geom_extrude
        geom_extrude.release(self._snap)
        self.reset()
        self.update_status()

    def _drop_last(self):
        if self.last is not None:
            from ..core import geom_extrude
            geom_extrude.release(self.last.get("snap"))
            self.last = None

    # -- hover highlight -----------------------------------------------------------------------------
    def _highlight(self, inf):
        doc, idx = _face_target(inf)
        if doc is None:
            self.hover_key, self.hover_polys = None, []
            return None
        key = (doc.key, idx, doc.version)
        if key == self.hover_key:
            return doc
        from ..core import entities
        bm = doc.bm
        bm.faces.ensure_lookup_table()
        kind, ids = entities.pick_entity(bm, 'FACE', idx)
        if kind == 'SURFACE':
            self.hover_key, self.hover_polys = key, []
            return None
        mw = doc.world()
        self.hover_polys = [[mw @ v.co for v in bm.faces[i].verts] for i in ids]
        self.hover_key = key
        return doc

    def hover(self, tc, inf):
        self._highlight(face_pick(tc, tc.xy, inf))

    # -- inference -----------------------------------------------------------------------------------
    def query_ctx(self, tc, xy):
        if self.session is None:
            return make_query(tc, xy, locks=Locks())
        skip = {self.doc.key: set(self.session.moving_faces)} if self.session.moving_faces else None
        return make_query(tc, xy, line=(self.p0.copy(), self.n.copy()), skip=skip, locks=Locks())

    # -- session -------------------------------------------------------------------------------------
    def _start(self, tc, ev, inf):
        doc = self._highlight(inf)
        if doc is None:
            return False
        _doc, idx = _face_target(inf)
        from ..core import geom_extrude
        bm = doc.bm
        bm.faces.ensure_lookup_table()
        f = bm.faces[idx]
        f.normal_update()
        nm = doc.world().to_3x3().inverted().transposed()
        self.n = (nm @ f.normal).normalized()
        side = inf.side if inf.side else (1 if inf.normal is None or Vector(inf.normal).dot(self.n) >= 0 else -1)
        self.u_view = self.n * (1.0 if side >= 0 else -1.0)
        self.doc, self.face_idx = doc, idx
        self.p0 = Vector(inf.point)
        self.copy = bool(ev.copy)
        self._screen_setup(tc, ev)
        self._snap = geom_extrude.snapshot(doc)
        from ..core import entities
        lf = entities.logical_face(bm, f)
        self.session = geom_extrude.PushPullSession(doc, lf, keep_original=self.copy)
        self.distance = 0.0
        return True

    def _screen_setup(self, tc, ev):
        """Screen direction of +n at the clicked point (to know which side the mouse went to)."""
        self.screen_side = 0
        self._s0 = self._sdir = None
        if tc is None or tc.region is None or tc.rv3d is None:
            return
        from ..core import viewutil
        a = viewutil.project(tc.region, tc.rv3d, self.p0)
        b = viewutil.project(tc.region, tc.rv3d, self.p0 + self.n * 0.1)
        if a is None or b is None or (b - a).length < 1e-3:
            return
        self._s0, self._sdir = (float(ev.x), float(ev.y)), (b - a).normalized()

    def _screen_track(self, ev):
        if self._sdir is None or ev is None:
            return
        dx, dy = ev.x - self._s0[0], ev.y - self._s0[1]
        t = dx * self._sdir.x + dy * self._sdir.y
        if abs(t) >= 3.0:                      # physical px: a real move to one side of the face
            self.screen_side = 1 if t > 0 else -1

    def _track(self, inf):
        if inf is None or inf.kind == "NONE":
            return
        d = (Vector(inf.point) - self.p0).dot(self.n)
        if abs(d - self.distance) <= 1e-9:
            return
        self.distance = d
        self.session.update(self._local(d))

    def _scale(self):
        sc = self.doc.world().to_scale()
        return ((abs(sc.x) + abs(sc.y) + abs(sc.z)) / 3.0) or 1.0

    def _local(self, d):
        """World distance → document distance (uniform scale of a group)."""
        return d / self._scale()

    def move(self, tc, ev, inf):
        if self.session is None:
            self._highlight(face_pick(tc, (ev.x, ev.y), inf))
            return Result.IDLE
        self._screen_track(ev)
        self._track(inf)
        self.update_status()
        return Result.RUNNING

    def press(self, tc, ev, inf):
        if self.session is None:
            if not self._start(tc, ev, face_pick(tc, (ev.x, ev.y), inf)):
                return Result.IDLE
            self.update_status()
            return Result.RUNNING
        if ev.clicks >= 2 and abs(self.distance) <= constants.GEOM_TOL and self.last_distance is not None:
            return self._commit(self.last_distance)         # double click: repeat the last distance
        self._track(inf)
        if abs(self.distance) <= constants.GEOM_TOL:
            return Result.RUNNING
        return self._commit(self.distance)

    def release(self, tc, ev, inf):
        if self.session is None:
            return Result.IDLE
        if ev.is_drag_release:
            self._track(inf)
            if abs(self.distance) > constants.GEOM_TOL:
                return self._commit(self.distance)
        return Result.RUNNING

    # -- Measurements --------------------------------------------------------------------------------
    def _typed(self, values, current):
        """Signed distance along n from a typed value: the side the mouse went to (the live distance, or
        — when the inference kept it at 0, e.g. snapped to a point of the face — the side of the cursor
        relative to the face on screen); with no movement, towards the viewer. A negative value flips."""
        if not values or values[0] is None or kind_of(values[0]) not in LENGTH_KINDS:
            return None
        v = value_of(values[0])
        if abs(current) > constants.GEOM_TOL:
            s = 1.0 if current > 0 else -1.0
        elif getattr(self, "screen_side", 0):
            s = float(self.screen_side)
        else:
            s = 1.0 if self.u_view.dot(self.n) > 0 else -1.0
        return v * s

    def vcb(self, tc, values):
        if self.session is None:
            return Result.PASS
        d = self._typed(values, self.distance)
        if d is None or abs(d) <= constants.GEOM_TOL:
            STATE.vcb_error = True
            return Result.RUNNING
        return self._commit(d)

    def _reapply(self, values):
        last = self.last
        if last is None or not values or kind_of(values[0]) not in LENGTH_KINDS:
            return False
        v = value_of(values[0])
        if abs(v) <= constants.GEOM_TOL:
            return False
        document = _documents()
        doc = document.active()
        if doc.key != last["doc_key"]:
            return False
        from ..core import geom_extrude
        geom_extrude.restore(doc, last["snap"])
        sign = 1.0 if last["shown"] >= 0 else -1.0
        d = v * sign * last["n"].dot(last["u_view"])
        s = geom_extrude.PushPullSession(doc, last["face_ids"], keep_original=last["copy"])
        s.distance = d / last["k"]
        s.finish()
        doc.write(undo_key=None)
        last["distance"] = d
        self.last_distance = d
        STATE.set_vcb(self.meta.vcb_label_key, fmt_length(v * sign))
        return True

    # -- commit --------------------------------------------------------------------------------------
    def _commit(self, d):
        self.distance = d
        self.session.distance = self._local(d)
        face_ids = list(self.session.face_ids)
        self.session.finish()
        doc = self.doc
        doc.write(undo_key="tool.su.pushpull.undo")
        self._drop_last()
        self.last = {"doc_key": doc.key, "face_ids": face_ids, "snap": self._snap, "n": self.n.copy(),
                     "u_view": self.u_view.copy(), "copy": self.copy, "distance": d, "shown": self._shown(),
                     "k": self._scale()}
        self._snap = None
        self.last_distance = d
        STATE.last_action = LastAction(tool_id=TOOL_ID, schema=self.meta.vcb_schema, reapply=self._reapply)
        shown = self._shown()
        self.session = None
        self.reset()
        self.update_status()
        STATE.set_vcb(self.meta.vcb_label_key, fmt_length(shown))
        return Result.IDLE

    # -- drawing -------------------------------------------------------------------------------------
    def draw_3d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None:
            return
        if self.session is None and self.hover_polys:
            for poly in self.hover_polys:
                prims.polygon(dc, poly, colors.rgba(colors.SELECTION, 0.55), stipple=True)
        elif self.session is not None and self.p0 is not None and abs(self.distance) > constants.GEOM_TOL:
            prims.dotted(dc, self.p0, self.p0 + self.n * self.distance, colors.rgba(colors.SELECTION, 1.0))


def register():
    i18n.register_strings(STRINGS)
