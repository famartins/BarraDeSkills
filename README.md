# Barra de Skills para Bloodstone

Coloca as skills do Bloodstone numa barra **horizontal ou vertical** onde você quiser na
tela, para acompanhar as recargas sem olhar para a lateral. Os buffs ativos (Ira,
Vampirismo etc.) aparecem junto da skill que os gera.

- **Só lê a imagem da tela.** Não mexe na memória do jogo e não envia cliques nem teclas.
- A recarga e o nível aparecem igual ao jogo, porque a barra é uma cópia da imagem.
- Você escolhe a vocação e as magias, e o programa **acha sozinho** onde elas estão.
- Windows apenas. O jogo precisa estar **em janela** ou **janela sem borda**.

> Programas que leem a tela costumam ser tranquilos, mas confira as regras do jogo antes de usar.

## Instalação

**Requisitos:** Windows 10 (versão 2004 ou mais nova) ou Windows 11, e Python 3.10 ou mais novo.

1. **Instale o Python** em <https://www.python.org/downloads/>.
   Na primeira tela do instalador, marque **"Add python.exe to PATH"**.
2. **Baixe o programa.** Escolha uma das opções:
   - **ZIP (mais simples):** no topo desta página, clique em **Code > Download ZIP**.
     Depois, botão direito no ZIP > **Extrair tudo...**, para uma pasta como
     `C:\BarraDeSkills`. Não rode o programa de dentro do ZIP.
   - **Git:** `git clone https://github.com/famartins/BarraDeSkills.git`
3. **Dê dois cliques em `iniciar.bat`.** Na primeira vez, ele instala as dependências
   sozinho. Se faltar algo, a janela preta diz o que é e como resolver.

   Para instalar manualmente: `pip install -r requirements.txt`

Para atualizar depois: baixe o ZIP de novo e substitua os arquivos (sua configuração
fica salva no `skillbar_config.json`, que não vem no ZIP), ou rode `git pull`.

## Primeiro uso

Abra o jogo em janela e dê dois cliques em `iniciar.bat`. Abre um assistente:

1. **Vocação:** escolha entre Cavaleiro, Bárbaro, Arqueiro, Xamã e Mago.
2. **Magias:** clique nas magias que quer na barra. A ordem dos cliques é a ordem na
   barra. Embaixo, escolha **Horizontal** ou **Vertical**.
3. **Achar na tela:** na primeira vez, a tela congela e você arrasta um retângulo sobre a
   **coluna inteira de skills** do jogo. O programa procura cada magia ali.
4. **Confirmar:** confira se o ícone da wiki bate com o da tela.
   - ✓ verde: encontrada.
   - ⚠ amarelo: confira e clique em **É a mesma**.
   - ✗ vermelho: use **Marcar** e clique no ícone, ou **Tirar da barra**.
5. **Pronto.** Arraste a barra para onde quiser. A posição fica salva.

Recomendado: botão direito na barra > aba **Jogo** > **Definir janela do jogo**, para a
barra sumir quando você trocar de programa.

Para mudar depois: botão direito na barra > **Trocar vocação/magias**.

### Buffs

Faça uma vez para cada buff:

1. Use a skill para o buff ficar **ativo** e aperte **Ctrl+Alt+F12**.
2. Na primeira vez, marque a **área dos buffs**: um retângulo cobrindo **todas as linhas**
   onde eles podem aparecer (ao lado do nível do personagem). Com muitos buffs, a fila
   quebra para a 2ª linha.
3. Arraste um retângulo **justo** sobre o ícone do buff.
4. **Clique na skill** que dá esse buff e informe a **duração real** do buff, em segundos
   (a wiki mostra o tempo de recarga da skill, não a duração do buff). O nome vem sugerido;
   ajuste se precisar. Salve.

O buff aparece junto da skill enquanto estiver ativo. Passe o mouse para ver o tempo
restante.

**Usou a skill de novo antes do buff acabar?** O programa percebe que o ícone da skill
escureceu (entrou em recarga) e **reinicia o tempo** do buff. Dá para desligar isso por
buff em **Editar**.

**Limitação:** o tempo é uma contagem do próprio programa, a partir da duração
informada, porque o tooltip do jogo não pode ser copiado.

## Atalhos

