# WS_G — Agente G (Construção, câmera, cenas)

Legenda: `[ ]` pendente · `[~]` em andamento · `[x]` feito. Brief: `PLANO.md` §9.2-G (sub-checklist copiado abaixo; o agente G mantém este arquivo).

## Sub-checklist §9.2-G
1. [x] ferramentas NAV (Órbita/Panorâmica/Aplicar zoom via `meta.operator`), Extensões de zoom, FOV 35° vertical, Exibições padrão, projeção
2. [x] `su.view_orbit/pan` (pivô no PRESS) para Ctrl+Cmd; recentralizar (duplo clique MMB); trackpad (modos + inverter zoom) com A — **itens do keymap "3D View" a instalar por A** (ver Notas)
3. [x] `guides` + `annotations`
4. [x] Fita métrica (guia, ponto-guia, modo medir)
5. [x] Transferidor (gizmo no hover, guia angular)
6. [x] Dimensões lineares (AC-DIM-1..3; texto em tela, Cmd+Z)
7. [x] P1: Anterior/Próxima, Janela de zoom, Posição da câmera, Texto com chamada, Texto em 3D (emite `"doc"`), Cenas + abas

## Aceite e comandos (referência)
- **Aceite**: AC-FIT-1..4, AC-TRA-1..2, AC-DIM-1..3, AC-NAV-1..8.
- **Comandos**: `tools/sketchup_mode/run_unit.sh test_g_` · `tools/sketchup_mode/run_gui.sh scn_g` (subconjunto: `SU_SCN_G=nav,tape tools/sketchup_mode/run_gui.sh scn_g`)

## Notas

### Navegação (bloco 1)
- Navegação 100 % própria (não depende de prefs do Blender): `core/camera.py` = matemática pura sobre um `View` (loc, rot, dist, persp, FOV) testada headless; `ops/view_ops.py` = operadores modais.
  - Órbita: turntable, eixo azul sempre vertical (sem rolagem, nivelada no início), pivô = geometria sob o PRESS (centro da tela no vazio), trava no topo/fundo; Shift durante a órbita = panorâmica; 2º PRESS em ≤ 0,35 s no mesmo lugar = recentralizar.
  - Panorâmica: o ponto agarrado fica exatamente sob o cursor (perspectiva correta).
  - Roda: dolly em direção ao ponto sob o cursor (fator 1/1,25 por dente); o ponto fica sob o cursor.
  - Duplo clique MMB: o ponto vai ao centro (pan).
  - FOV 35° **vertical**: o lens do viewport do Blender ajusta a LARGURA → camada `annot2d` chama `camera.check_fov` e reajusta o lens (deferido) quando a proporção muda.
  - Trackpad: modo "sketchup" (2 dedos = zoom no cursor, `trackpad_invert_zoom` inverte; Shift = pan; pinça = zoom) / "blender" (2 dedos = órbita, Shift = pan). **Direção do zoom com 2 dedos: conferir com o usuário** (§8.4).
  - Anterior/Próxima: histórico de vistas (sessão), empilhado ao fim de cada navegação.
- `Scene.su_pages` (G): `fov_v` + cenas (P1). `Scene.su_guides` (G): guias, dimensões, textos (memfile → Cmd+Z funciona).
- Ferramentas: Órbita (O), Panorâmica (H), Aplicar zoom (Z; Medidas "Campo de visão": `35` graus, `50mm` focal), Extensões de zoom (Shift+Z, COMMAND), Anterior (COMMAND P1).
- **Para A — keymap "3D View"** (região; tem de vir antes dos `view3d.*` do preset; o duplo clique cai para PRESS dentro do MESMO keymap, então o item DOUBLE_CLICK tem de estar no "3D View"): instalar `ops/view_ops.KEYMAP_VIEW3D` (mesmo formato de `KEYMAP`) no keymap "3D View" (`space_type='VIEW_3D', region_type='WINDOW'`) do keyconfig de add-on:
  `MIDDLEMOUSE DOUBLE_CLICK → su.view_recenter` · `MIDDLEMOUSE PRESS (e +alt) → su.view_orbit` · `shift+MIDDLEMOUSE PRESS → su.view_pan` · `WHEELUP/WHEELIN PRESS any → su.view_zoom(steps=1)` · `WHEELDOWN/WHEELOUT PRESS any → su.view_zoom(steps=-1)` · `TRACKPADPAN ANY any → su.view_trackpad` · `TRACKPADZOOM ANY any → su.view_trackpad`. Os `view3d.rotate/move/zoom/dolly/view_center_pick` podem sair do `ALLOW`. O `scn_g` instala esses itens se não estiverem lá (fixture).
- `KEYMAP` (Window, já entra pelo `keymap.finalize`): `ctrl+oskey LEFTMOUSE CLICK_DRAG → su.view_orbit` (+alt idem), `ctrl+oskey+shift → su.view_pan`. O pivô vem de `event.mouse_prev_press_x/y`.
- **Para A — COMMAND no LTS**: `DISPATCH.sync` trata um id COMMAND clicado no LTS como ferramenta. Contorno de G: o controlador COMMAND (`tools/nav._Command`) roda o comando no `activate` e devolve a ferramenta anterior. Melhor: o `sync` rodar `meta.operator` e voltar.
- **Para A — Option+clique**: os itens LEFTMOUSE do keymap das ferramentas (`base.tool_keymap`) não têm `any`/`alt` → Option+clique **não chega** ao `su.tool_event` (Mover-cópia, Fita/Transferidor "Option = alternar"…). Sugestão: `"any": True` nos itens PRESS/RELEASE (o `su.tool_event` já devolve PASS para Ctrl). G aceita também Option tocado durante a operação (chega pelo modal).
- Armadilha: registrar uma subclasse de um operador JÁ registrado substitui o tipo do pai (`su.view_orbit` sumia) → mixin não registrado (`_OrbitPan`). E `hasattr(bpy.ops.x, "y")` é sempre True: testar com `get_rna_type()`.
- Simulação de Ctrl+Cmd+arrasto no harness: o CLICK_DRAG leva os modificadores do estado da janela → enviar também os eventos de tecla `LEFT_CTRL`/`OSKEY` (com a própria flag) antes do clique (`scn_g._drag`).

