# REVISÃO FINAL — especialista SketchUp

Prints analisados:
- `screens/dia_resumo_1.png`, `dia_resumo_2.png`, `casca_v11_com_cenas.png`, `casa_resumo_v2.png`, `g_resumo_v2.png`, `f_transform_resumo.png`, `f_bloco1_resumo.png`, `c_inferencia_v2.png`;
- `f_componentes.png`, que está na worktree do agente F.

Comparei com `ref_images/`.

## 1. Veredito

**Sim, parece e se comporta como o SketchUp para um usuário real.** Um aluno meu reconheceria o programa e trabalharia nele sem explicação.

O que está certo:
- **Layout:** posições 2027, nomes pt-BR oficiais, LTS com a célula da Etiqueta vazia, Bandeja sem Etiquetas, status com dica de "Option", Medidas com o rótulo da operação.
- **Visual:** céu e horizonte, verso azul-acinzentado, sombreamento com o topo mais escuro, cilindro liso com silhueta, linha desenhada sobre a face visível.
- **Fluxos:** porta, janela, cumeeira com 2 águas sem dobra, Excluir face, duplo clique + Excluir, Borracha, cura da face.
- **Inferência:** pontos e eixos com as cores e dicas certas, inclusive "no grupo" e "no componente".
- **Seleção e edição:** stipple, bbox de grupo e componente, alças da Escala, cópias com `2x`, componentes com 3 instâncias.

O "teste do primeiro dia" (15/15 + trackpad) cobre o que um usuário faz nos primeiros minutos. Nada do Blender aparece nos prints.

## 2. Diferenças restantes (no máximo 10, em ordem)

| # | Diferença | Como o SketchUp faz | Classe |
|---|---|---|---|
| 1 | **Soleira da porta vazada** (casa com parede grossa, `dia_resumo_1` passo 6 e `casa_resumo_v2`): aparece uma faixa azul-acinzentada e uma linha colorida no piso do vão. Se for uma face que sobrou (a base do anel não foi entalhada), está errado. | Depois de perfurar a parede apoiada no chão, o vão fica **vazio**: a base da parede vira um "C" e só aparecem o chão e o eixo vermelho. Conferir com `doc_stats` (ROTEIRO_CASA B6): nenhuma face no vão. | **bloqueia** se for face sobrando; senão, melhoria |
| 2 | **"Perfis" vem marcado** no Estilo simples (Estilos › Editar). | No Estilo simples, Perfis vem **desmarcado**. A silhueta do cilindro aparece **independentemente** de Perfis, com a espessura normal da aresta. Desmarcar Perfis não pode apagar as silhuetas. | melhoria |
| 3 | **Transferidor do Girar** é uma elipse tracejada solta, longe do cursor (`f_transform` "Girar 90°"). | É um transferidor completo: círculo com marcas a cada 15°, colorido pelo plano (azul no chão, vermelho/verde nas paredes), **preso ao cursor** e deitado na face sob o cursor. O mesmo gizmo é usado no Transferidor. | melhoria (alta) |
| 4 | **Escala uniforme** mostra "2,00; 2,00; 2,00" na caixa Medidas. | Alça de canto (uniforme) mostra **um** valor, "2,00". Só as escalas não uniformes mostram valores por eixo. | melhoria |
| 5 | **Posição da câmera** continua ativa depois de posicionar, e Medidas mostra 2,00 m. | Depois do clique, troca **sozinha** para **Olhar ao redor**. A altura dos olhos padrão é **1,68 m**. Olhar ao redor é P2: trocar para ele quando existir; até lá, garantir o padrão de 1,68 m. | melhoria |
| 6 | **Abas de cena** começam na borda esquerda da janela, acima do LTS. | No 2027, as abas ficam **só sobre a área de desenho**, entre o LTS e a Bandeja, com visual de aba. | melhoria |
| 7 | **Estilos › Editar** usa listas e caixas de seleção. | Sub-abas com ícones (Aresta, Face, Fundo, Marca-d'água, Modelagem), e o estilo de face como **6 botões de ícone**. | melhoria |
| 8 | **Componentes** é uma lista de texto ("Componente#1 (3)"). | Grade de **miniaturas** dos componentes "No modelo". Clicar numa miniatura começa a inserção com o Mover. | melhoria |
| 9 | **Grupos/componentes de fora durante a edição** não aparecem esmaecidos (desvio já aceito na v1). | Ao entrar num grupo, o resto do modelo fica **esmaecido** e o contexto ganha uma caixa tracejada. Usuários antigos notam, mas não atrapalha o trabalho. | melhoria |
| 10 | **Menus dentro da janela** e **status bar de largura total**. São desvios aceitos e documentados. | Mac 2027: menus na barra global do macOS; a status bar fica só sob a área de desenho. | melhoria (aceita) |

**Conclusão.** Só o item 1 precisa de verificação antes de dizer "100%". Se o vão estiver vazio no `doc_stats`, não há bloqueio. Recomendo corrigir os itens 2–4 numa rodada curta, porque são baratos e visíveis.
