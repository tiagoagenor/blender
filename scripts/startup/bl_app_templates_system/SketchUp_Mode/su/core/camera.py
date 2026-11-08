# SPDX-License-Identifier: GPL-2.0-or-later
"""Camera / navigation math (owner: G). Contract: PLANO.md §2.4 (core/camera.py), §5.2, §6.3 AC-NAV-*.

Everything works on a `View`: a plain snapshot of a 3D view (location = orbit target, rotation,
distance, perspective/ortho, region size, vertical FOV). Pure math, so the navigation rules are unit
tested headless; `View.from_rv3d()` / `View.apply()` bridge to Blender's RegionView3D.

SketchUp rules implemented here:
  orbit_about   turntable, the blue axis always vertical (no roll), pivot = point under the cursor at
                the PRESS (screen-centre target over empty space); vertical travel clamped at top/bottom
  pan_to        the grabbed point stays under the cursor (perspective-correct)
  zoom_at       wheel: dolly towards the point under the cursor; that point stays under the cursor
  recenter_at   double MMB: the point goes to the screen centre (pan; rotation and depth kept)
  zoom_extents  fit the model's bounding box in 90 % of the region (rotation kept)
  standard_view Exibições padrão (Iso, Superior, Inferior, Frontal, Traseira, Esquerda, Direita)
  set_fov_v / keep_fov   vertical field of view 35° (Blender's viewport lens fits the WIDTH: the lens is
                re-fitted whenever the region aspect changes)
  push_history / previous / next   Câmera ▸ Anterior / Próxima
"""

import math
import time

import bpy
from mathutils import Matrix, Quaternion, Vector

from .. import constants, events, perf, registry

ORDER = 140

ORBIT_DEG_PER_PX = 0.4         # logical px (Blender's turntable sensitivity; SketchUp feels the same)
WHEEL_FACTOR = 1.0 / 1.25       # distance multiplier per wheel notch (zoom in)
EXTENTS_MARGIN = 0.9            # AC-NAV-6: bbox in 90 % of the region
HISTORY_MAX = 50
ISO_ELEVATION_DEG = 30.0
FOV_TOL_DEG = 0.05


def _clamp(x, a, b):
    return a if x < a else b if x > b else x


