# Crítica R2 — Especialista Blender/Python

Revisão do `PLANO.md` v2. **Critério desta rodada (decisão do usuário):** correção, simplicidade e execução por agentes paralelos. Velocidade não conta.
Tudo marcado **[VERIFICADO]** foi rodado agora no Blender 5.2.2. Scripts e prints ficam na pasta `crit/` do scratchpad:
`/private/tmp/claude-1313471784/-Users-tiago-agenor--claude-spares-spare-OyPPwD/b629df7a-43bf-4aae-9e76-4fba22f313f3/scratchpad/crit/` (`g_r2.py`, `h_r2.py`, `h_r2b.py`, `g_r2_out.txt`, `r2_above_c.png`, `r2_below_c.png`).

Veredito: a v2 incorporou bem a R1. A maior parte das novidades funciona: versos via GN, `Window` keymap e furos têm caminho verificado. Ainda há **um bloqueio real**: o Enter sobre um botão aperta o botão. Também há **três bugs de contrato** e uma fatia vertical **grande demais e mal distribuída**.

---

## 1. Os itens da R1 foram atendidos?

| R1 | Situação na v2 | Observação |
|---|---|---|
| 1 Fatia vertical | ✔ com problema | Grande demais e feita só por A (ver §3) |
| 2 6 agentes + integrador | ✔ | |
| 3 Sem stubs alheios | ✔ com problema | "B começa na Fase A sobre `document.py`/`geom.py` que **passam a ser de B**": a troca de dono no meio do caminho gera conflito. Esses arquivos devem ser de B desde o dia 0 |
| 4 Auto-descoberta, `@tool`, props por dono, `hasattr` | ✔ mais complexo que o necessário | Cadeia de finalizadores + classe `SU_SceneProps` dinâmica (ver §4) |
| 5 Fonte única da ferramenta | ✔ com lacuna | Falta definir quais eventos `su.tool_event` deixa passar (ver §2.4) |
| 6 Aba única, sem objeto ativo, glTF | ✔ | |
| 7 `status_text_set(None)` | ✔ | |
| 8 Cliques em Python | ✔ | |
| 9 Lista de permissão | ✔ com risco novo | Os itens foram para o `Window`: Enter sobre botões e janelas temporárias (ver §2.2) |
| 10 Arestas via GN | ✔ e estendido aos versos | Funciona, com 3 armadilhas (ver §2.1) |
| 11 Seleção em sets | ✔ | |
| 12 Sem ScreenGrid | ✔ | |
| 13 Snapshot e BVH | Parcial, aceitável | `bm.copy()` é OK sem meta de performance. Já a **BVH congelada** "por correção" não é necessária (ver §4.1) |
| 14 `undo_push` em toda mutação | ✔ | Conflita com o dono dos dados de load_post (ver §3.2) |
| 15 `rebuild_face` | ✔ | Agora com implementação verificada (ver §2.3) |
| 16/17 Orçamentos | Adiado | Correto pela decisão do usuário |
| 18 Prefs fora do template | ✔ | |
| 19 Harness | ✔ | |
| 20 Cortes | Parcial | Aceitável |
| 21 `draw_3d/2d` + `prims` | ✔ | |
| 22 Spikes | ✔ | |

---

## 2. Riscos técnicos novos da v2

### 2.1 Versos por cópia invertida em GN + backface culling — [VERIFICADO], funciona
Montei o nó: `Join(Set Material Index(Flip Faces(original), su_back_mat), Delete Geometry ONLY_FACE(original), original)` com `show_backface_culling=True` e `color_type='MATERIAL'`.
- De cima, o piso com normal −Z mostra o verso **pintado de madeira** (sem tom azul) e o verso padrão azul-acinzentado, os dois **iluminados**. De baixo, aparece a frente branca. Não há z-fighting e as arestas continuam visíveis. Prints: `r2_above_c.png`, `r2_below_c.png`.
- `material_index` da cópia = `su_back_mat` ✔. O índice da face original é `idx % n_orig` ✔.

