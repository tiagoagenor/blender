# Crítica R1 — Especialista Blender/Python + Performance

Revisão do `PLANO.md` v1 · Runtime verificado: **Blender 5.2.2 LTS** (`/Applications/Blender.app`, M1, Metal, Retina `pixel_size=2`).
Tudo marcado **[VERIFICADO]** foi executado agora no 5.2.2 (headless ou GUI com timers + `screen.screenshot`). Scripts e prints em
`/private/tmp/claude-1313471784/-Users-tiago-agenor--claude-spares-spare-OyPPwD/b629df7a-43bf-4aae-9e76-4fba22f313f3/scratchpad/crit/`
(`h0.py`, `h1.py`, `g_ui.py`, `g_ev.py`, `g_ev2.py`, `g_key.py`, `g_edge.py` + `*_out.txt` + `*.png`).

Veredito curto: o plano é **viável**, mas tem 4 suposições erradas (abas da bandeja, redesenho da status bar, duplo clique em testes, seleção persistida no bmesh), 3 escolhas caras demais (renderizador de arestas em Python, `ScreenGrid`, snapshot `bm.copy()` por operação) e um modelo de execução para equipe humana (8 workstreams, Fase 0 gigantesca, stubs escritos nos arquivos dos outros) que vai travar agentes paralelos. Abaixo, o que verifiquei e o que precisa mudar.

---

## 1. Bloqueios técnicos e suposições de API erradas

### 1.1 Tabela de verificação

