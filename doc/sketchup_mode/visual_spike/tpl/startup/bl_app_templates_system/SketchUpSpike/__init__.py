# SketchUp-mode VISUAL SHELL spike (Blender 5.2.2 app template).
# Throwaway prototype: everything in one file on purpose. See ../../../../FINDINGS.md.
import bpy, os, math, traceback
from bpy.app.handlers import persistent
from mathutils import Vector, Matrix

LOG = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "raw", "template_log.txt")
def P(*a):
    try:
        with open(LOG, "a") as f: print(*a, file=f)
    except Exception: pass

def srgb(r, g, b, a=None):
    t = (r / 255.0, g / 255.0, b / 255.0)
    return t if a is None else t + (a,)

# ---------------------------------------------------------------- colours (RESEARCH_SKETCHUP §4.2)
SKY_TOP   = srgb(30, 166, 221)
SKY_HOR   = srgb(191, 229, 245)
GROUND    = srgb(191, 191, 198)
AX_X, AX_Y, AX_Z = srgb(178, 0, 0), srgb(0, 178, 0), srgb(0, 0, 178)
FACE_BACK = srgb(164, 178, 187)
CHROME    = srgb(241, 241, 246)     # toolbar / chrome #F1F1F6
PANEL_HDR = srgb(224, 225, 233)     # tray panel header #E0E1E9
TRAY_BODY = srgb(244, 247, 252)     # tray body #F4F7FC
TEXT      = srgb(30, 30, 36)
NAVY      = srgb(0, 66, 110)
SEL_FILL  = srgb(214, 232, 250)
SEL_LINE  = srgb(0, 120, 215)
BORDER    = srgb(200, 200, 208)

# ---------------------------------------------------------------- tool catalogue (pt-BR, CRITICA §3.2)
# id -> (label, icon). icon "bi.NAME" = Blender built-in SVG icon, else toolbar .dat geometry icon.
T = {
    "su.search":   ("Pesquisar", "bi.VIEWZOOM"),
    "su.select":   ("Selecionar", "ops.generic.select"),
    "su.lasso":    ("Lasso", "ops.generic.select_lasso"),
    "su.paint":    ("Pintura", "brush.gpencil_draw.fill"),
    "su.eraser":   ("Apagar", "brush.gpencil_draw.erase"),
    "su.make_component": ("Criar componente", "ops.mesh.primitive_cube_add_gizmo"),
    "su.line":     ("Linha", "ops.gpencil.primitive_line"),
    "su.freehand": ("Desenho à mão livre", "ops.gpencil.draw"),
    "su.rectangle": ("Retângulo", "ops.gpencil.primitive_box"),
    "su.rotated_rectangle": ("Retângulo girado", "ops.transform.resize.cage"),
    "su.circle":   ("Círculo", "ops.gpencil.primitive_circle"),
    "su.polygon":  ("Polígono", "ops.gpencil.primitive_polyline"),
    "su.arc":      ("Arco", "ops.gpencil.primitive_arc"),
    "su.arc2":     ("Arco de dois pontos", "ops.gpencil.primitive_curve"),
    "su.arc3":     ("Arco de três pontos", "ops.mesh.spin"),
    "su.pie":      ("Pizza", "ops.gpencil.edit_bend"),
    "su.move":     ("Mover", "ops.transform.translate"),
    "su.pushpull": ("Empurrar/puxar", "ops.mesh.extrude_region_move"),
    "su.rotate":   ("Girar", "ops.transform.rotate"),
    "su.followme": ("Siga-me", "ops.mesh.extrude_faces_move"),
    "su.scale":    ("Escala", "ops.transform.resize"),
    "su.offset":   ("Equidistância", "ops.mesh.inset"),
    "su.axes":     ("Eixos", "bi.EMPTY_AXIS"),
    "su.flip":     ("Virar", "ops.gpencil.edit_mirror"),
    "su.tape":     ("Fita métrica", "ops.view3d.ruler"),
    "su.dimension": ("Dimensões", "bi.DRIVER_DISTANCE"),
    "su.protractor": ("Transferidor", "bi.DRIVER_ROTATIONAL_DIFFERENCE"),
    "su.text":     ("Texto", "bi.FILE_TEXT"),
    "su.section":  ("Plano de seção", "ops.mesh.bisect"),
    "su.text3d":   ("Texto em 3D", "bi.OUTLINER_OB_FONT"),
    "su.orbit":    ("Órbita", "bi.ORIENTATION_GIMBAL"),
    "su.pan":      ("Panorâmica", "bi.VIEW_PAN"),
    "su.zoom":     ("Aplicar zoom", "bi.ZOOM_IN"),
    "su.zoom_window": ("Janela de zoom", "bi.ZOOM_SELECTED"),
    "su.zoom_extents": ("Extensões de zoom", "bi.ZOOM_ALL"),
    "su.previous": ("Anterior", "bi.ZOOM_PREVIOUS"),
    "su.position_camera": ("Posição da câmera", "bi.VIEW_CAMERA"),
    "su.walk":     ("Percorrer", "bi.ARMATURE_DATA"),
    "su.look_around": ("Olhar ao redor", "bi.HIDE_OFF"),
    "su.fov":      ("Campo de visão", "bi.VIEW_PERSPECTIVE"),
}
# Large Tool Set (2027), None = separator. Two-column layout fills row by row; an odd group leaves
# its last right cell empty (that is exactly the empty "Etiqueta" cell CRITICA Q5 asks for).
LTS = ["su.select", "su.lasso", "su.paint", "su.eraser", "su.make_component", None,
       "su.line", "su.freehand", "su.rectangle", "su.rotated_rectangle", "su.circle", "su.polygon",
       "su.arc", "su.arc2", "su.arc3", "su.pie", None,
       "su.move", "su.pushpull", "su.rotate", "su.followme", "su.scale", "su.offset", "su.axes", "su.flip", None,
       "su.tape", "su.dimension", "su.protractor", "su.text", "su.section", "su.text3d", None,
       "su.orbit", "su.pan", "su.zoom", "su.zoom_window", "su.zoom_extents", "su.previous", None,
       "su.position_camera", "su.walk", "su.look_around", "su.fov"]
