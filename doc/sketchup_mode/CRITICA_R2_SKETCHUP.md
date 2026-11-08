# CRÍTICA R2 — especialista SketchUp (revisão do PLANO v2)

Resumo: a v2 incorporou bem a R1. Dos 14 bloqueantes, 11 estão corretos, 2 estão certos na ideia mas incompletos na implementação (B1 e B9) e 1 tem o teste de aceite errado (B10).

Os pontos novos que mais pesam são três:
- a seleção é perdida depois do desfazer e do Mover (§2.1);
- a superfície suave não é tratada como uma entidade (§2.2);
- vários aceites P0 não testam o que faz o SketchUp "parecer SketchUp" (§3).

Decisões finais do usuário respeitadas e não reabertas: Transferidor P0, performance adiada, sem Etiquetas.

---

## 1. Verificação dos bloqueantes da R1

| R1 | Situação na v2 | Observação |
|---|---|---|
| B1 teclas fora da viewport | **Incompleto** | A §3.5-1 só põe `TEXTINPUT` em `Window`. Faltam **RET, NUMPAD_ENTER, BACK_SPACE e ESC**: sem eles, "digitar `3` + Enter com o mouse na status bar" (o próprio aceite da §5.1) não funciona. A ordem dentro de `Window` também precisa ser explícita: `BACK_SPACE` → `su.vcb_key` (retorna `PASS` se o buffer estiver vazio) **antes** de `BACK_SPACE` → Excluir seleção. Senão, apagar um dígito digitado exclui a seleção. O mesmo vale para ESC (limpar buffer → cancelar → sair do grupo). |
| B2 verso com material próprio | Ok | Detalhe: o "lado clicado" da Pintura deve vir do sinal de `dot(direção do raio, normal da face)`. Não pode vir de qual cópia (original ou invertida) o `ray_cast` atingiu, porque as duas são coplanares e o resultado é arbitrário. |
| B3 laterais suaves | Ok | Falta a consequência na seleção (§2.2). |
| B4 curva como entidade | Ok | |
| B5 separadores | Ok | |
| B6 ordem da Bandeja | Ok | Seções P2 (Sombras, Suavizar arestas, Estruturador) **não** devem aparecer vazias. Mostre só as que existem, na ordem dada. |
| B7 nomes pt-BR | Ok | Uma inconsistência: §5.3 diz "G = Criar grupo até o P1", mas §4.3 diz que o botão Criar componente fica desabilitado até lá. Tecla e botão precisam fazer a mesma coisa (§4, item 6). |
| B8 trackpad | Ok na tabela | Implementação incompleta (ver B9). |
| B9 Ctrl+clique | **Incompleto** | O keymap da ferramenta tem `LEFTMOUSE ANY → su.tool_event`. Então Ctrl+clique (menu de contexto) e Ctrl+Cmd+arrastar (órbita) chegam **primeiro** à ferramenta como um PRESS: começam uma Linha, selecionam, etc. Regra que falta: no Mac, `press()` com `ctrl` (com ou sem Cmd/Shift) retorna `PASS` sem efeito, e o dispatcher deixa passar para os itens de contexto e de órbita. Isso precisa de teste GUI. |
| B10 dobra automática | **Aceite errado** | O aceite "aresta do topo da caixa movida 1 m para cima → topo dobra em 2 faces" está geometricamente errado. Subir uma aresta da borda do topo deixa o topo plano (ele só inclina), e nada dobra. Ver os aceites corretos na §3. A restrição de face também precisa permitir movimentos que **mantêm** a planaridade. Exemplo: o topo de uma caixa movido em +X dá uma caixa "cisalhada", e isso é permitido no SketchUp. Uma implementação ingênua ("face só se move ao longo da normal") travaria esse caso. |
| B11 histerese | Ok | O aceite 1,2×/1,6× é bom. |
| B12 plano antes do clique / retângulo em pé | Ok | |
| B13 Pintura com seleção / Apagar grupo | Ok | |
| B14 decimal do sistema | Ok | |

---

## 2. Problemas novos na v2

### 2.1 Seleção perdida no desfazer e no Mover (bloqueante de "feel")
A §3.7 diz "seleção não é desfeita: é limpa" e a §3.8 diz "limpa quando a topologia muda". As duas regras estão erradas para o SketchUp [EXP]:
- **Depois do Mover, Girar ou Escala, a seleção continua** nas mesmas entidades. É assim que se encadeia Mover → Girar → Escala sem reselecionar.
- **Depois de uma cópia com Option, a seleção passa a ser a cópia.** O próximo Girar ou `5x` age sobre ela.
- **Depois de Cmd+Z**, as entidades que voltaram a existir continuam selecionadas. O fluxo diário é: selecionar, Mover, "errei", Cmd+Z, Mover de novo. Limpar a seleção aqui irrita qualquer usuário.

