# CRÍTICA R1 — visão do especialista SketchUp (usuário avançado / instrutor)

Revisão do `PLANO.md` v1 com uma pergunta só: **um usuário brasileiro de SketchUp abre isso e sente que está no SketchUp?**
O plano é sólido na arquitetura e acerta a maior parte da spec. Mas tem erros de layout, de nomes pt-BR e de comportamento que um aluno meu notaria nos primeiros 5 minutos. Também deixa em P1/P2 coisas que **definem** a sensação de SketchUp.

Fontes usadas nesta crítica:
- **[QRC-PT]** Cartão de Referência Rápida oficial 2026, pt-BR, Mac: https://download.sketchup.com/QRC2026/HC-QRC2026.0-PT-BR-SU-Mac.pdf. É a fonte mais confiável de nomes pt-BR, porque reproduz os rótulos do app. Baixado e lido nesta sessão.
- **[H-PT]** Central de Ajuda pt-BR:
  - https://help.sketchup.com/pt-br/sketchup/user-interface
  - https://help.sketchup.com/pt-br/default-keyboard-shortcuts
  - https://help.sketchup.com/pt-br/sketchup/introducing-drawing-basics-and-concepts
  - A Central pt-BR é parcialmente traduzida por máquina e se contradiz. Quando ela diverge do [QRC-PT], vale o QRC.
- **[RN27]** Notas da versão 2027: https://help.sketchup.com/en/release-notes/sketchup-desktop-20270
- **[REF]** Imagens em `ref_images/`.
- **[EXP]** Comportamento conhecido do SketchUp, pela minha experiência de uso e ensino. Não verifiquei em fonte nesta sessão.

---

## 1. Problemas bloqueantes (sem corrigir, não "parece SketchUp")

### B1. Atalhos e VCB só funcionam com o mouse sobre a viewport
**O problema.** O plano põe os atalhos de ferramenta no keymap "SketchUp" (`VIEW_3D`/`WINDOW`, §5.1-2) e o `su.vcb_key` no keymap da ferramenta (§3.6). No Blender, uma tecla vai para o keymap da **região sob o mouse**. Com o cursor sobre a Bandeja, o Large Tool Set, a barra "Primeiros passos" ou a barra de status, nada acontece ao apertar `L`, `P`, `Espaço`, `⌫` ou ao digitar `3` Enter.

**Por que bloqueia.** Esse é o gesto mais comum do SketchUp:
1. Termina um Empurrar/puxar.
2. Leva o olho e o mouse até a caixa Medidas.
3. Digita `2,8` e aperta Enter.

No SketchUp isso funciona com o mouse em qualquer lugar da janela [EXP][H-PT "caixa Medidas"].

**Spec correta.**
- Atalhos de ferramenta, Delete/⌫, Cmd+A etc. e teclas do VCB funcionam **com o mouse em qualquer região da janela**.
- A única exceção é um campo de texto da UI em edição.
- Implementação: itens no keymap **`Window`**, com poll "modo SU ativo e nenhum campo de texto em edição". Alternativa: um modal leve em nível de janela que só intercepta teclas.
- Durante uma operação o modal já recebe tudo. O problema é o **estado ocioso**: lados do círculo antes do clique, redigitar depois de concluir e atalhos.
- Também precisa funcionar: **clicar na caixa Medidas e digitar ali** (o campo é editável; ao confirmar, chama o mesmo `APPLY`).
- Atenção: com o mouse sobre um botão do Blender, `⌫` reseta o valor do botão e Cmd+C/V copia valores. Os campos da Bandeja que não são de texto devem ignorar isso ou a tecla deve ir para o modo.

### B2. Verso pintado e piso pintado ficam azul-acinzentados (R7 subestimado)
**O problema.** O plano desenha o verso com o overlay de orientação de face do Blender e aceita que "faces pintadas também recebem o tom do verso" (R7, risco Baixo/Médio). Isso é bloqueante.

No SketchUp, **todo retângulo desenhado no chão nasce com o verso para cima** (Q21, correto). O fluxo nº 1 de qualquer aluno é: desenhar a planta, depois pintar o piso de madeira. Com o plano atual, o piso pintado aparece tingido de azul-acinzentado α 0,85, ou seja, a cor não aparece.

