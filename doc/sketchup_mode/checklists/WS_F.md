# WS_F — Agente F (Seleção, edição, materiais)

Legenda: `[ ]` pendente · `[~]` em andamento · `[x]` feito. Brief: `PLANO.md` §9.2-F (sub-checklist copiado abaixo; o agente F mantém este arquivo).

## Sub-checklist §9.2-F
1. [x] `materials` (slots 0/1 nos eventos `"load"` e `"doc"`, `paint` por lado); emitir `"doc"` ao copiar grupo/componente
2. [x] Selecionar (entidades, janela/cruzamento, contexto; dica com `modifiers.label()` → "Option")
3. [x] Apagar (curva, grupo, Shift/Option)
4. [x] Pintura (lado por `Hit.side`, seleção, superfície, conta-gotas) + seção Materiais
5. [x] `TransformSession` (AUTO/RESTRICT, cópia, arrays, index_map) + Mover
6. [x] Girar (transferidor no hover) e Escala (alças, `-1`)
7. [~] comandos: Excluir, tudo/nada/inverter, Criar/Fechar grupo, Inverter faces, Ocultar/Reexibir, Explodir; G/Criar componente = Criar grupo
8. [ ] menu de contexto; Informações da entidade
9. [ ] P1: Virar, Componentes, clipboard, Interseccionar (sobre `obj.data`)

## Aceite e comandos (referência)
- **Aceite**: AC-SEL-1..5, AC-APG-1..4, AC-PNT-1..4, AC-MOV-1..10, AC-GIR-1..3, AC-ESC-1..4.
- **Comandos**: `tools/sketchup_mode/run_unit.sh test_f_` · `tools/sketchup_mode/run_gui.sh scn_f` · `tools/sketchup_mode/shot.sh scn_f:caixa_selecionada /tmp/f.png && tools/sketchup_mode/compare.sh /tmp/f.png doc/sketchup_mode/ref_images/sketchup_selected_face_default_style.png doc/sketchup_mode/screens/selecao.png`

## Notas

### Bloco 1 — Selecionar + Apagar + Excluir
- `core/materials.py`: slots 0 "Padrão" / 1 "Padrão (verso)" nos eventos "load" e "doc" (D chama `ensure_slots` no `display_gn.ensure`), `slot_for`, `paint(doc, faces, material, side)`, paleta de 24 cores, `Material.su_mat`, `WindowManager.su_paint` (material ativo).
- `tools/select.py`: clique (aresta ≤ 7 px na frente da face vence), 2/3 cliques, grupo → objeto, duplo clique entra no grupo, fora do contexto não seleciona; janela (esq.→dir.) / cruzamento (dir.→esq.) — como no SketchUp, a caixa ignora oclusão; Shift alterna, Option adiciona, Shift+Option subtrai; dica com "Option". Ajudantes `pick/resolve/entity_refs/apply` usados por Apagar/Pintura/Mover.
- `tools/eraser.py`: aresta → entidade (curva inteira), faces dependentes somem, coplanares fundem; arrastar marca em azul e apaga no RELEASE (1 undo); face = nada; grupo some; Shift oculta, Option suaviza (+ sombreamento liso), Shift+Option des-suaviza.
- `ops/edit_ops.py`: `su.delete_selected` (Delete/⌫ depois de `su.vcb_key`), `su.select_all/none/invert` (Cmd+A, Shift+Cmd+A, Shift+Cmd+I), `su.escape` (Esc: limpa seleção, depois sai do grupo), `su.close_group`; `commit(docs, undo_key, select)` = 1 passo de undo com a seleção pré-operação certa.
- Testes: `test_f_select.py` (AC-SEL-1..4, AF-1/2/5/6, grupo), `test_f_eraser.py` (AF-3/3b, AC-APG-1..4); GUI `scn_f` (AC-SEL-1/5, AF-1b/2/5/6/7, Esc, Apagar AF-3/3b).
- **Pendente de A**: os itens LEFTMOUSE do keymap das ferramentas não têm `any=True` → Shift/Option/Cmd+clique não chegam à ferramenta na GUI (scn_f pula a verificação de Option até a correção; coberto headless).

