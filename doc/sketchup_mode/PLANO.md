# PLANO FINAL — Modo SketchUp para Blender (App Template em Python)

Versão: **final** (v4, 2026-11-08; aprovado com GO pelos dois críticos na rodada 3) · Branch: `sketchup-mode` · Runtime: **Blender 5.2.2 LTS** (`/Applications/Blender.app`, macOS arm64, Metal, Retina `pixel_size=2`, Python 3.13)
Base: `RESEARCH_SKETCHUP.md`, `RESEARCH_BLENDER_API.md`, `CRITICA_R1_*.md`, `CRITICA_R2_*.md`, `CRITICA_R3_*.md`, `CHECKLIST.md`, `ref_images/`, **spike visual** — achados em `VISUAL_SPIKE_FINDINGS.md`, código reutilizável em `doc/sketchup_mode/visual_spike/` (`tpl/startup/bl_app_templates_system/SketchUpSpike/__init__.py` ~770 linhas, `icons/` 117 `.dat` recoloridos, `tools/build_icons.py`, `tools/build_style_thumb.py`, `run.sh`, `driver.py`, `shots/shell_v3.png` — já visto e aprovado pelo usuário como ponto de partida).
Prioridades: **P0** obrigatório na v1 · **P1** entra na v1 depois dos P0 · **P2** adiado (botão desabilitado na posição, quando houver).
Regra de desempate (decisão do usuário): **funcionar primeiro; a implementação correta mais simples vence; performance depois** (§7).
Convenção: texto pt-BR, identificadores em inglês. **[decisão]** = decidido; mudanças passam pelo integrador (agente A).

---

## Histórico de revisões

| Versão | Resumo |
|---|---|
| v1 | Plano inicial (8 workstreams, Fase 0 com stubs, arestas em Python, ScreenGrid). |
| v2 | Crítica R1: execução enxuta (fatia + 6 agentes + integrador), arestas/versos por GN, seleção em sets, keymap por lista de permissão no `Window`, nomes pt-BR oficiais, novas prioridades; **decisão do usuário: performance adiada** (orçamentos viraram P2). |
| **final** | Crítica R3 (GO dos dois críticos): infraestrutura de execução paralela (worktree por agente, `lockf`, passo A0, isolamento com `BLENDER_USER_RESOURCES` + `TMPDIR` + `userpref.blend` semeado, evento `"doc"`, `run_unit.sh` com ambiente e `sys.path`), escopo da Viewport corrigido, iluminação 255/210/160 em P0, dica com Option, lacunas visuais ordenadas para D, **teste final de aceite de 15 passos (§12)** e sequência de lançamento (§9.6). |
| v3 | Crítica R2 + decisões do líder: captura modal das Medidas, `su.tool_event` só PRESS/RELEASE (Ctrl passa), seleção preservada (Mover/cópia/undo), superfície suave como entidade, lado da Pintura por `dot(raio, normal original)`, slot 1 = verso, `rebuild_face` por CDT, BVH congelada removida, load_post por eventos, props por dono, fatia vertical = integração de entregas pequenas de A–E, aceites de "feel", briefs por agente, comparação lado a lado mantida, **achados do spike visual: os agentes partem do código do spike** (arestas pelo renderizador Python do spike com silhuetas; GN só para a cópia de verso; toolbar no TOOL_HEADER; janela maximizada nos testes). |

### Changelog final (rodada 3)

**Crítica R3 Blender (CRITICA_R3_BLENDER.md §4)**

| # | Correção | Decisão | Onde |
|---|---|---|---|
| B1/4.2 | `flock` não existe no macOS → `lockf -k -t 1800` | Aceito | §8.2, §9.0 |
| B2/4.1 | Worktree + branch por agente; staging aponta para o worktree; merges serializados sob lock | Aceito, adaptado: o coordenador lança cada agente com `isolation: "worktree"` (worktree próprio de `sketchup-mode`); o agente comita na branch do worktree; só o integrador/coordenador faz merge em `sketchup-mode` sob `lockf /tmp/su_merge.lock` | §9.0, §9.6 |
| B3/4.4 | Passo **A0** (esqueleto) com merge antes de B–E | Aceito | §9.1 |
| B4/4.1 | `BLENDER_USER_RESOURCES` + `TMPDIR` por agente + `userpref.blend` semeado com splash off; scripts abortam fora de `/private/tmp/su_stage_*` | Aceito | §9.0, §8 |
| B5/4.5 | Evento `"doc"` para objetos-documento novos (verso GN + slots) | Aceito | §2.4, §3.10 |
| B6/4.3 | `run_unit.sh` com ambiente e template no `sys.path` | Aceito | §8.1 |
| 4.6 | `su_undo_serial` nos nomes reservados | Aceito | §2.3 |

**Crítica R3 SketchUp (CRITICA_R3_SKETCHUP.md)**

| # | Item | Decisão | Onde |
|---|---|---|---|
| §2 | Linha "Viewport" da §1.2 dizia "arestas e versos (GN)" | Corrigido: arestas = renderizador Python por atributo; GN = só verso | §1.2 |
| §2 | Filtro de arestas **por atributo** (linhas coplanares do usuário visíveis) | Aceito; AC-LIN-2 ganha verificação visual | §3.3, §6.2, §9.2-D |
| §3.2 | Luz invertida (topo mais claro) → calibrar 255/210/160 com topo mais escuro | Aceito, **P0** | §1.2, §3.3, §9.2-D |
| §3.3 | Dica com "Option" no Mac | Aceito (`modifiers.label()`) | §3.4, §9.2-D/F |
| §3.1–3.8 | Lacunas visuais ordenadas (ícones originais, luz, dica, faixa da aba, borda da caixa Medidas, ícones pino/ⓘ, Bandeja fechada, arestas pretas) | Aceito, atribuídas ao agente D na ordem dada | §9.2-D |
| §4 | Teste do primeiro dia (15 passos) | Aceito como **teste final de aceite** | §12 |

### Changelog v3

**Crítica R2 SketchUp (CRITICA_R2_SKETCHUP.md §4)**

| # | Item | Decisão | Onde |
|---|---|---|---|
| 1 | RET/NUMPAD_ENTER/BACK_SPACE/ESC no `Window`, `su.vcb_key` antes de Excluir/cancelar | Aceito (+ captura modal da R2 Blender) | §3.5, §5.1 |
| 2 | Ferramentas ignoram LMB com Ctrl; pivô da órbita no PRESS | Aceito | §3.6, §5.2, §6.3 |
| 3 | Seleção preservada após Mover/Girar/Escala, cópia vira seleção, undo restaura | Aceito | §3.8 (serial de undo) |
| 4 | Superfície suave = entidade (selecionar, pintar, pré-realce; Empurrar/puxar não age) | Aceito (P0) | §3.1, §6 |
| 5 | Lado da Pintura por `dot(raio, normal)` | Aceito | §2.4 `spatial.ray_cast`, §6.1 |
| 6 | G e botão Criar componente coerentes | Aceito: ambos fazem "Criar grupo" até o P1, com dica | §4.3, §5.3 |
| 7 | Aceite de dobra corrigido; restrição de face = rejeitar só o que deixa face não plana | Aceito | §6.1 AC-MOV-5..7 |
| 8 | Aceites de "feel" (porta, encaixe, cura, seleção, zoom/pivô, ⌫) | Aceito | §6 (IDs AC-*) |
| 9 | Bandeja sem seções P2; aba vertical como desvio aceito | Aceito; spike mostrou que o tema esconde a aba (§4.4) — desvio só se o tema falhar | §1.1, §4.4 |
| 10 | Opção "inverter zoom do trackpad"; roteiro confere direção | Aceito | §5.2, §8.4 |

**Crítica R2 Blender (CRITICA_R2_BLENDER.md §5)**

| # | Item | Decisão | Onde |
|---|---|---|---|
| 1 | `su.vcb_capture` modal de janela | Aceito (decisão do líder) | §3.5 |
| 2 | Poll: janela principal + área VIEW_3D/STATUSBAR/TOPBAR | Aceito | §5.1 |
| 3 | `su.tool_event` só PRESS/RELEASE; PASS para CLICK/CLICK_DRAG/Ctrl | Aceito | §3.6 |
| 4 | Normal e lado sempre da face original (`idx % n`) | Aceito | §2.4, §3.1 |
| 5 | Slot 1 = "Padrão (verso)", `su_back_mat` padrão 1 | Aceito | §3.1 |
| 6 | Exportar/Interseccionar sem modificadores; Raio X desliga cópia | Aceito | §3.3, §6.1 |
| 7 | GN calcula visibilidade (sem `su_visible` no write) | Aceito em parte e depois **substituído pelo spike visual**: `su_visible` sai do `write` ✔, mas as arestas são do renderizador Python do spike (filtra por atributos e desenha silhuetas de superfícies suaves, que o GN não consegue); GN fica só com a cópia de verso | §3.3 |
| 8 | `rebuild_face` = `delaunay_2d_cdt(output_type=5)` | Aceito | §3.1 |
| 9 | load_post por eventos, cada dono garante o seu | Aceito | §3.10 |
| 10 | B dono de document/geom desde o dia 0; fatia = integração de entregas mínimas | Aceito | §9 |
| 11 | Remover BVH congelada (relançar raio) | Aceito | §3.2 |
| 12 | Props registradas pelo dono (`Scene.su_<grupo>`), sem finalizadores (exceto keymap) | Aceito | §2.3 |
| 13 | Bandeja com `Panel`s nativos | **Rejeitado** com evidência: o spike visual implementou a Bandeja como **um** painel `HIDE_HEADER` com linhas em caixa (chevron + nome + ✕), sem a alça de arrastar do Blender, idêntica ao SketchUp (`shell_v3.png`), em ~40 linhas. Mantido, com `tray.register_section` no contrato; "lembrar entre arquivos" = P2 | §4.4 |
| 14 | Ids canônicos, prefixos i18n, semântica de eventos | Aceito | §2.4, Apêndice A |
| 15 | Windows → P2; `compare.py` lado a lado → P2; sem `display_fallback.py` | Parcial: Windows P2 ✔, sem fallback ✔; **comparação lado a lado mantida** (decisão do líder: o usuário pediu prints comparando com o SketchUp e acompanha pelo celular) — versão simples com `sips` | §8.3 |

**Spike visual (`VISUAL_SPIKE_FINDINGS.md`, código em `doc/sketchup_mode/visual_spike/`) — decisão: todo agente PARTE desse código, não reescreve.**

| Achado do spike | Decisão v3 | Onde |
|---|---|---|
| Shell completo e aprovado visualmente (`shell_v3.png`): menus pt-BR, Primeiros passos com grupos, LTS 2 colunas com célula vazia, Bandeja sem alça, status + Medidas, céu, eixos, luz, ícones | D porta o `__init__.py` do spike para os módulos de D; A porta `run.sh`/`driver.py` para o harness | §9 |
| **Arestas**: renderizador Python (numpy, cache por malha, polygon offset `win[2][3] -= win[2][3]*-0.0025`) com **arestas de perfil (silhueta) de superfícies suaves** — o overlay de wireframe ficou falhado e mostrava facetas | **Revisa a v2/R2**: arestas = renderizador do spike (`draw/edges.py`, D), filtrando por atributos (`su_bridge`, `su_hidden`; `su_soft` só como silhueta) em vez do ângulo de 20°. O GN não sabe a câmera e não desenharia a silhueta do cilindro. Performance de batches grandes fica para a Fase de performance | §3.3 |
| Versos pelo overlay de orientação (só cor padrão) | Mantém-se o **GN só para a cópia invertida de verso** (verificado na R2: verso pintado sem tom azul) | §3.3 |
| Toolbar no **TOOL_HEADER** com HEADER escondido (verificado) | Porta assim; quando as abas de cenas (P1) chegarem, a mesma `draw` passa para o HEADER e as abas vão para o TOOL_HEADER (as duas ordens verificadas na R1) | §4.1 |
| LTS: `_tools['OBJECT']` com `ToolDef`s + `None`; `_tools[None]=[]`; `tool_fallback_id='su.select'`; 2 colunas forçadas por patch de `_layout_generator_detect_from_region`; número ímpar no grupo = célula vazia | Adotado; as ferramentas reais continuam com `register_tool` (keymap/gizmo) e o `catalog` reordena `_tools['OBJECT']` com os `_bl_tool` | §4.3 |
| Aba única: `ui.wcol_tab` (inner, inner_sel, outline, text, text_sel) = cromo → invisível (sobra faixa de ~20 pt) | Adotado; aba visível deixa de ser desvio | §4.4 |
| Tema: `import _rna_xml` (não `rna_xml`); fundo de TOOLS/UI = `theme.regions.sidebars.back/tab_back` (`ThemeSpaceGradient.button` não existe); `wcol_toolbar_item.inner_sel=#D6E8FA`, `outline_sel=#0078D7`; `wcol_box` faixas #E0E1E9 sem arredondamento | Adotado (valores do spike) | §4.6 |
| Prefs: **`apps.show_edge_resize` deve ficar True** (False impede o arrasto das bordas); `show_statusbar_vram` é somente leitura (setattr em try); omitir `template_reports_banner` (faixa amarela) | Adotado | §4.7, §5.2, §3.4 |
| Luz: `.sl` própria (`light_ambient=0.42`, só `solid_lights[1]`, dir (-0.35,0.45,0.82), difusa 0,62, especular 0) → 243/222/185; `.sl` gravado em `bpy.app.tempdir` | Adotado como ponto de partida (calibração fina para 255/210/160 = P1); `light_ambient` entra no backup de prefs | §3.3, §5.2 |
| Isolamento: `BLENDER_USER_CONFIG` **não** redireciona DATAFILES → definir também `BLENDER_USER_DATAFILES` e `BLENDER_USER_EXTENSIONS` | Adotado em `dev_env.sh`/`run_gui.sh` | §9.0 |
| `--window-geometry`/`-p` **ignorado** neste Mac: janela maximizada 1512×854 pt → prints 3024×1708 | Harness não depende do tamanho; coordenadas sempre das regiões; `-p` passado mas não confiado | §8.2 |
| Larguras por arrasto simulado (TOOLS 193 px ≈ 96 pt, UI 603 px) | Usado no `build_startup.py` | §4.7 |
| Câmera inicial: FOV 35° vertical, yaw 33° de +Y para −X, pitch 6,6° para baixo, origem em NDC (−0,26, −0,39), distância 11,5 m; lente ajustada por `window_matrix[1][1]` após um redesenho | Adotado | §4.7 |
| Céu: linear do horizonte até a borda superior (cor do topo depende do pitch) | Adotado (simples); calibração por elevação = P2 | §3.3 |
| Eixo negativo pontilhado com espaçamento constante em tela (amostras projetadas, 4,5 px, `POINT_UNIFORM_COLOR`), oclusão mantida | Adotado | §3.3 |
| `bm.faces.new()` nasce com normal zero até `normal_update()` | Regra no kernel B | §3.1 |
| Ícones: `.dat` recoloridos com pré-inversão HSL; ícones SVG embutidos via `icon=` ficam na cor `wcol_*.text` | Adotado | §4.6 |