Além disso, no SketchUp **frente e verso têm materiais independentes** [EXP]: pintar o lado azul pinta só o verso, e a frente continua branca.

**Spec correta.**
- Cada face tem material de frente e material de verso.
- O verso "Padrão" é (164,178,187). O verso pintado mostra a cor do material, **sem tinta azul**.

**Implementação sugerida.**
- Workbench com `show_backface_culling=True` desenha só as frentes.
- O WS4 desenha os versos numa passada própria em POST_VIEW: faces com normal oposta à câmera, cor = material do verso (atributo de face `su_back_mat`) ou #A4B2BB, com a mesma iluminação 255/210/160.
- Remover o overlay de orientação de face.
- Pintura: clique no lado de trás grava `su_back_mat`.
- Isso vira **P0**. R7 deixa de ser "aceito".

### B3. Laterais de cilindro com 24 arestas pretas
**O problema.** Q23 e §6.2 deixam "laterais suaves após Empurrar/puxar de círculo/arco" como P1. Mas o **primeiro** exercício de todo curso é: círculo, Empurrar/puxar, cilindro. Se aparecem 24 riscos pretos e um sombreamento facetado, o usuário diz na hora "isso não é SketchUp".

**Spec correta** [EXP][RESEARCH §6]:
- Extrusão de borda que vem de curva (círculo, arco, polígono **não**) gera arestas laterais **suaves e atenuadas**: invisíveis, com sombreamento contínuo.
- Polígono gera arestas duras (o plano já acerta isso).

**Implementação.**
- Marcar `su_soft` nas laterais vindas de `su_curve` de círculo/arco.
- O renderizador de arestas pula essas arestas.
- Na malha: `sharp_face=False` nessas faces e `sharp_edge` só nas arestas duras, para o Workbench sombrear suave.
- **P0.** Barato e de alto impacto.

### B4. Curva como entidade: o plano se contradiz
**O problema.** A §3.8 diz que selecionar uma aresta de curva seleciona a curva inteira, e a Borracha da §6.1 apaga "curvas inteiras". Mas a §1.2 põe "Curvas como entidade" em **P1**.

No SketchUp, clicar num círculo seleciona o círculo inteiro. Mover um arco move o arco. Apagar um segmento apaga o arco todo. Isso é **P0**.

**Divisão.**
- P0: identidade da curva (`su_curve`) para seleção, apagar, mover e inferência de Centro.
- P1: edição de raio/segmentos no Informações da entidade.

### B5. Separadores da barra "Primeiros passos" errados
**O problema.** A §4.2 põe `|` entre **todos** os botões. A referência 2027 ([REF] `sketchup_getting_started_toolbar_v2027.png`, `..._4_v2027_mac_menubar.png`) e a 2023 têm **grupos**:

```
[Pesquisar] | [Selecionar▾] | [Apagar, Linha▾, Arco▾, Retângulo▾] |
[Empurrar/puxar, Equidistância, Mover, Girar, Escala, Virar] | [Fita métrica, Pintura] |
[Órbita, Panorâmica, Aplicar zoom, Extensões de zoom]
```

Sem os grupos Warehouse, LayOut, Comentário e Conta (Q4). `catalog.GETTING_STARTED` deve seguir exatamente isso, e a sonda de layout deve checar onde ficam os separadores.

### B6. Ordem da Bandeja padrão errada
**O problema.** A ordem do plano é: Info, Materiais, Componentes, Estilos, Sombras, Cenas, **Estruturador, Instrutor**.

A ordem 2027 [REF img 2 e 4] é: Informações da entidade, Materiais, Componentes, Estilos, (Ambientes, Etiquetas), Sombras, Cenas, **Instrutor**, (Padrões de hachura), Suavizar arestas, **Estruturador**.

**Ordem correta sem Etiquetas/Ambientes/Hachura:** Informações da entidade, Materiais, Componentes, Estilos, Sombras, Cenas, Instrutor (se existir), Suavizar arestas (se existir), Estruturador.