| # | Suposição do plano | Resultado no 5.2.2 | Evidência |
|---|---|---|---|
| V1 | §4.4 "Com uma só categoria, o Blender não desenha abas" na região UI | **FALSO.** Com todos os 82 painéis Python da região UI desregistrados e só a categoria "Tray", a aba vertical "Tray" continua desenhada. Painel sem `bl_category` vira "Misc" e também ganha aba. No código, só `space_userpref`, `space_file` e `space_project` têm `HideSinglePanelCategories`; a VIEW_3D não. | `g_ui.png`, `g_ev_crop.png`; `interface_panel.cc:2418` |
| V2 | Desregistrar painéis Python remove a aba "Item" | **Parcial.** `VIEW3D_PT_transform`, `VIEW3D_PT_vgroup` e `VIEW3D_PT_curves` são **painéis em C** (não dá para desregistrar). Eles somem só quando **não há objeto ativo** (`poll` = base ativa). Com `view_layer.objects.active=None`, a aba "Item" sumiu. Também existe a categoria "glTF Variants" (add-on glTF, necessário para o Exportar glTF P1). | `h0.py`, `g_ui.png` (2ª rodada), `view3d_buttons.cc:2741` |
| V3 | §3.4 escrever em `wm.su.vcb_display` (prop Python do WM) redesenha a status bar | **FALSO.** Mudar uma prop Python do WindowManager provocou **0** redesenhos (status bar, header, toolbar, bandeja). `workspace.status_text_set(None)` provocou **exatamente 1** redesenho, **só da status bar**. Isso resolve o S5: é o "tag redraw" barato e direcionado. | `g_ui_out.txt` (contadores) |
| V4 | §3.7/S3 `ed.undo_push` dentro de modal; custo em malha grande | **OK e barato.** Malha de 102k faces: `to_mesh+update` 3,4 ms, `undo_push` **0,93 ms**, `ed.undo` 3,1 ms, `ed.redo` 3,1 ms (memfile é incremental). **Armadilha verificada:** o objeto criado por Python **sem** `undo_push` depois dele **sumiu** no primeiro undo. Todo dado alterado fora de um passo de undo (load_post, timers, painéis via código) é perdido ou mesclado no passo errado. | `g_ui_out.txt` |
| V5 | S4: item `TEXTINPUT` no keymap da ferramenta + `PASS_THROUGH` para letras | **OK.** `TEXTINPUT` recebe `l`, `1`, `;`, `,` com `unicode` correto. `l` em PASS_THROUGH chegou ao item addon em **"Object Mode"**. **Mas:** `m` em PASS_THROUGH **não** chegou ao item addon em **"3D View"**, porque o `M` do Object Mode (`object.move_to_collection`) abriu um **menu popup** que engoliu as teclas seguintes. `,` em PASS_THROUGH abriu a pie de orientação e engoliu o `M` seguinte. | `g_key_out.txt` |
| V6 | §3.6 "`ev.double` vem de `value=='DOUBLE_CLICK'`"; §8.2 helper `double_click` | **Não testável por simulação.** `event_simulate` só aceita `PRESS/RELEASE/NOTHING` (erro explícito para `DOUBLE_CLICK`), e eventos simulados passam `check_double_click=false` (`wm_event_system.cc:WM_event_add_simulate`). Duas pressões seguidas no mesmo ponto chegam como `PRESS`, `PRESS`. | `g_ui_stdout`, `g_ev2_out.txt` |
| V7 | Simulação de cliques é confiável | **Sim, depois de fechar a splash.** Com a splash aberta (com `--factory-startup` ela aparece de forma intermitente), 3 de 5 cliques foram **engolidos** e o viewport nem redesenhou. Com a splash fechada (ESC simulado), 5/5 cliques chegaram ao modal nas 3 variantes. Popups abertos por teclas que passam adiante (V5) engolem eventos do mesmo jeito. | `g_ev_out.txt` × `g_ev2_out.txt`, `edge_near_s.png` |
| V8 | §4.2 header da VIEW_3D como "Primeiros passos", TOOL_HEADER embaixo como abas | **OK.** HEADER y=1603 fica acima do TOOL_HEADER y=1551, ambos com largura total da área. Altura de 52 px físicos = **26 lógicos** (fixa). 20 botões renderizaram. | `g_ui_out.txt`, `g_ui.png` |
| V9 | §3.3 renderizador próprio de arestas com "polygon offset" (S7) | **Funciona** (perto 9 m, longe 120 m, rasante): sem z-fighting visível com `POLYLINE_UNIFORM_COLOR` + `LESS_EQUAL` + offset do `GPU_polygon_offset_calc`. **Custo:** montar o batch de 200k arestas (`foreach_get` + `batch_for_shader`) leva **24–28 ms**. O orçamento do plano é 12 ms. | `edge_*.png`, `g_edge_out.txt` |
| V10 | (alternativa não considerada) arestas **nativas** via Geometry Nodes | **Funciona e é ~15× mais barata.** Um modificador GN por documento (original + cópia das arestas visíveis como arestas soltas, filtradas por um atributo de aresta `su_visible`) faz o **próprio Blender** desenhar as arestas pretas, sem overlay de wireframe, sem z-fighting e com controle por aresta (pontes e arestas suaves somem). Reavaliar a malha de 100k faces levou **1,7 ms**, e 0,8 ms após mudar coordenadas. Ordem das faces preservada: índice do `scene.ray_cast` == índice original em **18/18** faces. Grupos e instâncias de componente herdam isso de graça. | `g_edge.py`, `g_edge_out.txt`, `near_crop.png` |
| V11 | S12: `scene.ray_cast` vê a malha após `to_mesh` | **Vê**, mas o **1º ray_cast após qualquer mudança reconstrói a BVH**: 4,6 ms (10k faces), 12 ms (50k), **28 ms (100k)**. Mudar só coordenadas também reconstrói (21 ms a 100k). Depois disso, 2,4 µs por chamada. | `h1.py` |
| V12 | `Region.width` não é gravável; largura salva no startup.blend persiste | Somente leitura (confirmado). Templates **não embutidos** só sofrem versionamento mínimo (`blo_update_defaults_screen` sai cedo para templates não embutidos), então a largura salva **persiste**. O arrasto simulado ainda não foi testado (fica no S1/S10). | `h0.py`, `versioning_defaults.cc:88-120` |
| V13 | §5.2 prefs: o que é por template | Pelo `BKE_blender_userdef_app_template_data_swap`, são por template: `themes, addons, user_keymaps, keyconfigstr, gizmo_flag, app_flag, ui_scale`, splash e `show_navigate_ui`. **Não** são por template: `inputs.*`, `system.use_region_overlap`, `view.smooth_view`, `edit.undo_steps`. O backup/restore de `prefs.py` é necessário só para estes. `show_navigate_ui` e `ui_scale` já são escopo do template. | `blender.cc:426-447` |
| V14 | Gizmo como hover ocioso | Já verificado na pesquisa (g5: 40 chamadas, 0,027 ms; 0 chamadas durante modal). Não reverifiquei. Implicação: o modal precisa rodar a inferência ele mesmo (o plano já prevê). | `g5_out.txt` |
| V15 | `-p 0 0 1600 1000` | Nesta tela (3024 px = 1512 pt) a janela é **cortada**: o print saiu 3024×1708. Coordenadas de região/eventos são **pixels físicos** (`pixel_size=2`). | `g_ui.png` |

