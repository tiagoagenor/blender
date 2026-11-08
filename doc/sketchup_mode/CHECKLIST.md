# Checklist — Modo SketchUp no Blender

Branch: `sketchup-mode` · Blender de teste: 5.2.2 (/Applications/Blender.app)
Legenda: [x] feito · [~] em andamento · [ ] pendente
Sub-checklists de cada agente: `checklists/WS_A.md` … `WS_G.md`

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
- [x] Plano v2 → `PLANO.md` (performance adiada por decisão do usuário)
- [x] Crítica rodada 2 → `CRITICA_R2_*.md`
- [x] Plano v3 → `PLANO.md`
- [x] Crítica rodada 3 → `CRITICA_R3_*.md` (GO dos dois críticos)
- [x] Plano final → `PLANO.md` (teste final de aceite na §12)

## 3. Desenvolvimento
### 3.1 Base do template
- [x] Estrutura do App Template + ambiente de teste isolado (A0)
- [x] Layout: barra "Primeiros passos" no topo, Conjunto extenso à esquerda (2 colunas), Bandeja padrão à direita, barra de status com Medidas
- [x] Esconder o que não é do SketchUp — sem Etiquetas/Tags em lugar nenhum
- [x] Tema claro do SketchUp + céu azul no horizonte + chão cinza
- [x] Faces brancas / verso azul-acinzentado / arestas pretas / contorno de superfícies suaves
- [x] Eixos vermelho/verde/azul (negativos pontilhados)
- [x] Ícones próprios (41) no estilo SketchUp

### 3.2 Mouse e navegação
- [x] Botão do meio = órbita (eixo azul sempre em pé)
- [x] Shift + meio = panorâmica
- [x] Roda = zoom no cursor; duplo clique do meio = recentralizar
- [x] Trackpad (Ctrl+Cmd arrastar, pinça/2 dedos)
- [x] Órbita (O), Panorâmica (H), Zoom (Z), Extensões de zoom (Shift+Z), Janela de zoom, Anterior/Próxima

### 3.3 Motor de inferência e Medidas
- [x] Snap extremidade / ponto central / na aresta / na face / interseção / centro / do ponto
- [x] Travas de eixo (setas, inclusive antes do 1º clique) e cores
- [x] Dicas de texto em pt-BR
- [x] Caixa Medidas (digitação + Enter, funciona com o mouse em qualquer lugar, redigitar ajusta)

### 3.4 Ferramentas de desenho
- [x] Linha (L)
- [x] Retângulo (R) + Retângulo girado
- [x] Círculo (C), Polígono
- [x] Arco (A), Arco (centro), Arco de 3 pontos, Pizza
- [x] Desenho à mão livre
- [x] Criação automática de faces, furos, cura

### 3.5 Ferramentas de edição
- [x] Empurrar/Puxar (P) — encaixe, furo passante, duplo clique, Option
- [x] Equidistância (F)
- [x] Siga-me

### 3.6 Ferramentas de seleção e transformação
- [x] Selecionar (Espaço) — clique, duplo, triplo, janela/cruzamento, Shift/Option
- [x] Mover (M) + Option copiar + arrays (5x, /5) + dobra automática
- [x] Girar (Q) com transferidor
- [x] Escala (S) com alças
- [x] Apagar/Borracha (E), Excluir (Delete)
- [x] Pintura (B) + Materiais
- [x] Virar, Grupos, Componentes, Explodir, Ocultar/Reexibir, Interseccionar, menu do botão direito, Cmd+C/X/V

### 3.7 Precisão e câmera
- [x] Fita métrica (T) + guias
- [x] Transferidor + guias angulares
- [x] Dimensões (cotas)
- [x] Texto, Texto em 3D
- [x] Posição da câmera, Olhar ao redor, Cenas com abas, Estilos (Editar, arestas traseiras, Raio X)

### 3.8 Performance — ADIADO (decisão do usuário: primeiro funcionar, performance depois)
- [ ] Cache de geometria para snap
- [ ] Desenho GPU em lote (batches)
- [ ] Teste com modelo grande

### 3.9 Pedidos extras do usuário
- [x] Apagar só uma face (retângulo e caixa): face some, arestas ficam
- [x] Roteiro "casa simples" → `ROTEIRO_CASA.md`
- [x] Casa simples rodada no nosso Blender com prints de cada etapa (19/19)

## 4. Testes e comparação
- [x] Prints do nosso modo × SketchUp enviados ao usuário
- [x] Rodadas de ajustes com prints
- [x] Teste final "primeiro dia" (PLANO §12) 15/15 + trackpad
- [x] Revisão final do especialista SketchUp → `REVISAO_FINAL_SKETCHUP.md` (ajustes aplicados)
- [x] Rodada final: 425 testes + 14 cenários de tela, todos passando

## 5. Entrega
- [x] Commit na branch
- [x] Instruções de como abrir/testar → `COMO_USAR.md`
- [x] Avisar o usuário que está 100%
