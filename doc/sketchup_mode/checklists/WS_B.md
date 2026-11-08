# WS_B — Agente B (Geometria)

Legenda: `[ ]` pendente · `[~]` em andamento · `[x]` feito. Brief: `PLANO.md` §9.2-B (sub-checklist copiado abaixo; o agente B mantém este arquivo).

## Entrega mínima da fatia (§9.1-MA, linha B)
- [x] `Document` (write/begin/preview_write/cancel/invalidate, `root()` "Modelo", `get/active/visible_documents/invalidate_all/create_group`)
- [x] `add_edge` (já a versão completa), `auto_faces` (laço simples e contenção), `rebuild_face` (CDT tipo 5) + testes headless
- [x] Pedido extra do usuário: `erase_faces` / `erase_edges` com comportamento SketchUp (ROTEIRO_CASA "Apagar uma face", AF-1…AF-6 no kernel)

## Sub-checklist §9.2-B
1. [x] Document + camadas (`su_bridge su_soft su_hidden su_curve su_back_mat=1`) + raiz no evento "load"
2. [x] `rebuild_face` (CDT tipo 5, pontes, furo passante) — 15 testes (dentro, tocando borda, 2 furos, furo em furo, L côncavo)
3. [x] `add_edge` completo (solda, cruzamentos, divide faces) + `auto_faces` com contenção
4. [x] `erase_edges/faces`, `merge_coplanar`, cura (AC-LIN-3 no kernel)
5. [x] `ensure_planar`/`is_planar` (dobra)
6. [x] entidades: `logical_face`, `surface`, `pick_entity`, curvas + metadados
7. [x] seleção em sets + `snapshot/restore/remap` + expandir/conectado/tudo/inverter
8. [x] edit_context + `create_group` + helpers de Explodir — todos emitem `events.emit("doc", doc_key=…)` para objeto-documento novo
9. [x] `validate()` em todos os testes

## Aceite e comandos (referência)
- **Aceite**: AC-LIN-1..4 e AC-RET-3/4 no nível do kernel; AC-SEL-1..3 com `testing.dispatch`; AC-MOV-5..7 em conjunto com F (planaridade).
- **Comandos**: `tools/sketchup_mode/run_unit.sh test_b_` · `tools/sketchup_mode/run_gui.sh scn_b`

## Notas

- **Kernel** (`su/core/geom.py`): `add_edge` solda (vértice ou divide a aresta), divide nos cruzamentos e nos vértices sobre o segmento, reaproveita aresta existente (redesenhar = "tocar"; é a cura). `auto_faces` monta, para cada plano que passa pela aresta tocada e uma vizinha, o arranjo planar das arestas do plano (meias-arestas, poda de pendentes e de pontes do grafo, contenção → furos). Faces lógicas atravessadas por aresta tocada são dissolvidas e as regiões recriadas com o mesmo material e lado; regiões sem face cujo contorno externo tem aresta tocada viram face nova. Orientação de face nova: coerente com as vizinhas (fecha o sólido → para fora), senão horizontal → −Z.
- `rebuild_face` = CDT `output_type=5`; os loops são passados **CCW** (com CW o `orig_faces` da CDT sai trocado); `orig_faces` diz em que furo cada peça está; arestas não-entrada = `su_bridge`.
- `erase_faces`: apaga a face lógica inteira (com as pontes), arestas ficam. `erase_edges`: faces que dependem da aresta somem; duas faces lógicas coplanares separadas pela aresta se fundem (região recriada pela CDT); vértice que fica sem aresta é apagado; vértice com 2 arestas colineares é dissolvido (AF-3c: a aresta de 8 m volta inteira).
- **Undo headless funciona** (`ed.undo_push`/`ed.undo`/`ed.redo` em `--background`): AF-6 testado no kernel (contagens, normais, materiais). A restauração de seleção do AF-6 é de A/F.
- `Document` resolve `obj` pelo nome a cada acesso (o undo de memfile realoca os IDs); o `bm` é descartado no evento "undo"/"load" e quando o ponteiro da malha muda.
- `mathutils` é float32: comparar áreas/comprimentos com ~1e-5.

### Itens 5–8 (bloco 2)
- **Dobra** (`geom.ensure_planar`): divide cada face não plana por diagonais visíveis (prioridade: as duas metades planas → menor não-planaridade → diagonal mais curta), recursivo; `face_split` copia material/verso. AC-MOV-5 → 1 aresta de dobra, 7 faces planas; AC-MOV-6 (cumeeira) não precisa de dobra.
- **Entidades** (`entities.py`): `logical_face` (loops externo CCW / furos CW pela normal), `surface` (flood por `su_soft`), `pick_entity` (curva / aresta / superfície / face lógica; atualiza os índices), `curve_edges`, metadados de curva em `obj.su_doc.curves` (JSON, volta com o undo).
- **Seleção** (`selection.py`): sets de `Ref(doc_key, kind, index)`; `entity/expand_face/expand_edge/connected` devolvem refs (o chamador aplica); `select_all/invert` no contexto atual (geometria + objetos-filho); `version()` + evento "selection" a cada mudança; poda no evento "geometry" e no `restore` contando pela **malha** (o undo restaura a seleção antes de o evento "undo" invalidar o bm); `remap(doc_key, {'EDGE': {old: new}, 'FACE': {...}})`.
- **`Document.write(undo_key, select=None)`**: `select` define a seleção pós-operação entre `before_change` e `push`. Excluir = `write(undo_key=..., select=())`: o undo devolve a seleção de antes (AF-6, testado headless e na GUI). `write` também chama `index_update` (índice do bm == índice da malha).
- **Grupos**: `create_group` emite "doc"; `group_from(doc, faces, edges, name)` (Criar grupo: move faces lógicas + arestas; arestas usadas por faces de fora ficam também no doc; o grupo herda a matriz e os slots); `explode(obj)` (solda os vértices no doc pai, mapeia materiais por identidade, re-parenta filhos mantendo a matriz de mundo, apaga o objeto). Explodir não cria objeto-documento novo, então não emite "doc". `edit_context.enter/exit` limpam a seleção.
- Testes: `test_b_geom` (41) + `test_b_document` (9) + `test_b_entities` (10) + `test_b_selection` (12) = 72; GUI `scn_b` com 40 verificações e prints em `doc/sketchup_mode/screens/b_*.png`.
