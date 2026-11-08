# SPDX-License-Identifier: GPL-2.0-or-later
"""Materials of the documents (owner: F). Contract: PLANO.md §2.4-F, §3.1.

Every document object has slot 0 "Padrão" (white) and slot 1 "Padrão (verso)" (#A4B2BB). A face's
front material = `material_index`; its back material = the face INT attribute `su_back_mat`
(default 1, never −1) that D's GN copy shows on the flipped copy.

    ensure_slots(obj)                       slots 0/1 (on events "load" for every mesh, "doc" for new ones)
    slot_for(obj, material, side=1) -> int  slot of `material` in obj (appended when missing);
                                            None/"Padrão" → 0 (front) or 1 (back)
    paint(doc, face_ids, material, side)    side +1 → material_index, -1 → su_back_mat (bm only; the
                                            caller writes the document)
    palette() -> [Material]                 "Padrão" + the 24 colours of the Materials section
    new_color(rgb255, name=None) -> Material
    active() / set_active(material|None)    the Paint bucket's material (WindowManager.su_paint.active)
    material_of(doc, face_idx, side)        Material shown on that side (None = default)
Material.su_mat: kind ('DEFAULT_FRONT' | 'DEFAULT_BACK' | 'COLOR'), rgb (sRGB 0–1).
"""

import bpy
from bpy.props import FloatVectorProperty, PointerProperty, StringProperty

from .. import colors, constants, events, i18n, registry

ORDER = 125

MAT_FRONT = "Padrão"          # same names as D's display_gn fallback
MAT_BACK = "Padrão (verso)"
KIND_FRONT = 'DEFAULT_FRONT'
KIND_BACK = 'DEFAULT_BACK'
KIND_COLOR = 'COLOR'

# 24 colours (sRGB 0–255) of the "Cores" collection (own selection: SketchUp-like spread of hues + greys).
PALETTE = (
    ("mat.c01", (204, 51, 51)), ("mat.c02", (230, 115, 46)), ("mat.c03", (242, 191, 51)),
    ("mat.c04", (250, 235, 120)), ("mat.c05", (153, 191, 64)), ("mat.c06", (64, 140, 64)),
    ("mat.c07", (46, 102, 77)), ("mat.c08", (64, 166, 153)), ("mat.c09", (102, 179, 217)),
    ("mat.c10", (51, 102, 179)), ("mat.c11", (38, 51, 115)), ("mat.c12", (115, 77, 153)),
    ("mat.c13", (179, 102, 166)), ("mat.c14", (230, 166, 179)), ("mat.c15", (140, 64, 51)),
    ("mat.c16", (166, 115, 64)), ("mat.c17", (204, 166, 115)), ("mat.c18", (230, 217, 191)),
    ("mat.c19", (115, 102, 89)), ("mat.c20", (255, 255, 255)), ("mat.c21", (204, 204, 204)),
    ("mat.c22", (153, 153, 153)), ("mat.c23", (89, 89, 89)), ("mat.c24", (26, 26, 26)),
)

STRINGS = {
    "mat.default": {"pt_BR": "Padrão", "en": "Default"},
    "mat.default_back": {"pt_BR": "Padrão (verso)", "en": "Default (back)"},
    "mat.c01": "Vermelho", "mat.c02": "Laranja", "mat.c03": "Amarelo ouro", "mat.c04": "Amarelo claro",
    "mat.c05": "Verde-limão", "mat.c06": "Verde", "mat.c07": "Verde-escuro", "mat.c08": "Verde-água",
    "mat.c09": "Azul-céu", "mat.c10": "Azul", "mat.c11": "Azul-marinho", "mat.c12": "Roxo",
    "mat.c13": "Magenta", "mat.c14": "Rosa", "mat.c15": "Tijolo", "mat.c16": "Madeira",
    "mat.c17": "Areia", "mat.c18": "Bege", "mat.c19": "Concreto", "mat.c20": "Branco",
    "mat.c21": "Cinza claro", "mat.c22": "Cinza", "mat.c23": "Cinza-escuro", "mat.c24": "Preto",
    "mat.color_n": {"pt_BR": "Cor {n:02d}", "en": "Color {n:02d}"},
}


