# SPDX-License-Identifier: GPL-2.0-or-later
"""Tray section "Informações da entidade" (owner: F). PLANO.md §4.4, §6.1 (P0 minimum).

One entity: its type (Face, Superfície, Aresta, Curva, Grupo) + area / length / name (a group's name
is editable) + the face's materials (front/back). Several: "N entidades" with the counts per type and
the total area of the faces. Nothing selected: "Nenhuma seleção".
"""

import bpy

from .. import i18n, registry

ORDER = 561

STRINGS = {
    "edit.info.none": {"pt_BR": "Nenhuma seleção", "en": "No Selection"},
    "edit.info.face": {"pt_BR": "Face", "en": "Face"},
    "edit.info.surface": {"pt_BR": "Superfície", "en": "Surface"},
    "edit.info.edge": {"pt_BR": "Aresta", "en": "Edge"},
    "edit.info.curve": {"pt_BR": "Curva", "en": "Curve"},
    "edit.info.group": {"pt_BR": "Grupo", "en": "Group"},
    "edit.info.n_entities": {"pt_BR": "{n} entidades", "en": "{n} Entities"},
    "edit.info.area": {"pt_BR": "Área", "en": "Area"},
    "edit.info.length": {"pt_BR": "Comprimento", "en": "Length"},
    "edit.info.name": {"pt_BR": "Instância", "en": "Instance"},
    "edit.info.front": {"pt_BR": "Frente", "en": "Front"},
    "edit.info.back": {"pt_BR": "Verso", "en": "Back"},
    "edit.info.segments": {"pt_BR": "Segmentos", "en": "Segments"},
    "edit.info.component": {"pt_BR": "Componente", "en": "Component"},
    "edit.info.definition": {"pt_BR": "Definição", "en": "Definition"},
    "edit.info.n_instances": {"pt_BR": "{n} instâncias no modelo", "en": "{n} instances in model"},
}

KIND_KEYS = {"FACE": "edit.info.face", "SURFACE": "edit.info.surface", "EDGE": "edit.info.edge",
             "CURVE": "edit.info.curve", "OBJECT": "edit.info.group"}


def _units():
    return registry.optional("core.units"), getattr(bpy.context.scene, "su_units", None)


def fmt_len(m):
    u, s = _units()
    if u is not None and hasattr(u, "format_length"):
        return u.format_length(m, s)
    return "{:.2f}m".format(m).replace(".", ",")


def fmt_area(m2):
    u, s = _units()
    if u is not None and hasattr(u, "format_area"):
        return u.format_area(m2, s)
    return "{:.2f}m²".format(m2).replace(".", ",")


def summarize(refs=None):
    """[(kind, doc_key, [indices])] entities of the selection (pick_entity rule) + totals.
    Returns dict(entities=[...], area=float (world m²), length=float (world m))."""
    from ..core import document, entities, selection
    refs = selection.get() if refs is None else refs
    ents, area, length = [], 0.0, 0.0
    by_doc = {}
    for r in refs:
        if r.kind == selection.OBJECT:
            ents.append(("OBJECT", r.doc_key, []))
        else:
            by_doc.setdefault(r.doc_key, {"EDGE": set(), "FACE": set()})[r.kind].add(r.index)
    for key, sel in by_doc.items():
        doc = document.get_by_key(key)
        if doc is None:
            continue
        bm = doc.bm
        W = doc.world()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        for kind in ("FACE", "EDGE"):
            left = set(i for i in sel[kind] if i < (len(bm.faces) if kind == "FACE" else len(bm.edges)))
            while left:
                i = min(left)
                ek, idx = entities.pick_entity(bm, kind, i)
                left -= set(idx)
                ents.append((ek, key, idx))
            for i in sel[kind]:
                if kind == "FACE" and i < len(bm.faces):
                    f = bm.faces[i]
                    from mathutils.geometry import area_tri
                    vs = [W @ v.co for v in f.verts]
                    area += sum(area_tri(vs[0], vs[k], vs[k + 1]) for k in range(1, len(vs) - 1))
                elif kind == "EDGE" and i < len(bm.edges):
                    a, b = bm.edges[i].verts
                    length += ((W @ a.co) - (W @ b.co)).length
    return {"entities": ents, "area": area, "length": length}


def _is_component(name):
    document = registry.optional("core.document")
    obj = bpy.data.objects.get(name)
    return obj is not None and document is not None and hasattr(document, "is_component") \
        and document.is_component(obj)


def _materials_row(layout, key, idx):
    from ..core import document, materials
    doc = document.get_by_key(key)
    if doc is None or not idx:
        return
    for side, label in ((1, "edit.info.front"), (-1, "edit.info.back")):
        m = materials.material_of(doc, idx[0], side)
        layout.label(text="{}: {}".format(i18n.t(label),
                                           m.name if m is not None else i18n.t("mat.default")))


def draw(layout, context):
    sel = registry.optional("core.selection")
    if sel is None or sel.is_empty():
        layout.label(text=i18n.t("edit.info.none"))
        return
    s = summarize()
    ents = s["entities"]
    if len(ents) == 1:
        kind, key, idx = ents[0]
        if not (kind == "OBJECT" and _is_component(key)):
            layout.label(text=i18n.t(KIND_KEYS.get(kind, "edit.info.face")))
        col = layout.column(align=True)
        if kind == "OBJECT":
            obj = bpy.data.objects.get(key)
            document = registry.optional("core.document")
            if obj is not None and document is not None and hasattr(document, "is_component") \
                    and document.is_component(obj):
                col.label(text=i18n.t("edit.info.component"))
                col.label(text="{}: {}".format(i18n.t("edit.info.definition"), document.definition_name(obj)))
                col.prop(obj, "name", text=i18n.t("edit.info.name"))
                n = len(document.instances(obj.data))
                col.label(text=i18n.t("edit.info.n_instances", n=n))
            elif obj is not None:
                col.prop(obj, "name", text=i18n.t("edit.info.name"))
        elif kind in ("FACE", "SURFACE"):
            col.label(text="{}: {}".format(i18n.t("edit.info.area"), fmt_area(s["area"])))
            _materials_row(col, key, idx)
        else:
            col.label(text="{}: {}".format(i18n.t("edit.info.length"), fmt_len(s["length"])))
            if kind == "CURVE":
                col.label(text="{}: {}".format(i18n.t("edit.info.segments"), len(idx)))
        return
    layout.label(text=i18n.t("edit.info.n_entities", n=len(ents)))
    col = layout.column(align=True)
    counts = {}
    for kind, _k, _i in ents:
        counts[kind] = counts.get(kind, 0) + 1
    for kind in ("FACE", "SURFACE", "EDGE", "CURVE", "OBJECT"):
        if counts.get(kind):
            col.label(text="{} × {}".format(counts[kind], i18n.t(KIND_KEYS[kind])))
    if s["area"] > 0:
        col.label(text="{}: {}".format(i18n.t("edit.info.area"), fmt_area(s["area"])))


def _on_selection(**_kw):
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return
    for win in wm.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                for r in area.regions:
                    if r.type == 'UI':
                        r.tag_redraw()


def register():
    i18n.register_strings(STRINGS)
    tray = registry.optional("ui.tray")
    if tray is not None:
        tray.register_section(10, "entity", "tray.entity", draw)
    from .. import events
    events.subscribe("selection", _on_selection, order=300)


def unregister():
    from .. import events
    events.unsubscribe("selection", _on_selection)
    i18n.unregister_strings(STRINGS)
