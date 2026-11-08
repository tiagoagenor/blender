# SPDX-License-Identifier: GPL-2.0-or-later
"""Minimal stand-ins for other owners' modules (owner: A), used ONLY by A's tests while B/C have not
merged yet (PLANO §2.3-6: no stubs in other owners' files). `install(su_pkg)` puts a fake module in
sys.modules under the real name ONLY when the real module is missing; `uninstall()` removes them.

  core.document (B)  Document(write/world/invalidate) + root()/active()/get()/visible_documents()/invalidate_all()
  core.geom (B)      add_edge (weld + existing edge reuse) + auto_faces (shortest cycle → face, ground → −Z)
  core.vcb (C)       feed (PLANO §3.5-3 rules on STATE.vcb_buffer) + parse('length' and 'length2')
Each fake module has FAKE = True. Behaviour is deliberately simple: they exist to exercise A's routing.
"""

import sys
import types
from collections import deque

import bmesh
import bpy
from mathutils import Vector

_installed = []


class VCBValue:
    def __init__(self, kind, value):
        self.kind, self.value = kind, value

    def __repr__(self):
        return "VCBValue({!r}, {!r})".format(self.kind, self.value)


class EditResult:
    def __init__(self, new_verts=(), new_edges=(), new_faces=()):
        self.new_verts, self.new_edges, self.new_faces = list(new_verts), list(new_edges), list(new_faces)
        self.removed_faces = 0
        self.index_map = None


def _make_document(pkg):
    events = sys.modules[pkg + ".events"]
    undo = sys.modules[pkg + ".core.undo"]
    m = types.ModuleType(pkg + ".core.document")
    m.FAKE = True
    m._docs = {}

    class Document:
        def __init__(self, obj):
            self.obj = obj
            self.key = obj.name
            self.version = 0
            self.bm = bmesh.new()
            self.bm.from_mesh(obj.data)

        def write(self, *, undo_key):
            undo.before_change()
            self.bm.normal_update()
            self.bm.to_mesh(self.obj.data)
            self.obj.data.update()
            self.version += 1
            events.emit("geometry", doc_key=self.key)
            if undo_key:
                undo.push(undo_key)

        def world(self):
            return self.obj.matrix_world.copy()

        def invalidate(self):
            self.bm.free()
            self.bm = bmesh.new()
            self.bm.from_mesh(self.obj.data)

    def root(scene=None):
        ob = bpy.data.objects.get("Modelo")
        if ob is None:
            ob = bpy.data.objects.new("Modelo", bpy.data.meshes.new("Modelo"))
            (scene or bpy.context.scene).collection.objects.link(ob)
        return get(ob)

    def get(obj):
        d = m._docs.get(obj.name)
        if d is None or d.obj != obj:
            d = m._docs[obj.name] = Document(obj)
        return d

    def reset():
        for d in m._docs.values():
            d.bm.free()
        m._docs.clear()
        ob = bpy.data.objects.get("Modelo")
        if ob is not None:
            me = ob.data
            bpy.data.objects.remove(ob)
            bpy.data.meshes.remove(me)

    m.Document = Document
    m.root = root
    m.active = lambda: root()
    m.get = get
    m.visible_documents = lambda: [root()]
    m.invalidate_all = lambda: [d.invalidate() for d in m._docs.values()]
    m.reset = reset
    return m


def _make_geom(pkg):
    m = types.ModuleType(pkg + ".core.geom")
    m.FAKE = True
    m.EditResult = EditResult
    tol = 1e-5

    def weld_point(bm, co, tol=tol):
        for v in bm.verts:
            if (v.co - co).length <= tol:
                return v, False
        return bm.verts.new(co), True

    def add_edge(bm, a, b, *, curve_id=0):
        va, na = weld_point(bm, Vector(a))
        vb, nb = weld_point(bm, Vector(b))
        new_v = [v for v, n in ((va, na), (vb, nb)) if n]
        e = bm.edges.get((va, vb))
        if e is not None:
            return EditResult(new_v, [], [])
        e = bm.edges.new((va, vb))
        return EditResult(new_v, [e], auto_faces(bm, [e]))

    def _path(start, goal, skip):
        prev = {start: None}
        q = deque([start])
        while q:
            v = q.popleft()
            if v == goal:
                break
            for e in v.link_edges:
                if e == skip:
                    continue
                w = e.other_vert(v)
                if w not in prev:
                    prev[w] = v
                    q.append(w)
        if goal not in prev:
            return None
        out, v = [], goal
        while v is not None:
            out.append(v)
            v = prev[v]
        return out

    def auto_faces(bm, edges):
        faces = []
        for e in edges:
            path = _path(e.verts[0], e.verts[1], e)
            if path is None or len(path) < 3:
                continue
            f = bm.faces.new(path)
            f.normal_update()
            if abs(f.normal.z) > 0.99 and f.normal.z > 0.0 and all(abs(v.co.z) < tol for v in f.verts):
                f.normal_flip()              # ground face: back side up (normal −Z)
            faces.append(f)
        return faces

    m.weld_point = weld_point
    m.add_edge = add_edge
    m.auto_faces = auto_faces
    m.validate = lambda bm: []
    return m