class View:
    """Snapshot of a 3D view. `loc` = view centre (orbit target over empty space), `rot` = view
    rotation (columns: right, up, back), `dist` = distance from the eye to `loc`. Perspective:
    `tan_v` = tan(vertical FOV / 2). Orthographic: `ortho_c` = half height / dist."""

    def __init__(self, loc, rot, dist, *, persp=True, width=1000, height=800, fov_v_deg=None,
                 tan_v=None, ortho_c=None):
        self.loc = Vector(loc)
        self.rot = Quaternion(rot).normalized()
        self.dist = float(dist)
        self.persp = bool(persp)
        self.width = int(width)
        self.height = int(height)
        if tan_v is None:
            tan_v = math.tan(math.radians(fov_v_deg if fov_v_deg else constants.DEFAULT_FOV_V_DEG) / 2.0)
        self.tan_v = float(tan_v)
        self.ortho_c = float(ortho_c) if ortho_c else self.tan_v

    # ---------------------------------------------------------------------------------- basics
    def copy(self):
        return View(self.loc, self.rot, self.dist, persp=self.persp, width=self.width, height=self.height,
                    tan_v=self.tan_v, ortho_c=self.ortho_c)

    @property
    def matrix(self):
        return self.rot.to_matrix()

    @property
    def right(self):
        return Vector(self.matrix.col[0])

    @property
    def up(self):
        return Vector(self.matrix.col[1])

    @property
    def back(self):
        return Vector(self.matrix.col[2])

    @property
    def fwd(self):
        return -self.back

    @property
    def aspect(self):
        return self.width / max(1, self.height)

    @property
    def fov_v_deg(self):
        return math.degrees(2.0 * math.atan(self.tan_v))

    def eye(self):
        return self.loc + self.back * self.dist

    def half_h(self):
        """Orthographic half height (world units)."""
        return self.ortho_c * self.dist

    def ndc(self, xy):
        return (2.0 * xy[0] / max(1, self.width) - 1.0, 2.0 * xy[1] / max(1, self.height) - 1.0)

    def ray_dir_local(self, xy):
        nx, ny = self.ndc(xy)
        return Vector((nx * self.tan_v * self.aspect, ny * self.tan_v, -1.0)).normalized()

    def ray(self, xy):
        """(origin, unit direction) of the view ray through region pixel xy."""
        if self.persp:
            return self.eye(), (self.matrix @ self.ray_dir_local(xy)).normalized()
        nx, ny = self.ndc(xy)
        h = self.half_h()
        o = self.loc + self.right * (nx * h * self.aspect) + self.up * (ny * h) + self.back * (self.dist + 1e4)
        return o, self.fwd

    def project(self, p):
        """World point → region px Vector((x, y)), None behind the eye (perspective)."""
        m = self.matrix
        if self.persp:
            v = m.transposed() @ (Vector(p) - self.eye())
            if v.z > -1e-9:
                return None
            nx = v.x / -v.z / (self.tan_v * self.aspect)
            ny = v.y / -v.z / self.tan_v
        else:
            v = m.transposed() @ (Vector(p) - self.loc)
            h = self.half_h()
            nx = v.x / (h * self.aspect)
            ny = v.y / h
        return Vector(((nx + 1.0) * 0.5 * self.width, (ny + 1.0) * 0.5 * self.height))

    def depth(self, p):
        """Distance of p in front of the eye along the view direction."""
        return (Vector(p) - self.eye()).dot(self.fwd)

    def point_at_depth(self, xy, depth):
        """Point under pixel xy at `depth` along the view direction."""
        o, d = self.ray(xy)
        if self.persp:
            return o + d * (depth / max(1e-12, d.dot(self.fwd)))
        return o + d * (depth + 1e4)

    def center_xy(self):
        return (self.width * 0.5, self.height * 0.5)

    def same_as(self, other, tol=1e-6):
        return ((self.loc - other.loc).length < tol and abs(self.dist - other.dist) < tol
                and self.rot.rotation_difference(other.rot).angle < tol and self.persp == other.persp)

    # ---------------------------------------------------------------------------------- Blender bridge
    @classmethod
    def from_rv3d(cls, region, rv3d):
        wm = rv3d.window_matrix
        persp = bool(rv3d.is_perspective)
        v = cls(rv3d.view_location, rv3d.view_rotation, rv3d.view_distance, persp=persp,
                width=region.width, height=region.height)
        k = wm[1][1]
        if persp and k > 1e-9:
            v.tan_v = 1.0 / k
        elif not persp and k > 1e-12:
            v.ortho_c = (1.0 / k) / max(1e-9, rv3d.view_distance)
        return v

    def apply(self, rv3d):
        rv3d.view_rotation = self.rot
        rv3d.view_distance = self.dist
        rv3d.view_location = self.loc
        want = 'PERSP' if self.persp else 'ORTHO'
        if rv3d.view_perspective != 'CAMERA' and rv3d.view_perspective != want:
            rv3d.view_perspective = want

    def state(self):
        return (tuple(self.loc), tuple(self.rot), self.dist, self.persp)


# ------------------------------------------------------------------------------------------ navigation

def level(v):
    """Remove any roll: right axis horizontal, up axis pointing up (top/bottom views kept as they are)."""
    f = v.fwd
    if abs(f.z) > 0.999:
        return v
    right = f.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = right.cross(f).normalized()
    v.rot = Matrix((right, up, -f)).transposed().to_quaternion()
    return v


def orbit_about(v, pivot, dx, dy, deg_per_px=ORBIT_DEG_PER_PX):
    """Turntable orbit (blue axis vertical) about world point `pivot` by a mouse delta in LOGICAL px.
    Mouse right → the model turns right; mouse up → the camera goes down (grab metaphor)."""
    pivot = Vector(pivot) if pivot is not None else v.loc.copy()
    level(v)
    k = math.radians(deg_per_px)
    yaw = -dx * k
    f = v.fwd
    cur = math.asin(_clamp(f.z, -1.0, 1.0))
    new = _clamp(cur + dy * k, -math.pi / 2.0, math.pi / 2.0)
    q = Quaternion((0.0, 0.0, 1.0), yaw) @ Quaternion(v.right, new - cur)
    v.loc = pivot + q @ (v.loc - pivot)
    v.rot = (q @ v.rot).normalized()
    return v