---

## 1. Objetivo e escopo

### 1.1 Objetivo
`Blender --app-template SketchUp_Mode` (ou *Arquivo › Novo › SketchUp Mode*) abre uma aplicação que **parece e se comporta como o SketchUp 2027 no Mac**: barra "Primeiros passos", Conjunto extenso de ferramentas (2 colunas) à esquerda, Bandeja padrão à direita, barra de status com dica + **Medidas** digitável com o mouse em qualquer lugar, céu com horizonte, faces brancas / verso azul-acinzentado / arestas pretas, inferência colorida, ferramentas clique-mover-clique, mouse e trackpad do SketchUp.

Requisitos do usuário: R1 ferramentas/atalhos; R2 mouse igual; R3 cores + céu; R4 posições idênticas; R5 **sem Etiquetas/Tags**; R6 funcionar primeiro (performance depois); R7 pt-BR; R8 prints comparando com o SketchUp.

Desvios aceitos: barra de status de largura total (estilo 2023); menus dentro da janela; aba vertical "Bandeja padrão" **apenas** se o truque de tema não a esconder.

### 1.2 Escopo

**P0 fixo (usuário):** Selecionar, Mover (+copiar), Girar, Escala, Apagar, Pintura, Órbita, Panorâmica, Aplicar zoom, Extensões de zoom, Fita métrica (+guias), Transferidor (+guias angulares), Dimensões; Linha, Arco de dois pontos, Retângulo, Círculo, Polígono, Empurrar/puxar, Equidistância, Siga-me.

| Área | P0 | P1 | P2 |
|---|---|---|---|
| Casca | template + `startup/userpref.blend` gerados; menu do app + menus; Primeiros passos (grupos, flyouts); LTS exato; Bandeja; status + Medidas; tema; ícones | abas de cenas | abas de modelo, cursores desenhados, figura de escala, inglês completo, lembrar Bandeja entre arquivos, modo de modificadores Windows |
| Viewport | céu; arestas pelo renderizador Python **filtradas por atributo** (com silhuetas de superfícies suaves); versos pela cópia GN; eixos; seleção azul; **iluminação calibrada 255/210/160 (topo visto de cima é o mais escuro)** | Estilos (aba Editar), Arestas traseiras (K), Raio X | perfis, sombras, neblina, esmaecimento fora do contexto |
| Navegação | MMB órbita (pivô sob o cursor), Shift+MMB pan, roda no cursor, duplo clique MMB, trackpad Mac, Ctrl+clique = menu | Anterior/Próxima, Janela de zoom | L+M pan, órbita sem gravidade, Percorrer, Olhar ao redor |
| Inferência / Medidas | pontos, eixos, paralela/perpendicular, do ponto (2 pontos, 0,3 s), Shift/setas, histerese, dicas, unidades, decimal do sistema, captura modal | tangente, semicírculo, quadrado/seção áurea, `~` | — |
| Modelo | geometria pegajosa, furos (CDT), curvas e superfícies suaves como entidade, dobra automática, grupos aninhados, Ocultar/Reexibir, Explodir, seleção preservada | componentes, edição de curva, Interseccionar faces | plano de seção |
| Ferramentas | lista P0 + Criar grupo | Arco (centro), Virar, Criar componente, Texto com chamada, Texto em 3D, Posição da câmera, Janela de zoom, Anterior, Pesquisar | Lasso, Desenho à mão livre, Retângulo girado, Arco de três pontos, Pizza, Eixos, Plano de seção, Percorrer, Olhar ao redor, Campo de visão (ferramenta), texto de tela, Dimensões de raio/diâmetro |
| Bandeja | Informações da entidade (mínimo), Materiais (cores) | Info completa, texturas, Componentes, Estilos, Cenas | Sombras, Suavizar arestas, Estruturador. Instrutor cortado. **Etiquetas nunca.** |
| Arquivos | `.blend` | exportar OBJ/glTF/STL (sem modificadores) | importar |

Fora de escopo: `.skp`, LayOut, Warehouse, Comentários, conta Trimble, Procedimentos, Ruby, C/C++.

---

## 2. Diretórios, módulos e contratos

### 2.1 Nome
Pasta `SketchUp_Mode` em `scripts/startup/bl_app_templates_system/` → "SketchUp Mode". Nome do produto só em `constants.PRODUCT_NAME`. Nenhum asset da Trimble (ícones = recoloração dos ícones do Blender + desenhos próprios; textos próprios).

### 2.2 Árvore e donos

```
scripts/startup/bl_app_templates_system/SketchUp_Mode/
├── __init__.py                                   A
├── startup.blend  userpref.blend                 D  (GERADOS, commitados)
├── presets/keyconfig/SketchUp_Mode.py            A
├── icons/ (*.dat recoloridos, *.png, *_dim)       D  (GERADOS)
├── studiolights/sketchup.sl                      D
└── su/
    ├── __init__.py constants.py colors.py registry.py events.py settings.py i18n.py
    │   modifiers.py perf.py session.py testing.py keymap.py prefs.py          A
    ├── theme.py icons.py                                                      D
    ├── core/ state.py undo.py viewutil.py                                     A
    │         document.py geom.py entities.py selection.py edit_context.py     B
    │         spatial.py inference.py vcb.py units.py                          C
    │         geom_extrude.py                                                  E
    │         geom_transform.py materials.py                                   F
    │         guides.py camera.py                                              G
    │         style.py                                                         D
    ├── draw/ handlers.py                                                      A
    │         prims.py shaders.py sky.py axes.py edges.py selection_draw.py display_gn.py   D
    │         inference_draw.py tooltips.py                                    C
    │         annotations.py                                                   G
    ├── tools/ base.py catalog.py coming_soon.py                               A
    │          line.py                                                         A (fatia) → E após M-A
    │          rectangle.py circle.py polygon.py arcs.py pushpull.py offset.py followme.py   E
    │          select.py eraser.py paint.py move.py rotate.py scale.py flip.py  F
    │          tape.py protractor.py dimension.py text.py nav.py camera_tools.py   G
    ├── ops/  tool_ops.py (A) · edit_ops.py (F) · view_ops.py (G) · style_ops.py file_ops.py (D)
    └── ui/   topbar.py header_toolbar.py toolset.py statusbar.py tray.py hide.py dialogs.py tray_styles.py (D)
              context_menu.py tray_entity_info.py tray_materials.py tray_components.py (F)
              scene_tabs.py tray_scenes.py (G)

tools/sketchup_mode/  dev_env.sh run.sh run_unit.sh run_gui.sh shot.sh compare.sh compose.py (A)
                      build_all.sh build_startup.py build_userpref.py build_icons.py (D)
tests/sketchup_mode/  unit/run.py unit/fakes.py gui/harness.py gui/scn_smoke.py expected/colors.json (A)
                      unit/test_<dono>_*.py · gui/scn_<dono>.py (cada dono)
doc/sketchup_mode/checklists/WS_A.md … WS_G.md  (cada agente mantém o seu)
doc/sketchup_mode/visual_spike/  CÓDIGO-FONTE DE PARTIDA (somente leitura; portar, não editar)
```
Única troca de dono: `tools/line.py` (A escreve na fatia, E assume após M-A, registrado no checklist). `document.py`/`geom.py` são de **B desde o dia 0**.

### 2.3 Regras anti-conflito
1. **Auto-descoberta**: `su/__init__.py` importa `su/**`, ordena por `ORDER` (0–99 plataforma, 100–199 core, 200–299 draw, 300–399 tools, 400–499 ops, 500–599 ui) e chama `register()`. Único finalizador: `keymap.finalize()` (lê `ToolMeta.shortcut` e `KEYMAP` dos módulos).
2. **Ferramentas se autodeclaram** com `@tool(ToolMeta(...))`; `catalog.py` só tem listas de ids de layout. Id sem registro → botão desabilitado ("Em breve").
3. **Props pelo dono**: cada dono registra `bpy.types.Scene.su_<grupo> = PointerProperty(type=...)` (ou `Object.su_<grupo>`, `WindowManager.su_<grupo>`) no próprio `register()` e remove no `unregister()`. Nomes reservados: `su_undo_serial`(A, Scene, IntProperty) `su_units`(C) `su_style`(D) `su_guides`(G) `su_pages`(G) `su_doc`(B, Object) `su_mat`(F, Material) `su_vcb`(A, WM) `su_tray`(D, WM) `su_paint`(F, WM).
4. **Menus por existência**: item aparece só se o operador existe; toolbar/LTS mostram desabilitado.
5. **Cada ferramenta desenha a si mesma** (`draw_3d/draw_2d`) com `draw/prims.py`.
6. **Sem stubs em arquivo alheio**; consumidores usam a entrega mínima real do dono.
7. **i18n por dono**, prefixos obrigatórios: `tool.<id>.*` (dono da ferramenta), `ui.*`/`menu.*`/`tray.*` (D), `vcb.*`/`inf.*`/`units.*` (C), `edit.*`/`mat.*` (F), `view.*`/`guide.*`/`cam.*` (G), `undo.*`/`app.*` (A). `register_strings` falha em chave duplicada.

### 2.4 Contratos

Congelados ao fim da fatia (M-A): `base.py` (`BaseTool`, `Ev`, `ToolMeta`, semântica de eventos), `state.Inference`, `document.Document`, `selection`, `prims`, `spatial.ray_cast`. Mudança depois disso = PR revisado por A.

