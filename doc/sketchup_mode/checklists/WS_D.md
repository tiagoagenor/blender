# WS_D — Agente D (Casca de UI e visual)

Legenda: `[ ]` pendente · `[~]` em andamento · `[x]` feito. Brief: `PLANO.md` §9.2-D (sub-checklist copiado abaixo; o agente D mantém este arquivo).

## Sub-checklist §9.2-D
1. [ ] `prims.py` (congela em M-A) e `shaders` (tracejado, stipple)
2. [ ] portar `draw_edges` → `edges.py` trocando o critério de ângulo por atributos (`su_bridge`/`su_hidden` nunca; `su_soft` só como silhueta); grupos/instâncias via `matrix_world`; cinza fora do contexto
3. [ ] GN "SU_Display" só com a cópia de verso, aplicado nos eventos `"load"` **e `"doc"`** (S-B: grupos, instâncias, Raio X)
4. [ ] portar céu, eixos, luz `.sl` (gravada em `bpy.app.tempdir`), view transform; seleção azul + stipple + bbox
5. [ ] portar `apply_theme`/`apply_prefs` (armadilhas: `_rna_xml`, `regions.sidebars`, `show_edge_resize=True`, vram em try) + ícones recoloridos + `_dim`
6. [ ] toolbar (grupos/flyouts §4.2), LTS (§4.3, G = Criar grupo), status bar (§3.4), Bandeja (§4.4) com `register_section`, menus (§4.5) com nomes do Apêndice A, menu do app, Configurações
7. [ ] `hide.py` (inclui glTF Variants; 82 painéis da região UI, filhos primeiro)
8. [ ] `build_all.sh` reprodutível a partir da sequência de passos do spike + `driver.py` (larguras) + `set_view`/`fit_lens`
9. [ ] **lacunas visuais do `shell_v3` (CRITICA_R3_SKETCHUP §3), nesta ordem**:
   1. ícones **originais** (PNG via `bpy.utils.previews` + patch do resolvedor, já provado) com as metáforas do SketchUp para: Linha (lápis vermelho), Apagar (borracha), Pintura (balde), Fita métrica (fita), Empurrar/puxar (caixa + seta vermelha para cima), Mover (cruz de 4 setas vermelhas), Girar (setas circulares vermelhas), Escala (caixa + seta diagonal), Transferidor, Aplicar zoom (lupa), Panorâmica (mão), Órbita (setas orbitais vermelhas); estilo plano navy/ciano + vermelho; os demais seguem recoloridos;
   2. **luz P0**: recalibrar para frente ≈255, lateral ≈210, topo ≈160 (topo mais escuro) — sondas;
   3. dica da status bar com "Option" (`modifiers.label()`);
   4. reduzir a faixa vazia de ~20 pt da aba invisível (largura da aba no tema); se não der, desvio aceito;
   5. caixa Medidas com borda fina clara, alinhada à direita (`wcol_text` outline);
   6. ícones próprios de pino (cinza-claro) e ⓘ (preto fino);
   7. Bandeja **toda fechada** na 1ª abertura (o spike abre Estilos expandido);
   8. arestas pretas (0,0,0) ~1 pt conferidas pela sonda em tamanho real; **filtro por atributo**: diagonal desenhada pelo usuário numa face plana fica visível (AC-LIN-2 visual)
10. [ ] exportar sem modificadores (P1); Estilos aba Editar, Arestas traseiras, Raio X com cópia de verso desligada (P1)

## Aceite e comandos (referência)
- **Aceite**: sondas de cor (céu, horizonte, fundo, cromo, LTS ativo, Bandeja, status, face frente ≈255 / lateral ≈210 / topo ≈160, verso padrão, verso pintado sem tom azul, aresta preta, diagonal coplanar visível); passos 1, 2, 11, 12 da §12; ordem/separadores por `state_dump`; AC-PNT-1 (visual, com F); prints comparativos aprovados pelo líder.
- **Comandos**: `tools/sketchup_mode/build_all.sh` · `tools/sketchup_mode/run_gui.sh scn_d` · `tools/sketchup_mode/shot.sh none /tmp/d.png && tools/sketchup_mode/compare.sh /tmp/d.png doc/sketchup_mode/ref_images/sketchup_default_ui_2_v2027_empty_scene_large_toolset.png doc/sketchup_mode/screens/casca.png`

## Notas
- (de A0) O `userpref.blend` do template (`SketchUp_Mode/userpref.blend`) deve sair com **splash desligado**: com app template o `show_splash` vem dele (campos trocados por `BKE_blender_userdef_app_template_data_swap`), não do userpref do usuário. O harness já o desliga nos testes.
