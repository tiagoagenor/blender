# SPDX-License-Identifier: GPL-2.0-or-later
"""Escala (owner: F). PLANO.md §6.1 (AC-ESC-1..4).

The selection (or, with nothing selected, the entity under the cursor) gets a yellow bounding box
with grips: 8 corners (uniform; Shift = per axis), 12 edge midpoints (the 2 axes across the edge),
6 face centres (1 axis). Click a grip, move, click (or drag): the opposite grip stays fixed (Option =
about the centre). Medidas "Escala": `1,5` (factor), `3m` (new length along the grip's axis),
`2;1;1` (per axis), `-1` (mirror; faces are reversed so normals stay outward). A single group scales
by matrix in its own axes; geometry in world axes. The selection is kept.
"""

import bpy
from mathutils import Matrix, Vector

from .. import colors, constants, i18n, modifiers, registry
from ..core.state import STATE, LastAction, Locks
from . import move as move_tool
from .base import BaseTool, Result, ToolMeta, kind_of, make_query, tool, value_of

TOOL_ID = "su.scale"
YELLOW = (255, 210, 0)
GRIP_PX = 10

STRINGS = {
    "tool.su.scale.label": {"pt_BR": "Escala", "en": "Scale"},
    "tool.su.scale.hint_pick": {"pt_BR": "Selecione uma alça. Shift = Uniforme. {opt} = Em torno do centro.",
                                "en": "Pick a grip. Shift = Uniform. {opt} = About center."},
    "tool.su.scale.hint_drag": {"pt_BR": "Mova para escalar. Shift = Uniforme. {opt} = Em torno do centro.",
                                "en": "Move to scale. Shift = Uniform. {opt} = About center."},
    "tool.su.scale.undo": {"pt_BR": "Escala", "en": "Scale"},
}


def _fmt(f):
    return "{:.2f}".format(f).replace(".", ",")


class Box:
    """Bounding box of the targets: local min/max + matrix (world axes, or a single group's axes)."""

    def __init__(self, refs, verts):
        from ..core import document, selection
        self.matrix = Matrix.Identity(4)
        objs = [bpy.data.objects.get(r.doc_key) for r in refs if r.kind == selection.OBJECT]
        geo = [r for r in refs if r.kind != selection.OBJECT]
        pts = []
        if len(objs) == 1 and objs[0] is not None and not geo and not verts:
            o = objs[0]
            self.matrix = o.matrix_world.copy()
            pts = [Vector(c) for c in _local_corners(o)]
        else:
            for o in objs:
                if o is not None:
                    pts += [o.matrix_world @ Vector(c) for c in _local_corners(o)]
            by_doc = {}
            for r in geo:
                by_doc.setdefault(r.doc_key, set()).add((r.kind, r.index))
            for key, vs in (verts or {}).items():
                by_doc.setdefault(key, set()).update(('VERT', i) for i in vs)
            for key, items in by_doc.items():
                doc = document.get_by_key(key)
                if doc is None:
                    continue
                bm, W = doc.bm, doc.world()
                bm.verts.ensure_lookup_table()
                bm.edges.ensure_lookup_table()
                bm.faces.ensure_lookup_table()
                for k, i in items:
                    if k == 'FACE' and i < len(bm.faces):
                        pts += [W @ v.co for v in bm.faces[i].verts]
                    elif k == 'EDGE' and i < len(bm.edges):
                        pts += [W @ v.co for v in bm.edges[i].verts]
                    elif k == 'VERT' and i < len(bm.verts):
                        pts.append(W @ bm.verts[i].co)
        if not pts:
            self.mn = self.mx = None
            return
        self.mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        self.mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))

    def ok(self):
        return self.mn is not None

    def grips(self):
        """[(code (i,j,k) in {0,1,2}^3 minus centre, world point)] — 0 = min, 1 = mid, 2 = max."""
        out = []
        flat = [self.mx[a] - self.mn[a] <= constants.GEOM_TOL for a in range(3)]
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    code = (i, j, k)
                    if code == (1, 1, 1):
                        continue
                    if any(flat[a] and code[a] != 1 for a in range(3)) and sum(c != 1 for c in code) > 1:
                        continue
                    if any(flat[a] and code[a] != 1 for a in range(3)):
                        continue
                    out.append((code, self.matrix @ self.local(code)))
        return out

    def local(self, code):
        return Vector([(self.mn[a], (self.mn[a] + self.mx[a]) * 0.5, self.mx[a])[code[a]] for a in range(3)])