# Getting Started ("Primeiros passos"), groups per CRITICA B5. "*" suffix = flyout arrow.
GETTING_STARTED = [["su.search"], ["su.select*"],
                   ["su.eraser", "su.line*", "su.arc2*", "su.rectangle*"],
                   ["su.pushpull", "su.offset", "su.move", "su.rotate", "su.scale", "su.flip"],
                   ["su.tape", "su.paint"],
                   ["su.orbit", "su.pan", "su.zoom", "su.zoom_extents"]]
TRAY = [("entity", "Informações da entidade"), ("materials", "Materiais"), ("components", "Componentes"),
        ("styles", "Estilos"), ("shadows", "Sombras"), ("scenes", "Cenas"),
        ("soften", "Suavizar arestas"), ("outliner", "Estruturador")]
HINT = "Clique ou arraste para selecionar objetos. Shift = Adicionar/Subtrair. Ctrl = Adicionar. Shift + Ctrl = Subtrair."

# ---------------------------------------------------------------- icons
_BI = {}
def builtin_icon_value(name):
    if not _BI:
        for it in bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items:
            _BI[it.identifier] = it.value
    return _BI.get(name, _BI.get("QUESTION", 0))

from bl_ui.space_toolsystem_common import ToolSelectPanelHelper as TSP, ToolDef
_orig_icon = TSP._icon_value_from_icon_handle
ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")   # built by tools/build_icons.py
def _icon(icon_name):
    if icon_name and icon_name.startswith("bi."):
        return builtin_icon_value(icon_name[3:])
    if icon_name and not os.path.isabs(icon_name):
        alt = os.path.join(ICON_DIR, "su." + icon_name)
        if os.path.exists(alt + ".dat"):
            return _orig_icon(alt)          # absolute path wins in os.path.join(datafiles, name)
    return _orig_icon(icon_name)

def icon_of(tid):
    return _icon(T[tid][1])

# ---------------------------------------------------------------- operators
class SU_OT_placeholder(bpy.types.Operator):
    bl_idname = "su.placeholder"; bl_label = "Em breve"; bl_description = "Ferramenta do SketchUp (em breve)"
    name: bpy.props.StringProperty()
    def execute(self, context):
        self.report({'INFO'}, f"{self.name}: em breve"); return {'FINISHED'}

def tool_def(tid):
    label, icon = T[tid]
    return ToolDef.from_dict(dict(idname=tid, label=label, description=label + " (em breve)", icon=icon,
                                  cursor='DEFAULT', keymap=None))

# ---------------------------------------------------------------- menus (placeholders)
MENUS = [("arquivo", "Arquivo", ["Novo", "Abrir…", "Salvar", "Salvar como…", None, "Importar…", "Exportar ▸", None, "Imprimir…"]),
         ("editar", "Editar", ["Desfazer", "Refazer", None, "Recortar", "Copiar", "Colar", "Colar no local", "Excluir", None, "Selecionar tudo", "Selecionar nada", None, "Criar componente…", "Criar grupo"]),
         ("visualizar", "Visualizar", ["Barras de ferramentas…", "Guias de cenas", None, "Geometria oculta", "Eixos", "Guias", "Sombras", "Neblina", None, "Estilo de aresta ▸", "Estilo de face ▸"]),
         ("camera", "Câmera", ["Anterior", "Próxima", "Exibições padrão ▸", None, "Projeção paralela", "Perspectiva", "Perspectiva de dois pontos", None, "Órbita", "Panorâmica", "Aplicar zoom", "Extensões de zoom"]),
         ("desenho", "Desenho", ["Linhas ▸", "Arcos ▸", "Formas ▸"]),
         ("ferramentas", "Ferramentas", ["Selecionar", "Apagar", "Pintura", "Mover", "Girar", "Escala", "Empurrar/puxar", "Siga-me", "Equidistância", None, "Fita métrica", "Transferidor", "Eixos", "Dimensões", "Texto"]),
         ("janela", "Janela", ["Bandeja padrão ▸", "Gerenciar bandejas…", None, "Informações do modelo", "Preferências"]),
         ("extensoes", "Extensões", ["Extension Warehouse", "Gerenciador de extensões"]),
         ("ajuda", "Ajuda", ["Bem-vindo ao SketchUp", "Central de conhecimento", None, "Sobre o SketchUp"])]
_menu_classes = []
def _make_menu(key, label, items):
    def draw(self, context):
        for it in items:
            if it is None: self.layout.separator()
            else: self.layout.operator("su.placeholder", text=it).name = it
    return type(f"SU_MT_{key}", (bpy.types.Menu,), {"bl_idname": f"SU_MT_{key}", "bl_label": label, "draw": draw})
for k, l, its in MENUS: _menu_classes.append(_make_menu(k, l, its))

