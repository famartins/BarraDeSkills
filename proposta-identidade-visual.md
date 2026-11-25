# Proposta de identidade visual – Barra de Skills

Nov 25, 2026

## Resumo executivo

Esta proposta define uma nova identidade visual para a Barra de Skills, baseada em uma paleta de carvão quente com acento em ouro e tons de pergaminho. O objetivo é deixar a interface mais atual e coerente com a estética sombria do jogo, com hierarquia visual clara, sem alterar o funcionamento da barra sobre o jogo.

As mudanças atingem a camada de configuração e de seleção de magias. A sobreposição in-game mantém o mesmo comportamento, com ajustes apenas de cor e contraste.

## Paleta proposta

Oito cores, cada uma com um papel definido na interface:

| Papel | Hex | Uso na interface |
|---|---|---|
| Fundo base | #15120F | Janela e área de conteúdo mais profunda |
| Superfície | #1F1A16 | Cards, painéis e campos de busca |
| Borda | #3A3129 | Divisores e contornos |
| Texto principal | #EDE3D0 | Títulos e textos (tom pergaminho) |
| Texto secundário | #A89A84 | Legendas e descrições |
| Acento | #D4A03C | Botões principais, aba ativa e toggles ligados |
| Barra 1 | #C8452F | Vermelho ferrugem, mantendo a identificação atual |
| Barra 2 | #3A7BD5 | Azul, mantendo a identificação atual |

Contraste estimado pela fórmula WCAG:

- Texto principal sobre o fundo base: acima de 14:1.
- Texto secundário sobre a superfície: em torno de 6:1.
- Texto escuro (#15120F) sobre o acento dourado: em torno de 8:1. Por isso botões de acento devem usar texto escuro, e não branco.
- Branco sobre #C8452F: em torno de 5:1.
- Texto sobre #3A7BD5 fica próximo de 4,4:1 com branco e de 4,2:1 com escuro. É o ponto mais fraco da paleta: validar no protótipo, usando texto em negrito ou um tom de azul um pouco mais claro para textos pequenos.

## Direção visual

- Tema escuro com profundidade em três níveis (fundo, superfície e card), em vez de cinza uniforme.
- O carvão quente, em vez de preto puro ou cinza frio, combina com o clima do jogo e com as ilustrações em sépia.
- O ouro é o acento de interação (botões, seleção, toggles). Ele aparece com moderação, para não competir com os ícones de magia.
- Vermelho e azul continuam como identificação das Barras 1 e 2, então quem já usa o app não precisa reaprender a leitura.
- Cantos arredondados médios (12 a 16 px), sombras suaves e um leve brilho dourado no hover.
- As ilustrações das vocações (sépia) combinam com a paleta. Opção: manter a arte com um leve escurecimento na base, para o nome ficar legível sobre ela.

## Tipografia e componentes

Fonte: uma família sans-serif moderna com boa legibilidade em tamanhos pequenos (Inter, Manrope ou Plus Jakarta Sans, a validar). Escala sugerida: título 24 px, subtítulo 14 px, corpo 13 px e legenda 11 px, com peso 600 para títulos e 400 para textos.

Componentes:

- Abas: estilo segmentado, com indicador inferior dourado na aba ativa.
- Cards de vocação: moldura sutil, nome e contagem de magias alinhados, hover com leve elevação e brilho dourado.
- Grade de magias: largura fixa por card, para o texto não quebrar em alturas diferentes. Badge de ordem (1-2, 2-1) em pílula, na cor da barra correspondente.
- Filtros (Todas, Ataque, Cura, Suporte): chips, com estado ativo em ouro.
- Sliders e toggles: valor numérico à direita, preenchimento dourado, rótulo e descrição alinhados.
- Busca por nome de magia no topo da grade.
- Tooltip com nível, recarga e tipo ao passar o mouse sobre uma magia.

## Implementação

Stack: recomendamos pywebview (interface em HTML, CSS e JS, com Python como backend) ou PySide6 com QSS, se a equipe preferir ficar só em Python. A escolha depende da familiaridade com web e de quão distante do visual atual se quer ir.

Escopo técnico: alterar somente a camada de interface de configuração e seleção. Captura de tela, detecção de cliques, click-through, transparência e a lógica de recarga da sobreposição permanecem como estão.

Etapas:

1. Criar o sistema de tokens (cores, tipografia, espaçamento e raios) em um único arquivo de tema.
2. Fazer o protótipo da tela de magias com a nova paleta e validar com o time, incluindo o contraste sobre o azul da Barra 2.
3. Aplicar o tema nas abas, controles e tela de personagem.
4. Trocar a seleção de vocação e tratar as ilustrações.
5. Testar contraste, escala de DPI alta (150% e 200%) e a sobreposição sobre o jogo.
6. Se houver testes de regressão visual (ex.: Playwright com Argos), atualizar as capturas de referência.

## Próximos passos e decisões pendentes

Decisões necessárias para aprovação:

1. Stack: pywebview ou PySide6?
2. Tom do azul da Barra 2: manter #3A7BD5 ou usar um azul mais claro para melhorar o contraste do texto?
3. Ilustrações das vocações: manter a arte sépia com escurecimento na base, ou aplicar um filtro mais forte?
4. Escopo: só a janela de configuração, ou também as cores da sobreposição in-game?

Entregável seguinte: protótipo HTML da tela de magias com esta paleta, para aprovação visual antes da implementação.