def pan_to(v, p, xy, depth=None):
    """Move the camera (rotation kept) so world point `p` lands under region pixel `xy`."""
    p = Vector(p)
    if v.persp:
        d = v.depth(p) if depth is None else depth
        if d <= 1e-9:
            return v
        dirw = (v.matrix @ v.ray_dir_local(xy)).normalized()
        eye = p - dirw * (d / max(1e-12, dirw.dot(v.fwd)))
        v.loc = eye + v.fwd * v.dist
    else:
        q = v.point_at_depth(xy, 0.0)
        lateral = (q - p)
        lateral -= v.fwd * lateral.dot(v.fwd)
        v.loc = v.loc - lateral
    return v


def pan_pixels(v, dx, dy, depth_point=None):
    """Pan so the content moves by (dx, dy) region px (trackpad / keyboard)."""
    p = Vector(depth_point) if depth_point is not None else v.loc.copy()
    s = v.project(p)
    if s is None:
        p = v.loc.copy()
        s = v.project(p)
    return pan_to(v, p, (s.x + dx, s.y + dy))


def zoom_at(v, p, factor):
    """Dolly by `factor` (< 1 = closer) towards world point `p` (kept under its pixel)."""
    p = Vector(p)
    factor = max(1e-4, float(factor))
    if v.persp:
        eye = p + (v.eye() - p) * factor
        v.dist = max(1e-4, v.dist * factor)
        v.loc = eye + v.fwd * v.dist
    else:
        v.loc = p + (v.loc - p) * factor
        v.dist = max(1e-4, v.dist * factor)
    return v


def wheel_factor(steps):
    """Distance factor for `steps` wheel notches (+ = scroll up = zoom in)."""
    return WHEEL_FACTOR ** steps


def recenter_at(v, p):
    """Bring world point `p` to the screen centre (pan; rotation kept; p becomes the orbit target)."""
    p = Vector(p)
    if v.persp:
        d = v.depth(p)
        if d <= 1e-6:
            return v
        v.loc = p
        v.dist = d
    else:
        lateral = p - v.loc
        lateral -= v.fwd * lateral.dot(v.fwd)
        v.loc = v.loc + lateral
    return v


def _extent(v, pts):
    """(xmin, xmax, ymin, ymax) NDC of pts, or None if a point is behind the eye."""
    xs, ys = [], []
    for p in pts:
        s = v.project(p)
        if s is None:
            return None
        nx, ny = v.ndc(s)
        xs.append(nx)
        ys.append(ny)
    return min(xs), max(xs), min(ys), max(ys)