#### A — Plataforma
```python
# constants.py
PRODUCT_NAME="SketchUp Mode"; TEMPLATE_ID="SketchUp_Mode"; GEOM_TOL=1e-5
SNAP_PX_POINT=12; SNAP_PX_EDGE=7; SNAP_PX_AXIS=9; SNAP_PX_GUIDE=7; SNAP_RELEASE_FACTOR=1.5   # px lógicos → ui_px()
HOVER_ACQUIRE_S=0.3; MAX_REF_POINTS=2; DRAG_THRESHOLD_PX=6; DOUBLE_CLICK_S=0.35; MULTI_CLICK_DIST_PX=4
CIRCLE_SIDES=24; POLYGON_SIDES=6; ARC_SEGMENTS=12; ANGLE_SNAP_DEG=15.0; DEFAULT_FOV_V_DEG=35.0
SLOT_DEFAULT_FRONT=0; SLOT_DEFAULT_BACK=1
# colors.py — sRGB 0–255 (lista igual à v2): SKY HORIZON BACKGROUND GROUND FACE_FRONT FACE_BACK EDGE SELECTION
#   AXIS_X/Y/Z GUIDE INF_* TOOLTIP_* UI_* ICON_* SCALE_*; rgba(c,a)->sRGB 0–1; lin(c)->linear (materiais)
# registry.py
def register_classes(classes); def unregister_classes(classes)
def override(owner, attr, new); def restore_all()
def add_handler(list_name, fn); def remove_all_handlers(); def deferred(fn, delay=0.0)
# events.py — tópicos: "load" "doc"(doc_key) "geometry"(doc_key) "selection" "tool"(old,new) "undo"(direction) "style"
#   "doc": emitido ao criar um objeto-documento (B: create_group, Explodir, Document de objeto novo/importado;
#          F: cópia de grupo/componente; G: Texto em 3D). Assinantes: D display_gn.ensure(obj), F materials.ensure_slots(obj).
#   "load" continua cobrindo os objetos já existentes no arquivo.
def subscribe(topic, fn, order=500); def emit(topic, **kw)
# settings.py (JSON mínimo): language, trackpad_mode('sketchup'|'blender'), trackpad_invert_zoom(bool), click_style, continue_line
def get(key); def set(key, value)
# i18n.py
def register_strings(table: dict[str, dict[str, str]]); def t(key, **fmt) -> str
# modifiers.py (Mac)
def is_copy(ev)->bool  # Option (ev.alt)
def is_alt_action(ev)->bool  # Cmd (ev.oskey)
def label(name)->str
# perf.py
def span(name); def error(msg); def errors()->int
# session.py
def on_load_post()  # events.emit("load") (assinantes: B raiz, F materiais slots 0/1, D GN+estilo, A invariantes);
                    # depois: objeto ativo=None, ferramenta su.select, 1× undo.push("undo.init") se algo mudou
def on_depsgraph_update(dg)  # retorna cedo para ids da última escrita nossa; senão document.invalidate
# testing.py
def dispatch(ev, tool_id=None, inf=None) -> Result; def hover(xy) -> Inference; def set_clock(fn)
def state_dump() -> dict    # ferramenta, hint, vcb, inferência, seleção, contexto, ordem/separadores da toolbar e do LTS
def doc_stats(doc_key=None) -> dict   # contagens, faces lógicas, superfícies, áreas, bbox, faces não planas
```
```python
# core/state.py
@dataclass
class Inference:
    kind: str                      # NONE ENDPOINT MIDPOINT ON_EDGE ON_FACE INTERSECTION CENTER ORIGIN GUIDE_POINT ON_GUIDE FREE
    point: Vector
    linear: str = ''               # '' AXIS_X AXIS_Y AXIS_Z PARALLEL PERPENDICULAR PERP_FACE FROM_POINT TANGENT
    direction: Vector|None=None; ref_point: Vector|None=None; ref_edge: tuple|None=None
    normal: Vector|None=None       # SEMPRE da face original (idx % n_orig)
    side: int = 0                  # +1 frente vista, -1 verso visto (sign(-dot(ray_dir, normal)))
    plane: tuple|None=None; doc_key: str=''; elem: tuple[str,int]|None=None
    obj_name: str=''; in_context: str=''; locked: bool=False; tooltip_key: str=''; screen: tuple=(0.0,0.0)
@dataclass
class Locks: axis: str=''; shift: Inference|None=None; plane: tuple|None=None
@dataclass
class LastAction: tool_id: str; schema: str; reapply: Callable[[list], bool]
class State:
    inference; locks; hint_key; hint_fmt; vcb_label_key; vcb_value; vcb_buffer; vcb_error; last_action; ref_points
    def set_hint(self, key, **fmt); def set_vcb(self, label_key, value)
    def redraw_viewport(self, region=None); def redraw_statusbar(self)   # workspace.status_text_set(None)
STATE: State
# core/undo.py
def push(message_key: str) -> None
    # incrementa scene.su_undo_serial (int, no memfile), guarda selection.snapshot() em _SEL[serial], ed.undo_push
def before_change() -> None     # chamado por Document.write antes de mudar: _SEL[serial_atual] = seleção atual (pré-operação)
# undo_post/redo_post: lê scene.su_undo_serial restaurado → selection.restore(_SEL.get(serial)); events.emit("undo")
# core/viewutil.py — coordenadas de REGIÃO em pixels FÍSICOS
def mouse_ray(region, rv3d, xy); def project(region, rv3d, co); def ui_px(v); def line_px(v); def pixel_size_at(region, rv3d, co)
```
```python
# tools/base.py
class Result(Enum): IDLE=0; RUNNING=1; PASS=2
@dataclass(frozen=True)
class ToolMeta:
    id: str; label_key: str; icon: str; kind: str='TOOL'   # 'TOOL' | 'COMMAND' | 'NAV'
    operator: str=''          # COMMAND: operador executado; NAV: operador do LEFTMOUSE (view3d.rotate etc.)
    shortcut: str=''; cursor: str='DEFAULT'; vcb_label_key: str=''; vcb_schema: str=''
    priority: str='P0'; enabled: bool=True; search_synonyms: tuple=()
@dataclass
class Ev:
    type: str; value: str; x: int; y: int; unicode: str=''; shift: bool=False; copy: bool=False
    alt_action: bool=False; ctrl: bool=False; clicks: int=1; is_drag_release: bool=False; t: float=0.0
    press_x: int=0; press_y: int=0
class BaseTool:
    meta: ClassVar[ToolMeta]; inference_flags: ClassVar[frozenset]
    def activate(self, tc); def deactivate(self, tc); def hover(self, tc, inf)
    def press(self, tc, ev, inf)->Result; def release(self, tc, ev, inf)->Result; def move(self, tc, ev, inf)->Result
    def key(self, tc, ev)->Result; def vcb(self, tc, values)->Result; def cancel(self, tc)
    def query_ctx(self, tc, xy)->QueryCtx; def draw_3d(self, dc); def draw_2d(self, dc); def update_status(self)
def tool(meta: ToolMeta); def active_tool_id(context=None)->str; def controller(tool_id=None)->BaseTool
clock: Callable[[], float] = time.monotonic
# SEMÂNTICA DE EVENTOS (contrato):
#  keymap de toda ferramenta TOOL: LEFTMOUSE PRESS e RELEASE → su.tool_event (NÃO usar ANY).
#  su.tool_event: trata PRESS/RELEASE (DOUBLE_CLICK = PRESS; cliques contados em Python por clock+distância);
#    devolve PASS_THROUGH para CLICK, CLICK_DRAG e para PRESS com Ctrl (com ou sem Cmd/Shift) — no Mac,
#    Ctrl+clique = menu de contexto e Ctrl+Cmd+arrastar = órbita/pan (itens do keymap Window).
#  Ferramentas NAV (Órbita/Panorâmica/Aplicar zoom) não usam su.tool_event: keymap LEFTMOUSE PRESS → meta.operator.
#  No modal: MMB/roda/trackpad/NDOF → PASS_THROUGH; evento fora da região 3D → PASS_THROUGH;
#    tecla de outra ferramenta com buffer vazio → cancel + PASS_THROUGH; Cmd+Z → cancel; RIGHTMOUSE → ignorado.
#  Exceção em controlador → cancel() + perf.error + report de 1 linha; o modal termina.
# draw/handlers.py
def add_layer(name, space, order, fn)   # POST_VIEW: SKY=0 AXES=10 EDGES=20 SELECTION=30 GUIDES=40 ANNOT_3D=45 TOOL=50 INFERENCE=60
                                        # POST_PIXEL: ANNOT_2D=10 TOOL_2D=20 TOOLTIP=30
# tools/catalog.py — LARGE_TOOL_SET, GETTING_STARTED, FLYOUTS (ids do Apêndice A)
# ops/tool_ops.py — su.tool_activate(tool_id), su.vcb_key, su.vcb_capture (modal), su.vcb_field_apply, su.coming_soon(tool_id)
```

#### B — Geometria
```python
# core/document.py
class Document:
    key: str; obj; bm; version: int
    # camadas: edge bool su_bridge su_soft su_hidden; edge int su_curve; face int su_back_mat (padrão 1)
    def write(self, *, undo_key: str|None)   # undo.before_change(); to_mesh; update; version++; emit("geometry"); undo.push
    def begin(self)                          # snapshot bm.copy() (só ferramentas com pré-visualização ao vivo)
    def preview_write(self)                  # to_mesh sem undo/evento
    def cancel(self)                         # restaura snapshot + to_mesh
    def invalidate(self); def world(self) -> Matrix
def get(obj); def active(); def root(scene=None); def visible_documents(); def invalidate_all()
def create_group(name, parent_obj=None) -> Document
# assina "load": garante objeto raiz "Modelo" (su_doc.kind='MODEL')
# core/geom.py
@dataclass
class EditResult: new_verts; new_edges; new_faces; removed_faces: int=0; index_map: dict|None=None
def weld_point(bm, co, tol=GEOM_TOL); def add_edge(bm, a, b, *, curve_id=0) -> EditResult
def add_polyline(bm, pts, closed, *, curve_id=0); def add_closed_shape(bm, pts, normal, *, curve_id=0)
def auto_faces(bm, edges) -> list
def rebuild_face(bm, outer: list[Vector], inners: list[list[Vector]], normal, material: int, back_material: int,
                 *, through_holes: frozenset[int] = frozenset()) -> list
    # ALGORITMO DECIDIDO: projeta no plano → mathutils.geometry.delaunay_2d_cdt(..., output_type=5, need_ids=True)
    # → apaga o cluster → cria as faces → arestas que não são de entrada = su_bridge;
    # furo passante = descartar a face cujo loop é o do furo
def erase_edges(bm, edges); def erase_faces(bm, faces); def merge_coplanar(bm, edges)
def ensure_planar(bm, faces) -> EditResult     # dobra: divide face não plana com arestas visíveis
def is_planar(face, tol) -> bool; def reverse_faces(bm, faces); def orient_face(face, n)
def validate(bm) -> list[str]; def circle_points(...); def arc_points(...); def arc_from_bulge(...)
# core/entities.py
@dataclass
class LogicalFace: faces; outer_loop; inner_loops; plane
def logical_face(bm, face) -> LogicalFace          # flood fill por su_bridge
def surface(bm, face) -> list                      # flood fill por su_soft (superfície suave)
def pick_entity(bm, kind, index) -> tuple[str, list[int]]   # ('FACE'|'SURFACE'|'EDGE'|'CURVE', índices) — regra única de "entidade"
def curve_edges(bm, edge); def new_curve_id(doc); def get_curve_meta(doc, cid); def set_curve_meta(doc, cid, meta)
# core/selection.py — sets Python
@dataclass(frozen=True)
class Ref: doc_key: str; kind: str; index: int     # EDGE | FACE | OBJECT
def get(); def is_empty(); def count(); def version(); def set(refs); def add(refs); def remove(refs); def toggle(refs); def clear()
def select_all(); def invert(); def expand_face(ref); def expand_edge(ref); def connected(ref)
def edges_of(doc_key); def faces_of(doc_key); def objects(); def verts_of(doc); def bounds_world()
def snapshot() -> dict; def restore(snap: dict|None)          # usados por core/undo
def remap(doc_key, index_map: dict)                           # após operação que renumera (Explodir, rebuild_face)
# core/edit_context.py
def stack(); def enter(obj); def exit(); def exit_all(); def current_object(); def top_level_pick(obj); def is_in_context(obj)
```

#### C — Inferência / Medidas
```python
# core/spatial.py — sem cache na v1
def projection(region, rv3d, exclude=None) -> Projection   # numpy, todos os docs visíveis
def points_near(p, xy, r, exclude=None); def edges_near(p, xy, r, exclude=None)
def rect_query(p, x0, y0, x1, y1, mode)                   # 'WINDOW' | 'CROSSING'
def ray_cast(tc, origin, direction, *, skip: dict[str, set[int]]|None=None) -> Hit
    # Hit(ok, point, normal_orig, doc_key, face_idx_orig, side): face_idx_orig = idx % n_orig;
    # normal_orig = normal da face ORIGINAL (scene.ray_cast ignora culling e pode devolver a cópia de verso);
    # side = +1 se dot(direction, normal_orig) < 0 (frente vista) senão -1;
    # skip = faces em movimento → relança do ponto + ε na mesma direção (máx. 4×)
# core/inference.py
@dataclass
class QueryCtx: region; rv3d; xy; depsgraph; anchor=None; anchor_normal=None; plane=None; line=None
               flags=DEFAULT_FLAGS; exclude=frozenset(); skip=None; locks=None; previous=None
class InferenceEngine:
    def query(self, q) -> Inference; def acquire_tick(self, inf, t)
ENGINE: InferenceEngine
def lock_from_arrow(event_type, locks); def hover_plane(q) -> tuple[Vector, Vector, str]
# core/vcb.py
def feed(ev) -> str                 # 'CONSUMED'|'PASS'|'APPLY'|'CANCEL'
def parse(text, schema, units) -> list[VCBValue]; def apply_text(text)
# core/units.py
def system_decimal_sep() -> str     # defaults read -g AppleLocale (1×, ~15 ms, cache) → AppleLanguages → idioma; nunca setlocale
def decimal_sep(units); def list_sep(units); def format_length(m, units); def format_angle(rad, units)
def format_area(m2, units); def parse_length(text, units); def parse_angle(text)
# draw/tooltips.py — usado por inference_draw; prims.tooltip (D) é o primitivo
```

#### D — Casca e visual
```python
# draw/prims.py (congelado em M-A)
def line(dc, a, b, rgba, width=1.0, *, depth=True); def lines(dc, segs, rgba, width=1.0, *, depth=True)
def dashed(dc, a, b, rgba, width=1.0, dash_px=6, gap_px=4); def dotted(dc, a, b, rgba)
def points(dc, pts, rgba, size_px, shape='CIRCLE')    # CIRCLE SQUARE DIAMOND CROSS
def polygon(dc, pts, rgba, *, stipple=False); def text(dc, xy, s, size=11, rgba=(0,0,0,1), bg=None, align='LEFT')
def tooltip(dc, xy, lines); def protractor(dc, center, normal, ref_dir, axis_color); def box(dc, mn, mx, matrix, rgba, *, dashed=False)
def grips(dc, pts, rgba, size_px)
# draw/display_gn.py — SÓ a cópia de verso
def ensure(obj)                     # modificador "SU_Display": Join(original, Set Material Index(Flip Faces(original), su_back_mat))
def set_back_copy(enabled: bool)    # Raio X → False
# draw/edges.py — renderizador do spike, por atributos
def mark_dirty(doc_key: str|None = None)   # assina "geometry"; batch refeito no próximo desenho
def set_style(show_edges: bool, show_profiles_of_soft: bool = True, color_override: dict|None = None)
# regra: desenha arestas com not su_bridge and not su_hidden and not su_soft; arestas su_soft só quando são
# silhueta (as duas faces de lados opostos em relação à câmera); preto 1 pt, LESS_EQUAL + polygon offset
# ui/tray.py
def register_section(order: int, id: str, label_key: str, draw_fn: Callable[[UILayout, Context], None], priority='P0')
    # seções P2 não registradas não aparecem
# core/style.py
def apply(); def toggle(prop)
```

#### E/F/G — kernels de ferramenta
```python
# core/geom_extrude.py (E)
class PushPullSession:
    def __init__(self, doc, lface, keep_original)   # doc.begin(); cria topologia 1×; guarda faces em movimento (skip)
    def update(self, distance); def finish(self) -> EditResult; def cancel(self)
    moving_faces: set[int]
def offset_faces(bm, lface, distance, allow_overlap=False); def offset_edges(bm, edges, plane_normal, distance)
def follow_me(bm, profile, path, closed, smooth_from_curve)
# core/geom_transform.py (F)
class TransformSession:
    def __init__(self, refs, *, copy: bool, fold: str)   # 'AUTO' vértice/aresta, 'RESTRICT' face, 'FREE' (Cmd, P1)
    def set_matrix(self, m) -> Matrix                    # RESTRICT: rejeita só o que deixaria face não plana
    def finish(self) -> EditResult                       # index_map; cópia → seleção = cópia
    def cancel(self); def array(self, n, internal) -> EditResult
    moving_faces: set[int]
def mirror(refs, plane_co, plane_normal, copy)
# core/materials.py (F) — assina "load": garante slot 0 "Padrão" e slot 1 "Padrão (verso)" em todo doc
def ensure_slots(obj); def slot_for(obj, material) -> int; def paint(doc, face_ids, material, side)
# core/guides.py (G)
def add_guide_line(co, direction, ctx_obj=''); def add_guide_point(co, anchor, ctx_obj=''); def delete_guides(indices=None)
def guides_arrays(); def add_dimension(a, b, offset, kind='LINEAR'); def add_text(anchor, leader_end, text)
# core/camera.py (G)
def set_fov_v(deg); def keep_fov(region); def zoom_extents(selection_only=False); def push_history(); def previous(); def next()
def recenter_at(region, rv3d, xy); def standard_view(name); def set_projection(persp); def orbit_about(rv3d, pivot, dx, dy)
```

---

## 3. Arquitetura do núcleo