### Construção (bloco 2)
- `core/guides.py`: `add_guide_line/add_guide_point/delete_guides/count/guides_arrays/add_dimension/add_text/dimension_text/delete_annotations/pick`; registra `inference.set_guides_provider(guides_arrays)` (C). Guias ocultas por Visualizar ▸ Guias (`su_style.show_guides`) não são inferíveis.
- **Para F**: Apagar/Selecionar podem usar `guides.pick(region, rv3d, xy) -> ('GUIDE'|'DIM'|'TEXT', i)` e `guides.delete_guides([i])` / `guides.delete_annotations(dims=[i])` (+ `undo.push`). Editar ▸ Excluir guias = `su.delete_guides`.
- `draw/annotations.py`: guias tracejadas infinitas recortadas ao frustum (`clip_line`), ponto-guia = cruz; dimensões (linhas de extensão, barras, texto em tela, sempre legível); textos com chamada.
- Fita (T): aresta/guia → guia paralela (offset perpendicular; `1` Enter = 1 m); ponto → ponto-guia; Option = só medir; redigitar ocioso ("Ajustar") move a última guia.
- Transferidor: gizmo no hover no plano de `inference.hover_plane` (azul/vermelho/verde), centro → linha de base → ângulo (15° perto do transferidor; `30` / `3:12`), Option = só medir.
- Cenário `scn_g` (partes nav, tape, protractor, dimension): verde. Prints: `doc/sketchup_mode/screens/g_orbita.png`, `g_fita_guia.png`, `g_transferidor.png`, `g_transferidor_face.png`, `g_cotas.png` (v1), `g_cotas_v2.png`, `g_cotas_orbita.png`.
- Dimensões v2 (pedido do coordenador): desenhadas em TELA e por cima da geometria (como o SketchUp): 2 linhas de extensão a partir dos pontos medidos passando a linha de cota, linha de cota, barras a 45° (2 pt) nas pontas, texto centrado na linha (alinhado à tela, fundo claro). A ferramenta usa o mesmo desenho na pré-visualização (`annotations.draw_dimension_2d`).
- Fora (P2/adiado): redimensionar o modelo com a Fita (digitar novo comprimento após medir); dimensões associadas à geometria (hoje ficam fixas onde foram criadas).

### P1 (bloco 4)
- Anterior/Próxima: `su.view_previous/su.view_next` (+ COMMAND `su.previous` no LTS).
- Janela de zoom (`su.zoom_window`, ferramenta; o operador `su.zoom_window` do menu Câmera ativa a ferramenta): arrastar ou clique-clique; o centro da janela vai ao centro e a janela enche a região.
- Posição da câmera (`su.position_camera`; menu `su.position_camera_cmd`): clique = olho a 1,676 m sobre o ponto olhando na horizontal; arrastar = olhar para o ponto da soltura; Medidas "Altura dos olhos" antes (próxima) ou depois (reposiciona, sem passo de undo).
- Texto (`su.text`): clique numa entidade (face → área, aresta → comprimento, ponto → coordenadas), mover, clicar; abre `su.text_edit` (diálogo) para editar. Texto de tela (vazio) = P2.
- Texto em 3D (`su.text3d`): diálogo `su.text3d_dialog` (texto, altura, extrudado, profundidade; Enter = "Posicionar") e clique → GRUPO novo (`document.create_group` + evento `"doc"`): faces coplanares fundidas, arestas internas `su_bridge`, laterais curvas `su_soft`; deitado no chão ou na face sob o cursor (letras de pé ao longo do declive).
- Cenas: `Scene.su_pages.pages` (desfazível); Bandeja ▸ Cenas (`ui/tray_scenes.py`: + − ⟳, lista, nome/descrição; alterna as abas); `su.scene_add/go/update/remove`, `su.toggle_scene_tabs` (Visualizar ▸ Abas de cena).
- Prints P1: `g_posicao_camera.png`, `g_cenas.png` (abas Cena 1/Cena 2 acima da viewport), `g_texto.png`, `g_texto3d.png`.
- Abas (`ui/scene_tabs.py`): com cenas, o HEADER aparece com a barra Primeiros passos (`header_toolbar.draw_toolbar` de D) e o TOOL_HEADER (logo acima da viewport) mostra as abas — a troca prevista na §4.1; sem cenas, igual ao layout de D. **Para D**: `scene_tabs` sobrepõe `VIEW3D_HT_header.draw` e `VIEW3D_HT_tool_header.draw` (ORDER 580, depois de `header_toolbar`), chamando a sua `draw_toolbar`.
- (D, integração 44b13e0) Conflito resolvido: `ui/header_toolbar.py` (D) passou a ser o ÚNICO dono de `VIEW3D_HT_header.draw` / `VIEW3D_HT_tool_header.draw` e da visibilidade do HEADER (`draw_header`, `draw_tool_header`, `sync_regions`). `scene_tabs.py` (G, edição mínima de D) ficou só com o gancho `tabs_visible(context)` + `draw_tabs(layout, context)`; `sync()` delega a `header_toolbar.sync_regions()`.