| Ação | Como |
|---|---|
| Mover a barra | Arrastar com o botão esquerdo |
| Zoom da barra | Roda do mouse sobre a barra |
| Configurações | Botão direito na barra ou **Ctrl+Alt+F11** |
| Click-through (cliques atravessam a barra) | **Ctrl+Alt+F10** |
| Cadastrar buff | **Ctrl+Alt+F12** |

## Problemas comuns

| Sintoma | Solução |
|---|---|
| Nada acontece ao abrir o `iniciar.bat` | Leia a janela preta: ela diz o que falta (Python, extrair o ZIP, dependências). Tudo fica registrado em **`diagnostico.txt`**, na pasta do programa: mande esse arquivo numa issue. Se o `diagnostico.txt` nem for criado, o Windows ou o antivírus bloqueou o arquivo: botão direito no ZIP > **Propriedades** > marque **Desbloquear**, extraia de novo e libere a pasta no antivírus |
| Aviso "O Windows protegeu o computador" | **Mais informações** > **Executar assim mesmo** (o programa não é assinado digitalmente) |
| Ícones errados depois de mover ou redimensionar o jogo | Configurações > **Trocar vocação/magias** > **Procurar de novo** |
| O assistente não acha uma magia | Use **Marcar**. Se a magia ainda não foi aprendida ou está bloqueada, o ícone fica diferente |
| Os ícones da wiki não aparecem | Eles são baixados na primeira vez. Confira a internet. Dá para continuar sem eles |
| A barra não aparece por cima do jogo | Use modo janela ou janela sem borda, não tela cheia exclusiva |
| O jogo está no 2º monitor | `python skillbar.py --monitor 2` |
| A barra some mesmo com o jogo aberto | O jogo precisa estar em primeiro plano. Ou use **Mostrar sempre** na aba Jogo |
| O buff não aparece | Redefina a área dos buffs cobrindo todas as linhas (aba Buffs > **Redefinir área**) |
| Quero começar do zero | Apague o `skillbar_config.json` e a pasta `buffs` |

