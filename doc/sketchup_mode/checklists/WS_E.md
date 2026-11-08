# WS_E — Agente E (Desenho)

Legenda: `[ ]` pendente · `[~]` em andamento · `[x]` feito. Brief: `PLANO.md` §9.2-E (sub-checklist copiado abaixo; o agente E mantém este arquivo).

## Sub-checklist §9.2-E
1. [x] Retângulo (fatia) → completo (em pé automático, sobre face, porta)
2. [ ] Linha (assumida de A): duplo clique encerra, cura, plano vertical, redigitar
3. [x] Círculo e Polígono (gizmo de plano, lados, curva-entidade, laterais suaves)
4. [x] Arco de dois pontos
5. [x] Empurrar/puxar (skip de faces em movimento, encaixe, perfurar, esticar, Option, duplo clique, redigitar, recusa em superfície)
6. [x] Equidistância (com furo; duplo clique)
7. [~] Siga-me (caminho pré-selecionado; moldura)
8. [ ] P1: Arco (centro)

## Aceite e comandos (referência)
- **Aceite**: AC-LIN-1..7, AC-RET-1..5, AC-CIR-1..4, AC-ARC-1, AC-EMP-1..7, AC-EQD-1..3, AC-SIG-1..2.
- **Comandos**: `tools/sketchup_mode/run_unit.sh test_e_` · `tools/sketchup_mode/run_gui.sh scn_e` · `tools/sketchup_mode/shot.sh scn_e:porta /tmp/e.png`

## Notas

- **Retângulo** (`tools/rectangle.py`): plano = seta (trava a NORMAL: ↑ horizontal, → normal vermelha, ← normal verde — decisão AC-CIR-4) › face do 1º clique › face pairada que contém o 1º canto › plano de eixo pelo 1º canto que contém o ponto inferido ("em pé") › horizontal pelo 1º canto (cursor acima do horizonte → plano vertical de eixo voltado para a câmera). `L;W`: 1º valor no 1º eixo do plano (X, senão Y), sinais pelo quadrante do mouse, negativo inverte. Redigitar = restaura o snapshot de antes e redesenha ("Ajustar"). Retângulo vertical isolado é orientado para a câmera; o resto da orientação é do kernel B (chão → −Z, vizinhas).
- A consulta de inferência do Retângulo/Empurrar usa `Locks()` vazio (Shift/setas não viram trava de linha do motor; as setas são tratadas pela ferramenta).
- **Empurrar/puxar** (`core/geom_extrude.py`): reconstrução a partir do snapshot a cada movimento (simples; perf adiada). Regras: lados por aresta de contorno; lado coplanar com a vizinha → estende (puxar: aresta apagada, faces fundidas) ou corta (empurrar: região removida); face movida que cai sobre face coplanar existente → perfura as duas; face original fica só se a região coplanar for uma "folha" solta (piso) ou com Option; furo aberto continua aberto; lados de curva = `su_soft` + `smooth`. Distância digitada segue a direção atual; sem movimento, positivo = para o lado visto pela câmera.
- **AC-EMP-6** (Option no topo da caixa): resultado = 11 faces (topo original fica + 4 lados + topo novo). O "+1 face" do aceite só vale para uma face solta; registrado.
- **Seleção da face** (Empurrar/puxar, Equidistância, Siga-me): se a inferência é um ponto (ponto central, centro, aresta) sobre a face, a face vem de um `spatial.ray_cast` no cursor (`pushpull.face_pick`), como no SketchUp.
- **Círculo/Polígono** (`tools/circle.py`, `polygon.py`): gizmo de plano antes do clique (seta trava a normal; face pairada; chão); número antes do clique = Lados; `Ns`/raio durante e depois (Ajustar). Curva-entidade com metadados `kind/center/normal/radius/sides` (C infere o centro). Empurrar/puxar: laterais de círculo/arco `su_soft` + `smooth`, polígono duro; o círculo do topo vira uma curva nova (centro movido).
- **Arco de dois pontos** (`tools/arcs.py`): início, fim (ou comprimento da corda digitado), curvatura; `Nr` raio, `Ns` segmentos (padrão 12); metadados `kind=arc`.
- **Equidistância** (`core/geom_extrude.offset_faces`): laços com mitra; a face lógica é apagada e as regiões refeitas com `rebuild_face` (anel externo, miolo com furos, anéis dos furos); furo aberto continua aberto. Distância pelo cursor (distância ao contorno, + dentro). Sem eliminação de sobreposições em formas côncavas (P1); Cmd não faz nada ainda.
- **Siga-me** (`core/geom_extrude.follow_me`): varredura com mitra (projeção do anel no plano bissetor); caminho aberto mantém o perfil como tampa inicial e cria a final; caminho fechado remove o perfil. Faces "extras" que os laços novos fecham (ex.: tampa interna da moldura) são removidas. Falta: AC-SIG-2 na GUI; caminho pelo perímetro com Cmd+clique (o pairar sobre uma face já usa o perímetro).
- GUI `scn_e`: partes `retangulo`, `casa` (ROTEIRO Parte 1 passos 1, 2, 6–9 + Cmd+Z ×6 / Cmd+Shift+Z ×6), `encaixe` (AC-EMP-3, cilindro AC-CIR-1/2). Prints em `doc/sketchup_mode/screens/e_*.png`.