class SU_PG_mat(bpy.types.PropertyGroup):
    kind: StringProperty(name="Tipo", default="")
    rgb: FloatVectorProperty(name="Cor", size=3, subtype='COLOR_GAMMA', min=0.0, max=1.0,
                             default=(1.0, 1.0, 1.0))


class SU_PG_paint(bpy.types.PropertyGroup):
    active: StringProperty(name="Material ativo", default="")     # Material name; "" = Padrão
    new_color: FloatVectorProperty(name="Nova cor", size=3, subtype='COLOR_GAMMA', min=0.0, max=1.0,
                                   default=(0.8, 0.45, 0.3))


# ------------------------------------------------------------------------------------------- materials

def _setup(mat, rgb255, kind):
    mat.diffuse_color = colors.lin(rgb255)
    mat.roughness = 1.0
    mat.specular_intensity = 0.0
    mat.metallic = 0.0
    mat.su_mat.kind = kind
    mat.su_mat.rgb = tuple(c / 255.0 for c in rgb255)


def _default(name, rgb255, kind):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        _setup(m, rgb255, kind)
    elif not m.su_mat.kind:
        m.su_mat.kind = kind
    return m


def default_front():
    return _default(MAT_FRONT, colors.FACE_FRONT, KIND_FRONT)


def default_back():
    return _default(MAT_BACK, colors.FACE_BACK, KIND_BACK)


def is_default(mat):
    return mat is None or mat.su_mat.kind in (KIND_FRONT, KIND_BACK) or mat.name in (MAT_FRONT, MAT_BACK)


def ensure_slots(obj):
    """Slot 0 "Padrão" and slot 1 "Padrão (verso)" on a document object (idempotent)."""
    if obj is None or obj.type != 'MESH' or obj.library is not None:
        return
    mats = obj.data.materials
    if len(mats) == 0:
        mats.append(default_front())
    elif mats[0] is None:
        mats[0] = default_front()
    if len(mats) == 1:
        mats.append(default_back())
    elif mats[1] is None:
        mats[1] = default_back()


def slot_for(obj, material, side=1):
    """Slot index of `material` in obj (appended when missing). Default (None / Padrão) → 0 or 1."""
    ensure_slots(obj)
    if is_default(material):
        return constants.SLOT_DEFAULT_FRONT if side >= 0 else constants.SLOT_DEFAULT_BACK
    mats = obj.data.materials
    for i, m in enumerate(mats):
        if m == material:
            return i
    mats.append(material)
    return len(mats) - 1


def paint(doc, face_ids, material, side):
    """Paint faces `face_ids` of `doc` on `side` (+1 front → material_index, -1 back → su_back_mat).
    Changes the BMesh only (caller writes). Returns the number of faces changed."""
    from . import geom
    bm = doc.bm
    lay = geom.ensure_layers(bm)
    bm.faces.ensure_lookup_table()
    slot = slot_for(doc.obj, material, side)
    n = 0
    for i in face_ids:
        if not 0 <= i < len(bm.faces):
            continue
        f = bm.faces[i]
        if side >= 0:
            if f.material_index != slot:
                f.material_index = slot
                n += 1
        elif f[lay.back] != slot:
            f[lay.back] = slot
            n += 1
    return n


def material_of(doc, face_idx, side):
    """Material on that side of the face, None for the default ones."""
    from . import geom
    bm = doc.bm
    lay = geom.ensure_layers(bm)
    bm.faces.ensure_lookup_table()
    f = bm.faces[face_idx]
    slot = f.material_index if side >= 0 else f[lay.back]
    mats = doc.obj.data.materials
    m = mats[slot] if 0 <= slot < len(mats) else None
    return None if is_default(m) else m