Armadilhas encontradas, que precisam entrar no contrato:
1. **`scene.ray_cast` ignora o culling.** De cima **e** de baixo, o raio retornou a **cópia** (idx 14 = 6 + 8) com a normal **invertida** (0,0,1). Regra: a normal vem sempre da face original (`idx % n`), e o "lado clicado" (Pintura frente/verso, plano de inferência) é `sign(dot(ray_dir, normal_original))`, nunca a normal do hit.
2. **`su_back_mat = −1` no contrato (§2.4) é um bug.** `Set Material Index` com −1 não aponta para "Padrão (verso)". Reservar o **slot 1** de todo documento para "Padrão (verso)", com padrão `su_back_mat = 1`. Um verso pintado acrescenta um slot ao objeto.
3. **Exportar OBJ/glTF/STL e Interseccionar** usariam a malha avaliada, com faces duplicadas e arestas soltas. Exportar sempre sem modificadores (`apply_modifiers/use_mesh_modifiers=False`) e Interseccionar sobre `obj.data`. **Raio X** (P1) mostraria as duas cópias: desligar a cópia (entrada booleana do grupo) quando `xray`.

### 2.2 `Window` keymap para letras e Medidas em qualquer lugar — [VERIFICADO], com 1 bloqueio
Com o mouse sobre o viewport e sobre a Bandeja, `TEXTINPUT('3')`, `L`, `RET` e `BACK_SPACE` chegaram aos itens do `Window` ✔.
**Sobre um botão do header, o `RET` apertou o botão ("HEADER BUTTON PRESSED") e não chegou ao `Window`.** Esse tratamento é fixo no código da UI, não vem do keymap `User Interface`, então a lista de permissão não resolve. Portanto "`3` Enter com o mouse sobre o LTS, a toolbar, a Bandeja ou o campo Medidas" falha: aciona o botão sob o mouse ou entra em edição do campo.
**Correção:** quando o buffer de Medidas deixa de estar vazio (1º dígito via `Window TEXTINPUT`), iniciar um modal leve `su.vcb_capture`. Handlers modais de janela rodam **antes** dos handlers de região/UI. Esse modal consome texto, `RET`, `NUMPAD_ENTER`, `BACK_SPACE` e `ESC` até APPLY/CANCEL e repassa todo o resto (`PASS_THROUGH`). Com uma ferramenta em operação, o modal dela já cumpre esse papel. Precisa entrar no spike S-I.
Outros pontos:
- O `Window` keymap também vale nas **janelas temporárias** (Abrir/Salvar, Preferências). O poll dos itens SketchUp deve exigir janela principal e `context.area.type in {'VIEW_3D','STATUSBAR','TOPBAR'}`.
- **Ctrl+clique (menu de contexto) e Ctrl+Cmd+arrastar (órbita)** como itens `LEFTMOUSE CLICK/CLICK_DRAG` **nunca disparam** se nada mudar: o item `LEFTMOUSE ANY → su.tool_event` do keymap da ferramenta é avaliado antes e também casa com CLICK/CLICK_DRAG. Contrato de `base`: `su.tool_event` trata só `PRESS`/`RELEASE` (e `DOUBLE_CLICK` como `PRESS`). Ele devolve `PASS_THROUGH` para `CLICK`/`CLICK_DRAG` e para `PRESS` com Ctrl ou Ctrl+Cmd.

### 2.3 `rebuild_face` com furos — [VERIFICADO] via `mathutils.geometry.delaunay_2d_cdt`
Com `output_type=5` ("faces válidas para BMesh, com detecção de buracos"), o resultado é uma partição em n-gons, com as **arestas extras sendo exatamente as pontes**. Casos testados (área conferida):

| Caso | Faces de saída |
|---|---|
| 1 furo | 6+6 (anel) + 4 (face interna) |
| 2 furos | 7, 7, 6, 4, 4 |
| Furo tocando a borda | 8 + 4 |
| L côncavo + furo | 8, 6, 4 |

A face interna sempre sai, que é o comportamento certo para "retângulo dentro de face". Para um furo **passante**, basta descartar a face cujo conjunto de vértices é o do loop interno.
Isso torna `rebuild_face` uma função curta: projetar no plano → CDT tipo 5 (`need_ids` para mapear aos `BMVert` existentes) → apagar o cluster → criar faces → arestas não-entrada = `su_bridge`. O tipo 4 **não** serve: faces sobrepostas, área 10 em vez de 9. Recomendo fixar esse algoritmo no plano. O S-C vira só a suíte de testes.