### Bloco 2 — Pintura + Materiais
- `tools/paint.py` (B): lado pelo `Hit.side` do raio (frente → `material_index`, verso → `su_back_mat`), entidade inteira (face lógica / superfície suave), entidade selecionada → pinta a seleção (faces no lado clicado + grupos), grupo → faces Padrão (os dois lados, aninhados também), Option adjacentes com o mesmo material, Shift todas do modelo, Shift+Option mesmo objeto, Cmd = conta-gotas. 1 undo.
- `ui/tray_materials.py`: seção "Materiais" da Bandeja (ordem 20): amostra + nome do material ativo, "Cores" (Padrão + 24), "Em uso no modelo", "Criar material" (cor + botão); clicar numa amostra ativa a Pintura. Amostras = ícones `bpy.utils.previews` de cor sólida.
- Testes: `test_f_paint.py` (AC-PNT-1..4, superfície, grupo, Shift/Option, conta-gotas); GUI `scn_f` passo 6 (piso visto de cima → verso pintado, parede → lado visto, 1 undo). Print `screens/f_pintura.png`.
- Cmd+clique (conta-gotas) na GUI depende do `any=True` de A (coberto headless).

### Bloco 3 — Mover / Girar / Escala
- `core/geom_transform.py`: `TransformSession(refs, copy, fold, verts)` — vértices de arestas/faces selecionadas (as faces ligadas esticam), grupos por matriz; cópia = geometria duplicada no mesmo documento (grupos: objeto + malha duplicados, evento "doc"); `set_matrix` (pré-visualização ao vivo com `doc.begin/preview_write`; RESTRICT rejeita só a matriz que entortaria alguma face), `finish` (dobra AUTO com `geom.ensure_planar`, 1 undo, seleção mantida / cópia vira seleção), `cancel`, `array(n, internal, matrix_at)` (`5x` / `/5` substituem as cópias), `reapply_matrix` (Ajustar), `moving_faces`/`exclude` para a inferência; `mirror` (Virar, P1).
- `tools/move.py` (M): com seleção clica em qualquer lugar; sem seleção realça e pega a entidade sob o cursor (extremidade = o vértice); Option alterna cópia (também no meio); Medidas: distância (com seta travada sem mover o mouse usa o eixo), `[x;y;z]`/`<dx;dy;dz>`, depois `5x`, `/5`, nova distância.
- `tools/rotate.py` (Q): transferidor no hover no plano da face (cor do eixo; setas travam), centro → braço → ângulo, ajuste a 15°, `90`, `3:12`, cópia + `Nx` / `/N`.
- `tools/scale.py` (S): caixa amarela + 26 alças (cantos uniforme, Shift alterna; arestas 2 eixos; faces 1 eixo; Option = centro), `1,5`, `3m`, `2;1;1`, `-1` (faces invertidas para manter normais para fora); grupo sozinho = matriz nos eixos do grupo.
- Travas de seta/Shift são limpas ao concluir (A pode querer fazer isso no despacho).
- Testes: `test_f_move.py` (AC-MOV-1,2,3,5..10 + RESTRICT), `test_f_rotate.py` (AC-GIR-1..3, 15°), `test_f_scale.py` (AC-ESC-1..4, alça de aresta). GUI `scn_f` passos 7–10: cumeeira da casa (realce no hover, ↑, `2` → 2 águas + 2 oitões pentagonais, 7 faces planas, 1 undo), cópia com Option + `2x` (3 casas, seleção = última), Girar `90` em torno do canto, Escala `2` na alça do canto.
- AC-MOV-4 (encaixe extremidade-extremidade) depende da inferência de C com `exclude` — coberto pela exclusão dos vértices em movimento; sem teste GUI dedicado ainda.