def _make_vcb(pkg):
    state = sys.modules[pkg + ".core.state"]
    m = types.ModuleType(pkg + ".core.vcb")
    m.FAKE = True
    m.VCBValue = VCBValue
    starters = set("0123456789.,-[</*")

    def feed(ev):
        st = state.STATE
        buf = st.vcb_buffer
        if ev.type in {'RET', 'NUMPAD_ENTER'}:
            return 'APPLY' if buf else 'PASS'
        if ev.type == 'BACK_SPACE':
            if buf:
                st.vcb_buffer = buf[:-1]
                return 'CONSUMED'
            return 'PASS'
        if ev.type == 'ESC':
            if buf:
                st.vcb_buffer = ''
                return 'CANCEL'
            return 'PASS'
        ch = ev.unicode
        if not ch or (not buf and ch not in starters):
            return 'PASS'
        st.vcb_buffer = buf + ch
        return 'CONSUMED'

    def _num(s):
        s = s.strip().lower()
        if s.endswith("m"):
            s = s[:-1]
        return float(s.replace(",", "."))

    def parse(text, schema, units):
        parts = text.split(";")
        n = 2 if schema == "length2" else 1
        if len(parts) != n:
            raise ValueError("bad value")
        return [VCBValue("LENGTH", _num(p)) for p in parts]

    m.feed = feed
    m.parse = parse
    m.apply_text = lambda text: None
    return m


def _make_inference(pkg):
    """Endpoint (doc vertices + origin, 12 px) > axis from the anchor (9 px) > ground/anchor plane."""
    state = sys.modules[pkg + ".core.state"]
    m = types.ModuleType(pkg + ".core.inference")
    m.FAKE = True
    from bpy_extras import view3d_utils
    from mathutils import geometry

    class QueryCtx:
        def __init__(self, region=None, rv3d=None, xy=(0, 0), depsgraph=None, anchor=None, anchor_normal=None,
                     plane=None, line=None, flags=None, exclude=frozenset(), skip=None, locks=None, previous=None):
            self.__dict__.update(locals())
            del self.__dict__["self"]

    class Engine:
        def query(self, q):
            if q.region is None or q.rv3d is None:
                return state.Inference.none()
            xy = Vector(q.xy)
            scale = bpy.context.preferences.system.ui_scale or 1.0

            def px(co):
                p = view3d_utils.location_3d_to_region_2d(q.region, q.rv3d, co)
                return None if p is None else (p - xy).length

            pts = [Vector((0.0, 0.0, 0.0))]
            document = sys.modules.get(pkg + ".core.document")
            if document is not None:
                doc = document.root()
                mw = doc.world()
                pts += [mw @ v.co for v in doc.bm.verts]
            best = min(((px(p), p) for p in pts if px(p) is not None), default=(None, None), key=lambda t: t[0])
            if best[0] is not None and best[0] <= 12 * scale:
                kind = "ORIGIN" if best[1].length < 1e-9 else "ENDPOINT"
                return state.Inference(kind=kind, point=best[1].copy(), screen=tuple(q.xy))
            origin = view3d_utils.region_2d_to_origin_3d(q.region, q.rv3d, xy)
            ray = view3d_utils.region_2d_to_vector_3d(q.region, q.rv3d, xy)
            if q.anchor is not None:
                a = Vector(q.anchor)
                for name, d in (("AXIS_X", Vector((1, 0, 0))), ("AXIS_Y", Vector((0, 1, 0))),
                                ("AXIS_Z", Vector((0, 0, 1)))):
                    r = geometry.intersect_line_line(a, a + d, origin, origin + ray)
                    if r is None:
                        continue
                    p = r[0]
                    dist = px(p)
                    if dist is not None and dist <= 9 * scale and (p - a).length > 1e-6:
                        return state.Inference(kind="FREE", point=p, linear=name, direction=d, ref_point=a,
                                               screen=tuple(q.xy))
            co = Vector(q.anchor) if q.anchor is not None else Vector((0.0, 0.0, 0.0))
            p = geometry.intersect_line_plane(origin, origin + ray, co, Vector((0, 0, 1)))
            if p is None:
                return state.Inference.none()
            return state.Inference(kind="FREE", point=p, screen=tuple(q.xy))

        def acquire_tick(self, inf, t):
            pass

    m.QueryCtx = QueryCtx
    m.ENGINE = Engine()
    return m


MAKERS = {"core.document": _make_document, "core.geom": _make_geom, "core.vcb": _make_vcb,
          "core.inference": _make_inference}


def install(pkg="su", only=None):
    """Install fakes for missing modules of package `pkg`; returns the names installed."""
    names = []
    for rel, make in MAKERS.items():
        if only is not None and rel not in only:
            continue
        name = pkg + "." + rel
        if name in sys.modules and not getattr(sys.modules[name], "FAKE", False):
            continue                     # the real module exists: use it
        try:
            __import__(name)
            if not getattr(sys.modules[name], "FAKE", False):
                continue
        except ImportError:
            pass
        mod = make(pkg)
        sys.modules[name] = mod
        parent = sys.modules[pkg + "." + rel.rsplit(".", 1)[0]]
        setattr(parent, rel.rsplit(".", 1)[1], mod)
        _installed.append(name)
        names.append(name)
    return names


def is_fake(pkg, rel):
    return getattr(sys.modules.get(pkg + "." + rel), "FAKE", False)


def uninstall():
    while _installed:
        name = _installed.pop()
        mod = sys.modules.pop(name, None)
        if mod is not None and hasattr(mod, "reset"):
            mod.reset()
        pkg, _, leaf = name.rpartition(".")
        parent = sys.modules.get(pkg)
        if parent is not None and getattr(parent, leaf, None) is mod:
            delattr(parent, leaf)