### 2.4 Detecção do locale Apple — [VERIFICADO]
`subprocess.run(["defaults","read","-g","AppleLocale"])` dentro do Blender retornou `'pt_BR'` em cerca de 15 ms. `locale.localeconv()` sem `setlocale` retorna `'.'`, o que confirma que ler `defaults` é necessário. Fazer 1× com cache e fallback para `AppleLanguages` e depois para o idioma. ✔

### 2.5 Outros pontos novos
- **`su_visible` derivado em `Document.write`** acopla B ao estilo de D: alternar "mostrar suaves" exigiria reescrever todos os documentos. O nó GN deve calcular `not (su_bridge or su_hidden or (su_soft and not show_soft))` direto dos atributos, com `show_soft` como entrada do grupo definida por D. Remover `su_visible` do contrato.
- **`session.on_load_post` (A) cria materiais e GN**, que são domínios de F e D. Isso viola a regra de dono e cria dependência circular. A deve só emitir `events.emit("load")`: D garante o GN, F garante os materiais (slot 0/1), B garante a raiz. A faz um único `undo.push("undo.init")` depois de todos.
- **`tray.register_section`** é usado por F e G, mas não consta da §2.4.

---

## 3. Fatia vertical e precisão das interfaces

### 3.1 A fatia está grande demais e serializa o projeto
A lista da §9.1 cabe a um único agente: casca, céu, tema, `Document`/`geom`/`rebuild_face`, GN, inferência com histerese, Medidas com decimal do sistema, Linha, Retângulo, Empurrar/puxar com BVH, undo, `testing`, harness, `compare` com sondas e print ao usuário. São milhares de linhas, enquanto 4 agentes esperam. Ela é **suficiente** para congelar os contratos, mas não é **mínima**.

Proposta: a fatia é uma **integração feita por A de entregas mínimas dos donos**, com todos começando no dia 0 em módulos puros:

| Dono | Entrega do dia 0–1 |
|---|---|
| B | `Document` (write/invalidate), `add_edge` simples, `auto_faces` de laço simples, `rebuild_face` (CDT) + testes headless |
| C | `units`/`vcb.parse` (headless); inferência mínima (extremidade + eixos) |
| D | `prims.py`, `display_gn.py`, céu, tema base |
| A | registry/auto-descoberta, `base` + `su.tool_event` + gizmo de hover, Window keymap + `su.vcb_capture`, `testing`, harness, undo, Linha |
| E | Retângulo |

**Sai da fatia:** casca exata, histerese, decimal do sistema, Empurrar/puxar, `compare` com sondas e print ao usuário. Saída = E2E "Linha 3×2 via Medidas + Retângulo + Cmd+Z", e aí congelar. Os 6 agentes ficam ocupados desde o início.

### 3.2 Lacunas de contrato que vão gerar conflito
1. Troca de dono de `document.py`/`geom.py` (§9.2) → B é dono desde o dia 0.
2. `on_load_post` fazendo o trabalho de D/F/B (§2.5).
3. `tray.register_section(order, id, label_key, draw_fn)` ausente da §2.4 (ou eliminar, ver §4).
4. Lista **canônica de ids** de ferramenta (o Apêndice A deveria ser a fonte) e **prefixo de chave i18n por dono** (`tool.<id>.*` do dono da ferramenta, `ui.*` de D…) para evitar colisões em `register_strings`.
5. Semântica de eventos de `su.tool_event` (§2.2) e das ferramentas de navegação (G) em relação ao modal genérico.
6. `su_back_mat` (slot 1) e o slot 0 "Padrão": quem cria e quem garante (F), e quem lê (D, no GN).

---

## 4. Complexidade que dá para cortar agora que performance é adiada