### 1.2 O que muda por causa disso

1. **Bandeja (V1/V2):** aceitar **uma** aba vertical e chamá-la de `"Bandeja padrão"` (vira o "título" lateral). Remover o painel `SU_PT_tray_title` com `HIDE_HEADER`. Invariante global: **nunca ter objeto ativo** (`view_layer.objects.active=None` em load_post e após cada operação nossa). Isso também elimina o contorno e as arestas laranja do Blender. Desligar o add-on glTF no `userpref.blend` do template, ou incluir "glTF Variants" no `hide.py`.
2. **Status bar (V3):** `STATE.tag_redraw(statusbar=True)` = `context.workspace.status_text_set(None)` (com `temp_override(window=…)` fora de operador). O campo do VCB pode continuar como `prop` do WM para edição por clique, mas o redesenho **não** depende disso.
3. **Duplo/triplo clique (V6):** `tools/base.py` detecta duplo e triplo clique **sozinho** (tempo `time.monotonic()` + distância ≤ 4 px), ignorando o `DOUBLE_CLICK` do Blender (tratado como `PRESS`). Usar uma fonte de tempo injetável (`base.clock`) para os testes. Isso vale também para o duplo clique MMB (recentralizar): fica num item de keymap `MIDDLEMOUSE DOUBLE_CLICK` sem teste E2E, só manual.
4. **Teclado (V5):** o filtro de keymap por **lista de negação** (§5.1: "remover itens sem modificador nas teclas SPACE A B C…") **vai vazar**: `,` `.` `` ` `` `/` `-` `=` Home, F-keys, numpad e outras abrem pies e menus que engolem a entrada. Trocar por **lista de permissão**: nos keymaps `Object Mode`, `Object Non-modal`, `3D View`, `3D View Generic`, `Frames`, `Screen`, `Window` e `Screen Editing`, manter só itens explicitamente permitidos (navegação MMB/roda/trackpad/NDOF, undo/redo, arquivo, sair, F11 etc.) e descartar o resto. Itens de troca de ferramenta vão em **"Object Mode"**, nunca em "3D View" (V5).
5. **Undo (V4):** regra nova no contrato: *toda* mutação de `bpy.data` feita por nós termina num `undo.push` ou acontece dentro de operador com `'UNDO'`. `session.on_load_post` faz o que precisa **e** chama `ed.undo_push(message="SketchUp Mode init")`, ou então só cria dados quando o arquivo é aberto (antes do 1º passo). Teste obrigatório: "abrir → Cmd+Z imediato → raiz `Modelo` ainda existe".
6. **Seleção (§3.8):** **não** persistir seleção nas flags `select` do bmesh/mesh. Cada mudança de seleção exigiria `to_mesh`, que invalida a BVH (+28 ms no próximo ray_cast a 100k, V11) e as caches de GPU, e ainda mistura seleção com undo (o SketchUp não desfaz seleção). Seleção = conjuntos Python `{doc_key: (edges:set, faces:set)}` + objetos por nome, limpos em undo/redo/load e em qualquer mudança topológica do doc. **Nunca** usar `obj.select_set` (deixa as arestas nativas laranja, V10).
7. **Arestas (V9/V10):** trocar o P0 "renderizador próprio em Python" por **arestas nativas via GN** (spike S7' abaixo). O POST_VIEW em Python fica só para o que é pequeno ou dinâmico: seleção azul, pré-realce, elástico, inferência, back edges (K, P1) e esmaecimento fora do contexto. Isso remove a montagem de batches grandes, `push_pop` por instância e a iteração de componentes no Python.

---

## 2. Performance

### 2.1 Números medidos (headless 5.2.2, malha de caixas; N = faces)

| Operação | 10k | 50k | 100k |
|---|---|---|---|
| `bm.from_mesh` | 2,6 ms | 6,2 | 12,6 |
| `bm.to_mesh` (+`update`) | 0,6 | 1,5 | 3,0 |
| **1º `scene.ray_cast` após mudança (BVH)** | 4,6 | 12,3 | **28,5** |
| `ray_cast` com BVH pronta | 2,2 µs | 2,3 µs | 2,4 µs |
| `bm.copy()` (snapshot do `Document.begin`) | 2,3 | 11,6 | **28,7** |
| loop Python sobre `bm.faces` (só contar) | 1,4 | 6,8 | 14,2 |
| `foreach_get` co | 0,7 | 1,4 | 2,8 |
| Projetar todos os vértices (numpy, por mudança de vista) | 2,1 | 1,9 | 3,9 |
| **Consulta de vértice por varredura total** (por movimento) | 0,03 | 0,12 | **0,23** |
| Consulta de aresta, varredura total | 0,53 | 2,4 | 5,1 |
| **Consulta de aresta com pré-filtro bbox** (por movimento) | 0,06 | 0,20 | **0,39** |
| Grade (argsort+unique, só vértices) | 2,2 | 2,9 | 6,1 |
| Batch Python de arestas (200k arestas, GUI) | | | **24–28** |
| Reavaliação GN de arestas nativas (GUI) | | | **1,7** |
| `undo_push` / `ed.undo` (GUI, 102k) | | | **0,9 / 3,1** |

### 2.2 Onde o desenho atual vai ficar lento, e como corrigir

1. **`ScreenGrid` (§3.2) é complexidade sem ganho.** A varredura vetorizada sobre arrays projetados em cache (`xy`, `depth`, `lo/hi` das arestas) responde em **0,23 ms (vértices) + 0,39 ms (arestas) a 100k**, dentro do orçamento p50 de 0,8 ms. A inserção de arestas por célula em numpy é a parte mais difícil de escrever e de testar. **Corte o ScreenGrid e o "plano B GPU picking".** `spatial.py` vira: `Projection` em cache por `(view_hash, geometry_version)` com `xy, depth, vis_mask, edge_lo, edge_hi, mids_xy`, reconstruída no 1º movimento após a vista assentar (≈5–8 ms a 100k), e `rect_query` usa os mesmos arrays.
2. **BVH reconstruída a cada movimento durante pré-visualização ao vivo (V11).** Push/Pull e Mover com `preview_update` escrevem a malha a cada movimento. Se a inferência do modal fizer `scene.ray_cast` (fará), cada movimento paga **12–28 ms** de BVH em 50–100k. Correção: no `begin()` da sessão, construir **uma vez** uma `BVHTree.FromBMesh` da parte estática (ou usar `scene.ray_cast` só em outros docs) e fazer o ray do doc em edição contra essa BVH congelada. Orçamento: ≤ 1 ms por movimento para a inferência durante a pré-visualização.
3. **`Document.begin()` com `bm.copy()` = 29 ms a 100k em todo início de operação** (cada segmento de Linha!). Correção: ferramentas sem pré-visualização ao vivo não escrevem na malha até o commit. Para elas, `cancel` = `invalidate()` (relê com `from_mesh` só se alguém precisar). Ferramentas com pré-visualização movem vértices existentes (§7.1 regra 7) e guardam **só as coordenadas originais dos vértices movidos** (O(k)). Topologia nova (extrusão) é criada uma vez no início e removida no cancel.
4. **Commit a 100k faces, custo real:** `to_mesh` 3 + BVH no próximo hover 28 + `foreach_get`/projeção 7 + undo 1 + arestas (Python 25 | GN 2) ≈ **64 ms (Python) / 41 ms (GN)**. Dá para um clique, mas o orçamento "Commit 40 ms" da §7.2 ignora a BVH e a re-projeção. Corrigir a tabela para "**latência até o próximo hover pronto**" ≤ 50 ms a 100k, só com GN.
5. **Batch de arestas em Python (V9)** estoura o orçamento em 2× e precisa iterar instâncias de componentes no Python a cada frame. Com GN (V10), sai do caminho quente.
6. **Loops Python sobre o bmesh inteiro** custam 14 ms a 100k (só contar). `entities.face_cluster`, `validate`, `selection.select_all/invert`, `auto_faces` e `erase_edges` precisam ser **locais** (vizinhança das arestas tocadas). `validate()` completo só em testes e com `SU_DEBUG`. O plano já diz isso para o `add_edge`, mas não para os demais.
7. **`su_cluster` como camada em cache (§3.1):** invalidada a cada edição e custosa para manter. Calcular sob demanda, localmente, a partir da face clicada. Remover a camada.
8. **Redesenho (§7.1 regra 5):** a status bar só redesenha com `status_text_set(None)` (V3). Mudar o rótulo do VCB a cada movimento custa um redesenho da status bar (barato). Os headers da toolbar e do LTS só redesenham quando a ferramenta ativa muda, com `tag_redraw` explícito nessas regiões.
9. **`depsgraph_update_post`** dispara em todo `to_mesh` nosso. O handler deve ser O(1): comparar `update.id` com o conjunto "self-update" e retornar. Nada de varrer objetos.
10. **Orçamentos que faltam na §7.2:** "hover após commit (BVH + reprojeção)", "Python POST_VIEW total por frame ≤ 1 ms com 0 seleção / ≤ 3 ms com 10k arestas selecionadas" e "troca de ferramenta ≤ 5 ms".

---

## 3. Arquitetura e complexidade

### 3.1 O plano está escrito para uma equipe humana, não para 5–7 agentes

- **Fase 0 do WS0 é um gargalo:** todos os contratos, stubs, `props.py` congelado, `catalog.py` completo, harness, `bench.py` e `compare.py` antes de qualquer outro poder integrar. Agentes congelam contratos errados (ex.: `Ev.double`, `Preview.gizmo`, seleção em flags), e aí cada correção se espalha por 7 árvores.
- **"Stubs entregues nos arquivos dos donos marcados `# STUB(WS0)`"** garante conflito de merge: dois agentes escrevendo o mesmo arquivo.
- **Arquivos-registro compartilhados** que todo mundo edita: `su/__init__.py: MODULES`, `catalog.py`, `props.py`, `keymap.TABLE`, `ui/topbar.py` (menus que chamam operadores de todos).
- **Acoplamento visual cruzado:** o transferidor e a caixa de escala do WS6 são desenhados pelo WS3 (`Preview.gizmo` dict + `draw/preview.py`). O WS6 fica bloqueado pelo WS3 para ver o próprio trabalho.
- **Estado duplo de ferramenta:** `STATE.tool_id` × ferramenta ativa do workspace, mais uma "rede de segurança" no `refresh()` do gizmo. É fonte clássica de bug.
- **Integração semanal e ordem de merge WS0→WS2→…** é cadência humana. Agentes precisam de integração **contínua** com gate automático.