def _local_corners(o):
    out = []
    stack = [(o, Matrix.Identity(4))]
    while stack:
        x, m = stack.pop()
        if x.type == 'MESH' and len(x.data.vertices):
            out += [m @ Vector(c) for c in x.bound_box]
        for ch in x.children:
            stack.append((ch, m @ (x.matrix_world.inverted() @ ch.matrix_world)))
    return out or [Vector()]


@tool(ToolMeta(id=TOOL_ID, label_key="tool.su.scale.label", icon="ops.transform.resize", shortcut="S",
               cursor='CROSSHAIR', vcb_label_key="vcb.scale", vcb_schema="scale"))
class ScaleTool(BaseTool):

    def __init__(self):
        self.box = None
        self.targets = ([], {})
        self.hot = None              # grip code under the cursor
        self.grip = None             # grip being dragged
        self.session = None
        self.factors = Vector((1, 1, 1))
        self.uniform_toggle = False
        self.about_center = False
        self.last = None
        self.last_info = None

    # -- status --------------------------------------------------------------------------------------
    def update_status(self):
        opt = modifiers.label("copy")
        STATE.set_hint("tool.su.scale.hint_drag" if self.session else "tool.su.scale.hint_pick", opt=opt)
        if self.session is not None:
            STATE.set_vcb(self.meta.vcb_label_key, self.vcb_text(self.grip, self.factors, self.uniform_toggle))
        else:
            STATE.set_vcb(self.meta.vcb_label_key, STATE.vcb_value)

    def _refresh_box(self, tc=None, xy=None, inf=None):
        from ..core import selection
        if not selection.is_empty():
            self.targets = (list(selection.get()), {})
        elif tc is not None:
            self.targets = move_tool.hover_target(tc, xy, inf)
        else:
            self.targets = ([], {})
        self.box = Box(*self.targets) if (self.targets[0] or self.targets[1]) else None
        if self.box is not None and not self.box.ok():
            self.box = None

    def activate(self, tc):
        self.session = None
        self._refresh_box()
        self.update_status()

    def deactivate(self, tc):
        self.cancel(tc)

    def cancel(self, tc):
        if self.session is not None:
            self.session.cancel()
        self.session = None
        self.grip = None
        self.factors = Vector((1, 1, 1))
        self.update_status()

    # -- grips ---------------------------------------------------------------------------------------
    def _grip_at(self, tc, xy, inf):
        if self.box is None:
            return None
        grips = self.box.grips()
        if tc.region is not None and tc.rv3d is not None:
            from ..core import viewutil
            best, bd = None, viewutil.ui_px(GRIP_PX)
            for code, p in grips:
                s = viewutil.project(tc.region, tc.rv3d, p)
                if s is None:
                    continue
                d = (Vector(s) - Vector(xy)).length
                if d <= bd:
                    best, bd = code, d
            return best
        if inf is None or inf.kind == "NONE":
            return None
        size = max((self.box.mx - self.box.mn).length, 1.0)
        for code, p in grips:
            if (p - Vector(inf.point)).length <= 1e-4 * size:
                return code
        return None

    def _axes(self, code):
        return [a for a in range(3) if code is not None and code[a] != 1]

    def vcb_text(self, code, factors, uniform_toggle):
        """Medidas text as SketchUp shows it: ONE factor for a uniform scale (corner grip, or Shift),
        otherwise one value per scaled axis (1 for a face grip, 2 for an edge grip, 3 for Shift+corner)."""
        axes = self._axes(code)
        corner = len(axes) == 3
        uniform = (corner != uniform_toggle) if corner else uniform_toggle
        if uniform or not axes:
            return _fmt(factors[axes[0]] if axes else factors[0])
        return "; ".join(_fmt(factors[a]) for a in axes)

    def _uniform(self, code):
        corner = len(self._axes(code)) == 3
        return corner != self.uniform_toggle if corner else self.uniform_toggle

    def _anchor_local(self, code):
        if self.about_center:
            return (self.box.mn + self.box.mx) * 0.5
        return self.box.local(tuple(2 - c if c != 1 else 1 for c in code))

    def _matrix(self, factors):
        a = self._anchor_local(self.grip)
        S = Matrix.Diagonal((factors[0], factors[1], factors[2], 1.0))
        L = Matrix.Translation(a) @ S @ Matrix.Translation(-a)
        M = self.box.matrix
        return M @ L @ M.inverted()

    # -- events --------------------------------------------------------------------------------------
    def query_ctx(self, tc, xy):
        if self.session is not None:
            return make_query(tc, xy, exclude=self.session.exclude, skip=self.session.moving_faces)
        return make_query(tc, xy)

    def hover(self, tc, inf):
        self._refresh_box(tc, tc.xy, inf)
        self.hot = self._grip_at(tc, tc.xy, inf)

    def press(self, tc, ev, inf):
        if self.session is not None:
            return self._finish()
        self._refresh_box(tc, (ev.x, ev.y), inf)
        code = self._grip_at(tc, (ev.x, ev.y), inf)
        if code is None:
            return Result.IDLE
        from ..core import geom_transform
        refs, verts = self.targets
        self.grip = code
        self.uniform_toggle = ev.shift
        self.about_center = ev.copy
        self.factors = Vector((1, 1, 1))
        self.session = geom_transform.TransformSession(refs, copy=False, fold='AUTO', verts=verts)
        self.update_status()
        return Result.RUNNING

    def release(self, tc, ev, inf):
        if self.session is not None and ev.is_drag_release:
            return self._finish()
        return Result.RUNNING if self.session is not None else Result.IDLE

    def key(self, tc, ev):
        if self.session is None:
            return Result.PASS
        if ev.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'}:
            self.uniform_toggle = ev.value == 'PRESS'
            return Result.RUNNING
        if ev.type in {'LEFT_ALT', 'RIGHT_ALT'}:
            self.about_center = ev.value == 'PRESS'
            return Result.RUNNING
        return Result.PASS

    def move(self, tc, ev, inf):
        if self.session is None or inf is None or inf.kind == "NONE":
            return Result.RUNNING if self.session else Result.IDLE
        M = self.box.matrix
        p = M.inverted() @ Vector(inf.point)
        a = self._anchor_local(self.grip)
        g = self.box.local(self.grip)
        axes = self._axes(self.grip)
        f = Vector((1, 1, 1))
        if self._uniform(self.grip):
            d = g - a
            if d.length > constants.GEOM_TOL:
                k = (p - a).dot(d) / d.length_squared
                for ax in axes:
                    f[ax] = k
                if len(axes) < 3:
                    f = Vector((k, k, k))
        else:
            for ax in axes:
                den = g[ax] - a[ax]
                if abs(den) > constants.GEOM_TOL:
                    f[ax] = (p[ax] - a[ax]) / den
        self.factors = f
        self.session.set_matrix(self._matrix(f))
        self.update_status()
        return Result.RUNNING

    def vcb(self, tc, values):
        if self.session is None or not values:
            return Result.PASS
        f = self._factors_from(values, self.grip, self.box)
        if f is None:
            STATE.vcb_error = True
            return Result.RUNNING
        self.factors = f
        return self._finish()

    def _factors_from(self, values, code, box):
        axes = self._axes(code)
        size = box.mx - box.mn
        out = Vector((1, 1, 1))
        vals = []
        for v in values:
            if kind_of(v) == "LENGTH":
                vals.append(('L', value_of(v)))
            elif kind_of(v) in {"NUMBER", "SCALE"}:
                vals.append(('F', value_of(v)))
            else:
                return None
        if not vals:
            return None
        if len(vals) == 1:
            kind, x = vals[0]
            targets = axes if not self._uniform(code) or len(axes) == 3 else [0, 1, 2]
            for ax in targets:
                if kind == 'L':
                    if size[ax] <= constants.GEOM_TOL:
                        return None
                    out[ax] = x / size[ax]
                else:
                    out[ax] = x
            if kind == 'L' and self._uniform(code) and len(axes) == 3:
                k = x / max(size[axes[0]], constants.GEOM_TOL)
                out = Vector((k, k, k))
            return out
        for ax, (kind, x) in zip(axes, vals):
            if kind == 'L':
                if size[ax] <= constants.GEOM_TOL:
                    return None
                out[ax] = x / size[ax]
            else:
                out[ax] = x
        return out

    def _finish(self):
        s = self.session
        m = self._matrix(self.factors)
        self._apply_final(s, m)
        s.finish("tool.su.scale.undo")
        self.last = s
        self.last_info = (self.grip, self.about_center, self.uniform_toggle,
                          Box.__new__(Box), self.factors.copy())
        b = self.last_info[3]
        b.matrix, b.mn, b.mx = self.box.matrix.copy(), self.box.mn.copy(), self.box.mx.copy()
        STATE.last_action = LastAction(tool_id=TOOL_ID, schema=self.meta.vcb_schema, reapply=self._reapply)
        STATE.locks = Locks()                 # arrow/Shift locks end with the operation
        self.session = None
        self.grip = None
        self._refresh_box()
        self.update_status()
        grip, _c, uni, _b, f = self.last_info
        STATE.set_vcb(self.meta.vcb_label_key, self.vcb_text(grip, f, uni))
        return Result.IDLE

    def _apply_final(self, s, m):
        from ..core import geom
        s.set_matrix(m)
        if m.determinant() < 0:
            for p in s.parts:
                vs = set(p.verts)
                faces = [f for f in p.doc.bm.faces if all(v in vs for v in f.verts)]
                geom.reverse_faces(p.doc.bm, faces)

    def _reapply(self, values):
        if self.last is None or self.last_info is None:
            return False
        grip, center, uni, box, _f = self.last_info
        saved = (self.grip, self.about_center, self.uniform_toggle, self.box)
        self.grip, self.about_center, self.uniform_toggle, self.box = grip, center, uni, box
        try:
            f = self._factors_from(values, grip, box)
            if f is None:
                return False
            old_det = self.last.matrix.determinant()
            m = self._matrix(f)
            self.last.reapply_matrix(m)
            if (m.determinant() < 0) != (old_det < 0):
                from ..core import geom
                for p in self.last.parts:
                    vs = set(p.verts)
                    geom.reverse_faces(p.doc.bm, [x for x in p.doc.bm.faces if all(v in vs for v in x.verts)])
                    p.doc.write(undo_key=None)
            self.last_info = (grip, center, uni, box, f)
            STATE.set_vcb(self.meta.vcb_label_key, self.vcb_text(grip, f, uni))
            return True
        finally:
            self.grip, self.about_center, self.uniform_toggle, self.box = saved

    # -- drawing -------------------------------------------------------------------------------------
    def draw_3d(self, dc):
        prims = registry.optional("draw.prims")
        if prims is None or self.box is None or self.box.mn is None:
            return
        yellow = colors.rgba(YELLOW)
        if self.session is None:
            prims.box(dc, self.box.mn, self.box.mx, self.box.matrix, yellow)
            pts = [p for code, p in self.box.grips()]
            prims.grips(dc, pts, colors.rgba((0, 160, 0)), 6)
            if self.hot is not None:
                prims.grips(dc, [self.box.matrix @ self.box.local(self.hot)], colors.rgba((255, 0, 0)), 8)
        else:
            m = self._matrix(self.factors)
            prims.box(dc, self.box.mn, self.box.mx, m @ self.box.matrix, yellow)
            prims.grips(dc, [m @ self.box.matrix @ self.box.local(self.grip)], colors.rgba((255, 0, 0)), 8)


def register():
    i18n.register_strings(STRINGS)
