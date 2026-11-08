# WS_C — Agente C (Inferência / Medidas)

Legenda: `[ ]` pendente · `[~]` em andamento · `[x]` feito. Brief: `PLANO.md` §9.2-C (sub-checklist copiado abaixo; o agente C mantém este arquivo).

## Entrega mínima da fatia (§9.1-MA, linha C)
- [x] `units` + `vcb.parse` (comprimento, `L;W`) headless
- [x] inferência mínima (extremidade + eixos) + `inference_draw` mínimo
- (entregue além do mínimo: ponto central, em aresta, em face, origem, interseção, guias via provedor, paralela/perpendicular, perpendicular à face, "do ponto", travas, histerese, `hover_plane`, `rect_query`, `ray_cast` com `skip`/cópia de verso)

## Sub-checklist §9.2-C
1. [x] `units` (pt-BR via AppleLocale, m/cm/mm/pol/pés, ângulo, inclinação `3:12`) — `Scene.su_units`
2. [x] `vcb.parse` com todos os esquemas + `feed` (regras §3.5)
3. [x] `spatial.projection/points_near/edges_near/rect_query` + `ray_cast` (idx % n, side, skip)
4. [x] pipeline de inferência (prioridade, oclusão, eixos, paralela/perpendicular, do ponto, travas, plano livre, guias, centro, em contexto)
5. [x] histerese; `hover_plane`
6. [x] `inference_draw` (marcadores, linhas, pontilhadas, travada grossa, magenta) + tooltips com 2ª linha — a ScreenTip usa `prims.tooltip` (D); marcadores/linhas em GPU próprio (2D)
7. [~] P1: semicírculo (`arc_semicircle`), quadrado/seção áurea (`rect_shape`), `~` (`format_length/format_angle(mark_approx=True)`) feitos; **tangente** pendente

## Aceite e comandos (referência)
- **Aceite**: AC-INF-1..6, AC-VCB-1 (unit) — cobertos em `test_c_inference.py` / `test_c_units_vcb.py`; AC-EMP-3 (padrão "linha travada + face" testado no motor) e AC-MOV-4 junto com E/F.
- **Comandos**: `tools/sketchup_mode/run_unit.sh test_c_` · `tools/sketchup_mode/run_gui.sh scn_c`
- Prints: `doc/sketchup_mode/screens/c_inferencia.png` (v1) e `c_inferencia_v2.png` (grade 3×2: extremidade verde, ponto central ciano, eixo vermelho sólido, eixo azul travado grosso, "Do ponto" pontilhado verde, extremidade num grupo real em roxo + "no grupo").

## Notas (para A/E/F/G)
- **`viewutil.ui_px` devolve 0 em background** (`system.ui_scale == 0`): o motor usa `inference._px()` (1:1 quando 0). A pode corrigir no `viewutil`.
- **vcb.feed** devolve `'CANCEL'` para Esc com buffer (só a digitação é cancelada; a ferramenta continua); Esc com buffer vazio → `'PASS'` (a ferramenta cancela). Em `'APPLY'` o chamador usa `vcb.values(schema)` (None + `STATE.vcb_error` se inválido) e `vcb.take()`.
- **vcb.parse** levanta `ValueError` quando inválido; esquemas no docstring de `vcb.py` (`length`, `length2`, `line`, `distance`, `angle`, `sides`, `radius`, `arc`, `segments`, `scale`, `number`). Rótulos da caixa: chaves `vcb.*` (ex.: `vcb.length` = "Comprimento").
- **vcb.apply_text** (campo clicável) chama o aplicador instalado por A com `vcb.set_applier(fn)`.
- **QueryCtx**: `anchor` = último clique; `line=(co, dir[, linear])` restringe à linha (Empurrar/puxar: linha da normal → encaixe em face/ponto); `plane=(co, n)` restringe ao plano (Retângulo); `exclude`/`skip` para geometria em movimento. `previous` opcional (o motor lembra o último resultado).
- **Indicadores lineares**: `inference_draw` desenha a linha pontilhada (cor do eixo / magenta) de `inf.ref_point` até `inf.point`, e sólida grossa quando `inf.locked`. O elástico da ferramenta continua sendo da ferramenta (pode usar `inf.linear` para a cor).
- **Do ponto**: `inf.linear == 'FROM_POINT'`, `inf.ref_point` = ponto de referência, `inf.direction` = eixo; o dispatcher de A chama `ENGINE.acquire_tick(inf, clock())` a cada hover.
- **Guias (G)**: `inference.set_guides_provider(fn)`, `fn() -> {'points': [Vector], 'lines': [(co, dir)]}`.
- **Em contexto**: `Inference.in_context` = `'GROUP'`/`'COMPONENT'` para geometria de um documento que não é a raiz nem o contexto em edição (B: `su_doc.kind` `''` = grupo).
- **Setas para o plano — DECIDIDO (coordenador)**: a seta trava a **normal** do plano de desenho no eixo (convenção do transferidor): **↑ = azul → plano horizontal** (círculo deitado), **→ = vermelho → plano YZ**, **← = verde → plano XZ**. `hover_plane` já faz assim. **Aceite AC-CIR-4 corrigido para E**: "`→` (ou `←`) antes do clique no vazio → círculo vertical (normal vermelha/verde); `↑` → círculo horizontal (normal azul)".
- Rótulos de paralela/perpendicular: "Paralela à aresta", "Perpendicular à aresta", "Perpendicular à face" (o Apêndice A lista só "Paralela"/"Perpendicular").
- **Prints no harness (para A)**: `screen.screenshot` às vezes devolve um quadro antigo; o `scn_c` chama `bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=3)` antes de cada print e repete até duas capturas iguais. `inference_draw.last_drawn()` diz o que a camada desenhou.
- **Linhas lineares (revisão v2)**: no eixo / paralela / perpendicular = linha **sólida** na cor do eixo (magenta para paralela/perpendicular) do ponto inicial até o cursor, grossa quando travada; **"Do ponto" = pontilhada** na cor do eixo. Marcadores roxo-magenta (115,90,165) só para geometria dentro de grupo/componente (RESEARCH §5.1); ponto central fora de grupo = ciano (49,192,200).
- **Centro (B/E)**: pairar uma aresta de curva (`su_curve` ≠ 0) torna o centro inferível (últimas 2 curvas). O centro vem de `entities.get_curve_meta(doc, cid)["center"]` = `[x, y, z]` **no espaço local do documento** — E deve gravar esse campo ao criar círculo/arco/polígono.
- **Formas (E)**: `inference.rect_shape(q, corner, p, u, v)` → Inference com `tooltip_key` `inf.square`/`inf.golden` (ponto ajustado na diagonal; `inference_draw` desenha a diagonal pontilhada azul) ou None; `inference.arc_semicircle(q, a, b, bulge_point, normal)` → `(bulge, 'inf.half_circle' | '')`. A ferramenta põe o resultado em `STATE.inference` para desenhar.
