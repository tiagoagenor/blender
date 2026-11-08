# Checklist — Modo SketchUp no Blender

Branch: `sketchup-mode` · Blender de teste: 5.2.2 (/Applications/Blender.app)
Legenda: [x] feito · [~] em andamento · [ ] pendente

## 0. Preparação
- [x] Verificar repo e Blender instalado
- [x] Criar branch `sketchup-mode`
- [x] Testar print automático do Blender
- [x] Criar este checklist

## 1. Pesquisa (especialistas)
- [x] Especialista SketchUp: interface, atalhos, mouse, cores, inferência, ferramentas → `RESEARCH_SKETCHUP.md`
- [x] Baixar prints de referência do SketchUp → `ref_images/`
- [x] Especialista Blender API: viabilidade e arquitetura → `RESEARCH_BLENDER_API.md`

## 2. Planejamento (3 rodadas)
- [x] Plano v1 → `PLANO.md`
- [x] Crítica rodada 1 (especialista SketchUp + especialista Blender) → `CRITICA_R1_*.md`
- [x] Plano v2 → `PLANO.md` (performance adiada por decisão do usuário; sub-checklists por agente em `checklists/WS_<X>.md`)
- [x] Crítica rodada 2 → `CRITICA_R2_*.md`
- [x] Plano v3 → `PLANO.md` (briefs por agente na §9; agentes partem do código do spike visual)
- [x] Crítica rodada 3 → `CRITICA_R3_*.md` (GO dos dois críticos)
- [x] Plano final → `PLANO.md` (teste final de aceite na §12; sequência de lançamento na §9.6)

## 3. Desenvolvimento
### 3.1 Base do template
- [ ] Estrutura do App Template + instalação para teste
- [ ] Layout: barra de ferramentas no topo, Large Tool Set à esquerda, bandeja (tray) à direita, barra de status embaixo
- [ ] Esconder o que não é do SketchUp (sem painel Etiquetas/Tags)
- [ ] Tema/cores do SketchUp + céu azul no horizonte + chão
- [ ] Faces brancas / verso azul-acinzentado / arestas pretas
- [ ] Eixos vermelho/verde/azul

### 3.2 Mouse e navegação
- [ ] Botão do meio = órbita
- [ ] Shift + meio = panorâmica
- [ ] Roda = zoom no cursor
- [ ] Órbita (O), Pan (H), Zoom (Z), Zoom Extensão (Shift+Z)

### 3.3 Motor de inferência e VCB
- [ ] Snap ponto final / ponto médio / na aresta / na face
- [ ] Travas de eixo (setas) e cores
- [ ] Dicas de texto (tooltips)
- [ ] Caixa de medidas (VCB) com digitação + Enter

### 3.4 Ferramentas de desenho
- [ ] Linha (L)
- [ ] Retângulo (R)
- [ ] Círculo (C)
- [ ] Polígono
- [ ] Arco (A)
- [ ] Criação automática de faces

### 3.5 Ferramentas de edição
- [ ] Empurrar/Puxar (P)
- [ ] Deslocamento/Offset (F)
- [ ] Siga-me (Follow Me)

### 3.6 Ferramentas de transformação
- [ ] Selecionar (Espaço) — clique, duplo, triplo, janela/cruzamento
- [ ] Mover (M) + Ctrl copiar + arrays
- [ ] Rotacionar (Q)
- [ ] Escala (S)
- [ ] Borracha (E)
- [ ] Pintura (B)

### 3.7 Precisão
- [ ] Fita Métrica (T) + guias
- [ ] Transferidor + guias angulares
- [ ] Dimensão (cotas)

### 3.8 Performance — ADIADO (decisão do usuário: primeiro funcionar, performance depois)
- [ ] Cache de geometria para snap
- [ ] Desenho GPU em lote (batches)
- [ ] Teste com modelo grande

## 4. Testes e comparação
- [ ] Print do nosso modo × print do SketchUp (enviar ao usuário)
- [ ] Rodada de ajustes 1 (enviar print)
- [ ] Rodada de ajustes 2 (enviar print)
- [ ] Rodada de ajustes 3 (enviar print)
- [ ] Testar cada ferramenta

## 5. Entrega
- [ ] Commit na branch
- [ ] Instruções de como abrir/testar
- [ ] Avisar o usuário que está 100%
