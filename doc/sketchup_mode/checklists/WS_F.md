# WS_F — Agente F (Seleção, edição, materiais)

Legenda: `[ ]` pendente · `[~]` em andamento · `[x]` feito. Brief: `PLANO.md` §9.2-F (sub-checklist copiado abaixo; o agente F mantém este arquivo).

## Sub-checklist §9.2-F
1. [ ] `materials` (slots 0/1 nos eventos `"load"` e `"doc"`, `paint` por lado); emitir `"doc"` ao copiar grupo/componente
2. [ ] Selecionar (entidades, janela/cruzamento, contexto; dica com `modifiers.label()` → "Option")
3. [ ] Apagar (curva, grupo, Shift/Option)
4. [ ] Pintura (lado por `Hit.side`, seleção, superfície, conta-gotas) + seção Materiais
5. [ ] `TransformSession` (AUTO/RESTRICT, cópia, arrays, index_map) + Mover
6. [ ] Girar (transferidor no hover) e Escala (alças, `-1`)
7. [ ] comandos: Excluir, tudo/nada/inverter, Criar/Fechar grupo, Inverter faces, Ocultar/Reexibir, Explodir; G/Criar componente = Criar grupo
8. [ ] menu de contexto; Informações da entidade
9. [ ] P1: Virar, Componentes, clipboard, Interseccionar (sobre `obj.data`)

## Aceite e comandos (referência)
- **Aceite**: AC-SEL-1..5, AC-APG-1..4, AC-PNT-1..4, AC-MOV-1..10, AC-GIR-1..3, AC-ESC-1..4.
- **Comandos**: `tools/sketchup_mode/run_unit.sh test_f_` · `tools/sketchup_mode/run_gui.sh scn_f` · `tools/sketchup_mode/shot.sh scn_f:caixa_selecionada /tmp/f.png && tools/sketchup_mode/compare.sh /tmp/f.png doc/sketchup_mode/ref_images/sketchup_selected_face_default_style.png doc/sketchup_mode/screens/selecao.png`

## Notas