### 3.1 Geometria
- Sempre Object Mode; **nunca objeto ativo** (sem painéis C "Item", sem laranja).
- Documento por contexto: raiz "Modelo"; grupo = objeto malha (pai = grupo que contém); componente (P1) = coleção em "SU_Definitions" + instâncias. Malhas sem `su_doc.kind` = grupos.
- `Document.bm` vivo entre operações; face nova recebe `normal_update()` (nasce com normal zero — spike); ordem das faces preservada pelo GN; **índice e normal de face sempre da original** (`idx % n_orig`).
- **Furos**: `rebuild_face` por **CDT `output_type=5`** (verificado: 1 furo, 2 furos, furo tocando a borda, L côncavo + furo); pontes = arestas não-entrada (`su_bridge`); furo passante descarta a face do furo.
- **Auto-face**: ciclos planos mínimos pelas arestas novas; contenção → `rebuild_face` com furo; contida numa face → divide/fura.
- **Orientação**: chão → normal −Z (verso para cima); demais para a câmera; sólido fechado → para fora.
- **Divisões** (`add_edge`): solda, divide em extremos e cruzamentos coplanares, divide faces atravessadas. Implementação simples (pode varrer o doc inteiro na v1).
- **Apagar** aresta: faces dependentes somem; coplanares se fundem. **Planaridade**: nunca gravar face não plana (`ensure_planar` = dobra).
- **Entidades** (`entities.pick_entity`, regra única usada por Selecionar/Apagar/Pintura/pré-realce): aresta de curva → curva inteira; face com arestas `su_soft` → **superfície** inteira (flood fill); face com pontes → face lógica.
- **Suaves**: laterais vindas de curvas (círculo/arco, não polígono) → `su_soft`, `sharp_edge=False`, `sharp_face=False`.
- **Materiais** (F): slot 0 "Padrão" branco, slot 1 "Padrão (verso)" #A4B2BB; frente = `material_index`; verso = `su_back_mat` (padrão 1, nunca −1). `diffuse_color = lin(srgb)`; view transform Standard.

### 3.2 Inferência
Por movimento: raio → `spatial.ray_cast` (relança pulando faces em movimento) → `projection()` (numpy, sem cache) → candidatos com oclusão → prioridade extremidade > central > interseção > centro > ponto-guia > origem > em aresta > na linha-guia > restrição linear > em face > livre. Restrição linear a partir do âncora (eixos do contexto, paralela/perpendicular à última aresta pairada, perpendicular à face). "Do ponto": até 2 pontos, 0,3 s. Travas: Shift; setas ↑ azul, → vermelho, ← verde, ↓ paralela/perpendicular. **Histerese**: mesmo alvo mantido até `SNAP_* × 1,5`. Em grupo: geometria de fora inferível (não selecionável); marcadores magenta e 2ª linha "no grupo". `hover_plane()` para o gizmo de plano antes do clique. Sem inferência durante navegação. Redesenho só se mudou.