### 3.2 Corte (fora da v1 → P2), sem perda para "parecer e funcionar como SketchUp"

`ScreenGrid` e GPU picking; `su_cluster`; cursores desenhados (exigem `cursor_modal_set` na janela inteira; P0 nativo basta); Componentes completos (manter **Grupos**; Componentes viram P2 ou a última onda); abas de cenas; Estruturador; Instrutor; Recortar/Colar; Mão livre, Retângulo girado, Arco de 3 pontos, Torta, Texto, Eixos; Caminhar/Olhar ao redor; tabela Windows; `settings.json` (usar `AddonPreferences`? não existe para templates → JSON mínimo só com idioma); `perf` com overlay (manter só `span`/`stats`); inglês (manter `t()`, só pt_BR preenchido). Isso tira ~35% dos arquivos e ~40% dos cenários GUI.

### 3.3 Conjunto de módulos mais enxuto (6 agentes + integrador)

| Agente | Dono de | Começa com |
|---|---|---|
| **A — Plataforma** (integrador) | `__init__`, `registry`, `state`, `tools/base.py` (dispatcher modal, cliques próprios, hover via gizmo), `undo`, `session`, `keymap` (allow-list), `catalog` (só **layout**: ordem do LTS e da toolbar), `testing.py`, harness | **Fatia vertical** (ver §4) |
| **B — Geometria** (headless puro) | `core/document.py`, `geom.py`, `entities.py`, `selection.py` (Python sets), `edit_context.py` | `add_edge` + `auto_faces` de laço simples + `rebuild_face` com furos, ~40 testes |
| **C — Inferência/VCB** | `spatial.py` (sem grade), `inference.py`, `vcb.py`, `units.py`, `draw/inference_draw.py` | consulta endpoint/eixo sobre arrays em cache |
| **D — Casca de UI + visual** | tema, ícones, toolbar, LTS, status bar, bandeja, `hide.py`, startup/userpref build, céu, eixos, **GN de arestas**, `selection_draw` | build_startup + céu + GN |
| **E — Ferramentas de desenho** | line, rectangle, circle, polygon, arc2, pushpull, offset, followme + `geom_extrude.py` | Retângulo/Círculo sobre o kernel B |
| **F — Ferramentas de edição/construção** | select, eraser, paint, move, rotate, scale, tape, protractor, dimension, nav/câmera + `geom_transform.py`, `guides.py`, `camera.py`, painéis Entity Info/Materiais | Select/Eraser/Move |