# ---------------------------------------------------------------- header / bar overrides
_saved = {}
def topbar_left(self, context):
    layout = self.layout
    layout.separator(factor=0.5)
    for k, l, _ in MENUS:
        layout.menu(f"SU_MT_{k}", text=l)
def topbar_right(self, context):
    pass

def active_tool_id(context):
    try:
        t = context.workspace.tools.from_space_view3d_mode('OBJECT', create=False)
        return t.idname if t else ""
    except Exception: return ""

def tool_header(self, context):
    layout = self.layout
    act = active_tool_id(context)
    row = layout.row(align=False)
    row.scale_x = 1.15; row.scale_y = 1.1
    for gi, grp in enumerate(GETTING_STARTED):
        if gi: row.separator(factor=0.6, type='LINE')
        for tid in grp:
            flyout = tid.endswith("*"); tid = tid.rstrip("*")
            sub = row.row(align=True)
            if tid in ("su.search", "su.orbit", "su.pan", "su.zoom", "su.zoom_extents"):
                op = sub.operator("su.placeholder", text="", icon_value=icon_of(tid), emboss=False); op.name = T[tid][0]
            else:
                sub.operator("wm.tool_set_by_id", text="", icon_value=icon_of(tid), depress=(tid == act),
                             emboss=(tid == act)).name = tid
            if flyout:
                s2 = sub.row(align=True); s2.ui_units_x = 0.7
                s2.label(text="", icon='DOWNARROW_HLT')

def statusbar(self, context):
    layout = self.layout
    row = layout.row(align=True)
    row.label(text="", icon='PINNED')
    row.label(text="", icon='INFO')
    row.separator(factor=0.5, type='LINE')
    row.label(text=HINT)
    layout.separator_spacer()
    layout.separator_spacer()
    r = layout.row(align=True)
    r.separator(factor=0.5, type='LINE')
    r.label(text="Medidas")
    s = r.row(align=True); s.ui_units_x = 11
    s.prop(context.window_manager, "su_vcb", text="")

def v3d_header(self, context):
    pass

# ---------------------------------------------------------------- tray
TRAY_OPEN = {"styles"}   # rows expanded at start (SketchUp 2023 screenshot shows Styles open)
_pcoll = {}
def preview(name):
    """Preview icons (PNG) for tray thumbnails."""
    import bpy.utils.previews
    if "c" not in _pcoll:
        _pcoll["c"] = bpy.utils.previews.new()
        _pcoll["c"].load("style_simple", os.path.join(ICON_DIR, "style_simple.png"), 'IMAGE')
    return _pcoll["c"][name].icon_id

def _tray_body(key, lay):
    if key == "entity":
        lay.label(text="Nenhuma seleção")
    elif key == "styles":
        row = lay.row()
        row.template_icon(icon_value=preview("style_simple"), scale=4.0)
        col = row.column(align=True)
        col.label(text="Estilo simples")
        col.label(text="Cores padrão de face. Céu azul"); col.label(text="e fundo cinza.")
        tabs = lay.row(align=True)
        for t, on in (("Selecionar", True), ("Editar", False), ("Misturar", False)):
            tabs.operator("su.placeholder", text=t, depress=on).name = t
        grid = lay.grid_flow(columns=3, even_columns=True, align=True)
        for n in ("Diversos", "Cores", "Padrão", "Foto", "Esboço", "Retas"):
            grid.operator("su.placeholder", text=n, icon='FILE_FOLDER').name = n
    elif key == "materials":
        lay.label(text="Em uso no modelo")
    else:
        lay.label(text="(em breve)")

class SU_PT_tray(bpy.types.Panel):
    """Whole tray in ONE header-less panel (HIDE_HEADER => no Blender panel background and no drag grip).
    Each SketchUp panel row is a flat box (theme wcol_box) with a toggle chevron + label + X."""
    bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = "Bandeja"
    bl_label = "Bandeja padrão"; bl_options = {'HIDE_HEADER'}; bl_order = 0
    def draw(self, context):
        wm = context.window_manager
        lay = self.layout
        row = lay.row()
        row.label(text="Bandeja padrão")
        r = row.row(align=True); r.alignment = 'RIGHT'
        r.label(text="", icon='PINNED'); r.label(text="", icon='X')
        col = lay.column(align=True)
        for key, label in TRAY:
            prop = "su_tray_" + key
            is_open = getattr(wm, prop)
            hr = col.box().row(align=True)
            left = hr.row(align=True); left.alignment = 'LEFT'
            left.prop(wm, prop, text="", emboss=False, icon='DOWNARROW_HLT' if is_open else 'RIGHTARROW')
            left.label(text=label)
            x = hr.row(); x.alignment = 'RIGHT'
            x.operator("su.placeholder", text="", icon='X', emboss=False).name = "Fechar " + label
            if is_open:
                body = col.column(); body.separator(factor=0.4)
                _tray_body(key, body); body.separator(factor=0.6)

_tray_classes = [SU_PT_tray]

# ---------------------------------------------------------------- viewport drawing (sky + axes)
_draw = {"handles": [], "sky": {"key": None, "batch": None}, "axes": {"key": None, "pos": None, "neg": None}}

def horizon_ndc_y(rv3d):
    fwd = -(rv3d.view_matrix.inverted().col[2].xyz)
    if rv3d.is_perspective:
        h = Vector((fwd.x, fwd.y, 0.0))
        if h.length > 1e-6:
            c = rv3d.window_matrix @ rv3d.view_matrix @ Vector((h.x, h.y, 0.0, 0.0))
            if abs(c.w) > 1e-9: return c.y / c.w
    return -1.0 if fwd.z > 0 else (1.0 if fwd.z < -0.999 else 0.0)

