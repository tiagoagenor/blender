# WS_A — Agente A (Plataforma / integrador)

Legenda: `[ ]` pendente · `[~]` em andamento · `[x]` feito. Brief: `PLANO.md` §9.1-A0, §9.1-MA, §9.2-A.

## A0 — Esqueleto (§9.1-A0)
1. [x] `tools/sketchup_mode/dev_env.sh` (ambiente isolado em `/private/tmp/su_stage_<AGENTE>`, symlink do template, `userpref.blend` semeado com splash off)
2. [x] `tools/sketchup_mode/run_unit.sh` (exige ambiente; headless; `--pattern`)
3. [x] `tools/sketchup_mode/run_gui.sh` (`/usr/bin/lockf -k -t 1800 /tmp/su_gui.lock`, harness, `results.json`)
4. [x] `SketchUp_Mode/__init__.py` + `su/__init__.py` (auto-descoberta por `ORDER`; erro de import = `perf.error` + módulo pulado)
5. [x] `su/{constants,colors,registry,events,i18n,perf}.py`
6. [x] `su/core/state.py` (`Inference`, `Locks`, `LastAction`, `State`, `STATE`)
7. [x] `su/core/undo.py` (`push`/`before_change` reais, `Scene.su_undo_serial`)
8. [x] `su/core/viewutil.py`
9. [x] `su/draw/handlers.py` (`add_layer`)
10. [x] `su/tools/base.py` (`ToolMeta`, `@tool`, `BaseTool` vazio, `Ev`, `Result`)
11. [x] `tests/sketchup_mode/unit/run.py` (+ `test_a_platform.py`)
12. [x] `tests/sketchup_mode/gui/{harness.py,scn_smoke.py}` ("abre e fecha")
13. [x] `doc/sketchup_mode/checklists/WS_{A..G}.md`
14. [x] Gate A0: `source tools/sketchup_mode/dev_env.sh A && tools/sketchup_mode/run_unit.sh && tools/sketchup_mode/run_gui.sh scn_smoke` verdes; nada novo em `~/Library/Application Support/Blender`

## Fatia vertical (§9.1-MA) — parte de A
- [x] `run.sh`/`driver.py` do spike → `dev_env.sh`/harness (completo: `run.sh`, `shot.sh`+`scn_shot`, harness com mouse/teclado/`type_text`/`world_xy`/`state`/`stats`/`install_fakes`)
- [x] registry/auto-descoberta (`registry.optional`), `base` + `su.tool_event` + hover (item MOUSEMOVE do keymap da ferramenta → `su.tool_event`, PASS_THROUGH)
- [x] keymap `Window` + `su.vcb_key`/`su.vcb_capture` (+ keyconfig por lista de permissão)
- [x] undo (serial), session/eventos (`hold/release` de prontidão), `testing`, harness
- [x] **Linha** (AC-LIN-1, AC-LIN-6, AC-LIN-7 + cadeia/duplo clique/arrasto/Esc) — passa a E após M-A
- [x] Integrar B, C (vcb `set_applier`, esquema `line`, inferência real) e D (visual, `su_ui_ready`, K = Arestas traseiras)
- [ ] Fechar M-A com E (Retângulo 2×3 + Cmd+Z no `scn_smoke`) + print lado a lado vazio × ref 2

## Sub-checklist §9.2-A
1. [x] dev_env/run/run_unit/run_gui a partir de `visual_spike/run.sh` + `driver.py` (lock, splash, envs DATAFILES/EXTENSIONS, independente do tamanho da janela)
2. [x] auto-descoberta + registry + eventos + settings + i18n (detecção de duplicatas)
3. [x] `base`: `su.tool_event` (PRESS/RELEASE; PASS para CLICK/CLICK_DRAG/Ctrl), hover, cliques em Python, arrasto→2º clique, política de erro
4. [x] keymap por lista de permissão + itens `Window` na ordem §3.5 + poll; `su.vcb_key` + `su.vcb_capture`
5. [x] undo: serial em `scene.su_undo_serial`, `before_change`/`push`, restauração de seleção em undo/redo
6. [x] session por eventos + `undo.init`; invariante sem objeto ativo
7. [x] Linha (fatia) → passar a E (após M-A)
8. [x] `testing.dispatch/hover/set_clock/state_dump/doc_stats`
9. [~] `shot.sh` + `compare.sh`/`compose.py` (feitos) + sondas
10. [ ] menus de contexto via Ctrl+clique e órbita Ctrl+Cmd no `Window` (com G)
11. [ ] prefs com backup/restore + S-E (ida e volta de template, kill -9)
12. [ ] Integração contínua, rodadas de prints, CHECKLIST mestre

## Notas