1. **BVH congelada (`static_bvh`, `frozen=`)**: os índices das faces em movimento são estáveis durante a sessão, porque a topologia é criada 1×. `spatial.ray_cast` relança do ponto do hit + ε quando a face atingida está no conjunto em movimento (máx. 4 vezes). É correto e tem metade do código. Remover `Document.static_bvh` e `QueryCtx.frozen`.
2. **Props dinâmicas + cadeia de finalizadores**: cada dono registra o seu `Scene.su_<grupo> = PointerProperty(...)` no próprio `register()`. Sem `SU_SceneProps` dinâmico e sem `props.finalize`. Só o `keymap.finalize` precisa rodar depois de todos.
3. **Bandeja com um painel `HIDE_HEADER` + `layout.panel_prop` + estado em `settings`** (e o spike S-H): usar `Panel`s nativos com `bl_order` e `DEFAULT_CLOSED`. O cabeçalho nativo, a cor pelo tema e o estado aberto por arquivo vêm de graça. "Lembrar entre arquivos" fica para P2. Remove `register_section`, as props `tray_open_*` e o S-H.
4. **`su_visible` derivado** → expressão no GN (§2.5).
5. **`display_fallback.py` na árvore**: não criar o arquivo, a menos que o S-B falhe. O S-B já foi praticamente validado: arestas na R1 e versos agora.
6. **Modo de modificadores Windows**: sem teste em Windows, é código morto → P2.
7. **`compare.py` lado a lado**: manter só as sondas de cor e o `state_dump` para a ordem dos botões. A montagem lado a lado é cosmética e pode ser manual nas rodadas com o usuário.

---

## 5. Mudanças obrigatórias (v3)

1. **Medidas com captura modal:** ao iniciar o buffer, `su.vcb_capture` (modal de janela) consome texto/`RET`/`NUMPAD_ENTER`/`BACK_SPACE`/`ESC`; o resto passa. Adicionar ao S-I o teste "`3` Enter com o mouse sobre um botão do LTS, sobre a toolbar e sobre o campo Medidas" (hoje o botão é acionado — verificado).
2. **Poll dos itens SketchUp no `Window`:** janela principal e área em `VIEW_3D`/`STATUSBAR`/`TOPBAR`.
3. **`su.tool_event`:** só `PRESS`/`RELEASE`; `PASS_THROUGH` para `CLICK`/`CLICK_DRAG` e para `PRESS` com Ctrl ou Ctrl+Cmd (assim Ctrl+clique e as órbitas do trackpad funcionam).
4. **Lado e normal do hit** sempre pela face original (`idx % n`, `dot(ray_dir, n_orig)`). Escrever no contrato de `spatial.ray_cast`.
5. **`su_back_mat`:** slot 1 = "Padrão (verso)", padrão 1. Nunca −1.
6. **Exportar/Interseccionar sem modificadores;** Raio X desliga a cópia de verso via entrada do grupo GN.
7. **GN calcula a visibilidade** a partir de `su_bridge`/`su_hidden`/`su_soft` + entrada `show_soft`. Remover `su_visible` de `Document.write`.
8. **`rebuild_face` = CDT `output_type=5`** (+ descartar a face do furo passante). Registrar como algoritmo decidido.
9. **`load_post` por eventos:** cada dono garante o seu; A só emite o evento e faz 1 `undo_push`.
10. **B é dono de `document.py`/`geom.py` desde o dia 0.** A fatia vertical integra entregas mínimas de A, B, C, D e E (tabela da §3.1). Casca exata, histerese, decimal, Empurrar/puxar e prints saem da fatia.
11. **Remover a BVH congelada** (relançar o raio pulando as faces em movimento).
12. **Props registradas pelo próprio dono** (`Scene.su_<grupo>`). Remover `props.finalize` e a cadeia de finalizadores, exceto keymap.
13. **Bandeja com `Panel`s nativos** (`bl_order`, `DEFAULT_CLOSED`). Remover `panel_prop`, `register_section` e S-H.
14. **Adicionar à §2.4:** lista canônica de ids (Apêndice A), prefixos i18n por dono e a semântica de eventos de `base`.
15. **Mover para P2** o modo de modificadores Windows e o `compare.py` lado a lado. Não criar `display_fallback.py` sem uma falha do S-B.