def draw_sky():
    try:
        import gpu
        from gpu_extras.batch import batch_for_shader
        rv3d = bpy.context.region_data
        if rv3d is None: return
        sh = gpu.shader.from_builtin('SMOOTH_COLOR')
        y = max(-1.0, min(1.0, horizon_ndc_y(rv3d)))
        c = _draw["sky"]
        key = round(y, 5)
        if c["key"] != key:
            Z = 0.9999999
            # sky: linear from horizon colour at y to top colour at the top edge of the viewport
            top = SKY_TOP + (1.0,); hor = SKY_HOR + (1.0,); gnd = GROUND + (1.0,)
            pos = [(-1, y, Z), (1, y, Z), (1, 1, Z), (-1, 1, Z),
                   (-1, -1, Z), (1, -1, Z), (1, y, Z), (-1, y, Z)]
            col = [hor, hor, top, top, gnd, gnd, gnd, gnd]
            c["batch"] = batch_for_shader(sh, 'TRIS', {"pos": pos, "color": col},
                                          indices=[(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)])
            c["key"] = key
        with gpu.matrix.push_pop(), gpu.matrix.push_pop_projection():
            gpu.matrix.load_identity(); gpu.matrix.load_projection_matrix(Matrix.Identity(4))
            gpu.state.depth_test_set('LESS_EQUAL'); gpu.state.depth_mask_set(False)
            c["batch"].draw(sh)
            gpu.state.depth_test_set('NONE')
    except Exception:
        P("sky", traceback.format_exc())

def _neg_axis_dots(region, rv3d, d):
    """Screen-space even dotted line for the negative half-axis, lifted back to 3D (keeps depth test)."""
    from bpy_extras.view3d_utils import location_3d_to_region_2d, region_2d_to_origin_3d, region_2d_to_vector_3d
    from mathutils.geometry import intersect_line_line
    vm = rv3d.view_matrix
    pts2 = []
    t = 0.0
    for i in range(400):
        t = 0.0 if i == 0 else 0.01 * (1.06 ** i)
        if t > 5e4: break
        p = -d * t
        if (vm @ p).z > -0.05:   # behind / too close to camera
            continue
        q = location_3d_to_region_2d(region, rv3d, p)
        if q is not None: pts2.append(q)
    if len(pts2) < 2: return []
    a, b = pts2[0], pts2[-1]
    L = (b - a).length
    step = 3.0 * bpy.context.preferences.system.pixel_size * 1.5
    n = int(L / step)
    out = []
    W, H = region.width, region.height
    for k in range(n + 1):
        s = a.lerp(b, k / max(1, n))
        if s.x < -2 or s.y < -2 or s.x > W + 2 or s.y > H + 2: continue
        o = region_2d_to_origin_3d(region, rv3d, s); v = region_2d_to_vector_3d(region, rv3d, s)
        r = intersect_line_line(o, o + v, Vector((0, 0, 0)), -d)
        if r: out.append(tuple(r[1]))
    return out

# ---- custom edge renderer: hard edges + profile ("silhouette") of soft edges, black, 1 px (logical)
SOFT_ANGLE = math.radians(20.0)
_edge_cache = {}
def _mesh_edge_data(ob):
    import numpy as np
    me = ob.data
    key = (ob.name, me.as_pointer(), len(me.vertices), len(me.edges), tuple(round(x, 4) for r in ob.matrix_world for x in r))
    c = _edge_cache.get(ob.name)
    if c and c["key"] == key: return c
    mw = np.array(ob.matrix_world, dtype=np.float32)
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    co = co @ mw[:3, :3].T + mw[:3, 3]
    ev = np.empty(len(me.edges) * 2, np.int32); me.edges.foreach_get("vertices", ev); ev = ev.reshape(-1, 2)
    fn = np.empty(len(me.polygons) * 3, np.float32); me.polygons.foreach_get("normal", fn); fn = fn.reshape(-1, 3)
    fn = fn @ np.linalg.inv(mw[:3, :3]).T; fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12
    fc = np.empty(len(me.polygons) * 3, np.float32); me.polygons.foreach_get("center", fc); fc = fc.reshape(-1, 3)
    fc = fc @ mw[:3, :3].T + mw[:3, 3]
    # edge -> up to 2 faces
    ef = -np.ones((len(me.edges), 2), np.int64)
    ek_index = {tuple(sorted(e)): i for i, e in enumerate(ev.tolist())}
    for p in me.polygons:
        for k in p.edge_keys:
            i = ek_index[k]
            if ef[i, 0] < 0: ef[i, 0] = p.index
            else: ef[i, 1] = p.index
    two = ef[:, 1] >= 0
    ang = np.zeros(len(ev), np.float32)
    ang[two] = np.arccos(np.clip(np.einsum("ij,ij->i", fn[ef[two, 0]], fn[ef[two, 1]]), -1, 1))
    hard = (~two) | (ang > SOFT_ANGLE)
    c = dict(key=key, co=co, ev=ev, ef=ef, fn=fn, fc=fc, hard=hard, soft=two & ~hard, vkey=None, batch=None)
    _edge_cache[ob.name] = c
    return c

