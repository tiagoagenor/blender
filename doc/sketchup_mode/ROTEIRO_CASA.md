# ROTEIRO — Casa simples com Linha e Empurrar/puxar, e Apagar uma face

Este roteiro é a referência para um teste GUI automatizado com eventos simulados e para o teste manual do usuário. Ele reproduz a "primeira casa" que quase todo tutorial de iniciante ensina.

## Fontes

Não consegui ler legendas de vídeos do YouTube nesta sessão. Usei os tutoriais escritos que acompanham ou reproduzem esses vídeos e as páginas oficiais:

1. **Archgyan, "SketchUp for Beginners: Build a Complete House Model in 30 Minutes"**: https://archgyan.com/sketchup-for-beginners-your-first-3d-model-in-30-minutes/
   - Retângulo na origem digitando as dimensões, Empurrar/puxar 3 m.
   - Linha entre os pontos médios das arestas opostas do topo, Mover a linha no eixo azul 2 m: o telhado de duas águas aparece sozinho.
   - Porta 1×2,1 m e janelas 1,2×1,2 m desenhadas na parede e empurradas.
2. **Curso SketchUp (Google Sites, gnspes)**: https://sites.google.com/gnspes.ca/sketchup/home
   - Retângulo na origem, Empurrar/puxar, linha no centro do topo.
   - **Mover a linha para cima** forma a cumeeira.
   - Porta e janela com Retângulo + Empurrar/puxar para dentro.
3. **Exercício escolar (Claremont, SD63)**, "to make the roof, start with a line on the roof between midpoints": https://claremont.sd63.bc.ca/mod/resource/view.php?id=31329. Conteúdo visto só no trecho do resultado de busca.
4. **Ajuda oficial, "Erasing and undoing"**: https://help.sketchup.com/en/sketchup/erasing-and-undoing
   - A Borracha não apaga faces.
   - Apagar uma aresta apaga as faces que ela delimita.
   - Uma face pode ser apagada pelo menu de contexto **Apagar/Excluir**.
   - Desfazer: Cmd+Z no Mac.
5. **Ajuda oficial pt-BR, modelagem de elementos de construção** (paredes, telhado, aberturas): https://help.sketchup.com/pt-br/sketchup/modeling-specific-shapes-objects-and-building-features-3d. Vista só pelo resultado de busca.

Também uso comportamento conhecido do SketchUp, pela minha experiência de uso e ensino, marcado como [EXP].

## Convenções

- **Unidades:** metros. Decimal com vírgula e `;` separando valores (região pt-BR).
- **Eixos:** X = vermelho, Y = verde, Z = azul. O chão é z = 0.
- **Medidas:** "digitar `8;6` Enter" significa digitar com o mouse **onde estiver**, sem clicar na caixa Medidas.
- **Dicas de inferência:** usam os rótulos do Apêndice A. Exemplos: "Ponto de origem", "Ponto central", "Em aresta", "Em face", "No eixo vermelho/azul", "Interseção", "Ponto de extremidade".
- **Contagens:**
  - **V** = vértices.
  - **A** = arestas visíveis, sem pontes `su_bridge`.
  - **F** = faces **lógicas**: uma face com furo conta 1.
  - Em faces com furo, V − A + F = 2 + nº de furos.
- **Undo:** cada passo numerado é **1** passo de undo, exceto onde indicado.
- **Câmera:** a vista inicial padrão. Os cliques são as projeções em tela dos pontos 3D dados (`world_to_screen`).

---

## Parte 1 — Casa sólida (caminho canônico dos tutoriais)

