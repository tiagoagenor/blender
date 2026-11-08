# SPDX-License-Identifier: GPL-2.0-or-later
"""Siga-me (owner: E). PLANO.md §6.2 (AC-SIG-1..2).

Pre-selected path: select the path edges (e.g. the top edges of a box), activate Siga-me and click the
profile face → the profile is swept along them at once. Without a pre-selection: click the profile face,
then hover the path — an edge (its chain of connected edges, through vertices with two edges) or a face
(its perimeter: the SketchUp Cmd/Alt use) — the path is highlighted in red; click to sweep. Mitred joints;
an open path keeps the profile as the start cap and adds the end cap; a closed path removes the profile
face (moldura). Sweeping along a curve (arc/circle) gives a smooth surface. One undo step. Kernel:
core/geom_extrude.follow_me.
"""

from mathutils import Vector

from .. import colors, i18n, registry
from ..core.state import STATE, Locks
from .base import BaseTool, Result, ToolMeta, make_query, tool
from .pushpull import _face_target, face_pick

TOOL_ID = "su.followme"

STRINGS = {
    "tool.su.followme.label": {"pt_BR": "Siga-me", "en": "Follow Me"},
    "tool.su.followme.hint_start": {"pt_BR": "Selecione a face do perfil a extrudar.",
                                    "en": "Select the profile face to extrude."},
    "tool.su.followme.hint_path": {"pt_BR": "Selecione o caminho: uma aresta ou uma face (perímetro).",
                                   "en": "Select the path: an edge or a face (perimeter)."},
    "tool.su.followme.undo": {"pt_BR": "Siga-me", "en": "Follow Me"},
}


def _document():
    return registry.optional("core.document").active()


def chain_from_edge(bm, edge):
    """Connected chain of visible edges through vertices with exactly two visible edges."""
    from ..core import geom
    lay = geom.layers(bm)

    def vis(v):
        return [e for e in v.link_edges if not e[lay.bridge]]

    out = {edge}
    stack = [edge]
    while stack:
        e = stack.pop()
        for v in e.verts:
            es = vis(v)
            if len(es) != 2:
                continue
            for x in es:
                if x not in out:
                    out.add(x)
                    stack.append(x)
    return list(out)


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.followme.label", icon="ops.mesh.extrude_faces_move",
               cursor='CROSSHAIR', vcb_label_key="", vcb_schema=""))
