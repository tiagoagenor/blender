# Visual shell spike: checklist

## Setup
- [x] Read RESEARCH_BLENDER_API, RESEARCH_SKETCHUP, CRITICA_R1 and the reference images
- [x] App template folder `tpl/startup/bl_app_templates_system/SketchUpSpike/` + `run.sh` (isolated env vars) + `driver.py` (timer screenshot)
- [x] Isolate *all* user dirs (CONFIG, SCRIPTS, DATAFILES, EXTENSIONS). DATAFILES was missed at first; the one stray file it created was removed.

## Layout
- [x] One 3D viewport: timeline/outliner/properties closed, workspace tabs removed (batch_remove)
- [x] Top menu row pt-BR (Arquivo … Ajuda), placeholder menus
- [x] "Primeiros passos" toolbar in the tool header, SketchUp order and CRITICA B5 groups, flyout arrows
- [x] Large Tool Set in 2 columns, 2027 order, empty "Etiqueta" cell
- [x] "Bandeja padrão" on the right with the 8 requested panels (no Etiquetas)
- [x] Status bar: hint text left, "Medidas" field right
- [x] Region widths set by simulated edge drags
- [x] Single-category sidebar tab hidden (theme)
- [x] Tray rows without Blender's drag grip (v3: layout panels)

## Look
- [x] Light theme (Blender_Light + SketchUp chrome #F1F1F6 / #E0E1E9 / #F4F7FC)
- [x] Sky gradient + gray ground with a true horizon (POST_VIEW quad)
- [x] RGB axes, solid positive / dotted negative, depth-tested
- [x] No grid, 3D cursor, navigation gizmo, "User Perspective" text
- [x] View transform Standard; colours verified by pixel sampling
- [x] White faces with SketchUp-like shading (custom .sl studio light)
- [x] Back faces #A4B2BB (face orientation overlay)
- [x] Black 1 pt edges + cylinder profile edges (custom edge renderer)
- [x] Camera: 35° vertical FOV, start view derived from reference image 2
- [x] Tool icons recoloured to navy / cyan / red
- [x] Expanded tray panel content (v3)

## Deliverables
- [x] shots/shell_v1.png
- [x] shots/shell_v2.png
- [x] shots/shell_v3.png
- [ ] FINDINGS.md (Write blocked for subagent; content returned in report for the parent to save)
