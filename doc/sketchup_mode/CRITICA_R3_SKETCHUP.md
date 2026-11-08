# CRÍTICA R3 (final) — especialista SketchUp

## 1. Veredito: **GO**

O PLANO v3 resolve todos os bloqueantes da R1 e da R2:
- teclas e Medidas funcionam em qualquer região, e o Ctrl passa direto pela ferramenta;
- a seleção é preservada depois do Mover, da cópia e do desfazer;
- superfície suave, curva e face lógica são entidades únicas;
- o verso tem material próprio;
- a dobra automática tem os aceites corretos;
- os aceites de "feel" (porta, encaixe, cura, zoom no cursor e pivô) estão definidos.

O `shell_v3.png` já se lê como SketchUp à primeira vista: posições, menus pt-BR, grupos da toolbar, LTS com a célula da Etiqueta vazia, Bandeja, céu, eixos e cilindro sem facetas com silhueta. Pode começar o desenvolvimento.

## 2. Bloqueantes restantes

Nenhum bloqueante de comportamento. Há uma inconsistência de texto que pode confundir os agentes: a tabela de escopo (§1.2, linha "Viewport") ainda diz "arestas e versos (GN)", mas a §3.3 decide pelo renderizador Python do spike para as arestas e usa o GN só para a cópia de verso. Corrigir a linha antes de distribuir os briefs.

Regra que não pode se perder ao portar o spike: no spike, as arestas são filtradas por **ângulo > 20°**. Na v1, o filtro tem que ser **por atributo**. Linhas que o usuário desenha sobre uma face plana (contorno de porta, divisão de piso) têm ângulo 0° e **precisam aparecer**. O teste é o AC-LIN-2 visual: a diagonal desenhada numa face fica visível no print.

## 3. Lacunas visuais do `shell_v3` × SketchUp (para o agente D, em ordem)

1. **Ícones.** São glifos do Blender recoloridos, e o usuário de SketchUp acha a ferramenta pelo ícone. Desenhar ícones **originais** com as metáforas do SketchUp (metáforas não são protegidas):
   - lápis vermelho (Linha), borracha (Apagar), balde (Pintura), fita métrica (Fita métrica);
   - caixa com seta vermelha para cima (Empurrar/puxar), cruz de 4 setas vermelhas (Mover), setas circulares vermelhas (Girar), caixa com seta diagonal (Escala);
   - transferidor (Transferidor), lupa (Aplicar zoom), mão (Panorâmica), setas orbitais vermelhas (Órbita).

   Estilo plano navy/ciano com acentos vermelhos. É a maior diferença visual restante. Hoje, Linha, Empurrar/puxar e Mover não são reconhecíveis.
2. **Luz das faces invertida.** No shell, o topo da caixa está **mais claro** que a lateral (222 × 185). No SketchUp padrão, o topo visto de cima é o **mais escuro**: frente 255, lateral ~210, topo ~160 (`sketchup_selected_face_default_style.png`). A luz relativa à câmera deve vir quase de frente, levemente de cima e da direita, e não de cima. É um ajuste de direção da luz: subir a calibração 255/210/160 de **P1 para P0**.
3. **Dica da status bar com Ctrl.** O shell mostra "Ctrl = Adicionar. Shift + Ctrl = Subtrair". No Mac deve ser **Option** (Apêndice A). Usar `modifiers.label()`.
4. **Faixa vazia de ~20 pt à direita da Bandeja** (aba invisível). Reduzir ao mínimo (largura da aba no tema ou `ui_scale` da região); se não der, aceitar como desvio.
5. **Caixa Medidas** sem borda. No SketchUp é um campo claro com borda fina e fica alinhado à direita. Ajustar `wcol_text` (outline) na status bar.
6. **Ícones pino/ⓘ da status bar.** Hoje são glifos do Blender escuros e pesados. No SketchUp são cinza-claro (pino) e preto fino (ⓘ). Usar ícones próprios.
7. **Estado inicial da Bandeja.** O shell abre com Estilos expandido (estilo 2023). Seguir o Q16: **tudo fechado** na 1ª abertura (2027).
8. **Arestas.** Conferir no print em tamanho real que as arestas são **pretas** (0,0,0) com ~1 pt. No downscale parecem cinza; a sonda de cor da aresta deve passar.