Proposta mínima:
- `TransformSession.finish()` devolve o mapeamento de índices, e a seleção é remapeada (cópia → refs da cópia).
- Para o undo, gravar a seleção junto com cada `undo.push` (dict `undo_step → refs`) e restaurar no `undo_post`. Alternativa: um atributo bool `su_sel` escrito no `write()`, que o memfile restaura sozinho.

### 2.2 Superfície suave = uma entidade
Com B3 em P0, o comportamento associado também precisa ser P0 [EXP]:
- **Clicar na lateral de um cilindro seleciona a superfície inteira.** São as faces ligadas por arestas `su_soft`, e o Informações da entidade mostra "Superfície".
- **Pintura** pinta a superfície inteira.
- O **pré-realce do Mover** pega a superfície.
- **Empurrar/puxar não atua** em face de superfície curva (não há realce).

A implementação é um flood fill local por arestas `su_soft`, igual ao de `logical_face`.

### 2.3 Direção do zoom no trackpad
A direção do zoom por rolagem de dois dedos depende de "rolagem natural" do macOS. Ela não está especificada. Colocar no roteiro manual: "deslizar dois dedos para cima aproxima? conferir com o usuário". Adicionar uma opção "inverter zoom do trackpad" em Configurações. É barato e evita discussão.

### 2.4 Orbitar com Ctrl+Cmd: o pivô é o ponto do PRESS
`CLICK_DRAG` só dispara depois do limiar de arrasto. A órbita deve usar como pivô a profundidade sob o ponto do **PRESS**, não o ponto onde o arrasto foi detectado. Senão, o pivô "pula" alguns pixels.

### 2.5 Aba vertical "Bandeja padrão"
É um desvio visual pequeno, aceitável. Registrar como **desvio aceito** junto com os da §1.1, para ninguém tentar "consertar" depois.

---

## 3. Revisão dos aceites das ferramentas P0

Os aceites atuais provam que **a geometria está certa**. Faltam testes do que faz o SketchUp **parecer** SketchUp: encaixe em outra geometria, encadeamento, redigitar, seleção depois da ação e o caso de uso real. Acrescentar:

| Ferramenta | Aceites a acrescentar |
|---|---|
| **Linha** | (1) **Cura**: Excluir a face do topo de uma caixa e redesenhar uma das 4 arestas por cima → a face volta (gesto clássico de reparo). (2) Linha de borda a borda numa face **vertical** de caixa → divide em 2 faces. (3) Laço fechado num plano vertical (com ↑ travado) → face vertical. (4) MMB orbitando no meio da cadeia → o elástico continua do mesmo âncora, sem cancelar. |
| **Retângulo** | **Porta**: retângulo 0,9×2,1 começando **na aresta inferior** da face frontal de uma parede (caixa 4×0,2×2,8) → a face vira **2 faces sem pontes** (U + porta). Empurrar a porta `0,2` → abertura passante (é o roteiro §8.4). Retângulo sobre face vertical sem seta → nasce no plano da face. |
| **Círculo / Polígono** | Hover sobre a face lateral de uma caixa → gizmo vermelho/verde (plano da face), e o círculo nasce nela. `↑` antes do clique no vazio → círculo vertical. Clique na lateral do cilindro → seleciona a **superfície** (§2.2). |
| **Empurrar/puxar** | (1) **Encaixe em outra geometria**: duas caixas de alturas 1 e 2; puxar o topo da menor e pairar sobre o topo da maior ("Em face"/"Ponto de extremidade") → altura final 2,000. É o uso nº 1 da inferência no Empurrar/puxar. (2) Redigitar `1,5` após concluir → altura muda (1 passo "Ajustar"). (3) Duplo clique em outra face → mesma distância. |
| **Equidistância** | Duplo clique em outra face repete a distância. Equidistância numa face **com furo** → anel externo e furo deslocados corretamente. |
| **Siga-me** | Perfil retangular 0,1×0,1 na face superior de uma caixa, com o caminho = bordas do topo pré-selecionadas → moldura contínua, sólido fechado. |
| **Selecionar** | Clique numa aresta de grupo → seleciona o grupo (bbox azul). Dentro do grupo, a geometria de fora não é selecionável, mas a Linha encaixa nela. Esc sai do grupo. |
| **Apagar** | Arrastar sobre arestas que pertencem a uma curva → a curva inteira em 1 undo. Option sobre a aresta lateral de uma caixa → suaviza (aresta some, sombreamento contínuo). |
| **Pintura** | Pintar a lateral de um cilindro → a superfície inteira. Cmd+clique (conta-gotas) → material ativo = o da face. |
| **Mover** | (1) **Seleção mantida** depois do Mover; depois de Option+cópia, a seleção é a cópia (§2.1). (2) `/4` depois da cópia → 3 cópias intermediárias. (3) Encaixe: mover uma caixa pegando um canto e soltando no canto de outra ("Ponto de extremidade") → coincidência exata. (4) Sem seleção: pairar e arrastar uma face solta → estica a geometria ligada. (5) **Dobra** (substitui o aceite errado): mover **1 vértice** do topo de uma caixa 0,5 m para cima → o topo vira 2 triângulos com uma aresta de dobra; as laterais continuam quadriláteros planos. (6) **Cumeeira**: linha entre os pontos médios das arestas opostas do topo, mover essa linha 1 m em ↑ → 2 águas + 2 oitões pentagonais, 7 faces, todas planas. (7) **Face cisalhada permitida**: o topo de uma caixa movido 0,5 em +X → aceito e todas as faces planas. (8) Mover um grupo sobre geometria solta → nada gruda. |
| **Girar** | Hover sobre uma face vertical → transferidor vermelho/verde. Girar uma cópia de uma caixa em torno do canto, `90` + `3x` → 4 caixas a 90°. A seleção continua depois de girar. |
| **Escala** | `-1` numa alça de face → espelha (normais corretas, frente para fora). Escalar um grupo → só a matriz muda. |
| **Fita métrica** | Option (modo medir) → Medidas mostra o comprimento e **nenhuma** guia é criada. Ponto-guia a partir de uma extremidade. Interseção de duas guias inferível pela Linha. |
| **Transferidor** | Hover sobre uma face vertical → gizmo no plano dela. Guia angular com `30` encaixa a Linha. |
| **Dimensões** | Cota numa aresta de 3 m mostra "3,00m". Depois de Cmd+Z, ela some. O texto continua legível ao orbitar. |
| **Navegação** | **Zoom no cursor**: o ponto 3D sob o cursor continua sob o cursor (±2 px) depois de 5 passos de roda. **Pivô**: o ponto sob o cursor no início do arrasto MMB não se move na tela durante a órbita (±2 px). Duplo clique MMB → o ponto vai ao centro. Ctrl+clique abre o menu de contexto **sem** iniciar a ferramenta. |
| **Inferência** | **Prioridade**: com âncora na origem, o cursor perto de uma extremidade **e** do eixo vermelho → vence "Ponto de extremidade". "Em face": Linha no topo de uma caixa → os pontos ficam no plano do topo (z constante). |
| **Medidas** | Uma tabela de parse (unit) cobrindo: `2,5` · `250cm` · `2;3` · `[1;2;0]` · `<1;0;0>` · `5x` · `/5` · `12s` · `1r` · `3:12` · `~`. Com o mouse sobre a Bandeja: `2,5` + Enter redigita; `⌫` com buffer apaga o dígito e **não** exclui a seleção. |