### 3.3 Exibição
- **Versos — GN "SU_Display"** (D) por documento: `Join(original, Set Material Index(Flip Faces(original), su_back_mat))`. Workbench com `show_backface_culling=True`, `color_type='MATERIAL'` → verso padrão e verso pintado iluminados, sem tom azul (verificado R2). Raio X → cópia desligada. Exportar e Interseccionar usam `obj.data`/sem modificadores. Overlay de orientação de face e de wireframe **desligados**.
- **Arestas — renderizador Python do spike** (`draw/edges.py`, D, camada EDGES=20): numpy por documento (cache simples por versão do doc), arestas visíveis por atributo (não por ângulo), **silhuetas** de superfícies suaves (o contorno do cilindro, como no SketchUp), preto 1 pt, `LESS_EQUAL` + polygon offset do spike. Fora do contexto de edição: cor cinza via `color_override`.
- **POST_VIEW Python** também para: céu, eixos, seleção azul (arestas + stipple), pré-realce, guias, Dimensões, `draw_3d` das ferramentas, inferência.
- Céu (quad em NDC z=0,9999999, horizonte = linha de fuga, gradiente linear #BFE5F5→#1EA6DD até a borda superior, fundo #BFBFC6), eixos (negativo pontilhado com passo de 4,5 px em tela) e luz `.sl` portada do spike; cores sRGB direto.
- **Iluminação (P0)**: o spike deu 243/222/185 com o topo mais **claro** que a lateral — invertido. Recalibrar a luz relativa à câmera para vir quase de frente, levemente de cima e da direita, até a caixa padrão dar frente ≈255, lateral ≈210, topo visto de cima ≈160 (`sketchup_selected_face_default_style.png`; sondas ±12).

### 3.4 Barra de status
Esquerda: pino + ⓘ (ícones próprios, cinza-claro/preto fino) + dica (modificadores sempre por `modifiers.label()` → "Option"/"Cmd" no Mac, nunca "Ctrl"); direita: rótulo ("Medidas" ocioso; "Comprimento", "Distância", "Ângulo", "Raio", "Lados", "Curvatura", "Segmentos", "Dimensões", "Escala", "Inclinação", "Campo de visão", "Altura dos olhos") + campo `wm.su_vcb.field`. Redesenho por `status_text_set(None)`.

### 3.5 Medidas **[decisão]**
1. Keymap `Window`, nesta ordem, poll = janela principal **e** área em {VIEW_3D, STATUSBAR, TOPBAR} **e** modo SketchUp: `TEXTINPUT`, `RET`, `NUMPAD_ENTER`, `BACK_SPACE`, `ESC` → `su.vcb_key` (devolve PASS se não for para ele) → atalhos de ferramenta → `KEYMAP` dos módulos (Excluir em ⌫/Delete, Esc = sair do grupo, Cmd+A…).
2. **Captura modal**: ao entrar o 1º caractere com a ferramenta ociosa, `su.vcb_key` inicia `su.vcb_capture` (modal de janela, roda antes dos handlers de região/UI) que consome texto, RET, NUMPAD_ENTER, BACK_SPACE e ESC até APPLY/CANCEL e repassa o resto. Isso evita que Enter aperte o botão sob o mouse (verificado na R2). Com ferramenta em operação, o modal dela faz esse papel.
3. Buffer vazio: só dígitos, `.`, `,`, `-`, `[`, `<`, `/`, `*` iniciam; letras passam (atalhos). Buffer não vazio: tudo vai ao buffer; ⌫ apaga dígito (**não** exclui seleção); Esc limpa (com buffer vazio, Esc cancela a operação; ocioso e sem seleção, sai do grupo); Enter aplica.
4. APPLY: em operação → `tool.vcb()`; ocioso com `last_action` → `reapply()` + `undo.push("undo.adjust")`; ocioso sem ação → parâmetros pré-clique.
5. Caixa clicável: `wm.su_vcb.field` editável; `update` (com guarda) → `vcb.apply_text`.
6. Decimal pela região do macOS (`AppleLocale`); `,` decimal ⇒ `;` lista; ponto sempre aceito. Formato `2,50m`.

### 3.6 Ferramentas
Fonte única = ferramenta ativa do workspace; dispatcher compara com o último id visto e chama `deactivate/activate` + `emit("tool")`. Semântica de eventos no contrato (§2.4). Cliques múltiplos e arrasto→2º clique em Python com `clock` injetável. Ferramentas com pré-visualização ao vivo usam `doc.begin()/cancel()`; as demais não escrevem antes do commit.

### 3.7 Undo
Memfile. Toda mutação nossa termina em `undo.push` (ou operador com `'UNDO'`). Ações de ferramenta: `Document.write(undo_key)`; 1 passo por ação (cada segmento de Linha). `undo_post/redo_post` → `invalidate_all`, seleção restaurada (§3.8), `last_action=None`, operação cancelada.

### 3.8 Seleção **[decisão]**
Sets Python; sem flags, sem `select_set`, sem objeto ativo. Entidades por `entities.pick_entity`. Regras do SketchUp:
- Após **Mover/Girar/Escala**: seleção mantida nas mesmas entidades (`TransformSession.finish().index_map`).
- Após **cópia** (Option): seleção = cópia (inclusive para arrays seguintes).
- **Undo/redo**: `scene.su_undo_serial` (int salvo no memfile) é incrementado a cada `undo.push`; `undo.before_change()` grava a seleção pré-operação no serial atual e `push` grava a pós-operação no novo serial (dict Python). No `undo_post`/`redo_post`, lê o serial restaurado e aplica a seleção correspondente (os índices batem porque a topologia volta exatamente). Ex.: selecionar → Mover → Cmd+Z → as entidades continuam selecionadas no lugar original.
- Limpa só em: clique no vazio, Excluir, abrir arquivo, e refs que deixam de existir.

### 3.9 Convenções
Pixels físicos de região; `ui_px()` para raios/fonte, `line_px()` para espessura. `Document.write` → `emit("geometry")` → assinantes (seleção poda refs inválidas; camadas refazem batches de seleção).

### 3.10 Carga de arquivo por eventos
`session.on_load_post` → `emit("load")` com assinantes por dono: B (raiz "Modelo"), F (slots 0/1 em todo doc), D (GN em todo doc, estilo, tema de viewport), G (FOV/clip), A (objeto ativo = None, ferramenta Selecionar). Depois, **um** `undo.push("undo.init")` se algo mudou. Teste: abrir → Cmd+Z → "Modelo" existe. Objetos-documento criados depois (grupos, cópias, Texto em 3D, importados) passam pelo evento `"doc"` (verso GN + slots 0/1); teste: Criar grupo → orbitar por baixo → o verso do grupo aparece.

---

## 4. Layout da UI

### 4.1 Regiões
TOPBAR = menu do app + menus (`TOPBAR_HT_upper_bar.draw_left` com os `SU_MT_*`, `draw_right` vazio) · **TOOL_HEADER** = Primeiros passos, HEADER escondido (como no spike; quando as abas de cenas P1 chegarem, a toolbar passa para o HEADER e as abas para o TOOL_HEADER) · TOOLS = LTS 2 colunas (96 px lógicos, por arrasto no build — verificado no spike) · UI = Bandeja (320 px, `use_region_overlap=False`) · STATUSBAR global. `startup.blend`: 1 janela, 1 workspace, 1 área VIEW_3D, HUD desligado.

### 4.2 Primeiros passos (grupos exatos)
```
[Pesquisar] | [Selecionar▾(Selecionar, Lasso)] |
[Apagar, Linha▾(Linha, Desenho à mão livre), Arco▾(Arco de dois pontos*, Arco, Arco de três pontos, Pizza), Retângulo▾(Retângulo*, Retângulo girado, Círculo, Polígono)] |
[Empurrar/puxar, Equidistância, Mover, Girar, Escala, Virar] | [Fita métrica, Pintura] |
[Órbita, Panorâmica, Aplicar zoom, Extensões de zoom]
```

### 4.3 Conjunto extenso de ferramentas
| Linha | Esquerda | Direita |
|---|---|---|
| 1 | Selecionar (Espaço) | Lasso *(P2)* |
| 2 | Pintura (B) | Apagar (E) |
| 3 | Criar componente (G) — **até o P1 executa Criar grupo**, dica "Componentes ainda não disponíveis: grupo criado" | **vazio** (ex-Etiqueta) |
| — | | |
| 4 | Linha (L) | Desenho à mão livre *(P2)* |
| 5 | Retângulo (R) | Retângulo girado *(P2)* |
| 6 | Círculo (C) | Polígono |
| 7 | Arco *(P1)* | Arco de dois pontos (A) |
| 8 | Arco de três pontos *(P2)* | Pizza *(P2)* |
| — | | |
| 9 | Mover (M) | Empurrar/puxar (P) |
| 10 | Girar (Q) | Siga-me |
| 11 | Escala (S) | Equidistância (F) |
| 12 | Eixos *(P2)* | Virar *(P1)* |
| — | | |
| 13 | Fita métrica (T) | Dimensões |
| 14 | Transferidor | Texto *(P1)* |
| 15 | Plano de seção *(P2)* | Texto em 3D *(P1)* |
| — | | |
| 16 | Órbita (O) | Panorâmica (H) |
| 17 | Aplicar zoom (Z) | Janela de zoom *(P1)* |
| 18 | Extensões de zoom (Shift+Z) | Anterior *(P1)* |
| — | | |
| 19 | Posição da câmera *(P1)* | Percorrer *(P2)* |
| 20 | Olhar ao redor *(P2)* | Campo de visão *(P2)* |

Desabilitados: ícone `_dim` (40%), clique → `su.coming_soon` → "Em breve" na status bar. Ativo: #D8EEFB + contorno #007EC0.

### 4.4 Bandeja padrão **[decisão, evidência do spike]**
Portado do spike (`SU_PT_tray`). Um painel `HIDE_HEADER` (sem alça de arrastar) na categoria "Bandeja": linha-título "Bandeja padrão" com ícones fixar/✕ decorativos; cada seção = caixa com chevron (bool em `wm.su_tray.open_<id>`) + nome + ✕; corpo abaixo quando aberta. Aba vertical invisível pelo tema (`wcol_tab` inner/inner_sel/outline/text/text_sel = cromo; sobra uma faixa de ~20 pt, aceita). Seções via `tray.register_section`. Ordem: Informações da entidade (F, P0) · Materiais (F, P0) · Componentes (F, P1) · Estilos (D, P1) · Cenas (G, P1). Seções P2 (Sombras, Suavizar arestas, Estruturador) **não aparecem**. Tudo fechado ao abrir; lembrar entre arquivos = P2. `hide.py` desregistra painéis Python de outras categorias (inclui glTF Variants).

### 4.5 Menus (nomes do Apêndice A)
Menu do app: Sobre o SketchUp Mode, Configurações… (Cmd+,: trackpad, inverter zoom do trackpad, idioma), Abrir no Blender completo, Sair · **Arquivo**: Novo, Abrir…, Salvar, Salvar como…, Salvar uma cópia como…, Reverter, Exportar ▸ (P1) · **Editar**: Desfazer, Refazer, Recortar/Copiar/Colar/Colar no local (P1), Excluir, Excluir guias, Selecionar tudo, Selecionar nada, Inverter seleção, Ocultar, Reexibir ▸, Criar componente… (= Criar grupo até P1), Criar grupo, Fechar grupo/componente, Interseccionar faces ▸ (P1), Inverter faces, Explodir · **Visualizar**: Geometria oculta, Eixos, Guias, Estilo de aresta ▸ (P1), Estilo de face ▸ (P1), Abas de cena (P1) · **Câmera**: Anterior/Próxima (P1), Exibições padrão ▸, Projeção paralela/Perspectiva, Órbita, Panorâmica, Aplicar zoom, Janela de zoom (P1), Extensões de zoom, Posição da câmera (P1) · **Desenho** · **Ferramentas** · **Janela**: Bandeja padrão ▸, Informações do modelo (unidades m/cm/mm, precisão, ajuste de ângulo) · **Ajuda**: Atalhos (P1), Sobre. Menu de contexto (F): Informações da entidade, Excluir, Ocultar, Selecionar ▸, Criar grupo, Inverter faces, Explodir, Editar grupo, Zoom na seleção.

### 4.6 Tema, ícones, cursores
Tema = `apply_theme()` do spike: `Blender_Light` via `_rna_xml.xml_file_run` + overrides (cromo #F1F1F6 em topbar/statusbar/`regions.sidebars.back`; bandeja (244,247,252); `wcol_box` #E0E1E9 sem arredondamento; ativo `wcol_toolbar_item.inner_sel` #D6E8FA + `outline_sel` #0078D7; aba invisível; `view_3d.wire` preto; fundo #BFBFC6), gravado no `userpref.blend` do template. **Ícones**: recolorir os `.dat` de ferramentas do Blender (script do spike `tools/build_icons.py`: azul-marinho/ciano/vermelho, pré-inversão HSL para tema claro) e desenhar só o que faltar; variantes `_dim`. Cursores nativos (Linha/Formas `PAINT_CROSS`, Mover `SCROLL_XY`, Empurrar/puxar `SCROLL_Y`, Apagar `ERASER`, Pintura `PAINT_BRUSH`/`EYEDROPPER`, Órbita `HAND_CLOSED`, Panorâmica `HAND`, Aplicar zoom `ZOOM_IN`, demais `CROSSHAIR`/`DEFAULT`).

### 4.7 Build
`build_all.sh` (D): ícones (`build_icons.py` do spike) → `userpref.blend` (tema, keyconfig, sem splash, `show_corner_split=False`, `show_regions_visibility_toggle=False`, **`show_edge_resize=True`**, add-ons glTF/OBJ/STL) → `startup.blend` = a sequência de passos do spike (um por tick, 0,3 s: prefs+tema → `batch_remove` workspaces → `area_close` DOPESHEET/TIMELINE/OUTLINER/PROPERTIES → espaço/modelo/painéis → categoria da Bandeja → lente ×2) + larguras por arrasto simulado (`driver.py`) + cena com "Modelo", slots 0/1, GN, unidades, Standard, câmera do spike → `save_as_mainfile(copy=True)` → print. Binários commitados; nunca editar à mão.

---

## 5. Teclado e mouse

### 5.1 Keymap
Keyconfig "SketchUp_Mode" de `blender_default` com **lista de permissão** em todos os keymaps não modais (mantém navegação, desfazer/refazer, arquivo, sair, tela cheia; `User Interface` sem reset por ⌫ e sem copiar/colar valor). Itens SketchUp no `Window` na ordem da §3.5, poll (janela principal + área VIEW_3D/STATUSBAR/TOPBAR + modo). Teste `scn_keys`: A–Z, 0–9, pontuação com/sem Shift sobre viewport/Bandeja/LTS/toolbar/status → nenhum popup; `L` sobre a Bandeja ativa Linha; `3` Enter sobre um botão do LTS, da toolbar e sobre o campo Medidas redigita (captura modal); ⌫ com buffer não exclui.

### 5.2 Mouse e trackpad
| Entrada | Ação |
|---|---|
| Roda | zoom no cursor |
| MMB arrastar / Shift+MMB | órbita (pivô sob o cursor) / panorâmica |
| Duplo clique MMB | recentralizar |
| LMB | ferramenta |
| RMB ocioso / **Ctrl+clique** | menu de contexto (`Window`: `LEFTMOUSE CLICK ctrl` → `wm.call_menu`) |
| **Ctrl+Cmd(+Option) arrastar** / **+Shift** | órbita / panorâmica (`Window`: `LEFTMOUSE CLICK_DRAG` → `su.view_orbit`/`su.view_pan`, pivô = profundidade sob `press_x/y`, não sob o ponto de detecção do arrasto) |
| Trackpad "sketchup": 2 dedos / pinça | zoom no cursor (opção "inverter zoom do trackpad") / zoom |
| Trackpad "blender" | 2 dedos órbita, Shift pan, pinça zoom |

Prefs não-template com backup/restore (`unregister` + `exit_pre`): `use_zoom_to_mouse`, `use_mouse_depth_navigate`, `use_rotate_around_active=False`, `use_auto_perspective=False`, `TURNTABLE`, `DOLLY`, `invert_zoom_wheel=False`, `use_mouse_emulate_3_button=False`, `use_region_overlap=False`, `smooth_view=200`, `system.light_ambient` (spike: 0,42), `view.show_statusbar_*` (vram em try). Na barra de status, omitir `template_reports_banner`.

### 5.3 Atalhos (`Window`)
Espaço Selecionar · L Linha · R Retângulo · C Círculo · A Arco de dois pontos · P Empurrar/puxar · F Equidistância · M Mover · Q Girar · S Escala · E Apagar · B Pintura · T Fita métrica · O Órbita · H Panorâmica · Z Aplicar zoom · Shift+Z Extensões de zoom · **G = mesmo comando do botão Criar componente** (Criar grupo até o P1) · K Arestas traseiras (P1) · Shift+S Pesquisar (P1) · Shift+Espaço Lasso ("Em breve") · Delete/⌫ Excluir (após `su.vcb_key`) · Esc (após `su.vcb_key`): cancelar / sair do grupo · Cmd+Z / Cmd+Shift+Z / Cmd+Y · Cmd+A, Shift+Cmd+A, Shift+Cmd+I · Cmd+X/C/V (P1) · Cmd+N/O/S/Shift+S · Cmd+, Configurações · setas e Shift (travas) · Option = copiar/adicionar/nova face/suavizar/adjacentes/alternar guia/do centro · Cmd = conta-gotas/dobrar face (P1)/sobreposição/perímetro/ciclo de inferências.

---

## 6. Ferramentas: comportamento e aceites

Todo aceite também exige: 1 passo de undo por ação, nenhuma face não plana (`doc_stats`), Esc sem lixo, navegação no meio da operação sem cancelar, dica/rótulo corretos, sem objeto ativo. Unit = `testing.dispatch` headless; GUI = cenário simulado. IDs `AC-*` são citados nos briefs (§9).

### 6.1 Seleção e edição (F)
- **Selecionar**: clique (aresta ≤ 7 px vence face); 2 cliques face → face+arestas, aresta → aresta+faces, grupo → entra; 3 cliques → conectado; Option/Shift/Shift+Option; janela/cruzamento; vazio limpa; Esc sai do contexto; entidade por `pick_entity`.
  - AC-SEL-1 caixa: 1/2/3 cliques no topo → 1 face / 1+4 / 6+12. AC-SEL-2 clique num círculo → 24 arestas. AC-SEL-3 clique na lateral de cilindro → **superfície** (Informações: "Superfície"). AC-SEL-4 clique em aresta de grupo → grupo (bbox azul); dentro do grupo a geometria de fora não seleciona mas a Linha encaixa nela; Esc sai. AC-SEL-5 janela/cruzamento.
- **Apagar**: arestas (curva inteira), dependentes somem, coplanares fundem; grupo → apaga o grupo; Shift oculta; Option suaviza; Shift+Option des-suaviza.
  - AC-APG-1 linha dividindo retângulo → 1 face. AC-APG-2 arrasto sobre arestas de uma curva → curva inteira, 1 undo. AC-APG-3 Option na aresta lateral de caixa → suaviza (aresta some, sombreamento contínuo). AC-APG-4 aresta de grupo → grupo some.
- **Pintura**: lado por `Hit.side` (frente → `material_index`, verso → `su_back_mat`); com seleção, clicar numa entidade selecionada pinta a seleção; superfície inteira; grupo → faces Padrão; Option adjacentes, Shift todas, Shift+Option mesmo objeto; Cmd conta-gotas.
  - AC-PNT-1 piso no chão (verso para cima) pintado → sonda mostra a cor sem tom azul; frente branca. AC-PNT-2 lateral de cilindro → superfície inteira. AC-PNT-3 Cmd+clique → material ativo = o da face. AC-PNT-4 com 3 faces selecionadas, clicar numa delas → 3 pintadas.
- **Mover**: sem seleção, hover realça e pega a entidade; Option alterna cópia; `5x`, `/5`; vértice/aresta → dobra automática; face → `RESTRICT` (rejeita só o que deixaria face não plana; cisalhamento permitido); grupo = matriz; seleção mantida / cópia vira seleção.
  - AC-MOV-1 caixa `2` em +X → Δx 2,000; seleção mantida. AC-MOV-2 Option + `3x` → 4 caixas; seleção = última cópia. AC-MOV-3 `/4` após cópia → 3 intermediárias. AC-MOV-4 canto de uma caixa solto no canto de outra ("Ponto de extremidade") → coincidência exata. AC-MOV-5 **1 vértice** do topo 0,5 m para cima → topo em 2 triângulos com aresta de dobra; laterais planas. AC-MOV-6 **cumeeira**: linha entre pontos médios de arestas opostas do topo, mover 1 m ↑ → 2 águas + 2 oitões pentagonais, 7 faces planas. AC-MOV-7 topo movido 0,5 em +X → aceito (cisalhado), faces planas. AC-MOV-8 face solta sem seleção arrastada → estica a geometria ligada. AC-MOV-9 grupo sobre geometria solta → nada gruda. AC-MOV-10 selecionar → Mover → Cmd+Z → mesmas entidades selecionadas na posição original.
- **Girar**: transferidor no hover colorido pelo plano; centro, braço, ângulo/`3:12`; 15°; Option cópia + arrays; seleção mantida.
  - AC-GIR-1 hover sobre face vertical → transferidor vermelho/verde. AC-GIR-2 `90` exato. AC-GIR-3 cópia em torno do canto `90` + `3x` → 4 caixas.
- **Escala**: caixa amarela, alças; cantos uniforme (Shift), arestas/faces 2/1 eixos, Option centro; `1,5`, `3m`, `2;1;1`, `-1`.
  - AC-ESC-1 canto `2` → 2×2×2. AC-ESC-2 face `3m` → 1 eixo. AC-ESC-3 `-1` numa alça de face → espelhado com normais para fora. AC-ESC-4 grupo → só a matriz.
- **Comandos**: Excluir, tudo/nada/inverter, Criar/Fechar grupo, Inverter faces, Ocultar/Reexibir, Explodir (P0); Virar, Componentes, clipboard, Interseccionar faces sobre `obj.data` (P1).
- **Informações da entidade** P0 (tipo/contagem — Face, Superfície, Aresta, Curva, Grupo — área, comprimento, nome); **Materiais** P0 (24 cores + Padrão, criar cor).

### 6.2 Desenho (E)
- **Linha**: encadeia; Medidas; fechar laço cria face; duplo clique no mesmo ponto encerra; atravessar face divide; travas; redigitar.
  - AC-LIN-1 retângulo 3×2 por 4 segmentos com setas + Medidas → 1 face, normal −Z, 6,00 m². AC-LIN-2 diagonal divide; cruzamento coplanar divide as duas. AC-LIN-3 **cura**: Excluir o topo de uma caixa e redesenhar uma aresta → face volta. AC-LIN-4 borda a borda numa face vertical → 2 faces. AC-LIN-5 laço num plano vertical com ↑ travado → face vertical. AC-LIN-6 órbita MMB no meio da cadeia → continua do mesmo âncora. AC-LIN-7 `4` após concluir → último segmento 4.
- **Retângulo**: plano inferido; **em pé automático** ao longo de plano de eixo vertical; `L;W`; sobre face divide/fura.
  - AC-RET-1 `2;3` → face 2×3 normal −Z. AC-RET-2 R, origem, mover para a projeção de (2,0,3) → retângulo em XZ. AC-RET-3 1×1 dentro do topo de caixa 3×3 → furo + face interna; empurrar `1` → rebaixo. AC-RET-4 **porta**: parede 4×0,2×2,8, retângulo 0,9×2,1 começando na aresta inferior da face frontal → 2 faces sem pontes; empurrar a porta `0,2` → abertura passante. AC-RET-5 sobre face vertical sem seta → nasce no plano da face.
- **Círculo / Polígono**: gizmo no hover; Lados antes; raio; `Ns`; curva-entidade.
  - AC-CIR-1 `12`, origem, `1` → 12 arestas, área 3,0. AC-CIR-2 empurrar → cilindro sem arestas laterais visíveis, sombreamento contínuo e **contorno (silhueta) preto visível** dos dois lados, mudando ao orbitar; polígono mantém arestas duras. AC-CIR-3 hover na face lateral de caixa → gizmo vermelho/verde e círculo nasce nela. AC-CIR-4 `↑` antes do clique no vazio → círculo vertical.
- **Arco de dois pontos**: início, fim, curvatura; `Nr`, `Ns`. AC-ARC-1 corda 2, curvatura `1` → semicírculo 12 segmentos.
- **Empurrar/puxar**: face lógica (não age em superfície suave); perfura; esticar; Option; duplo clique; redigitar; laterais suaves de curvas.
  - AC-EMP-1 2×3 `1` → caixa 6 faces, 6 m³. AC-EMP-2 topo de novo `1` → 6 faces. AC-EMP-3 **encaixe**: caixas de alturas 1 e 2; puxar o topo da menor pairando sobre o topo da maior → altura 2,000. AC-EMP-4 redigitar `1,5` → altura muda ("Ajustar"). AC-EMP-5 duplo clique em outra face → mesma distância. AC-EMP-6 Option → +1 face. AC-EMP-7 hover em lateral de cilindro → sem realce, clique sem efeito.
- **Equidistância**: AC-EQD-1 face 2×2 `0,5` → 1×1 + anel. AC-EQD-2 duplo clique repete. AC-EQD-3 face com furo → anel externo e furo deslocados.
- **Siga-me**: AC-SIG-1 tubo em L com mitra. AC-SIG-2 perfil 0,1×0,1 com caminho = bordas do topo pré-selecionadas → moldura contínua fechada.

### 6.3 Construção e câmera (G)
- **Fita métrica**: AC-FIT-1 guia a `0,5` de uma aresta. AC-FIT-2 Option (medir) → Medidas mostra o comprimento, nenhuma guia criada. AC-FIT-3 ponto-guia a partir de extremidade. AC-FIT-4 interseção de duas guias inferível pela Linha.
- **Transferidor**: AC-TRA-1 hover sobre face vertical → gizmo no plano dela. AC-TRA-2 base +X, `30` → guia (cos30, sin30, 0) e a Linha encaixa nela.
- **Dimensões**: AC-DIM-1 aresta de 3 m → "3,00m". AC-DIM-2 Cmd+Z → some. AC-DIM-3 texto legível ao orbitar.
- **Navegação**: AC-NAV-1 zoom no cursor: o ponto 3D sob o cursor fica sob o cursor (±2 px) após 5 passos de roda. AC-NAV-2 pivô: o ponto sob o cursor no início do arrasto MMB não se move (±2 px). AC-NAV-3 duplo clique MMB → ponto ao centro (manual). AC-NAV-4 Ctrl+clique abre o menu **sem** iniciar a ferramenta. AC-NAV-5 Ctrl+Cmd+arrastar orbita com pivô no ponto do PRESS. AC-NAV-6 Shift+Z enquadra (bbox em 90% da região). AC-NAV-7 FOV vertical 35° ±0,5 após redimensionar. AC-NAV-8 Exibições padrão ▸ Superior olha −Z.
- P1: Anterior/Próxima, Janela de zoom, Posição da câmera, Texto com chamada, Texto em 3D, Cenas + abas.

### 6.4 Inferência e Medidas (C)
- AC-INF-1 extremidade/central/em aresta/em face com câmera sintética. AC-INF-2 eixo X do âncora com elástico vermelho; ↑ força Z; Shift trava. AC-INF-3 **prioridade**: perto de uma extremidade **e** do eixo vermelho → vence "Ponto de extremidade". AC-INF-4 "Em face": Linha no topo de caixa → z constante. AC-INF-5 histerese 1,2× mantém / 1,6× solta. AC-INF-6 "do ponto" após 0,3 s.
- AC-VCB-1 tabela de parse: `2,5` · `250cm` · `2;3` · `[1;2;0]` · `<1;0;0>` · `5x` · `/5` · `12s` · `1r` · `3:12` (e `~` na exibição, P1). AC-VCB-2 mouse sobre a Bandeja: `2,5` Enter redigita. AC-VCB-3 `3` Enter com o mouse sobre botão do LTS / toolbar / campo Medidas → redigita, nenhum botão acionado. AC-VCB-4 ⌫ com buffer apaga o dígito e não exclui a seleção.

---

## 7. Performance (adiada — decisão do usuário)
- v1: sem orçamentos, benchmarks ou gates. Exigência: **responsivo em modelos pequenos (até ~5k faces)** no roteiro manual; travar em modelo pequeno é bug.
- Ficam só escolhas gratuitas/simples: nada de `bpy.ops` no movimento do mouse; Object Mode; sets de seleção; sem inferência durante navegação; redesenho só quando muda; arestas/versos pelo GN.
- **Fase de performance (P2, após a v1 e a pedido do usuário)**: cache de projeção, pré-filtro bbox, cancel O(k) sem `bm.copy()`, pré-visualização GPU-only em docs grandes, operações locais, `bench.py`. Números medidos na Crítica R1 (`CRITICA_R1_BLENDER.md` §2) são a linha de base.

---

## 8. Testes e comparação

### 8.1 Headless (maior parte da cobertura)
`tools/sketchup_mode/run_unit.sh [padrão]` → exige `dev_env.sh`; roda `Blender --background --factory-startup --python tests/sketchup_mode/unit/run.py -- --pattern "<padrão>"`, e `run.py` insere `$SU_ROOT/scripts/startup/bl_app_templates_system/SketchUp_Mode` no `sys.path` antes de `import su` (módulos `draw/*` não são importados em background). Sem lock (pode rodar em paralelo). Kernel, CDT/furos, superfícies, dobra, seleção/undo-serial, VCB/unidades, inferência com câmera sintética, controladores via `testing.dispatch` com relógio injetado.

### 8.2 GUI (regras do harness)
`tools/sketchup_mode/run_gui.sh <cenario>` → `lockf -k -t 1800 /tmp/su_gui.lock …` (macOS não tem `flock`; `lockf` libera o lock se o processo morrer; só cenários GUI, `shot.sh` e `build_all.sh` usam esse lock) + ambiente do agente (§9.0: `BLENDER_SYSTEM_SCRIPTS`, `BLENDER_USER_RESOURCES`, `BLENDER_USER_CONFIG/SCRIPTS/DATAFILES/EXTENSIONS`, `TMPDIR`, `userpref.blend` semeado) + `Blender --app-template SketchUp_Mode --enable-event-simulate -p 0 0 1440 900 --python tests/sketchup_mode/gui/harness.py -- <cenario> <out_dir>` (base: `visual_spike/run.sh` + `driver.py`). **`-p` é ignorado neste Mac** (janela maximizada 1512×854 pt, prints 3024×1708): nada depende do tamanho da janela. ESC inicial e conferência de que não há popup; coordenadas de `region.*` (pixels físicos); **assert por passo** via `testing.state_dump()/doc_stats()`; duplo/triplo clique com `testing.set_clock`; resultado `out_dir/results.json`, exit ≠ 0 em falha. Cenário de fumaça `scn_smoke` roda em todo merge.

### 8.3 Prints lado a lado com o SketchUp **[mantido — decisão do líder]**
- `tools/sketchup_mode/shot.sh <cenario|none> <out.png>` → abre o modo (maximizado), executa o cenário opcional, `screen.screenshot`.
- `tools/sketchup_mode/compare.sh <nosso.png> <ref.png> <out.png>`: `sips --resampleHeight 900` nas duas imagens → `compose.py` (Blender headless, numpy: lado a lado com rótulos "SketchUp 2027" / "SketchUp Mode") → `sips -Z 1600` (leve para o celular). Saída em `doc/sketchup_mode/screens/`.
- Pares padrão: vazio × `ref_images/sketchup_default_ui_2_v2027_empty_scene_large_toolset.png`; caixa selecionada × `sketchup_selected_face_default_style.png`; Simple 2023 × `sketchup_default_ui_1_win2023_simple_template.png`.
- Sondas de cor (`expected/colors.json`) e ordem/separadores por `state_dump`. Rodadas com o usuário após M-A, M2, M3, M4.

### 8.4 Roteiro manual
"10 minutos de SketchUp" (planta, paredes, porta perfurada, janela com guias, cumeeira, cópias `3x`, piso pintado, Dimensões, salvar/reabrir, desfazer/refazer com a seleção) com mouse **e** só trackpad, conferindo com o usuário a direção do zoom de 2 dedos.

---

## 9. Execução e briefs dos agentes

### 9.0 Regras comuns (valem para todo brief)
- Leia este plano inteiro; seu contrato está na §2.4; não edite arquivo de outro dono; não crie stubs em arquivo alheio.
- **Git (worktree por agente)**: o coordenador lança cada agente com `isolation: "worktree"` → você já está num **worktree próprio** criado a partir de `sketchup-mode`, numa branch própria. Trabalhe e comite **só** nele (`git add` apenas dos seus arquivos; mensagem `su(<agente>): ...`). Antes de começar e antes de entregar: `git rebase sketchup-mode` (as refs são compartilhadas entre worktrees). **Nunca** edite a árvore principal `/Users/tiago.agenor/www/blender` nem faça merge em `sketchup-mode`: o merge é do integrador/coordenador, serializado (§9.6). Ao entregar, informe o nome da sua branch, o último commit e o resultado dos gates.
- **Ambiente (obrigatório; nunca tocar `~/Library/Application Support/Blender`)**: `source tools/sketchup_mode/dev_env.sh <AGENTE>` define `SU_ROOT=$(git rev-parse --show-toplevel)` (o seu worktree), `SU_STAGE=/private/tmp/su_stage_<AGENTE>`, `BLENDER_SYSTEM_SCRIPTS=$SU_STAGE/sys` (com `sys/startup/bl_app_templates_system/SketchUp_Mode` → symlink para `$SU_ROOT/scripts/startup/bl_app_templates_system/SketchUp_Mode`), `BLENDER_USER_RESOURCES=$SU_STAGE/user` (redireciona config/scripts/datafiles/extensions — verificado na R3), `BLENDER_USER_CONFIG/SCRIPTS/DATAFILES/EXTENSIONS` explícitos dentro de `$SU_STAGE/user`, `TMPDIR=$SU_STAGE/tmp` (luz `.sl`, `quit.blend`, autosaves) e semeia `$SU_STAGE/user/config/userpref.blend` com `show_splash=False` (gerado 1× em `--background --factory-startup`; sem isso o "Quick Setup" engole eventos). Todo script (`run_unit.sh`, `run_gui.sh`, `shot.sh`, `build_all.sh`) **aborta** se `SU_STAGE` não estiver definido ou se `BLENDER_USER_RESOURCES` estiver fora de `/private/tmp/su_stage_*`. Runtime: só `/Applications/Blender.app` (5.2.2).
- **Parta do spike visual** (`doc/sketchup_mode/visual_spike/`, achados em `VISUAL_SPIKE_FINDINGS.md`): se o que você precisa já existe lá (tema, prefs, céu, eixos, arestas, listas LTS/GETTING_STARTED/TRAY, câmera, ícones, run/driver), porte e adapte; não reescreva. Respeite as armadilhas da §3 do FINDINGS.
- Mantenha `doc/sketchup_mode/checklists/WS_<AGENTE>.md` (cópia do seu sub-checklist; marque [~]/[x]). O `CHECKLIST.md` principal é do integrador.
- **Gate de entrega** (no seu worktree, depois do rebase): `run_unit.sh` verde + `run_gui.sh scn_smoke` verde (inclui `perf.errors()==0`) + seu cenário verde + checklist atualizado. Só então peça o merge.
- **Prompt de lançamento** (o coordenador cola): *"Você é o agente <X> do projeto SketchUp Mode. Leia `doc/sketchup_mode/PLANO.md` (no seu worktree) inteiro (atenção às §2, §3, §9.0 e ao seu brief §9.2-<X> ou §9.1-A0), `VISUAL_SPIKE_FINDINGS.md` e o código em `doc/sketchup_mode/visual_spike/`. Execute o seu brief em ordem, marcando `doc/sketchup_mode/checklists/WS_<X>.md`. Respeite dono de arquivos e contratos. Ao terminar, rode os gates da §9.0 e relate branch, commit e resultados."*
- Strings só por `i18n.t()` com o seu prefixo (§2.3-7). Nunca a palavra "Etiqueta"/"Tag" na UI.
- Simples e correto primeiro; nada de otimização sem pedido.

### 9.1 Fase A — esqueleto A0 e fatia vertical

#### 9.1-A0 — Esqueleto (agente A, sozinho, primeiras horas; merge em `sketchup-mode` antes de qualquer outro agente rodar Blender)
- **Arquivos**: `tools/sketchup_mode/{dev_env.sh,run_unit.sh,run_gui.sh}` (lock e ambiente da §9.0), `SketchUp_Mode/__init__.py`, `su/__init__.py` (auto-descoberta: **erro de import de um módulo = `perf.error` + módulo pulado**; `scn_smoke` falha se `perf.errors()>0`), `su/{constants,colors,registry,events,i18n,perf}.py`, `su/core/state.py` (`Inference`, `Locks`, `LastAction`, `STATE`), `su/core/undo.py` (`push`/`before_change` reais, `su_undo_serial`), `su/core/viewutil.py`, `su/draw/handlers.py` (`add_layer`), `su/tools/base.py` (só `ToolMeta`, `@tool`, `BaseTool` com métodos vazios, `Ev`, `Result`), `tests/sketchup_mode/unit/run.py`, `tests/sketchup_mode/gui/{harness.py,scn_smoke.py}` (versão "abre e fecha"), `doc/sketchup_mode/checklists/WS_{A..G}.md` (vazios, com o sub-checklist de cada brief copiado).
- **Saída A0**: `run_gui.sh scn_smoke` abre o template vazio e fecha sem erro; `run_unit.sh` roda 0 testes com sucesso; nenhum arquivo criado fora de `/private/tmp/su_stage_A`. Merge em `sketchup-mode`. **Só então** B, C, D e E são lançados.
- **Comandos**: `source tools/sketchup_mode/dev_env.sh A && tools/sketchup_mode/run_unit.sh && tools/sketchup_mode/run_gui.sh scn_smoke`

#### 9.1-MA — Fatia vertical (dias 0–2 após A0): A integra entregas mínimas de B, C, D, E

| Dono | Entrega mínima (dia 0–1) |
|---|---|
| B | `Document` (write/begin/cancel/invalidate), `add_edge` simples, `auto_faces` de laço simples, `rebuild_face` (CDT) + testes headless |
| C | `units` + `vcb.parse` (comprimento, `L;W`) headless; inferência mínima (extremidade + eixos) + `inference_draw` mínimo |
| D | **porta o spike** para os módulos de D (tema, prefs, céu, eixos, `edges.py`, toolbar, LTS, Bandeja, status, ícones, câmera inicial) + `prims.py` + `display_gn.py` (cópia de verso) — a fatia já nasce com o visual do `shell_v3.png` |
| E | Retângulo |
| A | `run.sh`/`driver.py` do spike → `dev_env.sh`/harness; registry/auto-descoberta, `base` + `su.tool_event` + gizmo de hover, keymap `Window` + `su.vcb_key`/`su.vcb_capture`, undo (serial), session/eventos, `testing`, harness, **Linha** |

Saída M-A: E2E `scn_smoke` = "Linha 3×2 via Medidas → face; Retângulo 2×3; Cmd+Z remove o retângulo e mantém a face da linha; `3` Enter com o mouse sobre a Bandeja funciona" + print lado a lado (vazio × ref 2) enviado ao usuário. Então os contratos da §2.4 congelam. Fora da fatia: casca exata, histerese, decimal do sistema, Empurrar/puxar, sondas.

### 9.2 Briefs (Fase B, em paralelo após M-A)

#### Agente A — Plataforma / integrador
- **Arquivos**: `SketchUp_Mode/__init__.py`, `presets/keyconfig/SketchUp_Mode.py`, `su/{__init__,constants,colors,registry,events,settings,i18n,modifiers,perf,session,testing,keymap,prefs}.py`, `su/core/{state,undo,viewutil}.py`, `su/draw/handlers.py`, `su/tools/{base,catalog,coming_soon}.py`, `su/ops/tool_ops.py`, `tools/sketchup_mode/{dev_env.sh,run.sh,run_unit.sh,run_gui.sh,shot.sh,compare.sh,compose.py}`, `tests/sketchup_mode/{unit/run.py,unit/fakes.py,unit/test_a_*.py,gui/harness.py,gui/scn_smoke.py,gui/scn_keys.py,expected/colors.json}`; `tools/line.py` até M-A.
- **Fornece**: contratos A (§2.4), semântica de eventos, keymap, undo com seleção, eventos, `testing`, harness, prints.
- **Consome**: `selection.snapshot/restore` (B), `vcb.feed/parse` (C), `prims` (D), `ToolMeta`s de todos.
- **Sub-checklist**:
  1. [ ] dev_env/run/run_unit/run_gui a partir de `visual_spike/run.sh` + `driver.py` (lock, splash, envs DATAFILES/EXTENSIONS, independente do tamanho da janela)
  2. [ ] auto-descoberta + registry + eventos + settings + i18n (detecção de duplicatas)
  3. [ ] `base`: `su.tool_event` (PRESS/RELEASE; PASS para CLICK/CLICK_DRAG/Ctrl), gizmo de hover, cliques em Python, arrasto→2º clique, política de erro
  4. [ ] keymap por lista de permissão + itens `Window` na ordem §3.5 + poll; `su.vcb_key` + `su.vcb_capture`
  5. [ ] undo: serial em `scene.su_undo_serial`, `before_change`/`push`, restauração de seleção em undo/redo
  6. [ ] session por eventos + `undo.init`; invariante sem objeto ativo
  7. [ ] Linha (fatia) → passar a E
  8. [ ] `testing.dispatch/hover/set_clock/state_dump/doc_stats`
  9. [ ] `shot.sh` + `compare.sh`/`compose.py` + sondas
  10. [ ] menus de contexto via Ctrl+clique e órbita Ctrl+Cmd no `Window` (com G)
  11. [ ] prefs com backup/restore + S-E (ida e volta de template, kill -9)
  12. [ ] Integração contínua, rodadas de prints, CHECKLIST mestre
- **Aceite**: `scn_smoke`; `scn_keys` (AC-VCB-2..4, nenhum popup); AC-NAV-4; teste "abrir → Cmd+Z → Modelo existe"; AC-MOV-10 junto com F.
- **Comandos**: `tools/sketchup_mode/run_unit.sh test_a_` · `tools/sketchup_mode/run_gui.sh scn_smoke` · `tools/sketchup_mode/run_gui.sh scn_keys` · `tools/sketchup_mode/shot.sh none /tmp/a.png && tools/sketchup_mode/compare.sh /tmp/a.png doc/sketchup_mode/ref_images/sketchup_default_ui_2_v2027_empty_scene_large_toolset.png doc/sketchup_mode/screens/vazio.png`

#### Agente B — Geometria
- **Arquivos**: `su/core/{document,geom,entities,selection,edit_context}.py`, `tests/sketchup_mode/unit/test_b_*.py`, `gui/scn_b.py`.
- **Fornece**: contratos B. **Consome**: `undo.push/before_change`, `events` (A).
- **Sub-checklist**:
  1. [ ] Document + camadas (`su_bridge su_soft su_hidden su_curve su_back_mat=1`) + raiz no evento "load"
  2. [ ] `rebuild_face` (CDT tipo 5, pontes, furo passante) — 15 testes (dentro, tocando borda, 2 furos, furo em furo, L côncavo)
  3. [ ] `add_edge` completo (solda, cruzamentos, divide faces) + `auto_faces` com contenção
  4. [ ] `erase_edges/faces`, `merge_coplanar`, cura (AC-LIN-3 no kernel)
  5. [ ] `ensure_planar`/`is_planar` (dobra)
  6. [ ] entidades: `logical_face`, `surface`, `pick_entity`, curvas + metadados
  7. [ ] seleção em sets + `snapshot/restore/remap` + expandir/conectado/tudo/inverter
  8. [ ] edit_context + `create_group` + helpers de Explodir — todos emitem `events.emit("doc", doc_key=…)` para objeto-documento novo
  9. [ ] `validate()` em todos os testes
- **Aceite**: AC-LIN-1..4 e AC-RET-3/4 no nível do kernel; AC-SEL-1..3 com `testing.dispatch`; AC-MOV-5..7 em conjunto com F (planaridade).
- **Comandos**: `tools/sketchup_mode/run_unit.sh test_b_` · `tools/sketchup_mode/run_gui.sh scn_b`

#### Agente C — Inferência / Medidas
- **Arquivos**: `su/core/{spatial,inference,vcb,units}.py`, `su/draw/{inference_draw,tooltips}.py`, `tests/.../unit/test_c_*.py`, `gui/scn_c.py`.
- **Fornece**: contratos C (`ray_cast` com `side`/normal original, `query`, `feed/parse`). **Consome**: `Document`, `entities` (B), `prims` (D), `STATE` (A).
- **Sub-checklist**:
  1. [ ] `units` (pt-BR via AppleLocale, m/cm/mm/pol/pés, ângulo, inclinação)
  2. [ ] `vcb.parse` com todos os esquemas + `feed` (regras §3.5)
  3. [ ] `spatial.projection/points_near/edges_near/rect_query` + `ray_cast` (idx % n, side, skip)
  4. [ ] pipeline de inferência completo (prioridade, oclusão, eixos, paralela/perpendicular, do ponto, travas, plano livre, guias, centro, em contexto)
  5. [ ] histerese; `hover_plane`
  6. [ ] `inference_draw` (marcadores, linhas, pontilhadas, travada grossa, magenta) + tooltips com 2ª linha
  7. [ ] P1: tangente, semicírculo, quadrado/seção áurea, `~`
- **Aceite**: AC-INF-1..6, AC-VCB-1 (unit); AC-EMP-3 e AC-MOV-4 junto com E/F.
- **Comandos**: `tools/sketchup_mode/run_unit.sh test_c_` · `tools/sketchup_mode/run_gui.sh scn_c`

#### Agente D — Casca de UI e visual
- **Arquivos**: `startup.blend`, `userpref.blend`, `icons/`, `studiolights/`, `su/{theme,icons}.py`, `su/core/style.py`, `su/draw/{prims,shaders,sky,axes,edges,selection_draw,display_gn}.py`, `su/ops/{style_ops,file_ops}.py`, `su/ui/{topbar,header_toolbar,toolset,statusbar,tray,hide,dialogs,tray_styles}.py`, `tools/sketchup_mode/{build_all.sh,build_startup.py,build_userpref.py,build_icons.py}`, `tests/.../gui/scn_d.py`, `expected/layout.json`.
- **Fornece**: `prims`, `edges.mark_dirty/set_style`, `display_gn.ensure/set_back_copy`, `tray.register_section`, `style.apply/toggle`, layout. **Consome**: `catalog`, `ToolMeta`, `STATE` (A); `Document` (B).
- **Ponto de partida obrigatório**: `doc/sketchup_mode/visual_spike/tpl/startup/bl_app_templates_system/SketchUpSpike/__init__.py` (funções `apply_theme`, `apply_prefs`, `draw_sky`, `draw_axes`, `draw_edges`, `set_view`, `fit_lens`, listas `LTS`/`GETTING_STARTED`/`TRAY`, `SU_PT_tray`, overrides de topbar/tool header/status bar), `visual_spike/tools/build_icons.py` e `build_style_thumb.py`, `visual_spike/icons/`. Portar função por função para os módulos acima, mantendo o resultado visual do `shell_v3.png` (o print de M-A deve ficar igual ou melhor).
- **Sub-checklist**:
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
- **Aceite**: sondas de cor (céu, horizonte, fundo, cromo, LTS ativo, Bandeja, status, face frente ≈255 / lateral ≈210 / topo ≈160, verso padrão, verso pintado sem tom azul, aresta preta, diagonal coplanar visível); passos 1, 2, 11, 12 da §12; ordem/separadores por `state_dump`; AC-PNT-1 (visual, com F); prints comparativos aprovados pelo líder.
- **Comandos**: `tools/sketchup_mode/build_all.sh` · `tools/sketchup_mode/run_gui.sh scn_d` · `tools/sketchup_mode/shot.sh none /tmp/d.png && tools/sketchup_mode/compare.sh /tmp/d.png doc/sketchup_mode/ref_images/sketchup_default_ui_2_v2027_empty_scene_large_toolset.png doc/sketchup_mode/screens/casca.png`

#### Agente E — Desenho
- **Arquivos**: `su/tools/{line(após M-A),rectangle,circle,polygon,arcs,pushpull,offset,followme}.py`, `su/core/geom_extrude.py`, `tests/.../unit/test_e_*.py`, `gui/scn_e.py`.
- **Fornece**: ferramentas de desenho, `PushPullSession`. **Consome**: B (geom/entities/Document), C (query/vcb/hover_plane), D (prims), A (base).
- **Sub-checklist**:
  1. [ ] Retângulo (fatia) → completo (em pé automático, sobre face, porta)
  2. [ ] Linha (assumida de A): duplo clique encerra, cura, plano vertical, redigitar
  3. [ ] Círculo e Polígono (gizmo de plano, lados, curva-entidade, laterais suaves)
  4. [ ] Arco de dois pontos
  5. [ ] Empurrar/puxar (skip de faces em movimento, encaixe, perfurar, esticar, Option, duplo clique, redigitar, recusa em superfície)
  6. [ ] Equidistância (com furo; duplo clique)
  7. [ ] Siga-me (caminho pré-selecionado; moldura)
  8. [ ] P1: Arco (centro)
- **Aceite**: AC-LIN-1..7, AC-RET-1..5, AC-CIR-1..4, AC-ARC-1, AC-EMP-1..7, AC-EQD-1..3, AC-SIG-1..2.
- **Comandos**: `tools/sketchup_mode/run_unit.sh test_e_` · `tools/sketchup_mode/run_gui.sh scn_e` · `tools/sketchup_mode/shot.sh scn_e:porta /tmp/e.png`

#### Agente F — Seleção, edição, materiais
- **Arquivos**: `su/tools/{select,eraser,paint,move,rotate,scale,flip}.py`, `su/core/{geom_transform,materials}.py`, `su/ops/edit_ops.py`, `su/ui/{context_menu,tray_entity_info,tray_materials,tray_components}.py`, `tests/.../unit/test_f_*.py`, `gui/scn_f.py`.
- **Fornece**: `TransformSession`, `materials.*`, comandos de edição, seções da Bandeja. **Consome**: B, C, D (`prims`, `register_section`), A.
- **Sub-checklist**:
  1. [ ] `materials` (slots 0/1 nos eventos `"load"` e `"doc"`, `paint` por lado); emitir `"doc"` ao copiar grupo/componente
  2. [ ] Selecionar (entidades, janela/cruzamento, contexto; dica com `modifiers.label()` → "Option")
  3. [ ] Apagar (curva, grupo, Shift/Option)
  4. [ ] Pintura (lado por `Hit.side`, seleção, superfície, conta-gotas) + seção Materiais
  5. [ ] `TransformSession` (AUTO/RESTRICT, cópia, arrays, index_map) + Mover
  6. [ ] Girar (transferidor no hover) e Escala (alças, `-1`)
  7. [ ] comandos: Excluir, tudo/nada/inverter, Criar/Fechar grupo, Inverter faces, Ocultar/Reexibir, Explodir; G/Criar componente = Criar grupo
  8. [ ] menu de contexto; Informações da entidade
  9. [ ] P1: Virar, Componentes, clipboard, Interseccionar (sobre `obj.data`)
- **Aceite**: AC-SEL-1..5, AC-APG-1..4, AC-PNT-1..4, AC-MOV-1..10, AC-GIR-1..3, AC-ESC-1..4.
- **Comandos**: `tools/sketchup_mode/run_unit.sh test_f_` · `tools/sketchup_mode/run_gui.sh scn_f` · `tools/sketchup_mode/shot.sh scn_f:caixa_selecionada /tmp/f.png && tools/sketchup_mode/compare.sh /tmp/f.png doc/sketchup_mode/ref_images/sketchup_selected_face_default_style.png doc/sketchup_mode/screens/selecao.png`

#### Agente G — Construção, câmera, cenas
- **Arquivos**: `su/tools/{tape,protractor,dimension,text,nav,camera_tools}.py`, `su/core/{guides,camera}.py`, `su/draw/annotations.py`, `su/ops/view_ops.py`, `su/ui/{scene_tabs,tray_scenes}.py`, `tests/.../unit/test_g_*.py`, `gui/scn_g.py`.
- **Fornece**: guias (para inferência de C), câmera, `su.view_orbit/su.view_pan/su.view_recenter`, ferramentas NAV. **Consome**: C (query, hover_plane), D (prims), A.
- **Sub-checklist**:
  1. [ ] ferramentas NAV (Órbita/Panorâmica/Aplicar zoom via `meta.operator`), Extensões de zoom, FOV 35° vertical, Exibições padrão, projeção
  2. [ ] `su.view_orbit/pan` (pivô no PRESS) para Ctrl+Cmd; recentralizar (duplo clique MMB); trackpad (modos + inverter zoom) com A
  3. [ ] `guides` + `annotations`
  4. [ ] Fita métrica (guia, ponto-guia, modo medir)
  5. [ ] Transferidor (gizmo no hover, guia angular)
  6. [ ] Dimensões lineares
  7. [ ] P1: Anterior/Próxima, Janela de zoom, Posição da câmera, Texto com chamada, Texto em 3D (emite `"doc"`), Cenas + abas
- **Aceite**: AC-FIT-1..4, AC-TRA-1..2, AC-DIM-1..3, AC-NAV-1..8.
- **Comandos**: `tools/sketchup_mode/run_unit.sh test_g_` · `tools/sketchup_mode/run_gui.sh scn_g`

### 9.3 Marcos
| Marco | Conteúdo | Gate |
|---|---|---|
| M-A | fatia (§9.1) | `scn_smoke` + print ao usuário; contratos congelados |
| M2 | P0 de desenho + Selecionar/Apagar/Pintura + inferência completa + casca exata | unit + cenários + sondas + print |
| M3 | Mover/Girar/Escala, Fita/Transferidor/Dimensões, grupos, Ocultar/Explodir, trackpad | idem + roteiro manual parcial |
| M4 | P1 | idem + roteiro manual completo + prints finais |

### 9.4 Integração final (A)
- [ ] Gates verdes; varredura i18n; varredura "sem Etiquetas" (`grep -ri "tag\|etiqueta"` em UI/strings, exceto `tag_redraw`)
- [ ] S-E no build final; abrir `.blend` qualquer no modo e vice-versa; exportar sem duplicatas
- [ ] **Teste final de aceite (§12)** com mouse e com trackpad, sondas verdes e print lado a lado aprovado — só então dizer ao usuário que está pronto
- [ ] Rodadas de prints com o usuário
- [ ] Zip + `.command` + `COMO_USAR.md`

### 9.5 Spikes restantes
S-B (GN de verso em grupos/instâncias/Raio X — D, na fatia), S-C (suíte CDT — B), S-E (prefs/template — A), S-I (`Window` + captura modal sobre botões — A, na fatia), S6 (tracejado/stipple no Metal — D), S11 (MMB duplo clique, trackpad, Ctrl+clique, Ctrl+Cmd — G). Resolvidos: S-F e S-G (spike visual, `VISUAL_SPIKE_FINDINGS.md`), S-H (removido: Bandeja do spike), S-D (adiado com a performance).


### 9.6 Sequência de lançamento e merges (coordenador)
Todos os agentes com `isolation: "worktree"`. Merge = no repositório principal, **um por vez**:
`lockf -k -t 1800 /tmp/su_merge.lock sh -c 'cd <worktree> && git rebase sketchup-mode && source tools/sketchup_mode/dev_env.sh <X> && tools/sketchup_mode/run_unit.sh && tools/sketchup_mode/run_gui.sh scn_smoke && git -C /Users/tiago.agenor/www/blender merge --ff-only <branch>'` (se o ff falhar, repetir o rebase).

1. **A0** (§9.1-A0) — sozinho. → **Merge 1**.
2. Em paralelo, a partir do Merge 1: **A-fatia** (Linha, `su.tool_event`, gizmo, `Window`/captura, testing, harness completo), **B-mín**, **C-mín**, **D-porte do spike** (entregas da tabela §9.1-MA). B, C e D fazem merge assim que suas entregas mínimas passam (ordem livre, serializada pelo lock).
3. **E-Retângulo** — lançado quando B-mín e C-mín estão em `sketchup-mode`.
4. A integra tudo e fecha **M-A** (`scn_smoke` completo + print lado a lado ao usuário). → **Merge M-A; contratos congelados.**
5. **Fase B em paralelo**: briefs §9.2 **B, C, D, E, F, G** (6 agentes) + **A** como integrador. Cada agente pede merge ao cumprir blocos do seu sub-checklist (não só no fim).
6. **M2** (desenho + Selecionar/Apagar/Pintura + inferência + casca exata): merge dos agentes envolvidos + print ao usuário.
7. **M3** (transformações, construção, grupos, trackpad): idem + roteiro parcial da §12.
8. **M4** (P1) e **Integração final** §9.4 → **teste final §12**.

---

## 10. Riscos

| # | Risco | Mitigação |
|---|---|---|
| R1 | Furos | `rebuild_face` por CDT (verificado) + suíte S-C |
| R2 | Header de altura fixa (ícones ~20 px) | aceito |
| R3 | Sem cursores bitmap | nativos (P0) |
| R4 | Crash ao mutar layout no mesmo tick | layout só no `startup.blend` gerado |
| R5 | Lentidão em modelos grandes | aceita na v1 (decisão do usuário); Fase de performance |
| R6 | Seleção perdida/errada após undo | serial de undo + testes AC-MOV-10 |
| R7 | GN de verso: casos não cobertos (instâncias, ray_cast na cópia) | S-B; normal/lado sempre da original |
| R16 | Divergir do visual já aprovado no spike ao portar | D compara o print de M-A com `visual_spike/shots/shell_v3.png` (lado a lado) antes do merge |
| R8 | Teclas globais × botões da UI (Enter aperta botão) | captura modal `su.vcb_capture` + S-I + `scn_keys` |
| R9 | Keymap/tema/prefs vazando | escopo do template + backup/restore + S-E |
| R10 | Popups engolindo eventos em testes | lista de permissão; harness fecha splash |
| R11 | Trackpad | modos + inverter zoom + roteiro com o usuário |
| R12 | 5.2.2 × fonte 5.4-alpha | testar só no 5.2.2 |
| R13 | Marca/copyright | ícones do Blender recoloridos/próprios; textos próprios |
| R14 | Exportação com geometria duplicada do GN | exportar sem modificadores (teste no 9.4) |
| R16b | Agentes paralelos colidindo (git, perfil do Blender, tmp, import de módulo quebrado) | worktree por agente, staging por agente, `BLENDER_USER_RESOURCES`+`TMPDIR`, auto-descoberta tolerante a erro, merges sob `lockf` |
| R15 | Objeto ativo reaparecendo | invariante no load e após cada op; `scn_smoke` checa |

---

## 11. Decisões finais e pendências
Plano aprovado (GO) pelos dois críticos na rodada 3. Q1–Q25 como na v2 (respostas do especialista SketchUp), com ajustes da R2: G = Criar grupo até o P1 (coerente com o botão); seções P2 da Bandeja ocultas; opção "inverter zoom do trackpad"; modo de modificadores Windows → P2.
Pendências: (a) rótulos pt-BR de inferência/Bandeja/Editar — conferir com print de um SketchUp pt-BR, se o usuário tiver; (b) lacunas visuais restantes listadas no `VISUAL_SPIKE_FINDINGS.md` §4 (ícones de 20 pt, ✕ da Bandeja como ícone, faixa da aba invisível, bordas de região de 1 px) — aceitas na v1, revisitar com o usuário; (c) spikes da §9.5.


---

## 12. Teste final de aceite — "primeiro dia" (critério para dizer "100%")

Executar com o **mouse** e depois só com o **trackpad**, sem usar o Blender "por baixo". Cada passo precisa funcionar de primeira, **sem popup do Blender** e com **1 Cmd+Z por ação**. Fonte: CRITICA_R3_SKETCHUP §4.

1. **Abrir o modo**: sem splash, sem abas do Blender; céu, eixos, toolbar, LTS, Bandeja e Medidas visíveis; ferramenta Selecionar ativa; dica com "Option".
2. **Piso**: `R`, clicar na origem (dica "Ponto de origem"), `8;6` Enter → retângulo 8×6 com o **verso azul-acinzentado para cima**; Medidas mostra as dimensões.
3. **Volume e redigitar**: `P`, pairar o piso (realce azul), clicar, subir, `3` Enter → caixa com frentes brancas para fora; `2,8` Enter → altura 2,80 m.
4. **Navegar**: MMB orbita em torno do ponto sob o cursor; Shift+MMB panorâmica; roda aproxima em direção ao cursor; duplo clique MMB recentraliza; `Shift+Z` enquadra. Trackpad: dois dedos = zoom; Ctrl+Cmd+arrastar = órbita.
5. **Paredes**: `F` no topo, `0,15` Enter; `P` na face interna, empurrar `2,65` Enter → cômodo oco com paredes de 15 cm e piso.
6. **Porta**: `R` na face externa da parede da frente começando **na aresta inferior**, `0,9;2,1` Enter; `P` na porta, empurrar `0,15` → **abertura passante**, sem faces sobrando.
7. **Linha com inferência**: `L` numa parede: clicar no ponto central de uma aresta, subir pelo eixo azul (linha azul, dica "No eixo azul"), `1` Enter → a linha divide a face e fica **visível**; `Esc` encerra.
8. **Telhado**: caixa nova 4×4×3; `L` ligando os pontos centrais de arestas opostas do topo; `M` nessa linha, 1,5 m para cima (↑ ou eixo azul) → 2 águas + 2 oitões, nenhuma face torta.
9. **Grupo e cópias**: clique triplo na casa, botão direito (ou Ctrl+clique) › Criar grupo (bbox azul); `M`, Option, mover 10 m no vermelho, `2x` Enter → 3 casas, seleção = última cópia. Linha encostada num grupo **não gruda**.
10. **Girar**: com a cópia selecionada, `Q` → transferidor azul no chão; clicar num canto, no braço, `90` Enter → a cópia gira 90°.
11. **Cilindro**: `C`, clicar no chão, `0,4` Enter; `P`, `1` Enter → sem riscos laterais, sombreamento liso, contorno preto; clicar na lateral seleciona a **superfície** inteira.
12. **Pintura**: `B`, escolher uma cor; pintar uma parede e um retângulo desenhado no chão (verso para cima) → os dois **na cor**, sem tom azul.
13. **Medir e cotar**: `T` numa aresta, afastar, `1` Enter → guia tracejada a 1 m; a Linha mostra "Na linha" sobre a guia; Dimensões numa aresta de 8 m → "8,00m".
14. **Teclado em qualquer lugar**: mouse sobre a Bandeja: `L`, `R`, `Espaço` trocam a ferramenta; logo após um Empurrar/puxar, mouse sobre a barra de status, `1` Enter redigita a distância; `⌫` com algo digitado apaga o dígito e **não** exclui a seleção.
15. **Apagar, desfazer, salvar**: `E` na linha do passo 7 → faces se fundem; Cmd+Z até o vazio, Cmd+Shift+Z refaz tudo e a seleção volta; salvar, fechar, reabrir → mesmo visual e mesma ferramenta.

**Pronto** = 15/15 com mouse e com trackpad + sondas de cor verdes + print lado a lado aprovado pelo usuário. Cada passo tem um cenário GUI equivalente em `tests/sketchup_mode/gui/scn_final.py` (A, montado na Integração final a partir dos cenários dos donos), exceto os itens de trackpad e duplo clique MMB (manuais).

---

## Apêndice A — Ids canônicos e nomes pt-BR oficiais (QRC 2026 pt-BR Mac)

| id | Rótulo | Dono | Sinônimos (Pesquisar) |
|---|---|---|---|
| su.select | Selecionar | F | |
| su.lasso | Lasso (P2) | A (coming_soon) | Laço |
| su.paint | Pintura | F | Balde de tinta |
| su.eraser | Apagar | F | Borracha |
| su.make_component | Criar componente (= Criar grupo até P1) | F | |
| su.make_group | Criar grupo (comando) | F | |
| su.line | Linha | A→E | |
| su.freehand | Desenho à mão livre (P2) | A | Mão livre |
| su.rectangle · su.rotated_rectangle | Retângulo · Retângulo girado (P2) | E · A | |
| su.circle · su.polygon | Círculo · Polígono | E | |
| su.arc · su.arc2 · su.arc3 · su.pie | Arco (P1) · Arco de dois pontos · Arco de três pontos (P2) · Pizza (P2) | E · E · A · A | Torta, Setor |
| su.move | Mover | F | |
| su.pushpull | Empurrar/puxar | E | Empurrar, Puxar, Extrudar |
| su.rotate | Girar | F | Rotacionar |
| su.followme | Siga-me | E | Follow Me |
| su.scale | Escala | F | Dimensionar |
| su.offset | Equidistância | E | Deslocamento, Offset |
| su.axes | Eixos (P2) | A | |
| su.flip | Virar (P1) | F | Espelhar |
| su.tape | Fita métrica | G | Trena |
| su.dimension | Dimensões | G | Cotas |
| su.protractor | Transferidor | G | |
| su.text · su.text3d | Texto (P1) · Texto em 3D (P1) | G | |
| su.section | Plano de seção (P2) | A | Corte |
| su.orbit · su.pan · su.zoom | Órbita · Panorâmica · Aplicar zoom | G | Orbitar, Pan, Zoom |
| su.zoom_window · su.zoom_extents · su.previous | Janela de zoom (P1) · Extensões de zoom · Anterior (P1) | G | Zoom estendido |
| su.position_camera · su.walk · su.look_around · su.fov | Posição da câmera (P1) · Percorrer (P2) · Olhar ao redor (P2) · Campo de visão (P2) | G · A · A · A | Caminhar |
| su.search | Pesquisar (P1) | A | |
| su.delete_selected | Excluir | F | Apagar seleção |
| Menus | Arquivo, Editar, Visualizar, Câmera, Desenho, Ferramentas, Janela, Extensões, Ajuda | D | |
| Vistas | Exibições padrão: Iso, Superior, Inferior, Frontal, Traseira, Esquerda, Direita | G | |
| Estilo | Raio X, Grade de linhas, Linha oculta, Sombreado, Sombreado com texturas, Monocromático; Arestas, Arestas traseiras, Perfis | D | |
| Bandeja | Bandeja padrão, Informações da entidade, Materiais, Componentes, Estilos, Cenas | D/F/G | |
| Medidas | Medidas, Comprimento, Distância, Ângulo, Raio, Lados, Curvatura, Segmentos, Dimensões, Escala, Inclinação, Campo de visão, Altura dos olhos | C | |
| Inferência | Ponto de extremidade, Ponto central, Em aresta, Em face, Interseção, Centro, Ponto de origem, Ponto de orientação, Na linha, No eixo vermelho/verde/azul, Paralela, Perpendicular, Do ponto, Tangente no vértice, Quadrado, Seção áurea, Semicírculo; 2ª linha "no grupo"/"no componente" | C | Ponto final, Ponto médio |
| Dica Selecionar | Clique ou arraste para selecionar objetos. Shift = Adicionar/Subtrair. Option = Adicionar. Shift + Option = Subtrair. | F | |

## Apêndice B — Fluxo (Retângulo 2×3 digitado com o mouse sobre a Bandeja)
1. **R** (qualquer região) → `Window` → `su.tool_activate` → no próximo hover o dispatcher vê o id novo → `activate()` → dica/rótulo → `redraw_statusbar()`.
2. Hover → `ENGINE.query(previous=…)` → "Ponto de origem".
3. PRESS → `su.tool_event` → canto 1 → modal; `move` → `draw_3d` + Medidas "1,23m; 0,80m".
4. Mouse vai à Bandeja, digita `2;3` Enter → o modal da ferramenta recebe (ocioso: `Window` → `su.vcb_key` → `su.vcb_capture`) → `parse('length2')` → `add_closed_shape(normal=−Z)` → `doc.write("undo.rectangle")` (`before_change`, to_mesh, evento, `push` com serial) → `last_action`.
5. GN reavalia: arestas pretas + verso azul-acinzentado visível de cima.
6. `4;3` Enter → `reapply` → `write("undo.adjust")`. Cmd+Z → volta ao 2×3 com a mesma seleção daquele passo.
