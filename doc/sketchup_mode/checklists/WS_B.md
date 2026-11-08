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
5. [ ] `ensure_planar`/`is_planar` (dobra)
6. [ ] entidades: `logical_face`, `surface`, `pick_entity`, curvas + metadados
7. [ ] seleção em sets + `snapshot/restore/remap` + expandir/conectado/tudo/inverter
8. [~] edit_context + `create_group` + helpers de Explodir — todos emitem `events.emit("doc", doc_key=…)` para objeto-documento novo
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
- `edit_context` mínimo (pilha de nomes); `entities`/`selection` ainda não existem (itens 6 e 7).
- Testes: `test_b_geom.py` (41) + `test_b_document.py` (9); GUI `scn_b` com prints em `doc/sketchup_mode/screens/b_*.png`.