def draw_edges():
    try:
        import gpu, numpy as np
        from gpu_extras.batch import batch_for_shader
        ctx = bpy.context; rv3d = ctx.region_data
        if rv3d is None: return
        sh = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        cam = np.array(rv3d.view_matrix.inverted().translation, np.float32)
        vkey = tuple(round(x, 4) for x in cam)
        batches = []
        for ob in ctx.visible_objects:
            if ob.type != 'MESH': continue
            c = _mesh_edge_data(ob)
            if c["vkey"] != vkey or c["batch"] is None:
                sel = c["hard"].copy()
                if c["soft"].any():
                    ef, fn, fc = c["ef"], c["fn"], c["fc"]
                    idx = np.nonzero(c["soft"])[0]
                    s0 = np.einsum("ij,ij->i", fn[ef[idx, 0]], cam - fc[ef[idx, 0]]) > 0
                    s1 = np.einsum("ij,ij->i", fn[ef[idx, 1]], cam - fc[ef[idx, 1]]) > 0
                    sel[idx[s0 != s1]] = True            # profile of a smooth surface
                ev = c["ev"][sel]
                c["batch"] = batch_for_shader(sh, 'LINES', {"pos": c["co"]}, indices=ev) if len(ev) else None
                c["vkey"] = vkey
            if c["batch"]: batches.append(c["batch"])
        if not batches: return
        win = rv3d.window_matrix.copy()
        # same as GPU_polygon_offset(viewdist, dist=1): pull edges 0.25% towards the camera
        if rv3d.is_perspective: win[2][3] -= win[2][3] * -0.0025 * 1.0
        else: win[2][3] -= 0.00001 * rv3d.view_distance * 1.0
        ps = ctx.preferences.system.pixel_size
        with gpu.matrix.push_pop_projection():
            gpu.matrix.load_projection_matrix(win)
            gpu.state.depth_test_set('LESS_EQUAL'); gpu.state.depth_mask_set(False); gpu.state.blend_set('ALPHA')
            sh.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
            sh.uniform_float("lineWidth", 1.0 * ps)
            sh.uniform_float("color", (0, 0, 0, 1))
            for b in batches: b.draw(sh)
            gpu.state.depth_test_set('NONE'); gpu.state.blend_set('NONE')
    except Exception:
        P("edges", traceback.format_exc())

def draw_axes():
    try:
        import gpu
        from gpu_extras.batch import batch_for_shader
        rv3d = bpy.context.region_data; region = bpy.context.region
        if rv3d is None: return
        ps = bpy.context.preferences.system.pixel_size
        key = (tuple(round(x, 5) for row in rv3d.perspective_matrix for x in row), region.width, region.height)
        c = _draw["axes"]
        axes = ((Vector((1, 0, 0)), AX_X), (Vector((0, 1, 0)), AX_Y), (Vector((0, 0, 1)), AX_Z))
        if c["key"] != key:
            c["neg"] = [(_neg_axis_dots(region, rv3d, d), col) for d, col in axes]
            c["key"] = key
        line = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        pt = gpu.shader.from_builtin('POINT_UNIFORM_COLOR')
        gpu.state.depth_test_set('LESS_EQUAL'); gpu.state.depth_mask_set(False)
        gpu.state.blend_set('ALPHA')
        line.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
        line.uniform_float("lineWidth", 1.0 * ps)
        for d, col in axes:
            b = batch_for_shader(line, 'LINES', {"pos": [(0, 0, 0), tuple(d * 2000.0)]})
            line.uniform_float("color", col + (1.0,)); b.draw(line)
        gpu.state.point_size_set(1.0 * ps + 0.5)
        for pts, col in c["neg"]:
            if not pts: continue
            b = batch_for_shader(pt, 'POINTS', {"pos": pts})
            pt.uniform_float("color", col + (1.0,)); b.draw(pt)
        gpu.state.depth_test_set('NONE'); gpu.state.blend_set('NONE')
    except Exception:
        P("axes", traceback.format_exc())

