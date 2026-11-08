# SPDX-License-Identifier: GPL-2.0-or-later
"""Transform kernel for Mover / Girar / Escala (owner: F). Contract: PLANO.md §2.4-F, §3.8, §6.1 (AC-MOV-*).

    s = TransformSession(refs, copy=False, fold='AUTO', verts=None)
    s.set_matrix(m)          # world-space matrix applied to the ORIGINAL positions (live preview);
                             # RESTRICT returns the last accepted matrix when m would bend a face
    res = s.finish()         # fold (AUTO), write (1 undo step); selection = same entities (move) or the copy
    s.cancel()
    s.array(n, internal, matrix_at)   # after a COPY finish: n copies at matrix_at(k) (k = 1..n) or, internal
                                      # ("/n"), n copies at matrix_at(k/n) (the last one stays where the copy
                                      # was dropped); replaces the copies made before
    s.reapply_matrix(m)      # after a MOVE finish: move again to m (Medidas typed after the move)
    s.moving_faces           # {doc_key: {face idx}} faces that move rigidly (ray-cast skip)
    s.exclude                # spatial exclude (moving verts / moved objects) for inference

Geometry refs (EDGE/FACE of a document) move their vertices; faces linked to them stretch.
OBJECT refs (groups) move by matrix only (nothing sticks to them). `verts` = {doc_key: {vert idx}}
picks single vertices (Move on an endpoint with nothing selected).
fold: 'AUTO' (vertex/edge moves: faces that become non-planar are folded with visible edges,
geom.ensure_planar), 'RESTRICT' (face moves: a matrix that would leave a face non-planar is rejected;
shear that keeps faces planar is accepted), 'FREE' (P1).
Copies: geometry is duplicated inside the same document (not welded); groups and component instances
are duplicated with document.duplicate (instances share their definition mesh).
"""

import bmesh
import bpy
from mathutils import Matrix, Vector

from .. import events
from . import document, geom, selection

ORDER = 140

PLANAR_TOL = 1e-4


def _top_objects(objs):
    names = {o.name for o in objs}
    out = []
    for o in objs:
        p, nested = o.parent, False
        while p is not None:
            if p.name in names:
                nested = True
                break
            p = p.parent
        if not nested and o not in out:
            out.append(o)
    return out


def duplicate_object(obj, parent=None):
    """Copy of a group / component instance (B's document.duplicate: an instance SHARES its definition,
    a group gets its own mesh copy; children too; "doc" emitted for each new object)."""
    return document.duplicate(obj, parent)


def _copy_geometry(bm, faces, edges):
    """Duplicate faces + edges (and their verts) in `bm`. Returns (vmap old→new, new faces, new edges)."""
    lay = geom.ensure_layers(bm)
    vmap = {}
    edges = set(edges) | {e for f in faces for e in f.edges}

    def nv(v):
        n = vmap.get(v)
        if n is None:
            n = vmap[v] = bm.verts.new(v.co)
        return n
    new_edges = []
    emap = {}
    for e in edges:
        a, b = nv(e.verts[0]), nv(e.verts[1])
        ne = bm.edges.get((a, b)) or bm.edges.new((a, b))
        for name in ("bridge", "soft", "hidden", "curve"):
            ne[getattr(lay, name)] = e[getattr(lay, name)]
        ne.smooth = e.smooth
        emap[e] = ne
        new_edges.append(ne)
    new_faces = []
    for f in faces:
        nf = bm.faces.new([nv(v) for v in f.verts])
        nf.material_index = f.material_index
        nf.smooth = f.smooth
        nf[lay.back] = f[lay.back]
        nf.normal_update()
        new_faces.append(nf)
    return vmap, new_faces, new_edges


class _DocPart:
    """Per-document state of a session."""

    def __init__(self, doc, faces, edges, verts):
        self.doc = doc
        self.faces = faces          # BMFaces (selected entities)
        self.edges = edges          # BMEdges (selected)
        self.verts = verts          # BMVerts that move
        self.co0 = {}               # BMVert -> original local co
        self.copy_faces = []
        self.copy_edges = []