### B7. Nomes pt-BR errados nos rótulos mais visíveis
Os nomes errados aparecem nos menus, tooltips e LTS. A lista completa está na §3.2 desta crítica. Os piores:
- **Flip = "Virar"**, não "Inverter". "Inverter" colide com "Inverter faces" e "Inverter seleção", dois comandos diferentes que existem no mesmo menu Editar.
- **Eraser = "Apagar"**, não "Borracha" [QRC-PT][H-PT]. Isso força renomear o comando Delete do menu Editar para **"Excluir"**, senão haveria dois "Apagar".
- **Menus: "Visualizar"** (não "Exibir") e **"Desenho"** (não "Desenhar") [H-PT user-interface].
- **Dimensions = "Dimensões"**, não "Cotas". **Pie = "Pizza"**, não "Torta". **Walk = "Percorrer"**, não "Caminhar". **Orbit = "Órbita"**, não "Orbitar". **Zoom = "Aplicar zoom"**.
- **Vistas padrão:** Superior / Inferior / Frontal / Traseira / Esquerda / Direita / Iso. O plano usa "Topo, Base, Frente, Fundos".
- **Estilos de face:** "Grade de linhas" (wireframe; o plano usa "Estrutura de arame"), "Linha oculta" (o plano usa "Linhas ocultas"). **Back Edges = "Arestas traseiras"** (o plano usa "Arestas posteriores").

### B8. Trackpad (Q7) com gesto inventado
**O problema.** "Cmd + arrastar dois dedos = orbitar" não existe no SketchUp. O SketchUp 2027 [RN27] usa **gesto de um dedo (clicar e arrastar) + modificador**:
- Orbitar: Ctrl+Alt no Windows, "CMD" no Mac.
- Panorâmica: Shift+Ctrl+Alt no Windows, Cmd+Shift no Mac.

O Mac clássico usava **Ctrl+Cmd + clicar e arrastar** para orbitar e **Ctrl+Cmd+Shift** para panorâmica [RESEARCH §3].

A decisão completa está em Q7 (§3.1).

### B9. Ctrl+clique (Mac) precisa abrir o menu de contexto
Todo usuário de Mac com trackpad ou Magic Mouse faz Ctrl+clique para "botão direito", e no SketchUp Mac isso abre o menu de contexto [EXP]. O plano não mapeia isso. É obrigatório no Mac.

Atenção ao Ctrl+Cmd+arrastar do Q7: Ctrl+clique **sem arrastar** abre o menu; Ctrl+Cmd+arrastar orbita.

### B10. Mover vértice/aresta fora do plano precisa dobrar sozinho
**O problema.** A §6.1 diz: "Cmd = auto-dobra (P1; sem ele, movimento que deixaria face não planar é restringido)".

**Spec** [QRC-PT "dobra automática (permite mover mesmo que seja necessário acrescentar bordas e faces extras)"][EXP]:
- Mover **face**: o SketchUp restringe direções que deixariam faces vizinhas não planas. Cmd libera a dobra.
- Mover **vértice ou aresta**: o SketchUp dobra (triangula) automaticamente. É assim que se faz "puxar a cumeeira", "levantar um canto" etc.

Restringir vértice e aresta deixa o usuário "travado" sem entender por quê. Além disso, o kernel **nunca** pode gravar face não plana, porque o Blender aceita n-gon torto e renderiza errado.

**Correção.**
- P0: dobra automática para vértice/aresta e restrição para face.
- P1: Cmd para face.

### B11. Inferência sem histerese
**O problema.** O plano tem raios de captura (`SNAP_PX_*`) mas não tem raio de **liberação**. A inferência do SketchUp é "grudenta": uma vez no eixo vermelho, você pode se afastar alguns pixels e continua no eixo. O mesmo vale para Ponto final e Na aresta [EXP].

Sem histerese, o elástico pisca entre preto e vermelho e o usuário sente "tremido". Isso define o "feel" tanto quanto as cores.

**Spec.**
- Captura com `SNAP_PX_*` e liberação com cerca de 1,5× esse valor para a mesma inferência.
- A comparação "mudou?" da §3.2-8 considera a inferência anterior.

### B12. Retângulo, Círculo e Polígono: plano visível antes do clique e plano vertical automático
**Spec** [EXP][QRC-PT setas].
- **Antes** do 1º clique, o cursor ou a pré-visualização já mostra o plano em que a forma vai nascer:
  - Círculo, Polígono, Transferidor e Girar: gizmo colorido pelo plano.
  - O plano segue a face sob o cursor. No vazio, é o chão.
  - As setas trocam o plano antes de clicar (↑ azul etc.).
  - Shift sobre uma face trava o plano dela.
