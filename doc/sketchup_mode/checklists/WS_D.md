# WS_D — Agente D (Casca de UI e visual)

Legenda: `[ ]` pendente · `[~]` em andamento · `[x]` feito. Brief: `PLANO.md` §9.2-D (sub-checklist copiado abaixo; o agente D mantém este arquivo).

## Sub-checklist §9.2-D
1. [x] `prims.py` (congela em M-A) e `shaders` (tracejado, stipple)
2. [x] portar `draw_edges` → `edges.py` trocando o critério de ângulo por atributos (`su_bridge`/`su_hidden` nunca; `su_soft` só como silhueta); grupos/instâncias via `matrix_world`; cinza fora do contexto
3. [~] GN "SU_Display" só com a cópia de verso, aplicado nos eventos `"load"` **e `"doc"`** (S-B: grupos, instâncias, Raio X)
4. [x] portar céu, eixos, luz `.sl` (gravada em `bpy.app.tempdir`), view transform; seleção azul + stipple + bbox
5. [x] portar `apply_theme`/`apply_prefs` (armadilhas: `_rna_xml`, `regions.sidebars`, `show_edge_resize=True`, vram em try) + ícones recoloridos + `_dim`
6. [~] toolbar (grupos/flyouts §4.2), LTS (§4.3, G = Criar grupo), status bar (§3.4), Bandeja (§4.4) com `register_section`, menus (§4.5) com nomes do Apêndice A, menu do app, Configurações
7. [x] `hide.py` (inclui glTF Variants; 82 painéis da região UI, filhos primeiro)
8. [x] `build_all.sh` reprodutível a partir da sequência de passos do spike + `driver.py` (larguras) + `set_view`/`fit_lens`
9. [x] **lacunas visuais do `shell_v3` (CRITICA_R3_SKETCHUP §3), nesta ordem**:
   1. [x] ícones **originais** (PNG via `bpy.utils.previews` + patch do resolvedor, já provado) com as metáforas do SketchUp para: Linha (lápis vermelho), Apagar (borracha), Pintura (balde), Fita métrica (fita), Empurrar/puxar (caixa + seta vermelha para cima), Mover (cruz de 4 setas vermelhas), Girar (setas circulares vermelhas), Escala (caixa + seta diagonal), Transferidor, Aplicar zoom (lupa), Panorâmica (mão), Órbita (setas orbitais vermelhas); estilo plano navy/ciano + vermelho; os demais seguem recoloridos;
   2. [x] **luz P0**: recalibrar para frente ≈255, lateral ≈210, topo ≈160 (topo mais escuro) — sondas;
   3. [x] dica da status bar com "Option" (`modifiers.label()`);
   4. [x] reduzir a faixa vazia de ~20 pt da aba invisível (largura da aba no tema); se não der, desvio aceito;
   5. [x] caixa Medidas com borda fina clara, alinhada à direita (`wcol_text` outline);
   6. [x] ícones próprios de pino (cinza-claro) e ⓘ (preto fino);
   7. [x] Bandeja **toda fechada** na 1ª abertura (o spike abre Estilos expandido);
   8. [x] arestas pretas (0,0,0) ~1 pt conferidas pela sonda em tamanho real; **filtro por atributo**: diagonal desenhada pelo usuário numa face plana fica visível (AC-LIN-2 visual)
10. [ ] exportar sem modificadores (P1); Estilos aba Editar, Arestas traseiras, Raio X com cópia de verso desligada (P1)

## Aceite e comandos (referência)
- **Aceite**: sondas de cor (céu, horizonte, fundo, cromo, LTS ativo, Bandeja, status, face frente ≈255 / lateral ≈210 / topo ≈160, verso padrão, verso pintado sem tom azul, aresta preta, diagonal coplanar visível); passos 1, 2, 11, 12 da §12; ordem/separadores por `state_dump`; AC-PNT-1 (visual, com F); prints comparativos aprovados pelo líder.
- **Comandos**: `tools/sketchup_mode/build_all.sh` · `tools/sketchup_mode/run_gui.sh scn_d` · `tools/sketchup_mode/shot.sh none /tmp/d.png && tools/sketchup_mode/compare.sh /tmp/d.png doc/sketchup_mode/ref_images/sketchup_default_ui_2_v2027_empty_scene_large_toolset.png doc/sketchup_mode/screens/casca.png`

## Notas
- (de A0) O `userpref.blend` do template (`SketchUp_Mode/userpref.blend`) deve sair com **splash desligado**: com app template o `show_splash` vem dele (campos trocados por `BKE_blender_userdef_app_template_data_swap`), não do userpref do usuário. O harness já o desliga nos testes.

