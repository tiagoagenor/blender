# WS_C — Agente C (Inferência / Medidas)

Legenda: `[ ]` pendente · `[~]` em andamento · `[x]` feito. Brief: `PLANO.md` §9.2-C (sub-checklist copiado abaixo; o agente C mantém este arquivo).

## Sub-checklist §9.2-C
1. [ ] `units` (pt-BR via AppleLocale, m/cm/mm/pol/pés, ângulo, inclinação)
2. [ ] `vcb.parse` com todos os esquemas + `feed` (regras §3.5)
3. [ ] `spatial.projection/points_near/edges_near/rect_query` + `ray_cast` (idx % n, side, skip)
4. [ ] pipeline de inferência completo (prioridade, oclusão, eixos, paralela/perpendicular, do ponto, travas, plano livre, guias, centro, em contexto)
5. [ ] histerese; `hover_plane`
6. [ ] `inference_draw` (marcadores, linhas, pontilhadas, travada grossa, magenta) + tooltips com 2ª linha
7. [ ] P1: tangente, semicírculo, quadrado/seção áurea, `~`

## Aceite e comandos (referência)
- **Aceite**: AC-INF-1..6, AC-VCB-1 (unit); AC-EMP-3 e AC-MOV-4 junto com E/F.
- **Comandos**: `tools/sketchup_mode/run_unit.sh test_c_` · `tools/sketchup_mode/run_gui.sh scn_c`

## Notas
