# Crítica R3 (final) — Especialista Blender/Python

Revisão do `PLANO.md` v3 e do `visual_spike/`, para execução por sub-agentes.
**[VERIFICADO]** = executado agora no Blender 5.2.2 / macOS deste Mac.

## 1. Veredito: **GO**, condicionado às 6 correções de texto da §4 (todas na §9/§8.2, sem mudança de arquitetura)

Os contratos estão fechados. A R1 e a R2 foram incorporadas, e o spike visual dá um ponto de partida real. O que falta é **infraestrutura de execução paralela**: hoje, 6 agentes seguindo a §9 ao pé da letra quebrariam uns aos outros no primeiro dia.

## 2. Bloqueios restantes (só estes)

| # | Problema | Evidência |
|---|---|---|
| B1 | **`flock` não existe no macOS.** O comando de lock da §8.2 falha. Existem `/usr/bin/lockf` e `/usr/bin/shlock`. | [VERIFICADO] `which flock` → não encontrado; `lockf -k -t 30 /tmp/x.lock cmd` serializou 2 processos corretamente |
| B2 | **Nenhum isolamento de git entre agentes.** A §9.0 não fala de worktree nem de branch. Agentes na mesma árvore colidem no índice do git. Pior: a auto-descoberta importa **todos** os módulos de `su/**`, então um arquivo pela metade de outro agente derruba o Blender de todos. O symlink de staging também precisa apontar para a árvore **do agente**. | Desenho da §2.3/§9.0 |
| B3 | **Não existe passo "A0".** B, C, D e E dependem de `constants`, `events`, `i18n`, `registry`, `state` (Inference/STATE), `undo.push/before_change`, `handlers.add_layer`, `base.ToolMeta/@tool/BaseTool` e `dev_env.sh`, todos de A. A §9.1 diz "dias 0–1 em paralelo", mas sem esse esqueleto ninguém roda nada no Blender. | §9.1 |
| B4 | **Isolamento incompleto.** Use `BLENDER_USER_RESOURCES`, que redireciona config, scripts, datafiles e extensions de uma vez, mais **`TMPDIR` por agente**. Sem `TMPDIR` próprio, todos dividem `bpy.app.tempdir` (onde o `.sl` da luz é gravado), o `quit.blend` e os autosaves. Também é preciso **semear** um `userpref.blend` com splash desligada: com a config vazia, o Blender mostra o "Quick Setup", que engole eventos (R1 V7). | [VERIFICADO] Com `BLENDER_USER_RESOURCES` + `TMPDIR`: `user_resource(CONFIG/SCRIPTS/DATAFILES/EXTENSIONS)` e `tempdir` ficaram todos dentro da pasta isolada; `save_userpref` gravou lá; **0 arquivos** novos em `~/Library/Application Support/Blender` |
| B5 | **Objeto novo sem a cópia de verso.** `create_group` (B), Explodir, cópias de grupo (F), Texto 3D (G) e o futuro import criam objetos malha, mas só o evento `"load"` chama `display_gn.ensure` (D) e `materials.ensure_slots` (F). Com `show_backface_culling=True`, um grupo novo fica **sem verso** e vazado por trás. Falta o tópico `"doc"` em `events`. | §2.4 `events`, §3.10 |
| B6 | **`run_unit.sh` (§8.1)** roda sem as variáveis de ambiente e sem colocar o template no `sys.path`: `import su` falha, porque em `--background` sem `--app-template` o template não é carregado. | §8.1 |

Não bloqueiam, mas devem ser registrados:
- `scene.su_undo_serial` (A) falta na lista de nomes reservados da §2.3-3.
- O merge em `sketchup-mode` precisa ser **serializado**: rebase + gate + merge dentro de um lock próprio.

## 3. Executabilidade dos briefs da §9

- **Donos sem sobreposição:** ✔. A única troca de dono é `tools/line.py` (A→E), explícita. Os binários `startup.blend`/`userpref.blend` são só de D. Conferi as listas de arquivos da §9.2 contra a árvore da §2.2: sem duplicatas.
- **Interfaces consumidas existem em alguma entrega:** ✔ — `selection.snapshot/restore/remap` (B), `vcb.feed/parse`, `ray_cast→Hit`, `hover_plane` (C), `prims`, `register_section`, `edges.mark_dirty`, `display_gn.ensure` (D), `materials.ensure_slots/paint` (F), `su.view_orbit/pan/recenter` (G), `undo.before_change`, `testing.*` (A). **Exceção:** o evento `"doc"` (B5).
- **Ordem:** falta a A0 (B3). Depois da A0, B e C (headless) e D (porte do spike) começam juntos. E (Retângulo) depende de B e C mínimos. M-A congela os contratos. A Fase B é paralela.
- **Comandos de teste:** a forma está certa (`run_unit.sh test_<x>_`, `run_gui.sh scn_<x>`, `shot.sh`, `compare.sh` com `sips`). Faltam o lock (B1), o ambiente e o `sys.path` (B4, B6).
- **Lock de GUI:** previsto, mas com ferramenta inexistente (B1). Testes headless podem rodar em paralelo sem lock.