class TransformSession:
    def __init__(self, refs, *, copy=False, fold='AUTO', verts=None):
        self.copy = bool(copy)
        self.fold = fold
        self.matrix = Matrix.Identity(4)
        self.parts = []
        self.objects = []           # moved objects (copies when copy=True)
        self.mw0 = {}
        self.copies = []            # [[objects / (doc_key, faces, edges)]] per array element (after finish)
        self.finished = False
        refs = list(refs)
        by_doc = {}
        for r in refs:
            if r.kind in (selection.EDGE, selection.FACE):
                by_doc.setdefault(r.doc_key, {selection.EDGE: set(), selection.FACE: set()})[r.kind].add(r.index)
        for key, idx in (verts or {}).items():
            by_doc.setdefault(key, {selection.EDGE: set(), selection.FACE: set()}).setdefault('VERT', set()).update(idx)
        for key, sel in by_doc.items():
            doc = document.get_by_key(key)
            if doc is None:
                continue
            doc.begin()
            bm = doc.bm
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            faces = [bm.faces[i] for i in sorted(sel[selection.FACE]) if i < len(bm.faces)]
            edges = [bm.edges[i] for i in sorted(sel[selection.EDGE]) if i < len(bm.edges)]
            vsel = [bm.verts[i] for i in sorted(sel.get('VERT', ())) if i < len(bm.verts)]
            part = _DocPart(doc, faces, edges, [])
            part.src = (list(faces), list(edges))
            if self.copy:
                vmap, nf, ne = _copy_geometry(bm, faces, edges)
                for v in vsel:
                    if v not in vmap:
                        vmap[v] = bm.verts.new(v.co)
                part.copy_faces, part.copy_edges = nf, ne
                part.verts = list(vmap.values())
            else:
                vs = {v for f in faces for v in f.verts} | {v for e in edges for v in e.verts} | set(vsel)
                part.verts = list(vs)
            part.co0 = {v: v.co.copy() for v in part.verts}
            self.parts.append(part)
            doc.preview_write()
        objs = _top_objects([o for o in (bpy.data.objects.get(r.doc_key) for r in refs
                                         if r.kind == selection.OBJECT) if o is not None])
        self._src_objects = [(o.name, o.matrix_world.copy()) for o in objs]
        if self.copy:
            objs = [duplicate_object(o, o.parent) for o in objs]
            self._created_objects = list(objs)
        else:
            self._created_objects = []
        self.objects = objs
        self.mw0 = {o.name: o.matrix_world.copy() for o in objs}
        self._update_moving()

    # ------------------------------------------------------------------ info
    def _update_moving(self):
        self.moving_faces = {}
        ex = set()
        for p in self.parts:
            vs = set(p.verts)
            mf = {f.index for v in vs for f in v.link_faces if all(x in vs for x in f.verts)}
            self.moving_faces[p.doc.key] = mf
            ex.update((p.doc.key, v.index) for v in vs)
        for o in self.objects:
            stack = [o]
            while stack:
                x = stack.pop()
                ex.add(document.get(x).key if x.type == 'MESH' else x.name)
                stack.extend(x.children)
        self.exclude = frozenset(ex)

    def is_empty(self):
        return not any(p.verts for p in self.parts) and not self.objects

    def _bent(self, part):
        faces = {f for v in part.verts for f in v.link_faces}
        for f in faces:
            f.normal_update()
            if not geom.is_planar(f, PLANAR_TOL):
                return True
        return False

    # ------------------------------------------------------------------ transform
    def _apply(self, m):
        for p in self.parts:
            W = p.doc.world()
            L = W.inverted() @ m @ W
            for v, co in p.co0.items():
                if v.is_valid:
                    v.co = L @ co
        for o in self.objects:
            o.matrix_world = m @ self.mw0[o.name]

    def set_matrix(self, m):
        m = Matrix(m)
        self._apply(m)
        if self.fold == 'RESTRICT' and any(self._bent(p) for p in self.parts):
            self._apply(self.matrix)
            m = self.matrix
        else:
            self.matrix = m
        for p in self.parts:
            p.doc.preview_write()
        return m

    def cancel(self):
        for p in self.parts:
            p.doc.cancel()
        for o in self._created_objects:
            _remove_tree(o)
        if not self._created_objects:
            for o in self.objects:
                if bpy.data.objects.get(o.name) is not None:
                    o.matrix_world = self.mw0[o.name]
        self.parts, self.objects = [], []

    def _fold(self):
        res = geom.EditResult()
        if self.fold != 'AUTO':
            return res
        for p in self.parts:
            faces = list({f for v in p.verts if v.is_valid for f in v.link_faces})
            r = geom.ensure_planar(p.doc.bm, faces)
            res.new_edges += r.new_edges
            res.new_faces += r.new_faces
        return res

    def _commit(self, undo_key, select):
        from ..ops import edit_ops
        docs = [p.doc for p in self.parts]
        edit_ops.commit(docs, undo_key, select=select)

    def result_refs(self):
        """Refs of what was transformed (the copy when copying), for the selection."""
        out = []
        for p in self.parts:
            k = p.doc.key
            if self.copy:
                out += [selection.Ref(k, selection.FACE, f.index) for f in p.copy_faces if f.is_valid]
                out += [selection.Ref(k, selection.EDGE, e.index) for e in p.copy_edges if e.is_valid]
            else:
                out += [selection.Ref(k, selection.FACE, f.index) for f in p.faces if f.is_valid]
                out += [selection.Ref(k, selection.EDGE, e.index) for e in p.edges if e.is_valid]
        out += [selection.Ref(o.name, selection.OBJECT, 0) for o in self.objects]
        return out

    def finish(self, undo_key="tool.su.move.undo", keep_selection=True):
        """Fold (AUTO), write all documents as ONE undo step. Selection: same entities (move) or the copy."""
        res = self._fold()
        for p in self.parts:
            p.doc.bm.verts.index_update()
            p.doc.bm.edges.index_update()
            p.doc.bm.faces.index_update()
        pre = selection.get()
        refs = self.result_refs()
        select = refs if (self.copy or keep_selection) else None
        if not self.copy and keep_selection:
            # a move keeps the selection exactly (indices of existing elements do not change)
            select = pre if pre else None
        self._commit(undo_key, select)
        self.finished = True
        self.copies = [self._snapshot_copy()] if self.copy else []
        res.index_map = {}
        return res

    def _snapshot_copy(self):
        return {"objects": list(self.objects),
                "parts": [(p.doc.key, list(p.copy_faces), list(p.copy_edges), list(p.verts)) for p in self.parts]}

    # ------------------------------------------------------------------ after finish
    def reapply_matrix(self, m, undo_key=None):
        """Move (not copy) again to `m` from the ORIGINAL positions; writes without an undo step
        (the caller pushes "undo.adjust")."""
        for p in self.parts:
            p.verts = [v for v in p.verts if v.is_valid]
            p.co0 = {v: c for v, c in p.co0.items() if v.is_valid}
        self._apply(Matrix(m))
        self.matrix = Matrix(m)
        self._fold()
        for p in self.parts:
            p.doc.write(undo_key=undo_key)

    def array(self, n, internal, matrix_at):
        """Replace the copies by an array: n copies at matrix_at(k), k=1..n (or k/n, internal).
        The source = the original (pre-copy) entities. Writes without an undo step. Selection = last copy."""
        n = int(n)
        if not self.copy or n < 1:
            return False
        # remove every copy made so far
        for c in self.copies:
            for o in c["objects"]:
                _remove_tree(o)
            for key, faces, edges, verts in c["parts"]:
                doc = document.get_by_key(key)
                if doc is None:
                    continue
                vs = [v for v in verts if v.is_valid]
                if vs:
                    bmesh.ops.delete(doc.bm, geom=vs, context='VERTS')
        self.copies = []
        steps = [k / n for k in range(1, n + 1)] if internal else [float(k) for k in range(1, n + 1)]
        last = None
        for t in steps:
            last = self._make_copy(matrix_at(t))
            self.copies.append(last)
        docs = {p.doc.key: p.doc for p in self.parts}
        for d in docs.values():
            d.write(undo_key=None)
        if last is not None:
            refs = [selection.Ref(o.name, selection.OBJECT, 0) for o in last["objects"]]
            for key, faces, edges, _v in last["parts"]:
                refs += [selection.Ref(key, selection.FACE, f.index) for f in faces if f.is_valid]
                refs += [selection.Ref(key, selection.EDGE, e.index) for e in edges if e.is_valid]
            selection.set(refs)
        return True

    def _make_copy(self, m):
        c = {"objects": [], "parts": []}
        for p in self.parts:
            doc = p.doc
            bm = doc.bm
            src_f, src_e = p.src
            vmap, nf, ne = _copy_geometry(bm, [f for f in src_f if f.is_valid], [e for e in src_e if e.is_valid])
            W = doc.world()
            L = W.inverted() @ m @ W
            for v in vmap.values():
                v.co = L @ v.co
            c["parts"].append((doc.key, nf, ne, list(vmap.values())))
        for name, mw in self._src_objects:
            o = bpy.data.objects.get(name)
            if o is None:
                continue
            new = duplicate_object(o, o.parent)
            new.matrix_world = m @ mw
            c["objects"].append(new)
        return c