# ---------------------------------------------------------------- theme
def apply_theme():
    prefs = bpy.context.preferences
    preset = os.path.join(bpy.utils.system_resource('SCRIPTS'), "presets", "interface_theme", "Blender_Light.xml")
    try:
        import _rna_xml as rna_xml
        rna_xml.xml_file_run(bpy.context, preset, bpy.types.USERPREF_MT_interface_theme_presets.preset_xml_map)
    except Exception:
        P("theme preset", traceback.format_exc())
    th = prefs.themes[0]
    ui = th.user_interface
    ui.panel_header = PANEL_HDR + (1.0,); ui.panel_back = TRAY_BODY + (1.0,)
    ui.panel_sub_back = TRAY_BODY + (1.0,)
    ui.panel_title = TEXT; ui.panel_text = TEXT
    ui.panel_outline = BORDER + (1.0,)
    ui.panel_roundness = 0.0
    ui.editor_border = BORDER
    ui.editor_outline = BORDER + (0.0,)
    try: ui.editor_outline_active = BORDER + (0.0,)
    except Exception: pass
    ui.icon_saturation = 1.0
    # tool buttons (left Large Tool Set)
    w = ui.wcol_toolbar_item
    w.inner = CHROME + (1.0,); w.inner_sel = SEL_FILL + (1.0,)
    w.outline = CHROME + (1.0,); w.outline_sel = SEL_LINE + (1.0,)
    w.item = NAVY + (1.0,); w.text = NAVY; w.text_sel = NAVY; w.roundness = 0.25
    # header buttons (Getting Started)
    w = ui.wcol_tool
    w.inner = CHROME + (1.0,); w.inner_sel = SEL_FILL + (1.0,)
    w.outline = CHROME + (1.0,); w.outline_sel = SEL_LINE + (1.0,)
    w.text = NAVY; w.text_sel = NAVY; w.item = NAVY + (1.0,); w.roundness = 0.25
    for wn in ("wcol_regular", "wcol_text", "wcol_toggle"):
        w = getattr(ui, wn); w.inner = (1, 1, 1, 1); w.outline = BORDER + (1.0,); w.text = TEXT; w.text_sel = TEXT
    w = ui.wcol_box
    w.inner = PANEL_HDR + (1.0,); w.outline = srgb(250, 250, 252) + (1.0,); w.roundness = 0.0; w.text = TEXT
    w = ui.wcol_pulldown; w.text = TEXT; w.inner_sel = SEL_FILL + (1.0,); w.text_sel = TEXT
    # spaces
    v = th.view_3d
    sp = v.space
    sp.header = CHROME + (1.0,); sp.header_text = TEXT; sp.header_text_hi = TEXT
    sp.text = TEXT; sp.text_hi = TEXT; sp.title = TEXT
    w = ui.wcol_tab   # single-category sidebar still draws a tab: make it invisible (blends into chrome)
    w.inner = CHROME + (1.0,); w.inner_sel = CHROME + (1.0,); w.outline = CHROME + (1.0,)
    try: w.outline_sel = CHROME + (1.0,)
    except Exception: pass
    w.text = CHROME; w.text_sel = CHROME; w.item = CHROME + (1.0,)
    sb = th.regions.sidebars
    sb.back = CHROME + (1.0,); sb.tab_back = CHROME + (1.0,)
    g = sp.gradients
    g.background_type = 'SINGLE_COLOR'
    g.high_gradient = GROUND; g.gradient = GROUND
    v.wire = (0, 0, 0)
    v.object_selected = srgb(0, 0, 255); v.object_active = srgb(0, 0, 255)
    v.face_back = FACE_BACK + (1.0,)
    v.face_front = (0, 0, 0, 0)
    v.edge_width = 1
    for sname in ("topbar", "statusbar"):
        s = getattr(th, sname).space
        s.back = CHROME; s.header = CHROME + (1.0,)
        s.text = TEXT; s.header_text = TEXT; s.header_text_hi = TEXT; s.text_hi = TEXT
    th.statusbar.space.back = CHROME

def apply_prefs():
    p = bpy.context.preferences
    p.view.show_splash = False
    p.view.show_navigate_ui = False
    p.view.mini_axis_type = 'NONE'
    for n in ("show_statusbar_stats", "show_statusbar_memory", "show_statusbar_vram",
              "show_statusbar_version", "show_statusbar_scene_duration"):
        try: setattr(p.view, n, False)
        except Exception: pass
    p.system.use_region_overlap = False
    for n in ("show_corner_split", "show_regions_visibility_toggle"):
        if hasattr(p.apps, n): setattr(p.apps, n, False)
    p.inputs.view_rotate_method = 'TURNTABLE'
    p.inputs.use_zoom_to_mouse = True
    p.inputs.use_mouse_depth_navigate = True
    p.view.show_tooltips_python = False
    # SketchUp-like face shading: high ambient + one soft key light (view space), no specular
    sysp = p.system
    sysp.light_ambient = (0.42, 0.42, 0.42)
    L = sysp.solid_lights
    for i, l in enumerate(L):
        l.use = (i == 1); l.specular_color = (0, 0, 0); l.smooth = 0.0
    L[1].direction = Vector((-0.35, 0.45, 0.82)).normalized(); L[1].diffuse_color = (0.62, 0.62, 0.62)
    # solid_lights only feed a studio light when saved as a .sl file (prefs.studio_lights.new writes them)
    try:
        # NOTE: user_resource('DATAFILES') is NOT redirected by BLENDER_USER_CONFIG -> write to the session temp dir
        fp = os.path.join(bpy.app.tempdir or "/tmp", "sketchup.sl")
        for sl in p.studio_lights:
            if sl.name == "sketchup.sl": p.studio_lights.remove(sl)
        p.studio_lights.new(path=fp)
        P("studio light", fp, os.path.exists(fp))
    except Exception:
        P("studiolight", traceback.format_exc())

# ---------------------------------------------------------------- startup steps (one per timer tick)
_hidden_panels = []
def hide_v3d_ui_panels():
    def all_sub(c):
        for s in c.__subclasses__():
            yield s; yield from all_sub(s)
    victims = [c for c in set(all_sub(bpy.types.Panel))
               if getattr(c, "bl_space_type", "") == 'VIEW_3D' and getattr(c, "bl_region_type", "") == 'UI'
               and getattr(c, "bl_category", "") != "Bandeja" and getattr(c, "is_registered", False)]
    victims.sort(key=lambda c: 0 if getattr(c, "bl_parent_id", "") else 1)   # children first
    for c in victims:
        try: bpy.utils.unregister_class(c); _hidden_panels.append(c)
        except Exception: pass
    P("hidden UI panels", len(_hidden_panels))
    left = [(c.__name__, getattr(c, "bl_category", None)) for c in set(all_sub(bpy.types.Panel))
            if getattr(c, "bl_space_type", "") == 'VIEW_3D' and getattr(c, "bl_region_type", "") == 'UI' and c.is_registered]
    P("remaining UI panels", left)