- **Retângulo:** depois do 1º clique no vazio, se o 2º canto é levado para cima ao longo de um plano de eixo vertical (vermelho-azul ou verde-azul), o retângulo **fica em pé sozinho**, sem seta. Quem desenha parede no SketchUp faz isso o tempo todo.

A §6.2 fala só em "plano inferido". Escrever isso explícito no aceite, com um caso GUI-sim: R, clique na origem, mover para (2,0,3) na tela → retângulo no plano XZ.

### B13. Pintura com seleção ativa
**Spec** [EXP]: com entidades selecionadas, clicar com o Balde em qualquer face **da seleção** pinta **toda** a seleção. Isso falta na §6.1.

Também falta a Borracha num grupo: clicar numa aresta de grupo apaga o grupo inteiro.

### B14. "Medidas": separador decimal vem da região do sistema, não do idioma
**Spec** [EXP]: o SketchUp usa o separador decimal do **sistema operacional**. Com região Brasil, a vírgula é decimal e o `;` separa a lista. Isso vale mesmo com o app em inglês.

O plano decide por `language`. Mude para: `decimal='AUTO'` lê a região do macOS (`NSLocale`/`defaults read -g AppleLocale`, ou `locale.localeconv()` depois de `setlocale(LC_NUMERIC,'')`). Fallback é o idioma.

Exibir valores como o SketchUp: `2,50m` sem espaço e **`~ 2,50m`** quando o valor foi arredondado pela precisão (P1).

---

## 2. Problemas de prioridade (o que decide o "dia 1")

**Precisa subir para P0:**

| Item | Hoje | Correto | Por quê |
|---|---|---|---|
| Verso com material próprio + pintar verso sem tinta (B2) | aceito como limitação | **P0** | Todo piso desenhado no chão fica errado |
| Arestas suaves em extrusão de curva (B3) | P1 | **P0** | Primeiro exercício de qualquer curso |
| Curva como entidade (seleção/apagar/mover) (B4) | P1 | **P0** | Clicar num círculo e pegar 1 segmento é anti-SketchUp |
| Atalhos e VCB fora da viewport (B1) | não previsto | **P0** | Gesto mais frequente do SketchUp |
| Auto-dobra de vértice/aresta (B10) | restrito / P1 | **P0** | Telhados, rampas, ajustes |
| Ctrl+clique = menu de contexto (Mac) (B9) | ausente | **P0** | Usuário de MacBook |
| Trackpad (Q7) | P1 | **P0** no Mac | O usuário provavelmente está num MacBook. Sem mouse de 3 botões, sem trackpad certo não há navegação |
| Ocultar / Reexibir | P1 | P1, mas **cedo** (M3) | Usado o tempo todo; ok ficar em P1 se entrar junto com grupos |
| Explodir | P1 | P1 cedo (M3) | Desfazer um "Criar grupo" errado |

**Pode descer (não muda o dia 1):**

| Item | Hoje | Sugerido |
|---|---|---|
| Transferidor | P0 | **P1**. Pouco usado no dia 1; Girar + VCB cobrem |
| Instrutor (painel) | P1 | **P2/cortar**. Quase todo usuário fecha. Escrever 30 textos próprios (não pode copiar a Trimble) é trabalho sem retorno |
| Laço (Lasso) | P1 | **P2**, botão desabilitado na posição. Ferramenta nova (2025+), ninguém tem memória muscular |
| Mão livre (Desenho à mão livre), Retângulo girado, Arco de três pontos, Pizza | P1 | **P2** (desabilitados na posição). Arco (centro) fica P1 |
| Sombras (painel + sombra) | P1 | **P2**. Sombra do Workbench não é a do SketchUp e ninguém precisa no dia 1 |
| Olhar ao redor, Campo de visão (ferramenta) | P1 | **P2** (Shift+arrastar no Aplicar zoom já muda o FOV) |
| Cursores desenhados | P1 | P1 tardio. Os nativos servem se o hotspot estiver certo |
| Selos +/−/± no cursor do Selecionar | P1 | P2 |
| Cotas de raio/diâmetro, texto de tela | P1 | P2. O texto com chamada (leader) continua P1 |

