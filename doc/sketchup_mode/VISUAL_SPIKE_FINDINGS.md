# SketchUp-mode visual shell spike — findings

Blender 5.2.2, macOS arm64 (Metal), Retina (pixel_size = 2). Throwaway spike; code lives in the session scratchpad:
`/private/tmp/claude-1313471784/-Users-tiago-agenor--claude-spares-spare-OyPPwD/b629df7a-43bf-4aae-9e76-4fba22f313f3/scratchpad/visual_spike/`

| File | What |
|---|---|
| `tpl/startup/bl_app_templates_system/SketchUpSpike/__init__.py` | Whole shell (~770 lines, one file) |
| `tpl/.../SketchUpSpike/icons/` | 117 recoloured `.dat` tool icons + `style_simple.png` |
| `tools/build_icons.py` | Recolours Blender `.dat` toolbar icons to navy/cyan/red |
| `tools/build_style_thumb.py` | Original "Estilo simples" thumbnail (PIL) |
| `run.sh` | Fully isolated launch (see §1) |
| `driver.py` | Region resize via simulated drags, screenshot, quit |
| `shots/shell_v1..v3.png` | Iterations, 1600 px wide — v3 best |
| `raw/shell_v*_full.png` | Full 3024×1708 originals |

## Iterations
- v1: layout right (menus, Getting Started, 2-col LTS, tray, status bar, sky/ground, axes, light theme). Off: dull grey faces (default studio light), wireframe-overlay edges (thin, broken, cylinder facets visible), Blender-coloured icons.
- v2: custom `.sl` studio light (front 243, top 222, side 185); custom edge renderer (black 1 pt edges + cylinder profile edges, no facets); icons recoloured navy/cyan/red.
- v3: tray as flat SketchUp rows without Blender drag grip; Estilos expanded with original thumbnail, description, Selecionar/Editar/Misturar tabs and folder buttons; rectangle on the ground shows blue-grey back face.

Measured v3 pixels (all ~2 units low → screenshot colour profile, not pipeline; with view transform Standard, POST_VIEW gpu colours are written 1:1 in sRGB):

| Element | Measured | Target |
|---|---|---|
| Ground | 189,189,196 | 191,191,198 |
| Sky top | 36,165,220 | 30,166,221 |
| Horizon | 187,227,244 | 191,229,245 |
| Back face | 162,176,185 | 164,178,187 |
| Chrome | 240,240,245 | 241,241,246 |
| Tray header | 223,224,232 | 224,225,233 |

## 1. Running isolated (important)
```sh
BLENDER_SYSTEM_SCRIPTS=$HERE/tpl BLENDER_USER_CONFIG=$HERE/raw/cfg BLENDER_USER_SCRIPTS=$HERE/raw/uscripts \
BLENDER_USER_DATAFILES=$HERE/raw/udata BLENDER_USER_EXTENSIONS=$HERE/raw/uext \
Blender --app-template SketchUpSpike --enable-event-simulate --python driver.py -- out.png
```
- ⚠️ `BLENDER_USER_CONFIG` does NOT redirect `user_resource('DATAFILES')`. Always also set `BLENDER_USER_DATAFILES` and `BLENDER_USER_EXTENSIONS`. (A stray `.sl` landed in the real user datafiles once; it was deleted.) Template writes the `.sl` into `bpy.app.tempdir`.
- `--window-geometry` ignored on this Mac; window opens maximised 1512×854 pt → screenshots 3024×1708 px.
- `bpy.ops.screen.screenshot` with `temp_override(window=win)` captures the whole window incl. topbar/status bar.

## 2. What worked
### Startup sequence
No startup.blend; `load_post` queues steps one per timer tick (0.3 s apart) to avoid the area_close crash: (1) prefs+theme; (2) `bpy.data.batch_remove(other workspaces)`; (3) `screen.area_close` for DOPESHEET/TIMELINE/OUTLINER/PROPERTIES; (4) space settings, model, hide sidebar panels, `tool_set_by_id('su.select')`; (5) `region.active_panel_category='Bandeja'` + view; (6) lens fit ×2; (7) `driver_namespace['su_ready']`.