class FollowMeTool(BaseTool):

    def __init__(self):
        self.reset()

    def reset(self):
        self.doc = None
        self.profile = None            # face index of the profile
        self.path = None               # (local points, closed, smooth)
        self.path_world = []           # world segments for the red highlight
        self.hover_key = None
        self.hover_polys = []

    def update_status(self):
        STATE.set_hint("tool.su.followme.hint_start" if self.profile is None else "tool.su.followme.hint_path")
        STATE.set_vcb("", "")

    def activate(self, tc):
        self.reset()
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)

    def cancel(self, tc):
        self.reset()
        self.update_status()

    def query_ctx(self, tc, xy):
        return make_query(tc, xy, locks=Locks())

    # -- hover ---------------------------------------------------------------------------------------
    def _profile_at(self, inf):
        doc, idx = _face_target(inf)
        if doc is None:
            return None, None
        from ..core import entities
        bm = doc.bm
        bm.faces.ensure_lookup_table()
        kind, ids = entities.pick_entity(bm, 'FACE', idx)
        if kind == 'SURFACE':
            return None, None
        key = (doc.key, idx, doc.version)
        if key != self.hover_key:
            mw = doc.world()
            self.hover_polys = [[mw @ v.co for v in bm.faces[i].verts] for i in ids]
            self.hover_key = key
        return doc, idx

    def _path_at(self, inf):
        """(points, closed, smooth) of the path under the cursor (edge chain or face perimeter)."""
        from ..core import entities, geom, geom_extrude
        doc = self.doc
        if inf is None or inf.kind == "NONE" or (inf.doc_key and inf.doc_key != doc.key):
            return None
        bm = doc.bm
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        edges = None
        if inf.ref_edge is not None and inf.ref_edge[0] == doc.key and inf.ref_edge[1] < len(bm.edges):
            e = bm.edges[inf.ref_edge[1]]
            edges = entities.curve_edges(bm, e) if e[geom.layers(bm).curve] else chain_from_edge(bm, e)
        elif inf.elem and inf.elem[0] == "FACE" and inf.elem[1] < len(bm.faces):
            f = bm.faces[inf.elem[1]]
            if f.index == self.profile or f in entities.logical_face(bm, bm.faces[self.profile]).faces:
                return None
            lf = entities.logical_face(bm, f)
            pts = [v.co.copy() for v in lf.outer_loop]
            return pts, True, False
        if not edges:
            return None
        r = geom_extrude.order_path([(e.verts[0].co, e.verts[1].co) for e in edges])
        if r is None:
            return None
        lay = geom.layers(bm)
        smooth = any(e[lay.curve] and (entities.get_curve_meta(doc, e[lay.curve]) or {}).get("kind") != "polygon"
                     for e in edges)
        return r[0], r[1], smooth

    def _set_path(self, path):
        self.path = path
        self.path_world = []
        if path is None:
            return
        mw = self.doc.world()
        pts, closed, _s = path
        w = [mw @ p for p in pts]
        self.path_world = list(zip(w, w[1:])) + ([(w[-1], w[0])] if closed else [])

    def hover(self, tc, inf):
        if self.profile is None:
            self._profile_at(face_pick(tc, tc.xy, inf))
        else:
            self._set_path(self._path_at(inf))

    def move(self, tc, ev, inf):
        self.hover(tc, inf)
        return Result.RUNNING if self.profile is not None else Result.IDLE

    # -- clicks --------------------------------------------------------------------------------------
    def _preselected_path(self, doc):
        from ..core import geom_extrude
        sel = registry.optional("core.selection")
        if sel is None:
            return None
        ids = [r.index for r in sel.get() if r.kind == 'EDGE' and r.doc_key == doc.key]
        if not ids:
            return None
        bm = doc.bm
        bm.edges.ensure_lookup_table()
        es = [bm.edges[i] for i in ids if i < len(bm.edges)]
        r = geom_extrude.order_path([(e.verts[0].co, e.verts[1].co) for e in es])
        return (r[0], r[1], False) if r is not None else None

    def press(self, tc, ev, inf):
        if self.profile is None:
            doc, idx = self._profile_at(face_pick(tc, (ev.x, ev.y), inf))
            if doc is None:
                return Result.IDLE
            self.doc, self.profile = doc, idx
            pre = self._preselected_path(doc)
            if pre is not None:
                return self._commit(pre)
            self.update_status()
            return Result.RUNNING
        path = self._path_at(inf)
        if path is None:
            return Result.RUNNING
        return self._commit(path)

    def release(self, tc, ev, inf):
        return Result.RUNNING if self.profile is not None else Result.IDLE

    def _commit(self, path):
        from ..core import geom_extrude
        doc = self.doc
        pts, closed, smooth = path
        snap = geom_extrude.snapshot(doc)
        try:
            r = geom_extrude.follow_me(doc.bm, self.profile, pts, closed, smooth)
        except Exception:
            geom_extrude.restore(doc, snap)
            geom_extrude.release(snap)
            raise
        if not r["ok"]:
            geom_extrude.restore(doc, snap)
            geom_extrude.release(snap)
            return Result.RUNNING
        geom_extrude.release(snap)
        sel = registry.optional("core.selection")
        doc.write(undo_key="tool.su.followme.undo", select=() if sel is not None else None)
        self.reset()
        self.update_status()
        return Result.IDLE

    # -- drawing -------------------------------------------------------------------------------------
    def draw_3d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None:
            return
        if self.profile is None:
            for poly in self.hover_polys:
                prims.polygon(dc, poly, colors.rgba(colors.SELECTION, 0.55), stipple=True)
        elif self.path_world:
            prims.lines(dc, self.path_world, colors.rgba(colors.LOCKED, 1.0), width=2.0)


def register():
    i18n.register_strings(STRINGS)