Regras que eliminam arquivos compartilhados:
- **Auto-descoberta de módulos:** `su/__init__.py` importa todos os módulos de `su/**` e ordena por `ORDER: int` declarado no próprio módulo. Ninguém edita a lista.
- **Ferramentas se autodeclaram:** cada `tools/x.py` faz `@tool(ToolMeta(...))`. Atalhos e rótulos vêm daí. `catalog.py` contém só as listas de layout (ids), escritas uma vez.
- **Props por dono:** `props.py` só fornece `register_group(owner: str, cls)` e monta `Scene.su` de forma dinâmica. Guias e cotas pertencem ao F, estilo ao D, unidades ao C.
- **Desenho por ferramenta:** `BaseTool.draw_3d(dc)` / `draw_2d(dc)` chamados pela camada PREVIEW, mais uma lib congelada `draw/prims.py` (linha, tracejado, pontos, polígono translúcido, texto, tooltip, transferidor, caixa) entregue pelo D no dia 1. Remove `Preview.gizmo`/`labels` do contrato.
- **Ferramenta ativa = fonte única:** a identidade vem de `workspace.tools.from_space_view3d_mode('OBJECT').idname`. O controlador é resolvido sob demanda no `test_select`/`tool_event` (activate/deactivate quando o id observado muda). `su.tool_activate` só chama `wm.tool_set_by_id`. Remover a "rede de segurança".
- **Menus:** `topbar.py` desenha itens só se `hasattr(bpy.types, "SU_OT_x")`. Nenhum agente precisa editar o menu.