| # | Ação do usuário | O que o SketchUp mostra | Resultado esperado |
|---|---|---|---|
| 0 | Abrir o modo. | Ferramenta Selecionar ativa. Medidas vazia. Céu, eixos. | Modelo vazio: V0 A0 F0. |
| 1 | **Piso.** `R`. Pairar a origem e clicar em (0,0,0). Mover para o quadrante +X+Y. Digitar `8;6` Enter. | Marcador escuro e dica "Ponto de origem". Pré-visualização no chão; pode aparecer a diagonal tracejada "Quadrado" ou "Seção áurea". Rótulo "Dimensões", valor vivo "x,xxm; y,yym". | Retângulo (0,0,0)–(8,6,0): V4 A4 F1. Área 48,00 m². **Normal −Z**: o verso azul-acinzentado fica para cima. Medidas mostra "8,00m; 6,00m". |
| 2 | **Volume.** `P`. Pairar o piso e clicar. Subir o mouse. Digitar `3` Enter. | O piso fica realçado com pontilhado azul no hover. Pré-visualização ao vivo da caixa. Rótulo "Distância". | Caixa 8×6×3: V8 A12 F6. Todas as normais para fora: topo +Z, base −Z (a frente branca fica do lado de fora). Volume 144 m³. |
| 3 | **Cumeeira.** `L`. Clicar no ponto central da aresta do topo em x=0, ou seja (0,3,3). Mover até o ponto central da aresta oposta (8,3,3) e clicar. | Ponto ciano, dica "Ponto central". O elástico fica **vermelho** ("No eixo vermelho"). No 2º ponto: ciano "Ponto central". | A linha divide o topo em 2 faces de 8×3 (24 m² cada). As arestas de 6 m do topo são divididas no meio: V10 A15 F7. A cadeia da Linha **termina sozinha** porque uma face foi criada [EXP]; se não terminar, `Esc`. |
| 4 | **Telhado.** `M`. Pairar a cumeeira (realce azul), clicar sobre ela, por exemplo no ponto central (4,3,3). Subir pelo eixo azul e digitar `2` Enter. | Linha pontilhada azul, dica "No eixo azul". Rótulo "Distância". As faces ligadas esticam ao vivo. | Cumeeira em (0,3,5)–(8,3,5). Duas águas planas de 8×3,606 m (28,84 m² cada). Dois oitões **pentagonais** planos (24 m² cada). Contagem inalterada: V10 A15 F7. **Nenhuma aresta de dobra** aparece: tudo continua plano. |
| 5 | **Guias da janela.** `T`. Clicar na aresta vertical esquerda da fachada (x=0, y=0). Mover para +X sobre a fachada e digitar `1` Enter. Depois clicar na aresta inferior da fachada, mover para cima e digitar `0,9` Enter. | Cursor da Fita com "+". Rótulo "Comprimento". Guias tracejadas infinitas. | 2 guias: x = 1 (vertical) e z = 0,9 (horizontal), ambas no plano y = 0. Geometria inalterada. São 2 passos de undo. |
| 6 | **Porta.** `R`. Clicar no ponto central da aresta inferior da fachada, (4,0,0). Mover para cima e para a direita **sobre a fachada**. Digitar `1;2,1` Enter. | Dica "Ponto central". O retângulo nasce **no plano da parede**, sem seta (a dica mostra "Em face"). | Porta (4..5, z 0..2,1) com área 2,10 m². A fachada vira uma face em **U** com 8 vértices, **sem pontes visíveis**. V14 A20 F8. |
| 7 | **Rebaixo da porta.** `P`. Clicar na porta. Empurrar para dentro (+Y) e digitar `0,15` Enter. | Realce da porta. Pré-visualização para dentro. | Porta em y = 0,15 com 3 faces novas (2 batentes e 1 verga). A base da casa ganha um **entalhe** e fica com 47,85 m². Sem aresta solta na soleira em y = 0. V18 A27 F11. |
| 8 | **Janela.** `R`. Clicar na interseção das guias (1,0,0,9). Mover para cima e para a direita sobre a fachada. Digitar `1,2;1,2` Enter. | X vermelho, dica "Interseção". Retângulo no plano da parede. | Janela (1..2,2; z 0,9..2,1). A fachada fica com **1 furo**, sem pontes nem triângulos visíveis. V22 A31 F12. |
| 9 | **Rebaixo da janela.** `P`. Clicar na janela. Empurrar `0,1` Enter. | Realce do vidro. | 4 faces laterais novas e vidro em y = 0,1. V26 A39 F16. |
| 10 | *(Opcional)* **Moldura.** Antes do passo 9: `F` na janela, mover para dentro, digitar `0,08` Enter. Depois `P` no vidro interno e empurrar `0,05`. | Rótulo "Distância". Contorno de equidistância ao vivo. | Anel de moldura de 0,08 m e vidro de 1,04×1,04 rebaixado 0,05. |
| 11 | **Desfazer e refazer.** Cmd+Z até o modelo vazio. Depois Cmd+Shift+Z até o fim. | — | Cada passo volta exatamente. Contagens iguais às da tabela em cada ponto. Seleção e guias restauradas. |