## 4. Teste do primeiro dia (aceite final antes de dizer "100%")

Executar com mouse **e** depois com o trackpad, sem tocar no Blender "por baixo". Cada passo precisa funcionar de primeira, sem popup do Blender e com 1 Cmd+Z por ação.

1. **Abrir o modo.** Sem splash, sem abas do Blender. Céu, eixos, toolbar, LTS, Bandeja e Medidas visíveis; ferramenta Selecionar ativa; dica com "Option".
2. **Piso.** `R`, clicar na origem (dica "Ponto de origem"), digitar `8;6` Enter. Resultado: retângulo 8×6 com o **verso azul-acinzentado para cima**, e Medidas mostra as dimensões.
3. **Volume e redigitar.** `P`, pairar o piso (realce azul), clicar, subir, digitar `3` Enter. Resultado: caixa com frentes brancas para fora. Digitar `2,8` Enter: a altura muda para 2,80 m.
4. **Navegar.** Arrastar com o botão do meio orbita em torno do ponto sob o cursor. Shift+meio faz panorâmica. A roda aproxima em direção ao cursor. Duplo clique do meio recentraliza. `Shift+Z` enquadra tudo. Com o trackpad: dois dedos dão zoom, e Ctrl+Cmd+arrastar orbita.
5. **Paredes.** `F` no topo, `0,15` Enter. Depois `P` na face interna, empurrar `2,65` Enter. Resultado: cômodo oco com paredes de 15 cm e piso.
6. **Porta.** `R` na face externa da parede da frente, começando **na aresta inferior**, `0,9;2,1` Enter. Depois `P` na porta, empurrar `0,15`. Resultado: **abertura passante**, sem faces sobrando.
7. **Linha com inferência e eixos.** `L` numa parede: clicar no ponto central de uma aresta, subir pelo eixo azul (linha azul e dica "No eixo azul"), digitar `1` Enter. A linha divide a face e fica **visível**. `Esc` encerra.
8. **Telhado.** Fazer uma caixa nova 4×4×3. Com `L`, ligar os pontos centrais das arestas opostas do topo. Com `M`, mover essa linha 1,5 m para cima (seta ↑ ou eixo azul). Resultado: 2 águas e 2 oitões, sem face torta.
9. **Grupo e cópias.** Clique triplo na casa, botão direito, Criar grupo (bbox azul). `M`, Option, mover 10 m no vermelho, `2x` Enter. Resultado: 3 casas, e a seleção é a última cópia. Desenhar uma linha encostada num grupo: ela **não gruda**.
10. **Girar.** Com a cópia selecionada, `Q`: o transferidor azul aparece no chão. Clicar num canto, depois no braço, digitar `90` Enter. A cópia gira 90°.
11. **Cilindro.** `C`, clicar no chão, `0,4` Enter. `P` com `1` Enter. Resultado: sem riscos laterais, sombreamento liso, contorno preto. Clicar na lateral seleciona a **superfície** inteira.
12. **Pintura.** `B`, escolher uma cor. Pintar uma parede e pintar um retângulo desenhado no chão (verso para cima): as duas **aparecem na cor**, sem tom azul.
13. **Medir e cotar.** `T` numa aresta, afastar e digitar `1` Enter: guia tracejada a 1 m. Na Linha, a guia aparece como "Na linha". Dimensões numa aresta de 8 m: aparece "8,00m".
14. **Teclado em qualquer lugar.** Com o mouse sobre a Bandeja: `L`, `R`, `Espaço` trocam a ferramenta. Logo depois de um Empurrar/puxar, com o mouse sobre a barra de status, digitar `1` Enter redigita a distância. `⌫` com algo digitado apaga o dígito e **não** exclui a seleção.
15. **Apagar, desfazer, salvar.** `E` na linha do passo 7: as faces se fundem. Cmd+Z várias vezes até o vazio, depois Cmd+Shift+Z refaz tudo, e a seleção volta. Salvar, fechar, reabrir: tudo igual (mesmo visual e mesma ferramenta).

Passar nos 15 passos, com a sonda de cor verde e o print lado a lado aprovado, é o critério para dizer ao usuário que está pronto.