### 3.4 Contratos que faltam

1. `su/testing.py`: `dispatch(ev: Ev)`, `hover(xy)`, `state_dump()`, `set_clock(fn)`, `doc_stats()`, para testar ferramentas de forma determinística **sem** a camada de eventos (ver §5).
2. **Face lógica:** `entities.logical_face(bm, face) -> LogicalFace{faces, outer_loop, inner_loops, plane}` e `geom.rebuild_face(bm, outer, inners, normal, material)`. Com isso, "pontes re-escolhidas a cada edição" vira **reconstruir a face lógica** (apagar faces do cluster → recriar com 2 pontes por furo). É uma função testável no lugar de manutenção incremental espalhada por `add_edge`, `erase_edges`, `pushpull` e `offset`.
3. **Notificação de mudança:** `document.commit()` → `events.emit("geometry", doc_key)`, com assinantes `spatial`, `selection` e `draw`. Hoje está implícito em vários lugares.
4. **Convenções de coordenadas:** região vs janela, pixels **físicos** (`pixel_size=2`), `ui_px()`. Os raios de snap da §2.4 estão em px lógicos e precisam ser multiplicados por `pixel_size`, não por `ui_scale` (aqui `ui_scale=2.0` também; documentar qual).
5. **Política de erro:** exceção em controlador → `cancel()` + report de 1 linha + `perf.errors++`, nunca deixar modal pendurado.

### 3.5 Problemas de ordem

- O WS2 (geometria) é o caminho crítico, mas M1 "Casca" vem antes dele. Inverter: o kernel B começa no dia 1, headless, e a casca roda em paralelo.
- WS5/6/7 "usam stubs até M2" → retrabalho. Com a fatia vertical, eles começam sobre código **real** mínimo (Linha + `add_edge` real simples).
- `build_startup.py` depende de `core/style.py` (WS4) e do tema (WS1): no plano, os dois têm donos diferentes. Na proposta, ficam com o mesmo agente D.

---

## 4. Spikes antes de construir e abordagens a mudar

### 4.1 Já resolvidos por esta crítica (remover da lista)
S3 (V4), S4 (V5), S5 (V3), S7 (V9, e V10 como alternativa), S12 (V11), parte do S10 (V1: há aba; V12: largura persiste).

### 4.2 Spikes que ainda bloqueiam (≤ ½ dia cada, antes de distribuir trabalho)