def v3d_area(win):
    return max((a for a in win.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width * a.height)

def build_model():
    import bmesh
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    sc = bpy.context.scene
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0; sc.view_settings.gamma = 1.0
    us = sc.unit_settings; us.system = 'METRIC'; us.length_unit = 'METERS'
    coll = sc.collection
    # box 2 x 3 x 1.5 m sitting on the origin, + a cylinder
    me = bpy.data.meshes.new("Caixa"); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * 2 + 1.0, v.co.y * 3 + 1.5, v.co.z * 1.5 + 0.75))
    bm.to_mesh(me); bm.free()
    coll.objects.link(bpy.data.objects.new("Caixa", me))
    me = bpy.data.meshes.new("Retangulo"); bm = bmesh.new()
    vs = [bm.verts.new(v) for v in ((-4.2, -0.4, 0), (-4.2, -2.4, 0), (-1.2, -2.4, 0), (-1.2, -0.4, 0))]
    f = bm.faces.new(vs)
    f.normal_update()
    if f.normal.z > 0: f.normal_flip()          # normal -Z: we look at its blue-grey back face
    bm.to_mesh(me); bm.free()
    coll.objects.link(bpy.data.objects.new("Retangulo", me))
    me = bpy.data.meshes.new("Cilindro"); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.55, radius2=0.55, depth=1.8)
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector((-2.6, 1.6, 0.9)))
    for f in bm.faces: f.smooth = len(f.verts) == 4
    bm.to_mesh(me); bm.free()
    coll.objects.link(bpy.data.objects.new("Cilindro", me))

def configure_space(area):
    sp = area.spaces.active
    sp.show_region_header = False
    sp.show_region_tool_header = True
    sp.show_region_toolbar = True
    sp.show_region_ui = True
    try: sp.show_region_hud = False
    except Exception: pass
    sp.show_gizmo = False
    sp.lens = 35; sp.clip_start = 0.05; sp.clip_end = 20000
    sh = sp.shading
    sh.type = 'SOLID'; sh.light = 'STUDIO'; sh.studio_light = 'sketchup.sl'; sh.color_type = 'SINGLE'; sh.single_color = (1, 1, 1)
    sh.show_specular_highlight = False; sh.show_cavity = False; sh.show_xray = False; sh.show_shadows = False
    sh.show_backface_culling = False; sh.show_object_outline = False; sh.background_type = 'THEME'
    try: sh.use_world_space_lighting = False
    except Exception: pass
    ov = sp.overlay
    ov.show_floor = False; ov.show_axis_x = False; ov.show_axis_y = False; ov.show_axis_z = False
    ov.show_cursor = False; ov.show_object_origins = False; ov.show_text = False; ov.show_stats = False
    ov.show_relationship_lines = False; ov.show_extras = False
    ov.show_wireframes = False; ov.wireframe_threshold = 0.1; ov.wireframe_opacity = 1.0
    ov.show_face_orientation = True
    try: ov.show_viewer_attribute = False
    except Exception: pass

# default camera like SketchUp's start view (derived from ref image 2, see FINDINGS)
CAM = dict(yaw_deg=33.0, pitch_deg=6.6, origin_ndc=(-0.26, -0.387), vfov_deg=35.0, dist=11.5)
def set_view(area):
    sp = area.spaces.active; r3 = sp.region_3d
    region = next(r for r in area.regions if r.type == 'WINDOW')
    yaw = math.radians(CAM["yaw_deg"]); pitch = math.radians(CAM["pitch_deg"])
    fwd = Vector((-math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), -math.sin(pitch)))
    right = fwd.cross(Vector((0, 0, 1))).normalized(); up = right.cross(fwd)
    R = Matrix((right, up, -fwd)).transposed()           # columns = view x, y, z
    r3.view_perspective = 'PERSP'
    r3.view_rotation = R.to_quaternion()
    aspect = region.width / max(1, region.height)
    tv = math.tan(math.radians(CAM["vfov_deg"]) / 2)
    nx, ny = CAM["origin_ndc"]
    dcam = Vector((nx * tv * aspect, ny * tv, -1.0)).normalized()
    dw = R @ dcam
    C = -dw * CAM["dist"]                                  # camera position so that origin lands on (nx, ny)
    r3.view_distance = 10.0
    r3.view_location = C + fwd * 10.0
    P("view set; cam", tuple(round(x, 2) for x in C), "aspect", round(aspect, 3))

def fit_lens(area):
    """Make the vertical FOV exactly CAM['vfov_deg'] (viewport lens/sensor mapping is not obvious)."""
    sp = area.spaces.active; r3 = sp.region_3d
    wm = r3.window_matrix
    cur = wm[1][1]; target = 1.0 / math.tan(math.radians(CAM["vfov_deg"]) / 2)
    sp.lens = sp.lens * target / cur
    P("lens fitted", round(sp.lens, 3), "wm11", round(cur, 4), "->", round(target, 4))

STEPS = []
def step(fn): STEPS.append(fn); return fn

@step
def s_theme():
    apply_prefs(); apply_theme()
    win = bpy.context.window_manager.windows[0]
    keep = bpy.data.workspaces.get("Layout") or win.workspace
    win.workspace = keep

@step
def s_workspaces():
    win = bpy.context.window_manager.windows[0]
    keep = win.workspace
    bpy.data.batch_remove([ws for ws in bpy.data.workspaces if ws != keep])
    keep.name = "SketchUp"

@step
def s_close_areas():
    win = bpy.context.window_manager.windows[0]; scr = win.screen
    for t in ('DOPESHEET_EDITOR', 'TIMELINE', 'OUTLINER', 'PROPERTIES'):
        for a in [a for a in scr.areas if a.type == t]:
            with bpy.context.temp_override(window=win, screen=scr, area=a):
                bpy.ops.screen.area_close()