Achou um bug? Abra uma [issue](https://github.com/famartins/BarraDeSkills/issues) com um
print da tela e o que aparece na janela preta do terminal.

---

## Detalhes técnicos

### Como funciona

- **Captura:** a cada quadro (padrão 30 FPS, ajustável), o programa captura com
  [`mss`](https://github.com/BoboTiG/python-mss) o retângulo que engloba as skills. Depois
  recorta cada ícone e monta a faixa (horizontal ou vertical) com Pillow. Com zoom, a
  ampliação usa *nearest neighbor* para manter o pixel art nítido.
- **Janela sobreposta:** é uma janela Tkinter sem borda, `topmost`, com os estilos Win32
  `WS_EX_NOACTIVATE` (não rouba o foco do jogo), `WS_EX_TOOLWINDOW` (não aparece na
  barra de tarefas) e `WS_EX_LAYERED`. O click-through liga o `WS_EX_TRANSPARENT`.
- **Sem eco na captura:** `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` impede que
  a própria barra apareça nas capturas, mesmo sobreposta às skills originais.
- **Telas:** [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), tema escuro
  (`telas.py`). As janelas sobrepostas continuam em Tk puro por causa dos estilos Win32.
- **Dados das vocações:** `ferramentas/atualizar_wiki.py` lê a tabela "Magias" das
  páginas da [Bloodpedia](https://bloodpedia.vercel.app/) e gera `dados/vocacoes.json`
  (nome, tipo, nível e link do ícone de cada magia, e a arte de cada vocação). As imagens pertencem aos criadores
  do jogo e **não vão no repositório**: `wiki.py` baixa cada um na primeira vez para
  `cache/icones/`.
- **Localização automática** (`localizar.py`, numpy):
  - Compara só o **miolo** de cada ícone da wiki (sem os cantos onde o jogo desenha a
    tecla de atalho e o "Lv").
  - A escala tela/wiki é estimada uma vez, testando de 0,5× a 2,5×. Atalho: 1,0×, o
    caso comum, porque os ícones da wiki têm 44 px, como no jogo em 1440p.
  - A busca grossa amostra pixels e posições com `sliding_window_view` e refina em volta
    dos melhores candidatos.
  - Classificação pelo erro absoluto médio: até 12 = encontrada, até 30 = dúvida (o ícone
    pode estar sem cor, por exemplo bloqueado), acima disso = não encontrada.
- **Reconhecimento de buffs** (`buffcore.py`): 10× por segundo, captura a área dos buffs
  e procura cada ícone cadastrado, numa busca grossa seguida de confirmação. O buff é
  aceito se o erro médio for ≤ `buff_threshold` (padrão 14, numa escala de 0 a 255). Se a
  área marcada for pequena, a busca cresce para os lados e para baixo (3 linhas).
- **Cronômetro** (`BuffTracker`): o buff começa a contar quando aparece. Ele continua
  "ativo" por 1 s depois de sumir, para não piscar se algo cobrir o ícone. Se o jogo sai
  de foco, a contagem é congelada e retomada quando o jogo volta.
- **Reinício ao reusar** (`CastDetector`): acompanha o brilho médio de cada skill. Uma
  queda brusca (abaixo de 75% do normal, em até 3 quadros) indica que a skill entrou em
  recarga. Depois disso, não dispara de novo até o brilho voltar a 90%. Escurecimentos
  lentos (por exemplo, a noite no jogo) não contam.
- **Buffs junto das skills:** é uma segunda janela sobreposta, alinhada à barra (acima na
  horizontal, ao lado na vertical). O fundo usa uma *color key* (`LWA_COLORKEY`, cor
  `#ff00fe`), então só os ícones são visíveis e os cliques atravessam o resto.

### Arquivos

| Arquivo | Conteúdo |
|---|---|
| `skillbar.py` | Programa principal: barra, janela de buffs, calibração, atalhos |
| `telas.py` | Assistente, configurações e editor de buff (CustomTkinter) |
| `wiki.py` | Carrega `dados/vocacoes.json` e mantém o cache de ícones |
| `localizar.py` | Acha as magias na barra lateral do jogo |
| `buffcore.py` | Busca de ícone, cronômetro, detecção de uso da skill e área de busca |
| `dados/vocacoes.json` | Magias de cada vocação, gerado da Bloodpedia |
| `ferramentas/atualizar_wiki.py` | Regera o JSON quando a wiki mudar |
| `tests/` | Testes: `python -m unittest discover -s tests` |
| `iniciar.bat` | Inicia o programa: confere o Python, instala as dependências e mostra erros em português |
| `requirements.txt` | `mss`, `Pillow`, `numpy`, `customtkinter` |
| `skillbar_config.json`, `buffs/`, `cache/` | Criados no uso. Locais, ignorados pelo git |

### Linha de comando

```
python skillbar.py                 inicia (assistente no primeiro uso)
python skillbar.py --calibrar      marca os ícones manualmente, sem o assistente
python skillbar.py --monitor 2     usa o monitor 2 nas telas de marcação
python skillbar.py --janelas       lista as janelas abertas (executável e título)
python skillbar.py --jogo X.exe    só mostra a barra com X.exe em primeiro plano ("" desativa)
```

### Configuração (`skillbar_config.json`)

| Chave | Padrão | Descrição |
|---|---|---|
| `vocacao` / `magias` | `""` / `[]` | Vocação e magias (slugs da wiki, na ordem da barra) |
| `regions` | `[]` | `[x, y, largura, altura]` de cada skill, em pixels da tela |
| `sidebar_area` | `null` | `[x, y, largura, altura]` da barra lateral de skills do jogo |
| `orientation` | `"horizontal"` | `"horizontal"` ou `"vertical"` |
| `zoom` / `gap` / `fps` | `1.0` / `4` / `30` | Ampliação, espaço entre ícones e atualizações por segundo |
| `pos` | automático | Posição `[x, y]` da barra |
| `click_through` | `false` | Cliques atravessam a barra |
| `exclude_from_capture` | `true` | A barra não aparece em capturas de tela |
| `game_process` / `game_title` | `""` | Executável ou trecho do título da janela do jogo |
| `buffs` | `[]` | `{name, duration, desc, file, skill, skill_slug, restart_on_cast}`. `skill` é o índice na barra (0 = 1ª) ou `null`. `skill_slug` mantém o vínculo se a ordem mudar |
| `buff_area` | `null` | `[x, y, largura, altura]` da área de buffs no jogo |
| `buff_zoom` | `1.5` | Ampliação extra dos ícones de buff |
| `buff_threshold` | `14` | Tolerância do reconhecimento (menor = mais exato) |

O programa ativa *DPI awareness* por monitor, então as coordenadas são pixels reais
mesmo com escala do Windows acima de 100%.