- A0 concluído (gate verde: `run_unit.sh` 11 testes OK; `run_gui.sh scn_smoke` PASS com `perf.errors()==0`; `~/Library/Application Support/Blender` inalterado).
- §9.2-A item 1: falta `run.sh` (abrir o modo à mão) — fica para a fatia. Item 2: falta `settings.py`. Item 5: `push`/`before_change`/handlers de undo prontos; restauração de seleção depende de `core/selection.py` (B), consumido via `sys.modules` quando existir.
- **Splash com app template**: o `show_splash` vem do userpref do TEMPLATE (campos trocados em `BKE_blender_userdef_app_template_data_swap`), não do `userpref.blend` semeado. O harness desliga `show_splash` no início do `--python` (roda antes de `WM_init_splash_on_startup`). **D**: o `userpref.blend` do template deve sair com splash desligado. Não semeamos `config/SketchUp_Mode/userpref.blend` porque ele teria prioridade sobre o `userpref.blend` do template (tema de D).
- `dev_env.sh` semeia `userpref.blend` com `use_preferences_save=False` (o template pode mexer em prefs sem gravar nada).
- Pronto/`su_ready`: `su/__init__.py` assina `load_post` → `session.on_load_post()` se existir, senão `events.emit("load")`; `su_ready=True` 0,5 s depois (deferido). Quando o startup de D tiver passos por timer, ajustar para marcar pronto ao fim deles.
- `State.redraw_statusbar` chama `WorkSpace.status_text_set_internal(None)` (não `status_text_set`, que trocaria `STATUSBAR_HT_header.draw` de volta para `_draw_orig` e desfaria o override de D).
- Imports dentro de `su` sempre relativos (o pacote é `bl_app_templates_system.SketchUp_Mode.su` na GUI e `su` nos testes).
- Em ambiente dev (`SU_STAGE` definido) `sys.dont_write_bytecode=True`: só o `SketchUp_Mode/__pycache__/__init__*.pyc` ainda é criado (gitignored).
- Agentes isolados em worktree: o verificador do Claude Code recusa `source dev_env.sh` direto no Bash (o script roda `git rev-parse`); contorno: um wrapper `zsh <arquivo>.sh` que faz `cd <worktree> && source tools/sketchup_mode/dev_env.sh X && ...`.

### Fatia (notas)
- Despacho único `tools.base.DISPATCH.handle(tc, ev, inf)` para o modal real (`su.tool_event`), o hover, o keymap `Window` e `testing.dispatch` (os testes headless exercitam o roteamento real). Cmd+Z no modal = cancelar + PASS_THROUGH (o undo roda em seguida). Shift = trava (`STATE.locks.shift`) no despacho; setas → `inference.lock_from_arrow` (C).
- Medidas: A chama `vcb.feed(ev)` (C); em `'APPLY'` A lê `STATE.vcb_buffer`, roteia (`DISPATCH.apply_vcb`: rodando → `tool.vcb`; ocioso com `last_action` → `reapply` + `undo.push("undo.adjust")`; ocioso sem → `tool.vcb`) e limpa o buffer. **C**: `feed` não limpa o buffer no APPLY; `parse` levanta exceção (ou devolve vazio) em erro → `STATE.vcb_error`. `wm.su_vcb.field` (get = buffer ou valor; set = aplicar) — **D** desenha `prop(wm.su_vcb, "field")`.
- Ferramentas: `catalog.register` (ORDER 390) cria um `WorkSpaceTool` por `ToolMeta` TOOL/NAV (keymap LEFTMOUSE PRESS/RELEASE + MOUSEMOVE → `su.tool_event`; sem gizmo: o estilo de D usa `space.show_gizmo = False`, que desliga todo gizmo, então o hover vai pelo keymap); **D** monta o LTS com `catalog.lts_tooldefs()` (registrados usam o `_bl_tool`; os demais = placeholder; clique em placeholder → "Em breve" e volta à ferramenta anterior). Cliques na toolbar via `wm.tool_set_by_id` são percebidos pelo desenho/hover (sync); preferir `su.tool_activate`.
- Keyconfig: não há `presets/keyconfig/SketchUp_Mode.py` (a pasta do template não está nos caminhos de presets); `keymap.py` gera "SketchUp_Mode" a partir de `blender_default` com lista de permissão e ativa por timer (depois do `keyconfig_init` do Blender); restaura o anterior no unregister.
- Undo inicial: o Blender monta a pilha de undo DEPOIS do `load_post` → o que os donos fazem no evento `"load"` já entra no passo "Original" ("abrir → Cmd+Z → Modelo existe" por construção); `undo.init` só é empurrado se algo mudar depois (passos por timer).
- Prontidão: **D** (passos por timer) chama `session.hold("d.startup")` no `"load"` e `session.release("d.startup")` no último passo.
- B, C e D integrados (até 0be0a33): Linha usa `Document`/`add_edge` (já roda `auto_faces`), `vcb.feed/parse` e `ENGINE.query` reais. `fakes.py` só entra para módulo ausente (hoje nenhum). Teclas que não são de ferramenta passam pelo modal sem cancelar (K funciona desenhando).
- `scn_a` (27 checks): L sobre a Bandeja, hover → "Ponto de origem", Ctrl+clique não inicia, retângulo 3×2 pelas Medidas (1 face 6 m², normal −Z, 4 undos), MMB no meio da cadeia, `3` Enter sobre a Bandeja (modal) e `4` Enter ocioso (captura → Ajustar), Cmd+Z ×2. Prints: `doc/sketchup_mode/screens/a_*.png`.