## Entrega 1 — porte do spike (fatia M-A)
- Módulos: `su/theme.py` (tema, prefs de runtime com backup/restore, luz `.sl` carregada do template), `su/icons.py` (resolvedor de ícones `bi.`/`.dat` recolorido/`png.`, variantes `_dim`), `su/core/style.py` (`Scene.su_style`, `apply`/`toggle`), `su/draw/{shaders,prims,sky,axes,edges,display_gn}.py`, `su/ui/{startup,hide,toolset,header_toolbar,statusbar,tray,tray_styles,topbar,dialogs}.py`, `su/ops/style_ops.py`; build `tools/sketchup_mode/{build_all.sh,build_icons.py,build_icons_png.py,build_userpref.py,build_startup.py}`; gerados `startup.blend`, `userpref.blend` (splash off), `icons/`, `studiolights/sketchup.sl`.
- **Arquivo novo de D**: `su/ui/startup.py` (passos do spike, um por tick, + câmera inicial); `driver_namespace["su_ui_ready"]` ao fim — **A**: o `su_ready` pode passar a esperar por ele.
- Luz calibrada (sondas do scn_d): frente 255, lateral 209, topo 159; verso no chão (101,110,116) = mesmo fator do topo (0,63 × #A4B2BB, como no SketchUp).
- Arestas por atributo (`su_bridge`/`su_hidden` nunca, `su_soft` só como silhueta); cinza fora do grupo aberto (`edit_context.current_object`).
- `display_gn.ensure` dá os materiais "Padrão"/"Padrão (verso)" só enquanto `core/materials.py` (F) não existe.
- Prefs de runtime de D (região sem sobreposição, mini eixos, status bar, tooltips Python) — **A**: deduplicar com `prefs.py` quando existir.
- Menus por existência: ids esperados de F/G (ajustar nos donos ou aqui): `su.select_all/select_none/select_invert/delete_selected/delete_guides/hide/unhide_*/make_group/make_component/close_group/reverse_faces/explode/cut/copy/paste/paste_in_place/intersect_faces/export`, `su.view_standard(view)`, `su.set_projection(persp)`, `su.view_previous/view_next/zoom_window/zoom_extents_cmd/position_camera_cmd`, `su.settings`, `su.model_info`, `su.shortcuts`, `su.open_full_blender`, `su.toggle_scene_tabs`.
- Bandeja: F/G registram `tray.register_section(10, "entity", "tray.entity", fn)`, `(20, "materials", "tray.materials", …)`, `(30, "components", "tray.components", …, 'P1')`, `(50, "scenes", "tray.scenes", …, 'P1')` (rótulos `tray.*` já registrados por D; hoje há marcadores de lugar).
- Testes: `tests/sketchup_mode/unit/test_d_shell.py` (12), `tests/sketchup_mode/gui/scn_d.py` (layout + sondas de cor). Print: `doc/sketchup_mode/screens/casca_v4.png`.

## Entrega 2 — lacunas visuais 9.1, 9.4, 9.5, 9.6
- 9.1: ícones ORIGINAIS vetoriais (`tools/sketchup_mode/build_icons_draw.py` → `icons/su.draw.<nome>.dat`, alça `draw.<nome>`): Selecionar, Linha, Apagar, Pintura, Fita métrica, Empurrar/puxar, Mover, Girar, Escala, Transferidor, Aplicar zoom, Panorâmica, Órbita (+ `_dim`). PNG via `bpy.utils.previews` foi descartado: o Blender desenha previews a 16 px na toolbar; o formato de geometria `.dat` (o mesmo dos ícones do Blender) escala sem perda. Enquadrados em 13–87 % como os ícones do Blender; cores pré-invertidas (tema claro).
- 9.4: a faixa da aba sumiu — o painel único da Bandeja limpa `PanelType.category` no 1º desenho (`self.bl_category = ""`); sem categoria, a região não reserva a faixa de abas (`region_panels_collect_categories`). `active_panel_category` passa a "UNSUPPORTED".
- 9.5: caixa Medidas branca com borda fina clara (`wcol_text.outline` 190,190,198), à direita (já do porte).
- 9.6: pino cinza-claro e ⓘ preto fino próprios (`draw.ui_pin`/`draw.ui_info`, margem maior para caber ao lado do texto de 11 pt).
- Arestas em monitor 1× (1080p externo): linha suavizada de 1 px saía cinza (102) → `lineSmooth` desligado quando `pixel_size < 1.5`; sonda preta (0,0,0) nos dois monitores.
- Seções P2 da Bandeja (Sombras, Suavizar arestas, Estruturador): o pedido do coordenador conflita com a §4.4 (decisão R2 #9: seções P2 não aparecem). Implementado atrás de `tray.SHOW_P2_SECTIONS` (padrão **False**, como no plano); com True aparecem como linhas acinzentadas.
- Print: `doc/sketchup_mode/screens/casca_v5.png`.

## Entrega 3 — Bandeja completa + seleção (item 4)
- Decisão do líder (sobrepõe §4.4): `tray.SHOW_P2_SECTIONS = True` — Bandeja na ordem do SketchUp: Informações da entidade, Materiais, Componentes, Estilos, **Sombras**, Cenas, **Suavizar arestas**, **Estruturador** (P2 = linhas acinzentadas; "Em breve." só no corpo aberto). Etiquetas nunca.
- `su/draw/selection_draw.py` (camada SELECTION=30), lendo `core/selection` (B): face selecionada = retícula de pontos azuis (shader stipple, Metal OK), aresta selecionada = azul #0000FF 1 pt por cima da preta, objeto/grupo selecionado = caixa envolvente azul (objeto + descendentes, nos eixos do objeto), grupo aberto = caixa tracejada cinza. Redesenho no evento "selection".
- scn_d: sondas de seleção (retícula azul na face, aresta azul 0,0,255). Print: `doc/sketchup_mode/screens/casca_v6.png`.
