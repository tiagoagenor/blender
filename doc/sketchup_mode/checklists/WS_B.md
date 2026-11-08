# WS_B — Agente B (Geometria)

Legenda: `[ ]` pendente · `[~]` em andamento · `[x]` feito. Brief: `PLANO.md` §9.2-B (sub-checklist copiado abaixo; o agente B mantém este arquivo).

## Sub-checklist §9.2-B
1. [ ] Document + camadas (`su_bridge su_soft su_hidden su_curve su_back_mat=1`) + raiz no evento "load"
2. [ ] `rebuild_face` (CDT tipo 5, pontes, furo passante) — 15 testes (dentro, tocando borda, 2 furos, furo em furo, L côncavo)
3. [ ] `add_edge` completo (solda, cruzamentos, divide faces) + `auto_faces` com contenção
4. [ ] `erase_edges/faces`, `merge_coplanar`, cura (AC-LIN-3 no kernel)
5. [ ] `ensure_planar`/`is_planar` (dobra)
6. [ ] entidades: `logical_face`, `surface`, `pick_entity`, curvas + metadados
7. [ ] seleção em sets + `snapshot/restore/remap` + expandir/conectado/tudo/inverter
8. [ ] edit_context + `create_group` + helpers de Explodir — todos emitem `events.emit("doc", doc_key=…)` para objeto-documento novo
9. [ ] `validate()` em todos os testes

## Aceite e comandos (referência)
- **Aceite**: AC-LIN-1..4 e AC-RET-3/4 no nível do kernel; AC-SEL-1..3 com `testing.dispatch`; AC-MOV-5..7 em conjunto com F (planaridade).
- **Comandos**: `tools/sketchup_mode/run_unit.sh test_b_` · `tools/sketchup_mode/run_gui.sh scn_b`

## Notas