Pós-condições em todos os passos:
- `validate()` sem erros e nenhuma face não plana;
- sem objeto ativo e sem contorno laranja;
- nenhum popup do Blender;
- navegação com o botão do meio funciona **durante** os passos 1–9 sem cancelar a operação.

## Parte 2 — Variante com espessura de parede (furo passante)

É o jeito que os cursos brasileiros de arquitetura ensinam logo depois da casa sólida. Esta variante testa a **perfuração** e o Excluir face.

| # | Ação | Resultado esperado |
|---|---|---|
| B1 | `R` na origem, `8;6` Enter. | V4 A4 F1. |
| B2 | `F` no piso, mover para dentro, `0,15` Enter. | Anel + face interna 7,7×5,7: V8 A8 F2. |
| B3 | Clicar na face interna (Selecionar) e apertar **Excluir** (⌫). | Fica só o anel: V8 A8 F1 (face com furo). As arestas internas **permanecem**. |
| B4 | `P` no anel, subir, `2,8` Enter. | Paredes ocas de 15 cm: V16 A24 F10 (topo e base do anel contam 1 cada). |
| B5 | `R` na fachada externa a partir do ponto central da aresta inferior (4,0,0), `1;2,1` Enter. | Fachada externa em U: +1 face. |
| B6 | `P` na porta, empurrar para dentro até a face interna. Digitando `0,15` **ou** pairando a parede interna (dica "Em face"). | **Abertura passante**: a porta e a região correspondente da face interna somem. Ficam 3 faces novas (2 batentes e 1 verga). A base do anel é cortada e vira uma face em "C". Um raio de (4,5; −1; 1) na direção +Y atravessa e atinge a parede interna de trás em y = 5,85. |

---

## Diferenças que um usuário de SketchUp nota na hora (vigiar)

1. **Medidas** recebe `8;6` sem clicar no campo e com o mouse em qualquer lugar. Os valores aparecem como "8,00m".
2. **Piso recém-desenhado** mostra o **verso azul-acinzentado** para cima. Depois do Empurrar/puxar, tudo que fica do lado de fora é **branco**.
3. **Retângulo:** o 1º valor segue a direção do mouse (vermelho) e o 2º a outra direção. Valores negativos invertem.
4. **Hover:** o Empurrar/puxar realça a face com pontilhado azul **antes** do clique, e a pré-visualização é ao vivo.
5. **Cumeeira:** o ponto central dá um ponto ciano. A linha fica vermelha quando está paralela ao eixo. A linha divide o topo **na hora** e a cadeia termina.
6. **Mover a cumeeira** estica as faces ligadas. **Não** pode aparecer triângulo, aresta de dobra ou face torta nos oitões.
7. **Retângulo na parede** cai no plano da parede sozinho (sem seta). Começar na aresta inferior produz um **U**: **nenhuma** ponte nem diagonal visível.
8. **Janela dentro da parede** gera um furo limpo: só as 4 arestas da janela aparecem.
9. **Empurrar a porta** não deixa aresta solta na soleira, nem face sobrando, nem z-fighting.
10. **Perfurar** (variante B) faz as duas faces sumirem. A abertura fica vazada.
11. **Inferência:** as dicas amarelas em pt-BR e as cores dos marcadores são as da folha de inferência.
12. **Undo:** 1 Cmd+Z por ação. Nunca "meio passo" e nunca desfazer o estado inicial do modelo.
13. **Navegação:** o botão do meio orbita no meio de qualquer passo sem perder o elástico. A roda aproxima em direção ao cursor.
14. **Nada do Blender aparece:** sem Edit Mode, sem contorno laranja, sem painel "Ajustar última operação", sem menus em pizza.
15. **Arestas:** pretas e contínuas. Os batentes e a verga mostram as arestas de canto.

---

## Apagar uma face

### Comportamento do SketchUp