## 4. Correções exatas

### 4.1 Substituir o 2º item da §9.0 ("Ambiente: …") por:

> - **Ambiente (obrigatório, nunca tocar `~/Library/Application Support/Blender`)**:
>   1. Cada agente trabalha no **seu worktree e branch**: `git -C /Users/tiago.agenor/www/blender worktree add ../su-wt-<X> -b su-<X> sketchup-mode` (pode ser sparse: `git -C ../su-wt-<X> sparse-checkout set scripts/startup/bl_app_templates_system/SketchUp_Mode tools/sketchup_mode tests/sketchup_mode doc/sketchup_mode`). Nunca editar a árvore principal.
>   2. `source tools/sketchup_mode/dev_env.sh <X>` define, para o agente X: `SU_ROOT=<worktree do agente>`, `SU_STAGE=/private/tmp/su_stage_<X>`, `BLENDER_SYSTEM_SCRIPTS=$SU_STAGE/sys` (com `sys/startup/bl_app_templates_system/SketchUp_Mode` → symlink para `$SU_ROOT/scripts/startup/bl_app_templates_system/SketchUp_Mode`), `BLENDER_USER_RESOURCES=$SU_STAGE/user` (cobre config/scripts/datafiles/extensions), também `BLENDER_USER_CONFIG/SCRIPTS/DATAFILES/EXTENSIONS` explícitos dentro de `$SU_STAGE/user`, e `TMPDIR=$SU_STAGE/tmp` (pasta criada). O script também semeia `$SU_STAGE/user/config/userpref.blend` com `show_splash=False` (gerado 1× em `--background --factory-startup`).
>   3. Todo script (`run_unit.sh`, `run_gui.sh`, `shot.sh`, `build_all.sh`) **aborta** se `SU_STAGE` não estiver definido e se `BLENDER_USER_RESOURCES` apontar para fora de `/private/tmp/su_stage_*`.
>   4. Merge: `lockf -k -t 1800 /tmp/su_merge.lock sh -c 'git fetch . && git rebase sketchup-mode && tools/sketchup_mode/run_unit.sh && tools/sketchup_mode/run_gui.sh scn_smoke && git -C /Users/tiago.agenor/www/blender merge --ff-only su-<X>'` — o merge principal é serializado por esse lock, e o integrador A pode assumir esse passo.

### 4.2 §8.2, trocar `flock /tmp/su_gui.lock` por:

> `lockf -k -t 1800 /tmp/su_gui.lock …` (macOS não tem `flock`; `lockf` libera o lock se o processo morrer). Só cenários GUI, `shot.sh` e `build_all.sh` usam esse lock; testes headless rodam sem lock.

### 4.3 §8.1, trocar o comando por:

> `tools/sketchup_mode/run_unit.sh [padrão]` → exige `dev_env.sh`; roda `Blender --background --factory-startup --python tests/sketchup_mode/unit/run.py -- --pattern "<padrão>"`, e `run.py` insere `$SU_ROOT/scripts/startup/bl_app_templates_system/SketchUp_Mode` no `sys.path` antes de `import su` (módulos `draw/*` não são importados em background).

### 4.4 Inserir no início da §9.1:

> **A0 — esqueleto (A, primeiras horas; merge antes de qualquer outro agente rodar Blender):** `dev_env.sh`, `run_unit.sh`, `run_gui.sh` (com lock e ambiente da §9.0), `SketchUp_Mode/__init__.py`, `su/__init__.py` (auto-descoberta: **erro de import de um módulo = `perf.error` + módulo pulado**, e `scn_smoke` falha se `perf.errors()>0`), `constants`, `colors`, `registry`, `events`, `i18n`, `perf`, `core/state.py` (dataclasses `Inference`/`Locks`/`STATE`), `core/undo.py` (`push`/`before_change` reais), `core/viewutil.py`, `draw/handlers.py` (`add_layer`), `tools/base.py` (só `ToolMeta`, `@tool`, `BaseTool` com métodos vazios, `Ev`, `Result`), `tests/sketchup_mode/unit/run.py`. Saída da A0: template vazio abre via `run_gui.sh scn_smoke` (só "abre e fecha") e `run_unit.sh` roda 0 testes com sucesso. Só então B, C, D e E criam seus worktrees.

### 4.5 §2.4 `events.py`, acrescentar o tópico e os assinantes:

> `"doc"(doc_key)` — emitido por B (`create_group`, Explodir, `Document` de objeto novo/importado) e por F (cópia de grupo/componente) e G (Texto em 3D) ao criar um objeto-documento; assinantes: D `display_gn.ensure(obj)` e F `materials.ensure_slots(obj)`. `"load"` continua cobrindo os objetos já existentes no arquivo.

### 4.6 §2.3-3, acrescentar aos nomes reservados:

> `su_undo_serial` (A, Scene, IntProperty).

---
Com 4.1–4.6 aplicados, a §9 fica executável por sub-agentes sem colisões. As demais divergências são de produto, não de execução.