**Pode subir de P2 para P1 (barato e muito usado):**
- **Interseccionar faces ▸ Com o modelo / Com a seleção.** É usado por todo usuário intermediário (telhados, recortes). Viável com um objeto temporário em Edit Mode + `bpy.ops.mesh.intersect`, fora do caminho do mouse.
- **Posição da câmera.** Clicar num ponto põe o olho a 1,68 m olhando na horizontal. São umas 50 linhas e mantém o LTS "vivo".
- **Texto em 3D.** Curva FONT do Blender convertida em malha dentro de um grupo. Barato.
- O **Plano de seção** fica P2.

---

## 3. Respostas definitivas às perguntas em aberto (§11) e nomes pt-BR

### 3.1 Perguntas

| # | Resposta definitiva |
|---|---|
| Q1 | Ok. `SketchUp_Mode` / "SketchUp Mode", nome numa constante só. Na UI, onde o SketchUp diz "SketchUp" (ex.: "Sobre o SketchUp"), usar `PRODUCT_NAME`. |
| Q2 | Modelo "Simples – Metros": formato **Decimal, metros, precisão 0,00** ("2,50m"), ângulo 0,0°, **ajuste de ângulo 15°**, ajuste de comprimento desligado. Na caixa Informações do modelo › Unidades, oferecer cm e mm, que muitos arquitetos brasileiros usam. Mudar a unidade só muda a exibição; digitar `250cm` sempre funciona. |
| Q3 | **2027 unificado** (LTS à esquerda, cromo #F1F1F6, Bandeja à direita) com **modificadores do Mac** (Option = "Ctrl do Windows", Cmd = "Alt do Windows"), porque o usuário está no Mac. Deixar `platform_modifiers='windows'` como opção: muitos brasileiros aprenderam no Windows. Dois desvios aceitos e documentados: (a) a barra de status do 2027 fica só sob a área de desenho (entre o LTS e a Bandeja), e a nossa será a global, de largura total, como no Windows 2023, o que é aceitável; (b) os menus ficam dentro da janela, não na barra global do macOS. |
| Q4 | Não reproduzir, nem desabilitados. Correto. O menu **Procedimentos** (2027) também fica fora. |
| Q5 | Mostrar **desabilitados** na posição exata, com o ícone normal a ~40% de opacidade e a dica "Em breve" na barra de status ao clicar. Nunca deixar buraco, exceto a célula da Etiqueta. **A célula da Etiqueta (linha 3, direita) fica vazia**: a posição de todo o resto vale mais que preencher a grade. Não puxar Eixos ou outra ferramenta para lá. |
| Q6 | Nenhuma figura na v1 (a referência 2027 "vazia" também não tem). P2: silhueta 2D original de ~1,75 m como grupo apagável. |
| Q7 | Padrão "sketchup" (Mac): **rolagem de dois dedos = zoom no cursor**; **pinça = zoom**; **Ctrl+Cmd + clicar e arrastar = Órbita**; **Ctrl+Cmd+Shift + clicar e arrastar = Panorâmica**. Aceitar também Option+Cmd (mapeamento 2027 de Ctrl+Alt) [RN27][RESEARCH §3]. Não usar Cmd sozinho: ele é o modificador de ferramenta (dobra automática, conta-gotas). Opção "blender" nas Preferências: dois dedos = Órbita, Shift + dois dedos = Panorâmica, pinça = zoom. Vale **P0**, e muitos usuários de MacBook vão preferir o modo "blender". |
| Q8 | Não suportado na v1. Correto. P2: segurar **Option** durante a órbita desliga a gravidade [QRC-PT]. |
| Q9 | Ignorar (não cancela). Correto. |
| Q10 | Usar a tabela da §3.2 abaixo. |
| Q11 | Omitir as abas de modelo na v1. Abas de cena P1 no TOOL_HEADER, visíveis só quando há ≥ 1 cena (como no 2027). |
| Q12 | Ok, com um ajuste: o Mac 2027 tem o menu de app "SketchUp" (Sobre, Configurações Cmd+,). Substituir o menu-logo do Blender na TOPBAR por um menu com o ícone do produto contendo: Sobre, Configurações… (Cmd+,), **Abrir no Blender completo**, Sair. Assim Janela não leva itens que o SketchUp não tem ali. |
| Q13 | **0,3 s** (0,4 s parece lento para quem trabalha rápido). Manter no máximo **2** pontos adquiridos. Mais que isso gera linhas pontilhadas demais. |
| Q14 | Chão desligado. Correto. |
| Q15 | "Auto" (clique-mover-clique **e** arrastar). Correto. |
| Q16 | Todos colapsados na 1ª abertura. Correto. Depois **lembrar** quais painéis o usuário expandiu (o SketchUp lembra). Guardar em `settings.json` e reaplicar no `load_post`, para não depender do screen do .blend aberto. |
| Q17 | Sim. Ocioso: "Medidas". Durante a ferramenta, o rótulo da operação ("Comprimento", "Distância", "Ângulo", "Raio", "Lados", "Curvatura", "Segmentos", "Dimensões", "Escala", "Inclinação", "Campo de visão", "Altura dos olhos"). O campo também aceita clique e digitação (B1). |
| Q18 | 1 px lógico. Correto. |
| Q19 | 35° **vertical**. Correto. |
| Q20 | Ligado. Correto. Duplo clique no mesmo ponto também encerra a cadeia de linhas. |
| Q21 | Sim. Correto. Por isso B2 é P0. |
| Q22 | 24 / 6 / 12. Correto. |
| Q23 | Sim, **P0** (B3). |
| Q24 | Não. Correto. |
| Q25 | Sim. Correto. Dentro de um grupo, a geometria de fora **continua inferível** (encaixa em pontos de fora), mas não é selecionável nem gruda. |

### 3.2 Apêndice A corrigido (nomes oficiais pt-BR)

Fonte principal: [QRC-PT] 2026 Mac, a ficha oficial com os rótulos do app. "✗" marca o que muda em relação ao plano. Os nomes antigos e os do usuário viram **sinônimos de busca** no `su.search`.

| id | Oficial pt-BR | Plano v1 | Sinônimos de busca |
|---|---|---|---|
| su.select | Selecionar | ✓ | |
| su.lasso | **Lasso** | ✗ Laço | Laço, Seleção com lasso |
| su.paint | Pintura | ✓ | Balde de tinta |
| su.eraser | **Apagar** | ✗ Borracha | Borracha |
| su.make_component | Criar componente | ✓ | |
| su.line | Linha | ✓ | |
| su.freehand | **Desenho à mão livre** | ✗ Mão livre | Mão livre |
| su.rectangle | Retângulo | ✓ | |
| su.rotated_rectangle | Retângulo girado | ✓ | |
| su.circle | Círculo | ✓ | |
| su.polygon | Polígono | ✓ | |
| su.arc | Arco | ✓ | |
| su.arc2 | **Arco de dois pontos** | ✗ "2 pontos" | Arco |
| su.arc3 | **Arco de três pontos** | ✗ | |
| su.pie | **Pizza** | ✗ Torta | Torta, Setor |
| su.move | Mover | ✓ | |
| su.pushpull | **Empurrar/puxar** (p minúsculo) | ~ | Empurrar, Puxar, Extrudar |
| su.rotate | Girar | ✓ | Rotacionar, Rotar |
| su.followme | Siga-me | ✓ | Follow Me |
| su.scale | Escala | ✓ | Dimensionar |
| su.offset | Equidistância | ✓ | Deslocamento, Deslocar, Offset |
| su.axes | Eixos | ✓ | |
| su.flip | **Virar** | ✗ Inverter | Espelhar, Flip |
| su.tape | Fita métrica | ✓ | Trena |
| su.dimension | **Dimensões** | ✗ Cotas | Cotas, Dimensão |
| su.protractor | Transferidor | ✓ | |
| su.text | Texto | ✓ | |
| su.section | Plano de seção | ✓ | Corte |
| su.text3d | **Texto em 3D** | ✗ | |
| su.orbit | **Órbita** | ✗ Orbitar | Orbitar |
| su.pan | Panorâmica | ✓ | Pan |
| su.zoom | **Aplicar zoom** | ✗ Zoom | Zoom |
| su.zoom_window | Janela de zoom | ✓ | |
| su.zoom_extents | Extensões de zoom | ✓ | Zoom extensão, Zoom estendido |
| su.previous | Anterior | ✓ | |
| su.position_camera | **Posição da câmera** | ✗ | |
| su.walk | **Percorrer** | ✗ Caminhar | Caminhar |
| su.look_around | Olhar ao redor | ✓ | |
| su.fov | Campo de visão | ✓ | |
| su.search | Pesquisar (QRC: "Pesquisa") | ✓ | |
| LTS | **Conjunto extenso de ferramentas** | — | |
| barra | **Primeiros passos** [H-PT] | ✓ | |
| vcb | **Medidas** (caixa Medidas) [H-PT] | ✓ | |
| status | barra de status / **Informações do modelo** (ícone ⓘ) | ✓ | |

**Menus** [H-PT user-interface]: **Arquivo, Editar, Visualizar, Câmera, Desenho, Ferramentas, Janela, Extensões, Ajuda.** O plano muda em "Exibir"→Visualizar e "Desenhar"→Desenho.

**Vistas padrão** [QRC-PT "Exibições padrão"]: Iso, Superior, Inferior, Frontal, Traseira, Esquerda, Direita. O submenu se chama "Exibições padrão".

**Estilo** [QRC-PT]:
- Faces: Raio X, Grade de linhas, Linha oculta, Sombreado, Sombreado com texturas, Monocromático.
- Arestas: Arestas, **Arestas traseiras** (K), Perfis.

**Bandeja** (alta confiança pela UI pt-BR; não achei fonte escrita nesta sessão, conferir numa instalação pt-BR): Bandeja padrão, Informações da entidade, Materiais, Componentes, Estilos, Sombras, Cenas, Instrutor, Suavizar arestas, Estruturador, Neblina.

**Editar** (conferir numa instalação pt-BR): Desfazer, Refazer, Recortar, Copiar, Colar, Colar no local, **Excluir**, **Excluir guias**, Selecionar tudo, Selecionar nada, Inverter seleção, Ocultar, Reexibir ▸, Criar componente…, Criar grupo, Fechar grupo/componente, Interseccionar faces ▸, Inverter faces.

**Mouse** [QRC-PT]: Rolar = Zoom; Clicar e arrastar = Órbita; Shift+Clicar e arrastar = Pan; Clicar duas vezes = "Centraliza a exibição novamente".

**Dicas de inferência** [H-PT drawing-basics, que dá os rótulos pt-BR entre parênteses]:
- Pontos: Ponto de origem, Ponto de extremidade, Ponto central, Em aresta, Em face, Interseção, Centro.
- Linhas: No eixo vermelho/verde/azul, Paralela, Perpendicular, Do ponto, Tangente no vértice.
- Guias e formas: Ponto de orientação (guia), Na linha, Quadrado, Seção áurea, Semicírculo.
- Sufixo em grupo/componente: "no grupo" / "no componente", numa **2ª linha** do tooltip ([REF] inference sheet: "Endpoint / Origin in Component").
- Os termos "Ponto final" e "Ponto médio" do plano são o jeito de falar de muitos instrutores, mas **não** são os rótulos oficiais. Esses rótulos são o item de menor confiança da tabela: se o usuário tiver um SketchUp pt-BR instalado, um print de 2 minutos resolve.

**Modificadores na dica do Selecionar** (Mac): "Clique ou arraste para selecionar objetos. Shift = Adicionar/Subtrair. Option = Adicionar. Shift + Option = Subtrair." Ok, é texto próprio.

**Rótulos do VCB que faltam no `i18n`** [QRC-PT]: **Curvatura** (abaulamento do arco), **Segmentos**, **Inclinação**, **Altura dos olhos**.

---

## 4. Simplificar ou cortar (o usuário de SketchUp não sente falta)

1. **Instrutor**: cortar da v1 (§2).
2. **Estilos (painel)**: na v1, só a aba "Editar" com Arestas (liga/desliga, Arestas traseiras, Perfis), Faces (estilo, Raio X) e Fundo (céu, chão, cores). Sem biblioteca de estilos, miniaturas ou "Mix".
3. **Sombras**: P2 (§2).
4. **Abas de modelo**: fora (ok).
5. **Ferramentas raras**: Laço, Mão livre, Retângulo girado, Arco de três pontos, Pizza, Olhar ao redor e Campo de visão (ferramenta) vão para P2, como botões desabilitados na posição.
6. **Botões L+M = pan**: P2. Ninguém usa.
7. **Figura de escala, Neblina, Ambientes, Hachura, Procedimentos**: fora (ok).
8. **"✕" por painel e pino da Bandeja**: decorativos ou P2 (ok).
9. **Cores de inferência "em contexto"**: usar uma cor só (magenta) para todos os marcadores dentro de grupo. Não tentar reproduzir o roxo (115,90,165) do "Origin in Component".

---

## 5. Mudanças obrigatórias no plano (lista acionável)

1. **Keymap global**: mover os atalhos de ferramenta, Delete/⌫, Cmd+A/Shift+Cmd+A/Shift+Cmd+I e as teclas do VCB ociosas para o keymap `Window`, com poll do modo e sem campo de texto ativo. Criar um GUI-sim: mouse sobre a Bandeja, `L` ativa Linha; mouse sobre a barra de status, `3` Enter redigita a última linha.
2. **Caixa Medidas editável** por clique, chamando o mesmo `APPLY` do VCB.
3. **Verso próprio (P0)**: `show_backface_culling=True`, passada de verso do WS4 com material de verso (`su_back_mat`), sem overlay de orientação. A Pintura grava frente ou verso conforme o lado clicado. Remover o R7 como "limitação aceita".
4. **Arestas suaves/atenuadas P0** nas laterais de extrusão de curvas (círculo/arco), com sombreamento suave (`sharp_face=False`, `sharp_edge` nas duras). Polígono continua duro.
5. **Curva como entidade P0** (seleção, Apagar, Mover, inferência de Centro). Edição de raio/segmentos P1.
6. **Separadores da barra "Primeiros passos"** exatamente como em B5. A sonda de layout checa as posições dos separadores.
7. **Ordem da Bandeja**: Informações da entidade, Materiais, Componentes, Estilos, Sombras, Cenas, (Instrutor), (Suavizar arestas), Estruturador.
8. **Substituir o Apêndice A** pela tabela da §3.2, incluindo menus (Visualizar, Desenho), vistas, estilos, VCB e inferências. Renomear Delete para **"Excluir"** e Flip para **"Virar"**.
9. **Trackpad (Q7) P0** com o mapeamento da §3.1. **Ctrl+clique = menu de contexto** no Mac.
10. **Mover**: vértice/aresta com dobra automática (P0); face restrita com Cmd para dobrar (P1). Invariante: nunca gravar face não plana.
11. **Histerese de inferência** (liberação ≈ 1,5× captura) em pontos, arestas e eixos. Adicionar `SNAP_RELEASE_FACTOR` em `constants.py`.
12. **Plano antes do clique** (gizmo colorido) para Círculo, Polígono, Girar e Transferidor, mais **retângulo vertical automático** ao arrastar ao longo de um plano de eixo vertical. Ambos com aceite GUI-sim.
13. **Pintura com seleção** pinta toda a seleção. **Apagar** sobre grupo apaga o grupo.
14. **Separador decimal pela região do macOS**, não pelo idioma. Exibir `~` em valores arredondados (P1).
15. **Linha**: duplo clique no mesmo ponto encerra a cadeia.
16. **Q13**: pausa de 0,3 s e no máximo 2 pontos adquiridos.
17. **Prioridades**: Transferidor → P1; Instrutor → cortar; Laço, Mão livre, Retângulo girado, Arco de três pontos, Pizza, Olhar ao redor, Campo de visão e Sombras → P2. Interseccionar faces, Posição da câmera e Texto em 3D → P1. Ocultar/Reexibir e Explodir no M3.
18. **Menu-app** (ícone do produto) na esquerda da TOPBAR: Sobre, Configurações… (Cmd+,), Abrir no Blender completo, Sair.
19. **Botões P2 desabilitados**: ícone a 40% e mensagem "Em breve" na barra de status. Célula da Etiqueta vazia.
20. **Tooltip "no grupo"/"no componente"** em 2ª linha da caixa amarela.
21. **Lembrar os painéis da Bandeja** expandidos entre sessões (`settings.json`).
22. **Documentar os desvios aceitos**: barra de status de largura total (estilo 2023) e menus dentro da janela.