| # | Spike | Critério de saída |
|---|---|---|
| S-A | **Fatia vertical** (agente A, 1–2 dias): template carrega; 1 ferramenta Linha com hover (gizmo) + modal + endpoint/eixo X + VCB `3` Enter + auto-face de retângulo + commit + undo + arestas GN + status bar | print + teste E2E verde; aí congelar `base.py`, `Ev`, `Inference` e `Document` |
| S-B | **Arestas GN em produção:** cor fora do contexto (`shading.wireframe_color_type='OBJECT'` + `obj.color` afeta arestas soltas?); arestas de componente instanciado; custo com 20 grupos; seleção sem `select_set` | 3 prints + tempos |
| S-C | **`rebuild_face` com furos:** retângulo dentro de face, furo tocando borda, 2 furos, furo dentro de furo, push/pull atravessando | 15 testes headless |
| S-D | **Pré-visualização ao vivo a 50k:** Push/Pull com `to_mesh` por movimento + BVH congelada; medir o frame inteiro (incluindo extração de batch interna do Blender) | p95 ≤ 16 ms a 50k, ou definir o limiar real do "GPU-only" |
| S-E | **Ida e volta de template:** SketchUp Mode → General → SketchUp Mode → sair e reabrir o Blender normal: keyconfig ativo, tema, `inputs.*`, `use_region_overlap`, painéis e headers restaurados; e **crash simulado** (kill -9) seguido de reabrir o Blender normal (as prefs de input vazam? o autosave de prefs grava o valor alterado?) | checklist verde |
| S-F | `build_startup.py`: arrasto simulado das bordas TOOLS/UI até 96/320 px lógicos (com snap de colunas do toolbar) | `region.width` conferido; senão, fazer 1 vez à mão e commitar o binário |
| S-G | Luz de estúdio: `studio_lights.load()` precisa rodar em toda sessão (não persiste por template?); calibrar 255/210/160 | sondas OK |

### 4.3 Abordagens a mudar (resumo)
Bandeja com 1 aba nomeada; status bar via `status_text_set(None)`; cliques múltiplos detectados em Python; keymap por **lista de permissão** em keyconfig próprio (ou, alternativa: overlay em `keyconfigs.addon` com bloqueadores gerados a partir de `keyconfigs.default`, que se limpa sozinho no unregister; decidir no S-E); seleção em Python (sem flags, sem `select_set`); sem objeto ativo, nunca; arestas por GN; sem `ScreenGrid`; snapshot O(k) em vez de `bm.copy()`; BVH congelada na pré-visualização; `undo_push` após qualquer mutação nossa; furos via `rebuild_face`.

---

## 5. Estratégia de testes

**Realista, com ajustes:**

1. **Unit headless:** bmesh, mathutils, numpy e `bpy.data` funcionam em `--background` (`ed.undo_push` até retorna FINISHED). É aqui que deve estar **80%** da cobertura: kernel de geometria, VCB/unidades, inferência com câmera sintética (matrizes numpy) e **controladores de ferramenta via `testing.dispatch`** com `Inference` falsa. Rápido (< 10 s) e paralelizável entre agentes.
2. **GUI E2E (`--enable-event-simulate`):** confiável **desde que** (a) a splash esteja fechada: o `userpref.blend` do template tem `show_splash=False`, mas em execução com `--factory-startup` o harness manda `ESC` primeiro e confere que nenhum popup está aberto; (b) nenhuma tecla de teste caia num atalho do Blender que abra menu (V5); (c) cada passo espere ≥ 1 tick de timer e **verifique o efeito** (assert por passo, não só no fim). Duplo clique não pode vir do Blender (V6) → helper `double_click` = dois PRESS/RELEASE com `testing.set_clock` avançando < 0,35 s.
3. **Tamanho de janela:** `-p 0 0 1440 900` (cabe em 1512×982 pt). Todas as coordenadas vêm de `region.x/y/width/height` (pixels físicos). Nada de constantes em px.
4. **Paralelismo:** vários agentes abrindo Blender GUI ao mesmo tempo funciona (cada um com `BLENDER_USER_CONFIG` isolado), mas mede performance com ruído e pode roubar foco. O harness deve usar um lock (`flock /tmp/su_gui.lock`) para cenários GUI, e `bench.py` roda só pelo integrador.
5. **`bench.py`:** "500 MOUSEMOVE numa espiral" num único tick não mede frame (eventos são processados sem redesenho entre eles). Distribuir em ticks (ex.: 10 eventos por tick) e medir via `perf.span` dentro do `test_select`/modal + tempo entre callbacks POST_PIXEL.
6. **Prints e sondas:** `screen.screenshot` capta o framebuffer da janela em sRGB (OK para sondas de cor com view transform `Standard`). A comparação com o SketchUp deve usar **frações da região**, não pixels absolutos (DPI diferente). As sondas de layout por "centro de cada botão vs catálogo" são frágeis com ícones de 20 px; usar `testing.state_dump()` para a ordem e o print só para cor e posição grosseira.
7. **Cenários por agente:** cada agente tem 1 cenário E2E curto (≤ 30 s) mais unit tests. Um cenário "fumaça" global (fatia vertical) roda em todo merge.