---

## 4. Mudanças obrigatórias (v3)

1. **Teclas de Medidas em `Window`**: incluir RET, NUMPAD_ENTER, BACK_SPACE e ESC (não só `TEXTINPUT`), com a ordem: `su.vcb_key` (PASS se o buffer estiver vazio) antes de Excluir/cancelar/sair do grupo. Aceite: `⌫` com buffer ≠ vazio não exclui a seleção.
2. **Ferramentas ignoram LMB com Ctrl (Mac)**: `press()` com `ctrl` → `PASS`, para Ctrl+clique (menu) e Ctrl+Cmd(+Shift)+arrastar (órbita/pan) funcionarem. A órbita usa o pivô do ponto do PRESS.
3. **Seleção preservada**: depois de Mover, Girar e Escala, mantém; depois de uma cópia, passa a ser a cópia; depois de desfazer/refazer, é restaurada (gravada por passo de undo ou em atributo `su_sel`). Remover "seleção limpa no undo" da §3.7/§3.8.
4. **Superfície suave como entidade (P0)**: Selecionar, Pintura e pré-realce agem na superfície inteira (flood fill por `su_soft`); Empurrar/puxar não age nela; o Informações da entidade mostra "Superfície".
5. **Pintura**: o lado é determinado por `dot(raio, normal)`, não pela cópia atingida.
6. **G e botão Criar componente coerentes** até o P1. Recomendo: ambos executam "Criar grupo", e a dica da status bar diz que componentes ainda não existem. Não deixar a tecla funcionando com o botão desabilitado.
7. **Trocar o aceite de dobra** da §6.1 Mover pelos casos (5), (6) e (7) da §3. A restrição de face deve ser "rejeitar só o que deixaria alguma face não plana", não "só ao longo da normal".
8. **Acrescentar os aceites da §3** aos cenários de cada dono, priorizando: Porta (Retângulo + Empurrar/puxar), Encaixe em outra geometria (Empurrar/puxar e Mover), Cura da face (Linha), Seleção depois do Mover/cópia, Zoom no cursor/pivô, ⌫ com buffer.
9. **Bandeja**: não mostrar seções P2. Registrar a aba vertical como desvio aceito (§1.1).
10. **Trackpad**: opção "inverter zoom do trackpad"; o roteiro manual confere a direção com o usuário.
