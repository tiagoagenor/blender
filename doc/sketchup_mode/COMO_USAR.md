# Como usar o SketchUp Mode

## Abrir

No Terminal:

```bash
/Users/tiago.agenor/www/blender/tools/sketchup_mode/abrir.command
```

Ou dê dois cliques em `tools/sketchup_mode/abrir.command` no Finder.

Ele abre o Blender 5.2.2 instalado com o modo SketchUp, usando uma configuração separada em `/private/tmp/su_stage_USUARIO`. O seu Blender normal não é alterado.

## Mouse

| Ação | Mouse | Trackpad (Mac) |
|---|---|---|
| Órbita | botão do meio arrastando | Ctrl+Cmd arrastando |
| Panorâmica | Shift + botão do meio | Ctrl+Cmd+Shift arrastando |
| Zoom (no cursor) | roda | pinça / 2 dedos |
| Recentralizar | duplo clique do meio | — |
| Menu de contexto | botão direito | Ctrl+clique |

## Atalhos

| Tecla | Ferramenta |
|---|---|
| Espaço | Selecionar |
| L | Linha |
| R | Retângulo |
| C | Círculo |
| A | Arco |
| P | Empurrar/Puxar |
| F | Equidistância |
| M | Mover (Option = copiar) |
| Q | Girar |
| S | Escala |
| E | Apagar (Borracha) |
| B | Pintura |
| G | Criar componente |
| T | Fita métrica |
| O / H / Z | Órbita / Panorâmica / Zoom |
| Shift+Z | Extensões de zoom |
| K | Arestas traseiras |
| Delete / ⌫ | Excluir seleção |
| Cmd+Z / Cmd+Shift+Z | Desfazer / Refazer |
| Setas | Travar eixo (→ vermelho, ← verde, ↑ azul) |

Digite números a qualquer momento para a caixa **Medidas** (ex.: `3` Enter, `8;6` Enter, `5x` depois de uma cópia).

## Diferenças conhecidas em relação ao SketchUp

- Performance ainda não foi otimizada (decisão: primeiro funcionar). Modelos muito grandes podem ficar lentos.
- Sem Etiquetas/Tags (pedido do usuário).
- Painéis Sombras, Suavizar arestas e Estruturador aparecem na Bandeja mas ainda estão vazios.
- Itens menores listados em `REVISAO_FINAL_SKETCHUP.md` (ex.: miniaturas na seção Componentes).

## Testes (desenvolvimento)

```bash
cd /Users/tiago.agenor/www/blender && zsh -c 'source tools/sketchup_mode/dev_env.sh LEAD && tools/sketchup_mode/run_unit.sh && tools/sketchup_mode/run_gui.sh scn_primeiro_dia'
```

Código do modo: `scripts/startup/bl_app_templates_system/SketchUp_Mode/`. Plano e decisões: `doc/sketchup_mode/PLANO.md`.