---

## 6. Mudanças obrigatórias no plano (numeradas)

1. **Substituir a Fase 0 por uma fatia vertical** (S-A) feita por um único agente. Congelar `base.py`, `Ev`, `Inference`, `Document` e `selection` **depois** dela, a partir de código que roda.
2. **Reduzir para 6 agentes + integrador** com a divisão da §3.3. O kernel de geometria começa no dia 1, headless.
3. **Proibir stubs em arquivos de outro dono.** Cada dono entrega sua versão mínima real. Stubs, se houver, ficam em `su/_stubs/` importados por *fallback*.
4. **Auto-descoberta de módulos** (`ORDER` por módulo), **ferramentas autodeclaradas** (`@tool(ToolMeta)`), **props por dono** (`props.register_group`) e **menus por `hasattr`**. `catalog.py` contém só layout.
5. **Ferramenta ativa com fonte única** (workspace tool). Remover `STATE.tool_id` como verdade e a "rede de segurança" do gizmo.
6. **§4.4:** aceitar 1 aba "Bandeja padrão"; remover `SU_PT_tray_title`; invariante **sem objeto ativo**; tratar a categoria "glTF Variants".
7. **§3.4/S5:** redesenho da status bar = `workspace.status_text_set(None)`. A prop do WM não redesenha.
8. **§3.6:** duplo e triplo clique detectados em Python com relógio injetável; ignorar `DOUBLE_CLICK`.
9. **§5.1:** keymap por **lista de permissão**. Troca de ferramenta em "Object Mode". Teste "nenhuma tecla imprimível abre popup do Blender" (varrer A–Z, 0–9 e pontuação com e sem Shift).
10. **§3.3/§4.8:** arestas via **modificador GN** (`su_visible` por aresta). O POST_VIEW Python só para overlays pequenos. Atualizar R1 e R20.
11. **§3.8:** seleção em conjuntos Python; sem flags persistidas; sem `obj.select_set`.
12. **§3.2:** remover `ScreenGrid` e GPU picking. `spatial` = projeção em cache + varredura vetorizada (medido: 0,23 + 0,39 ms a 100k).
13. **§2.4 Document:** remover `bm.copy()` do `begin()`. Cancel O(k) (coordenadas originais + topologia criada). BVH congelada da parte estática durante pré-visualização ao vivo.
14. **§3.7:** regra "toda mutação nossa termina em `undo_push`", incluindo `session.on_load_post`. Teste "abrir → desfazer → `Modelo` existe".
15. **§3.1:** furos via `geom.rebuild_face` (reconstrução da face lógica). Remover `su_cluster`.
16. **§7.2:** corrigir orçamentos com os números medidos. Adicionar "latência commit→hover pronto ≤ 50 ms a 100k", "Python POST_VIEW ≤ 1 ms/frame (sem seleção)" e "batch de arestas: N/A (GN)".
17. **§7.1:** proibir loop Python sobre todo o bmesh em qualquer caminho de usuário (`validate` só em teste/debug). Operações locais à vizinhança tocada.
18. **§5.2 / `prefs.py`:** backup e restore só do que **não** é por template (V13). Tirar `show_navigate_ui` e `ui_scale` da lista. Incluir o spike S-E (crash/autosave).
19. **§8.2:** harness com `-p 0 0 1440 900`, fechamento da splash, assert por passo, lock GUI e `testing.py` para testes determinísticos. `bench.py` com eventos distribuídos em ticks.
20. **§1.2/§9:** mover para P2 os itens da §3.2 desta crítica (Componentes, abas de cena, Estruturador, Instrutor, clipboard, Mão livre, Retângulo girado, Arco de 3 pontos, Torta, Texto, Eixos, Caminhar, Olhar ao redor, cursores desenhados, inglês, tabela Windows). Entregar um P0 sólido primeiro.
21. **Desenho de ferramentas:** `BaseTool.draw_3d/draw_2d` + `draw/prims.py` congelado no dia 1. Remover `Preview.gizmo` e o desenho de gizmos de outras ferramentas pelo WS3.
22. **Atualizar a lista de spikes** (§9.1): remover S3, S4, S5, S7 e S12 (resolvidos); adicionar S-A…S-G.