@step
def s_space():
    win = bpy.context.window_manager.windows[0]
    area = v3d_area(win)
    configure_space(area)
    build_model()
    hide_v3d_ui_panels()
    with bpy.context.temp_override(window=win, area=area):
        bpy.ops.wm.tool_set_by_id(name="su.select")

@step
def s_tray():
    win = bpy.context.window_manager.windows[0]
    area = v3d_area(win)
    for r in area.regions:
        if r.type == 'UI':
            try: r.active_panel_category = 'Bandeja'
            except Exception: P("cat", traceback.format_exc())
    set_view(area)

@step
def s_lens():
    win = bpy.context.window_manager.windows[0]
    area = v3d_area(win); fit_lens(area); set_view(area)

@step
def s_lens2():
    win = bpy.context.window_manager.windows[0]
    area = v3d_area(win); fit_lens(area); set_view(area)
    bpy.app.driver_namespace["su_ready"] = True
    P("ready")

def _run_steps():
    if not STEPS_PENDING: return None
    fn = STEPS_PENDING.pop(0)
    try: fn()
    except Exception: P(fn.__name__, traceback.format_exc())
    return 0.3
STEPS_PENDING = []

@persistent
def _on_load_post(_):
    if bpy.app.background: return
    STEPS_PENDING[:] = list(STEPS)
    bpy.app.timers.register(_run_steps, first_interval=0.5)

# ---------------------------------------------------------------- register
from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active as TA
_saved_tools = None

def _force_two_columns(layout, region, scale_y):
    return TSP._layout_generator_multi_columns(layout, column_count=2, scale_y=scale_y), False

def register():
    global _saved_tools
    P("register")
    bpy.types.WindowManager.su_vcb = bpy.props.StringProperty(name="Medidas", default="")
    for key, label in TRAY:
        setattr(bpy.types.WindowManager, "su_tray_" + key, bpy.props.BoolProperty(name=label, default=key in TRAY_OPEN))
    bpy.utils.register_class(SU_OT_placeholder)
    for c in _menu_classes + _tray_classes: bpy.utils.register_class(c)
    TSP._icon_value_from_icon_handle = staticmethod(_icon)
    _saved["detect"] = TSP._layout_generator_detect_from_region
    TSP._layout_generator_detect_from_region = staticmethod(_force_two_columns)
    _saved_tools = {k: list(v) for k, v in TA._tools.items()}
    _saved["fallback"] = TA.tool_fallback_id
    TA.tool_fallback_id = "su.select"
    TA._tools[None] = []
    TA._tools['OBJECT'] = [None if t is None else tool_def(t) for t in LTS]
    _saved["tl"] = bpy.types.TOPBAR_HT_upper_bar.draw_left
    _saved["tr"] = bpy.types.TOPBAR_HT_upper_bar.draw_right
    _saved["th"] = bpy.types.VIEW3D_HT_tool_header.draw
    _saved["sb"] = bpy.types.STATUSBAR_HT_header.draw
    _saved["vh"] = bpy.types.VIEW3D_HT_header.draw
    bpy.types.TOPBAR_HT_upper_bar.draw_left = topbar_left
    bpy.types.TOPBAR_HT_upper_bar.draw_right = topbar_right
    bpy.types.VIEW3D_HT_tool_header.draw = tool_header
    bpy.types.STATUSBAR_HT_header.draw = statusbar
    bpy.types.VIEW3D_HT_header.draw = v3d_header
    if not bpy.app.background:
        _draw["handles"] = [
            bpy.types.SpaceView3D.draw_handler_add(draw_sky, (), 'WINDOW', 'POST_VIEW'),
            bpy.types.SpaceView3D.draw_handler_add(draw_edges, (), 'WINDOW', 'POST_VIEW'),
            bpy.types.SpaceView3D.draw_handler_add(draw_axes, (), 'WINDOW', 'POST_VIEW')]
    bpy.app.handlers.load_post.append(_on_load_post)

def unregister():
    for h in _draw["handles"]: bpy.types.SpaceView3D.draw_handler_remove(h, 'WINDOW')
    _draw["handles"] = []
    bpy.app.handlers.load_post.remove(_on_load_post)
    TSP._icon_value_from_icon_handle = staticmethod(_orig_icon)
    TSP._layout_generator_detect_from_region = staticmethod(_saved["detect"])
    TA._tools.clear(); TA._tools.update(_saved_tools); TA.tool_fallback_id = _saved["fallback"]
    bpy.types.TOPBAR_HT_upper_bar.draw_left = _saved["tl"]
    bpy.types.TOPBAR_HT_upper_bar.draw_right = _saved["tr"]
    bpy.types.VIEW3D_HT_tool_header.draw = _saved["th"]
    bpy.types.STATUSBAR_HT_header.draw = _saved["sb"]
    bpy.types.VIEW3D_HT_header.draw = _saved["vh"]
    for c in reversed(_menu_classes + _tray_classes): bpy.utils.unregister_class(c)
    bpy.utils.unregister_class(SU_OT_placeholder)
    for c in reversed(_hidden_panels):
        try: bpy.utils.register_class(c)
        except Exception: pass
    _hidden_panels.clear()
    del bpy.types.WindowManager.su_vcb
    for key, _ in TRAY: delattr(bpy.types.WindowManager, "su_tray_" + key)
    if "c" in _pcoll: bpy.utils.previews.remove(_pcoll.pop("c"))