### Theme
- Light theme: `import _rna_xml as rna_xml` (`import rna_xml` fails in 5.2), `xml_file_run(ctx, "Blender_Light.xml", USERPREF_MT_interface_theme_presets.preset_xml_map)`.
- Overrides: `ui.panel_*`; `ui.wcol_toolbar_item` (inner=chrome, inner_sel=#D6E8FA, outline_sel=#0078D7 → SketchUp selected tool look); `ui.wcol_tool` (header buttons); `ui.wcol_box` tray bands #E0E1E9 roundness 0; `topbar.space`/`statusbar.space` back+header #F1F1F6; toolbar/sidebar region bg in 5.x is `theme.regions.sidebars.back` / `.tab_back` (`ThemeSpaceGradient.button` gone); `view_3d.face_back=#A4B2BB`, `face_front` alpha 0, `wire` black.

### Preferences
`system.use_region_overlap=False` (opaque docked toolbar/tray); `view.show_navigate_ui=False`; `mini_axis_type='NONE'`; `show_splash=False`; `apps.show_corner_split=False`; `show_regions_visibility_toggle=False`. ⚠️ keep `apps.show_edge_resize=True` (False kills region-edge drags). `view.show_statusbar_vram` read-only → wrap setattr in try.

### Menu row
Override `TOPBAR_HT_upper_bar.draw_left` with nine `layout.menu("SU_MT_*")` (pt-BR), `draw_right` empty → removes Blender logo menu, workspace tabs, scene/view-layer selectors.

### Getting Started bar
Hide 3D header (`show_region_header=False`); override `VIEW3D_HT_tool_header.draw`: each tool = `wm.tool_set_by_id(icon_value=…, depress=active, emboss=active)`; nav buttons placeholder op `emboss=False`; groups split by `row.separator(factor=.6, type='LINE')`; ▾ = `label(icon='DOWNARROW_HLT')` with `ui_units_x=0.7`.

### Large Tool Set
- `VIEW3D_PT_tools_active._tools['OBJECT']` = list of `ToolDef.from_dict(...)` + `None` separators; no `register_tool` needed; `tool_set_by_id` finds them.
- `_tools[None]=[]`, `tool_fallback_id='su.select'` (else "builtin.select_box not found" banner).
- Force 2 columns: monkey-patch `ToolSelectPanelHelper._layout_generator_detect_from_region` → `_layout_generator_multi_columns(column_count=2)`.
- Odd tool count in a group leaves last right cell empty → empty "Etiqueta" cell for free.

### Region widths
`Region.width` read-only. With `--enable-event-simulate` driver sends MOUSEMOVE to edge, LEFTMOUSE PRESS, 10 MOUSEMOVEs, RELEASE, each phase its own tick. Coordinates in device px (2× Retina); `Window.width` is points. Result TOOLS 193 px (~96 pt), UI 603 px. Real build: save in startup.blend.

### Single-category sidebar tab
C draws the tab strip even with one category; empty category becomes "Misc". Hack: colour `ui.wcol_tab` (inner, inner_sel, outline, text, text_sel) = chrome → invisible tab, leaves ~20 pt empty strip. The other 82 VIEW_3D/UI panels unregistered (children first), re-registered on unregister.

### Tray without drag grip
Blender draws the grip for every top-level panel with a background; `HIDE_HEADER` panels have none (without region overlap) → no grip. Tray = ONE `HIDE_HEADER` panel: title row ("Bandeja padrão", pin, ✕); each SketchUp panel = `col.box().row()` with toggle `prop(wm, "su_tray_<key>", icon=RIGHTARROW/DOWNARROW_HLT, emboss=False)`, label, right ✕; body drawn when open (WindowManager BoolProperty). `UILayout.panel()` also gripless but headers get no band colour.

### Status bar
Override `STATUSBAR_HT_header.draw`: left PINNED + INFO icons, LINE separator, hint text; `separator_spacer()`; right "Medidas" label + `prop(wm, "su_vcb", ui_units_x=11)`. Omit `template_reports_banner` (else yellow banner).

### Sky and ground
POST_VIEW full-screen quad at NDC z=0.9999999, depth test LESS_EQUAL. Horizon = vanishing line of horizontal view direction. Sky linear #BFE5F5 (horizon) → #1EA6DD (top edge); ground flat #BFBFC6. Theme background #BFBFC6.

### Axes
POST_VIEW with depth test. Positive halves `POLYLINE_UNIFORM_COLOR` 1 pt, 2000 m. Negative halves dotted with even screen spacing: project half-axis to 2D (log-spaced samples in front of camera), step every 4.5 px, lift back to 3D via `intersect_line_line(view ray, axis)`, draw `POINT_UNIFORM_COLOR` points. Keeps occlusion; cached per perspective matrix.

### Faces
Solid, `color_type='SINGLE'` white, view transform Standard. Default studio light too dark (176/135/85). Custom studio light: `prefs.system.light_ambient=0.42`; only `solid_lights[1]` on, direction (-0.35,0.45,0.82), diffuse 0.62, specular 0; `prefs.studio_lights.new(path)` writes+loads `.sl`; `shading.studio_light='sketchup.sl'`, `use_world_space_lighting=False`. Editing `solid_lights` alone doesn't change "Default". Result 243/222/185.

### Back faces
`overlay.show_face_orientation=True` with theme `face_back`, transparent `face_front` → 162,176,185. Note: new `bm.faces.new()` face has zero normal until `normal_update()`.

### Edges (custom renderer, replaces wireframe overlay)
POST_VIEW, cached per mesh with numpy (world coords, edge→face map, dihedral angle). Hard edges (boundary or angle > 20°) always drawn; soft edges only as profile edges (two faces on opposite sides w.r.t. camera, sign of `n·(cam − face_center)`). Black `POLYLINE_UNIFORM_COLOR` 1 pt, depth LESS_EQUAL, pulled toward camera with GPU_polygon_offset formula on a copy of window_matrix: `win[2][3] -= win[2][3] * -0.0025`. No z-fighting seen. Wireframe overlay gave 1 device-px gappy edges; `wireframe_threshold=0.1` still showed 15° facets.

### Icons
`bi.NAME` handles → built-in SVG icon ids (from `UILayout.prop` icon enum), drawn in `wcol_*.text` navy. `.dat` geometry icons recoloured by `tools/build_icons.py` (white/grey→navy #00426E, Blender green→cyan #0096DC, orange→red, black→white). Blender inverts HSL lightness of geometry icons when `wcol_toolbar_item.inner` is light (`interface_icons.cc`) → script stores pre-inverted colours. Absolute path icons: `os.path.join(datafiles, "/abs/su.x")` keeps the absolute path.

### Start view
From reference image 2 (vanishing points): vertical FOV 35°, yaw 33° from +Y toward −X, pitch 6.6° down, origin at NDC (−0.26, −0.39), distance 11.5 m. Lens vs FOV: after a redraw read `rv3d.window_matrix[1][1]` and apply `lens *= target/current` (viewport lens 35 ≠ 35° FOV; ~76 at aspect 1.5).

## 3. Didn't work / pitfalls
`import rna_xml` (use `_rna_xml`); `ThemeSpaceGradient.button`; `show_statusbar_vram` read-only; `apps.show_edge_resize=False` kills edge drags; `invoke_popup` from timer not shown in screenshot; qlmanage/Inkscape couldn't render Blender white SVG icons; `wireframe_threshold` doesn't hide facets; `layout.panel()` headers have no band colour.

## 4. Remaining visual gaps vs SketchUp
1. Top toolbar icons ~20 pt vs 24–32 pt (fixed ~26 pt header).
2. Icon artwork = recoloured Blender glyphs (PNG via `bpy.utils.previews` + resolver patch proven).
3. Tray: ✕ is an icon not a boxed ✕; ~20 pt empty strip from invisible tab; folder entries are buttons not 64 px tiles.
4. Status bar: no Measurements box border/grip; Blender pin/ⓘ icons.
5. Menus inside window (Mac SketchUp uses global menu bar); items placeholders; Inter font.
6. Blender 1 px region borders.
7. Region widths via simulated drag → ship startup.blend.
8. Edges: no AA tuning; profile only for soft edges; no hidden/bridge attribute; no back edges/X-ray.
9. Shading camera-relative (SketchUp follows the sun).
10. Sky top colour depends on pitch.
11. Out of scope: selection blue, inference markers, tooltips.

## 5. Reuse
`apply_theme()`/`apply_prefs()` + colour constants → starting theme/userpref; `draw_sky`, `draw_axes`, `draw_edges` → `su/draw/`; `tools/build_icons.py` → stand-in icon set; `LTS`, `GETTING_STARTED`, `TRAY` lists encode 2027 order, critique grouping and pt-BR names; `set_view()`/`fit_lens()` reproduce the start view.