def _remove_tree(obj):
    if obj is None or bpy.data.objects.get(obj.name) is None:
        return
    for ch in list(obj.children):
        _remove_tree(ch)
    me = obj.data if obj.type == 'MESH' else None
    bpy.data.objects.remove(obj)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)


def mirror(refs, plane_co, plane_normal, copy, verts=None, undo_key="tool.su.flip.undo"):
    """Virar (P1): reflect the refs in the plane (world) as ONE undo step. Faces that move rigidly are
    reversed so normals stay outward (geometry folds where a partial selection bends faces).
    Returns the finished session."""
    n = Vector(plane_normal).normalized()
    R = Matrix.Identity(4)
    for i in range(3):
        for j in range(3):
            R[i][j] = (1.0 if i == j else 0.0) - 2.0 * n[i] * n[j]
    c = Vector(plane_co)
    T = Matrix.Translation(c) @ R @ Matrix.Translation(-c)
    s = TransformSession(refs, copy=copy, fold='AUTO', verts=verts)
    s.set_matrix(T)
    reverse_rigid(s)
    s.finish(undo_key)
    return s


def reverse_rigid(s):
    """Reverse the faces whose vertices all moved (after a mirroring matrix)."""
    for p in s.parts:
        vs = set(p.verts)
        geom.reverse_faces(p.doc.bm, [f for f in p.doc.bm.faces if all(v in vs for v in f.verts)])