- **Selecionar uma face com 1 clique** seleciona **só a face**, sem as arestas. **Excluir** (tecla Delete, ou menu de contexto › Excluir, ou Editar › Excluir) remove **só a face**. Todas as arestas ficam e as faces vizinhas não mudam [Fonte 4][EXP].
- **A Borracha (Apagar) não apaga faces.** Clicar numa face com a Borracha não faz nada [Fonte 4].
- **Apagar uma aresta** (Borracha ou aresta selecionada + Excluir) remove a aresta **e as faces que ela delimita** [Fonte 4]. Se ela separava duas faces **coplanares**, as duas se fundem numa só [EXP].
- **Duplo clique numa face** seleciona a face e as suas arestas. Excluir remove as arestas e, por consequência, **todas as faces que dependiam delas** [EXP].
- **Cura:** redesenhar com a Linha uma aresta de um contorno fechado e coplanar que está sem face (por exemplo, por cima de uma aresta existente) **recria a face** [EXP; RESEARCH §7].
- **Teclas:**
  - **Mac:** a tecla "delete" do teclado do Mac (⌫, `BACK_SPACE` no Blender) **e** fn+delete / ⌦ (`DEL`) apagam a seleção.
  - Regra do nosso modo: se a caixa Medidas tem texto digitado, ⌫ apaga o último caractere e **não** a seleção (`su.vcb_key` vem antes).
  - **Windows** (modo opcional): Delete apaga. Backspace só edita a caixa Medidas, e Alt+Backspace é Desfazer.

### Testes (GUI, contagens como acima)

| ID | Preparação | Ação | Esperado |
|---|---|---|---|
| AF-1 | Retângulo 8×6 no chão. | Clique simples na face (Selecionar) e **⌫**. | Face removida. **4 arestas e 4 vértices ficam**: V4 A4 F0. A seleção fica vazia. |
| AF-1b | Igual ao AF-1. | Clique simples e **fn+delete (DEL)**. | Igual ao AF-1. |
| AF-2 | Caixa 8×6×3. | Clique simples no topo e ⌫. | Só o topo some. A caixa fica aberta: V8 **A12** F5. As outras 5 faces ficam com a mesma área, a mesma normal e o mesmo material. |
| AF-3 | Caixa 8×6×3 nova. | `E` (Apagar) e clique na aresta superior da fachada, (0,0,3)–(8,0,3). | A aresta some, e com ela o **topo e a fachada**, que ela delimitava: V8 A11 F4. |
| AF-3b | Caixa nova. | `E` e clique no **meio da face** do topo, longe das arestas. | Nada acontece: V8 A12 F6 e nenhum passo de undo. |
| AF-3c | Caixa com a cumeeira desenhada (Parte 1, passo 3). | `E` na cumeeira. | As duas metades do topo **se fundem** em 1 face de 48 m²: volta a V8 A12 F6 (os vértices dos pontos centrais somem e as arestas de 6 m voltam a ser inteiras: o SketchUp funde arestas colineares cujo vértice ficou só com 2 ligações [EXP]). |
| AF-4 | Resultado do AF-2 (topo aberto). | `L`: clicar em (0,0,3) ("Ponto de extremidade") e depois em (8,0,3), por cima da aresta existente. | O topo **é recriado**: V8 A12 F6, ou seja, **nenhuma aresta duplicada**. A cadeia da Linha termina. Normal do topo: +Z, para fora. É verificação flexível: o SketchUp nem sempre orienta a face recriada, mas a nossa implementação deve orientá-la para fora quando ela fecha o sólido. |
| AF-5 | Caixa nova. | Duplo clique no topo (face + 4 arestas) e ⌫. | Somem o topo, as 4 arestas superiores **e as 4 faces laterais** que dependiam delas. Fica a **base + 4 arestas verticais soltas**: V8 A8 F1. |
| AF-6 | Depois de cada um de AF-1…AF-5. | Cmd+Z. | Estado anterior **exato**: contagens, normais e materiais. A seleção que existia antes da exclusão é restaurada. Depois, Cmd+Shift+Z refaz. |
| AF-7 | Caixa nova com `1,5` digitado na Medidas (sem Enter) e o topo selecionado. | ⌫ uma vez. | A Medidas fica com "1,"; a face **não** é excluída. |
| AF-8 | Caixa nova. | Botão direito no topo › **Excluir**. | Igual ao AF-2. |
