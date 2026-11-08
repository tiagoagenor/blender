# SPDX-License-Identifier: GPL-2.0-or-later
"""Helpers for C's tests (owner: C): synthetic camera (region + RegionView3D stand-ins) and scene
objects. No TestCase here (run.py imports it harmlessly)."""

import math

import bpy
from mathutils import Matrix, Vector

PREFIX = "SUC_"


class FakeRegion:
    def __init__(self, width=1000, height=800):
        self.width, self.height = width, height


class FakeRV3D:
    """Perspective view looking from `eye` to `target` (vertical FOV in degrees)."""

    def __init__(self, eye, target, region, fov_v=35.0, near=0.1, far=1000.0, up=(0.0, 0.0, 1.0)):
        eye, target, up = Vector(eye), Vector(target), Vector(up)
        f = (target - eye).normalized()
        s = f.cross(up).normalized()
        u = s.cross(f)
        self.view_matrix = Matrix((
            (s.x, s.y, s.z, -s.dot(eye)),
            (u.x, u.y, u.z, -u.dot(eye)),
            (-f.x, -f.y, -f.z, f.dot(eye)),
            (0.0, 0.0, 0.0, 1.0)))
        aspect = region.width / region.height
        t = 1.0 / math.tan(math.radians(fov_v) / 2.0)
        self.window_matrix = Matrix((
            (t / aspect, 0.0, 0.0, 0.0),
            (0.0, t, 0.0, 0.0),
            (0.0, 0.0, (far + near) / (near - far), 2.0 * far * near / (near - far)),
            (0.0, 0.0, -1.0, 0.0)))
        self.perspective_matrix = self.window_matrix @ self.view_matrix
        self.view_rotation = self.view_matrix.to_3x3().transposed().to_quaternion()
        self.view_location = target.copy()
        self.view_distance = (target - eye).length
        self.is_perspective = True
        self.view_perspective = 'PERSP'


def camera(eye=(9.0, -7.0, 6.0), target=(2.0, 2.0, 0.5), size=(1000, 800)):
    region = FakeRegion(*size)
    return region, FakeRV3D(eye, target, region)


def project(region, rv3d, co):
    from bpy_extras import view3d_utils
    return view3d_utils.location_3d_to_region_2d(region, rv3d, Vector(co))


def mesh_object(name, verts, edges=(), faces=()):
    me = bpy.data.meshes.new(PREFIX + name)
    me.from_pydata([tuple(v) for v in verts], list(edges), list(faces))
    me.update()
    obj = bpy.data.objects.new(PREFIX + name, me)
    if hasattr(obj, "su_doc"):
        obj.su_doc.kind = 'GROUP'           # B: a plain group document
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    return obj


def box(name, mn, mx):
    x0, y0, z0 = mn
    x1, y1, z1 = mx
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return mesh_object(name, v, faces=f)


def face_index(obj, normal):
    n = Vector(normal)
    for p in obj.data.polygons:
        if (p.normal - n).length < 1e-6:
            return p.index
    raise KeyError(normal)


_hidden = []


def isolate_scene():
    """Hide the factory-startup objects (default cube…) from the viewport/depsgraph."""
    for obj in bpy.context.scene.objects:
        if not obj.name.startswith(PREFIX) and not obj.hide_viewport:
            obj.hide_viewport = True
            _hidden.append(obj.name)
    bpy.context.view_layer.update()


def cleanup():
    for obj in list(bpy.data.objects):
        if obj.name.startswith(PREFIX):
            me = obj.data
            bpy.data.objects.remove(obj)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
    for ng in list(bpy.data.node_groups):
        if ng.name.startswith(PREFIX):
            bpy.data.node_groups.remove(ng)
    for name in _hidden:
        obj = bpy.data.objects.get(name)
        if obj is not None:
            obj.hide_viewport = False
    _hidden.clear()
    bpy.context.view_layer.update()


def add_back_copy_gn(obj):
    """Stand-in for D's SU_Display: Join(original, Flip Faces(original))."""
    ng = bpy.data.node_groups.new(PREFIX + "back", 'GeometryNodeTree')
    ng.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    gi = ng.nodes.new('NodeGroupInput')
    go = ng.nodes.new('NodeGroupOutput')
    flip = ng.nodes.new('GeometryNodeFlipFaces')
    join = ng.nodes.new('GeometryNodeJoinGeometry')
    ng.links.new(gi.outputs[0], flip.inputs[0])
    ng.links.new(gi.outputs[0], join.inputs[0])
    ng.links.new(flip.outputs[0], join.inputs[0])
    ng.links.new(join.outputs[0], go.inputs[0])
    mod = obj.modifiers.new("SU_Display", 'NODES')
    mod.node_group = ng
    bpy.context.view_layer.update()
    return mod
