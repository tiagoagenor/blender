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
- [ ] `run.sh`/`driver.py` do spike → `dev_env.sh`/harness (completo)
- [ ] registry/auto-descoberta, `base` + `su.tool_event` + gizmo de hover
- [ ] keymap `Window` + `su.vcb_key`/`su.vcb_capture`
- [ ] undo (serial), session/eventos, `testing`, harness
- [ ] **Linha**

## Sub-checklist §9.2-A
1. [~] dev_env/run/run_unit/run_gui a partir de `visual_spike/run.sh` + `driver.py` (lock, splash, envs DATAFILES/EXTENSIONS, independente do tamanho da janela)
2. [~] auto-descoberta + registry + eventos + settings + i18n (detecção de duplicatas)
3. [ ] `base`: `su.tool_event` (PRESS/RELEASE; PASS para CLICK/CLICK_DRAG/Ctrl), gizmo de hover, cliques em Python, arrasto→2º clique, política de erro
4. [ ] keymap por lista de permissão + itens `Window` na ordem §3.5 + poll; `su.vcb_key` + `su.vcb_capture`
5. [~] undo: serial em `scene.su_undo_serial`, `before_change`/`push`, restauração de seleção em undo/redo
6. [ ] session por eventos + `undo.init`; invariante sem objeto ativo
7. [ ] Linha (fatia) → passar a E
8. [ ] `testing.dispatch/hover/set_clock/state_dump/doc_stats`
9. [ ] `shot.sh` + `compare.sh`/`compose.py` + sondas
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