def palette():
    """[Material] of the colour collection (created once per file), default first."""
    out = [default_front()]
    for i, (key, rgb) in enumerate(PALETTE):
        name = i18n.t(key)
        m = bpy.data.materials.get(name)
        if m is None or m.su_mat.kind != KIND_COLOR:
            m = bpy.data.materials.new(name)
            _setup(m, rgb, KIND_COLOR)
        out.append(m)
    return out


def palette_rgb():
    """[(name, rgb255)] without creating materials (tray swatches)."""
    return [(i18n.t(k), rgb) for k, rgb in PALETTE]


def palette_material(index):
    """Material of palette entry `index` (0-based, without the default), created when missing."""
    key, rgb = PALETTE[index]
    name = i18n.t(key)
    m = bpy.data.materials.get(name)
    if m is None or m.su_mat.kind != KIND_COLOR:
        m = bpy.data.materials.new(name)
        _setup(m, rgb, KIND_COLOR)
    return m


def new_color(rgb255, name=None):
    if not name:
        n = 1
        while bpy.data.materials.get(i18n.t("mat.color_n", n=n)) is not None:
            n += 1
        name = i18n.t("mat.color_n", n=n)
    m = bpy.data.materials.new(name)
    _setup(m, tuple(int(round(c)) for c in rgb255), KIND_COLOR)
    return m


def in_model():
    """Materials used by some face of a visible document (front or back), defaults excluded."""
    used = []
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or obj.library is not None:
            continue
        me = obj.data
        if not len(me.materials):
            continue
        idx = set()
        if len(me.polygons):
            import numpy as np
            a = np.zeros(len(me.polygons), dtype=np.int32)
            me.polygons.foreach_get("material_index", a)
            idx.update(int(i) for i in np.unique(a))
            at = me.attributes.get("su_back_mat")
            if at is not None and at.domain == 'FACE':
                b = np.zeros(len(me.polygons), dtype=np.int32)
                at.data.foreach_get("value", b)
                idx.update(int(i) for i in np.unique(b))
        for i in sorted(idx):
            m = me.materials[i] if 0 <= i < len(me.materials) else None
            if m is not None and not is_default(m) and m not in used:
                used.append(m)
    return used


def active():
    wm = getattr(bpy.context, "window_manager", None)
    p = getattr(wm, "su_paint", None)
    if p is None or not p.active:
        return None
    return bpy.data.materials.get(p.active)


def set_active(material):
    wm = getattr(bpy.context, "window_manager", None)
    p = getattr(wm, "su_paint", None)
    if p is None:
        return
    p.active = "" if is_default(material) else material.name
    _redraw_tray()


def _redraw_tray():
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return
    for win in wm.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                for r in area.regions:
                    if r.type == 'UI':
                        r.tag_redraw()


# ------------------------------------------------------------------------------------------- events

def _on_load(**_kw):
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.library is None:
            ensure_slots(obj)


def _on_doc(doc_key=None, **_kw):
    obj = bpy.data.objects.get(doc_key) if isinstance(doc_key, str) else None
    if obj is None:
        _on_load()
    else:
        ensure_slots(obj)


_classes = (SU_PG_mat, SU_PG_paint)


def register():
    i18n.register_strings(STRINGS)
    registry.register_classes(_classes)
    bpy.types.Material.su_mat = PointerProperty(type=SU_PG_mat)
    bpy.types.WindowManager.su_paint = PointerProperty(type=SU_PG_paint)
    events.subscribe("load", _on_load, order=150)     # after B's root (100), before D's GN (300)
    events.subscribe("doc", _on_doc, order=150)


def unregister():
    events.unsubscribe("load", _on_load)
    events.unsubscribe("doc", _on_doc)
    for cls, attr in ((bpy.types.WindowManager, "su_paint"), (bpy.types.Material, "su_mat")):
        if hasattr(cls, attr):
            delattr(cls, attr)
    registry.unregister_classes(_classes)
    i18n.unregister_strings(STRINGS)