def fit_points(v, pts, margin=EXTENTS_MARGIN):
    """Zoom extents: rotation kept, camera moved so `pts` fill `margin` of the region, centred."""
    pts = [Vector(p) for p in pts]
    if not pts:
        return v
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (mn + mx) * 0.5
    radius = max((mx - mn).length * 0.5, 1e-3)
    if not v.persp:
        m = v.matrix.transposed()
        loc_pts = [m @ (p - c) for p in pts]
        xs = [q.x for q in loc_pts]
        ys = [q.y for q in loc_pts]
        cx, cy = (min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5
        hw, hh = max(1e-6, (max(xs) - min(xs)) * 0.5), max(1e-6, (max(ys) - min(ys)) * 0.5)
        v.loc = c + v.right * cx + v.up * cy
        v.dist = max(hh, hw / v.aspect) / margin / max(1e-9, v.ortho_c)
        return v

    def place(D):
        w = v.copy()
        w.loc = c.copy()
        w.dist = D
        for _ in range(4):                       # recentre the screen bbox (depth varies per corner)
            e = _extent(w, pts)
            if e is None:
                break
            ox, oy = (e[0] + e[1]) * 0.5, (e[2] + e[3]) * 0.5
            w.loc = w.loc + w.right * (ox * w.tan_v * w.aspect * D) + w.up * (oy * w.tan_v * D)
        return w

    def size(w):
        e = _extent(w, pts)
        if e is None:
            return float("inf")
        return max((e[1] - e[0]) * 0.5, (e[3] - e[2]) * 0.5)

    lo, hi = radius * 1e-3, radius * 1e4
    for _ in range(60):                          # extent decreases with the distance → bisection
        mid = math.sqrt(lo * hi)
        if size(place(mid)) > margin:
            lo = mid
        else:
            hi = mid
    w = place(hi)
    v.loc, v.dist = w.loc, w.dist
    return v


STANDARD_VIEWS = ("ISO", "TOP", "BOTTOM", "FRONT", "BACK", "LEFT", "RIGHT")


def standard_rotation(name):
    """Rotation of Câmera ▸ Exibições padrão ▸ <name> (columns right, up, back)."""
    X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
    if name == "TOP":
        r, u, b = X, Y, Z
    elif name == "BOTTOM":
        r, u, b = X, -Y, -Z
    elif name == "FRONT":
        r, u, b = X, Z, -Y
    elif name == "BACK":
        r, u, b = -X, Z, Y
    elif name == "LEFT":
        r, u, b = -Y, Z, -X
    elif name == "RIGHT":
        r, u, b = Y, Z, X
    elif name == "ISO":                          # from front-right-top: red runs to the lower right
        e = math.radians(ISO_ELEVATION_DEG)
        b = Vector((math.cos(e) / math.sqrt(2.0), -math.cos(e) / math.sqrt(2.0), math.sin(e)))
        r = Z.cross(b).normalized()
        u = b.cross(r).normalized()
    else:
        raise ValueError("unknown standard view {!r}".format(name))
    return Matrix((r, u, b)).transposed().to_quaternion()


def standard_view_of(v, name):
    """Same target and distance, rotation of the standard view."""
    v.rot = standard_rotation(name)
    return v


def lens_for_fov(lens, tan_v_now, fov_v_deg):
    """Viewport lens giving vertical FOV `fov_v_deg` (tan(fov/2) ∝ 1/lens at a fixed aspect)."""
    want = math.tan(math.radians(fov_v_deg) / 2.0)
    if tan_v_now <= 1e-12 or want <= 1e-12:
        return lens
    return lens * tan_v_now / want


# ------------------------------------------------------------------------------------------ scene data

def fov_v():
    """Vertical FOV of the model (degrees): scene.su_pages.fov_v when G's pages exist, else 35°."""
    scene = getattr(bpy.context, "scene", None)
    pages = getattr(scene, "su_pages", None) if scene is not None else None
    v = getattr(pages, "fov_v", 0.0) if pages is not None else 0.0
    return v if v > 0.0 else constants.DEFAULT_FOV_V_DEG


# ------------------------------------------------------------------------------------------ GUI glue

def view3d(context=None):
    """(window, area, region, rv3d) of the mode's main 3D view (or the context's)."""
    context = context or bpy.context
    region = getattr(context, "region", None)
    area = getattr(context, "area", None)
    if region is not None and region.type == 'WINDOW' and area is not None and area.type == 'VIEW_3D':
        return context.window, area, region, context.region_data
    from ..tools import base
    return base.find_view3d(context)


def current(region=None, rv3d=None):
    if region is None or rv3d is None:
        _w, _a, region, rv3d = view3d()
    if region is None or rv3d is None:
        return None
    return View.from_rv3d(region, rv3d)


def apply(v, rv3d=None, area=None):
    if rv3d is None:
        _w, area, _r, rv3d = view3d()
    if rv3d is None:
        return
    v.apply(rv3d)
    if area is not None:
        area.tag_redraw()


def hit_point(region, rv3d, xy, tc=None):
    """World point of the geometry under region pixel xy (None over empty space / sky)."""
    try:
        from bpy_extras import view3d_utils
        o = view3d_utils.region_2d_to_origin_3d(region, rv3d, xy)
        d = view3d_utils.region_2d_to_vector_3d(region, rv3d, xy).normalized()
    except Exception:
        return None
    spatial = registry.optional("core.spatial")
    if spatial is not None and hasattr(spatial, "ray_cast"):
        try:
            h = spatial.ray_cast(tc, o, d)
            return Vector(h.point) if h.ok else None
        except Exception:
            perf.exception("camera: ray_cast")
            return None
    dg = bpy.context.evaluated_depsgraph_get()
    ok, loc, *_ = bpy.context.scene.ray_cast(dg, o, d)
    return Vector(loc) if ok else None


def set_fov_v(deg, context=None):
    """Set the model FOV (vertical degrees, 1–120) and refit the viewport lens."""
    deg = _clamp(float(deg), 1.0, 120.0)
    scene = (context or bpy.context).scene
    pages = getattr(scene, "su_pages", None)
    if pages is not None:
        pages.fov_v = deg
    _w, area, region, rv3d = view3d(context)
    if area is not None:
        keep_fov(area, region, rv3d, force=True)
    return deg


def keep_fov(area, region, rv3d, force=False):
    """Refit the lens so the vertical FOV is fov_v() (perspective only). True if the lens changed."""
    if area is None or rv3d is None or not rv3d.is_perspective or rv3d.view_perspective == 'CAMERA':
        return False
    k = rv3d.window_matrix[1][1]
    if k <= 1e-9:
        return False
    tan_now = 1.0 / k
    want = fov_v()
    if not force and abs(math.degrees(2.0 * math.atan(tan_now)) - want) < FOV_TOL_DEG:
        return False
    sp = area.spaces.active
    lens = lens_for_fov(sp.lens, tan_now, want)
    if abs(lens - sp.lens) > 1e-6:
        sp.lens = _clamp(lens, 1.0, 250.0)
        area.tag_redraw()
        return True
    return False


_fov_pending = [False]


def check_fov(dc):
    """Called by a draw layer (draw/annotations.py): schedule a lens refit when the FOV drifted
    (region resize / aspect change). Never writes from inside the draw callback."""
    rv3d = dc.rv3d
    if rv3d is None or not rv3d.is_perspective or rv3d.view_perspective == 'CAMERA' or _fov_pending[0]:
        return
    k = rv3d.window_matrix[1][1]
    if k <= 1e-9 or abs(math.degrees(2.0 * math.atan(1.0 / k)) - fov_v()) < FOV_TOL_DEG:
        return
    _fov_pending[0] = True
    area = dc.context.area

    def fix():
        _fov_pending[0] = False
        try:
            for r in area.regions:
                if r.type == 'WINDOW':
                    keep_fov(area, r, area.spaces.active.region_3d)
        except ReferenceError:
            pass
    registry.deferred(fix, 0.0)


# ------------------------------------------------------------------------------------------ history

_history = {"items": [], "index": -1, "t": 0.0}


def _snap(v):
    return v.copy()


def push_history(v=None, *, debounce=0.0):
    """Remember the current view (after a navigation). `debounce` s: replace the last entry when the
    previous push was more recent (wheel zoom bursts)."""
    v = v or current()
    if v is None:
        return
    h = _history
    items = h["items"]
    now = time.monotonic()
    del items[h["index"] + 1:]
    if items and items[-1].same_as(v):
        h["t"] = now
        return
    if debounce and items and now - h["t"] < debounce and len(items) > 1:
        items[-1] = _snap(v)
    else:
        items.append(_snap(v))
    if len(items) > HISTORY_MAX:
        del items[0]
    h["index"] = len(items) - 1
    h["t"] = now


def _go(step):
    h = _history
    items = h["items"]
    cur = current()
    if cur is None:
        return False
    if not items or not items[h["index"]].same_as(cur):
        push_history(cur)
    i = h["index"] + step
    if not 0 <= i < len(items):
        return False
    h["index"] = i
    apply(items[i].copy())
    return True


def previous():
    return _go(-1)


def next():                                      # noqa: A001 — contract name
    return _go(+1)


def history_state():
    return len(_history["items"]), _history["index"]


def clear_history():
    _history.update(items=[], index=-1, t=0.0)


# ------------------------------------------------------------------------------------------ module API

def zoom_extents(selection_only=False):
    """Fit the visible model (or the selection) in 90 % of the main 3D view."""
    _w, area, region, rv3d = view3d()
    if rv3d is None:
        return False
    pts = model_points(selection_only)
    if not pts:
        return False
    push_history()
    v = View.from_rv3d(region, rv3d)
    fit_points(v, pts)
    apply(v, rv3d, area)
    push_history(v)
    return True


def model_points(selection_only=False):
    """World corners of the visible documents' geometry (or of the selection)."""
    if selection_only:
        sel = registry.optional("core.selection")
        b = sel.bounds_world() if sel is not None and not sel.is_empty() else None
        if b is not None:
            mn, mx = b
            return [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
    pts = []
    for obj in bpy.context.view_layer.objects:
        if obj.type not in {'MESH', 'CURVE', 'FONT'} or not obj.visible_get():
            continue
        me = obj.data
        if obj.type == 'MESH' and len(me.vertices) == 0:
            continue
        pts += [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return pts


def standard_view(name):
    _w, area, region, rv3d = view3d()
    if rv3d is None:
        return False
    push_history()
    v = View.from_rv3d(region, rv3d)
    standard_view_of(v, name)
    apply(v, rv3d, area)
    push_history(v)
    return True


def set_projection(persp):
    _w, area, region, rv3d = view3d()
    if rv3d is None:
        return False
    rv3d.view_perspective = 'PERSP' if persp else 'ORTHO'
    if area is not None:
        area.tag_redraw()
        if persp:
            registry.deferred(lambda: keep_fov(area, region, rv3d, force=True), 0.05)
    return True


def recenter(region, rv3d, xy):
    p = hit_point(region, rv3d, xy)
    if p is None:
        return False
    push_history()
    v = View.from_rv3d(region, rv3d)
    recenter_at(v, p)
    v.apply(rv3d)
    push_history(v)
    return True


class SU_Page(bpy.types.PropertyGroup):
    """A scene ("Cena", P1): a saved camera."""
    loc: bpy.props.FloatVectorProperty(size=3)
    rot: bpy.props.FloatVectorProperty(size=4, default=(1.0, 0.0, 0.0, 0.0))
    dist: bpy.props.FloatProperty(default=10.0)
    persp: bpy.props.BoolProperty(default=True)
    fov_v: bpy.props.FloatProperty(default=constants.DEFAULT_FOV_V_DEG)
    description: bpy.props.StringProperty()


class SU_Pages(bpy.types.PropertyGroup):
    fov_v: bpy.props.FloatProperty(name="Campo de visão", default=constants.DEFAULT_FOV_V_DEG, min=1.0, max=120.0)
    pages: bpy.props.CollectionProperty(type=SU_Page)
    active: bpy.props.IntProperty(default=-1)
    show_tabs: bpy.props.BoolProperty(default=True)


# ------------------------------------------------------------------------------------------ scenes (P1)

def pages(scene=None):
    scene = scene or bpy.context.scene
    return getattr(scene, "su_pages", None)


def store_page(page, v):
    page.loc = v.loc
    page.rot = tuple(v.rot)
    page.dist = v.dist
    page.persp = v.persp
    page.fov_v = fov_v()


def page_view(page, base_view):
    w = base_view.copy()
    w.loc = Vector(page.loc)
    w.rot = Quaternion(page.rot).normalized()
    w.dist = page.dist
    w.persp = page.persp
    return w


def add_page(name=None):
    """New scene from the current view (Cenas ▸ +). Returns its index."""
    pg = pages()
    v = current()
    page = pg.pages.add()
    page.name = name or "Cena {:d}".format(len(pg.pages))
    if v is not None:
        store_page(page, v)
    pg.active = len(pg.pages) - 1
    return pg.active


def go_page(index):
    pg = pages()
    if pg is None or not 0 <= index < len(pg.pages):
        return False
    _w, area, region, rv3d = view3d()
    pg.active = index
    if rv3d is None:
        return True
    page = pg.pages[index]
    push_history()
    v = page_view(page, View.from_rv3d(region, rv3d))
    if page.fov_v > 0:
        pg.fov_v = page.fov_v
    apply(v, rv3d, area)
    push_history(v)
    if v.persp and area is not None:
        registry.deferred(lambda: keep_fov(area, region, rv3d, force=True), 0.05)
    return True


def update_page(index):
    pg = pages()
    v = current()
    if pg is None or v is None or not 0 <= index < len(pg.pages):
        return False
    store_page(pg.pages[index], v)
    return True


def remove_page(index):
    pg = pages()
    if pg is None or not 0 <= index < len(pg.pages):
        return False
    pg.pages.remove(index)
    pg.active = min(pg.active, len(pg.pages) - 1)
    return True


def _on_load(**_kw):
    clear_history()


CLASSES = (SU_Page, SU_Pages)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.su_pages = bpy.props.PointerProperty(type=SU_Pages)
    events.subscribe("load", _on_load)


def unregister():
    events.unsubscribe("load", _on_load)
    clear_history()
    del bpy.types.Scene.su_pages
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
