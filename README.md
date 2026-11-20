# Barra de Skills para Bloodstone

Coloca as skills do Bloodstone numa barra horizontal embaixo da tela, para acompanhar os
cooldowns sem olhar para a lateral. Os buffs ativos (Ira, Vampirismo etc.) aparecem logo
acima da skill que os gera.

- **Só lê a imagem da tela.** Não mexe na memória do jogo e não envia cliques nem teclas.
- O cooldown e o nível aparecem igual ao jogo, porque a barra é uma cópia da imagem.
- Windows apenas. O jogo precisa estar **em janela** ou **janela sem borda**.

> Programas que leem a tela costumam ser tranquilos, mas confira as regras do jogo antes de usar.

## Instalação

**Requisitos:** Windows 10 (versão 2004 ou mais nova) ou Windows 11, e Python 3.10 ou mais novo.

1. **Instale o Python** em <https://www.python.org/downloads/>.
   Na primeira tela do instalador, marque **"Add python.exe to PATH"**.
2. **Baixe o programa.** Escolha uma das opções:
   - **ZIP (mais simples):** no topo desta página, clique em **Code > Download ZIP** e
     extraia em uma pasta, por exemplo `C:\BarraDeSkills`.
   - **Git:** `git clone https://github.com/famartins/BarraDeSkills.git`
3. **Instale as dependências.** Abra um terminal dentro da pasta (botão direito num
   espaço vazio > **Abrir no Terminal**) e rode:

   ```
   pip install -r requirements.txt
   ```

Para atualizar depois: baixe o ZIP de novo e substitua os arquivos (sua configuração
fica salva no `skillbar_config.json`, que não vem no ZIP), ou rode `git pull`.

## Primeiro uso

1. **Abra o jogo** em janela e dê dois cliques em `iniciar.bat`.
2. **Calibre as skills.** A tela congela com instruções no topo:
   - Na 1ª skill, **arraste um retângulo** sobre o ícone.
   - Nas demais, **clique no centro** do ícone, na ordem em que quer ver na barra.
   - **Enter** conclui. Botão direito ou Backspace desfaz. **Esc** cancela.
3. **Posicione a barra** arrastando com o botão esquerdo. A posição fica salva.
4. **(Recomendado) Defina a janela do jogo**, para a barra sumir quando você trocar de
   programa: botão direito na barra > **Definir janela do jogo** > clique no jogo em até 3 s.

### Buffs

Faça uma vez para cada buff:

1. Use a skill para o buff ficar **ativo** e aperte **Ctrl+Alt+F12**.
2. Na primeira vez, marque a **área dos buffs**: um retângulo cobrindo a **linha inteira**
   onde eles aparecem (ao lado do nível do personagem), não só um ícone.
3. Arraste um retângulo **justo** sobre o ícone do buff.
4. Informe o **nome**, a **duração em segundos** e **clique na skill** acima da qual ele deve
   aparecer. Salve.

Para ver o tempo restante, passe o mouse sobre o buff. Para trocar a duração ou a skill,
use botão direito na barra > **Buffs...** > **Editar...**.

**Limitação:** o tempo é uma contagem do próprio programa, a partir da duração informada,
porque o tooltip do jogo não pode ser copiado. Se você reusar a skill com o buff ainda
ativo, a contagem não reinicia.

## Atalhos

| Ação | Como |
|---|---|
| Mover a barra | Arrastar com o botão esquerdo |
| Zoom da barra | Roda do mouse sobre a barra |
| Configurações (zoom, espaço, FPS, buffs, recalibrar, sair) | Botão direito na barra ou **Ctrl+Alt+F11** |
| Click-through (cliques atravessam a barra) | **Ctrl+Alt+F10** |
| Cadastrar buff | **Ctrl+Alt+F12** |

## Problemas comuns

| Sintoma | Solução |
|---|---|
| Ícones errados depois de mover ou redimensionar o jogo | Configurações > **Recalibrar** |
| A barra não aparece por cima do jogo | Use modo janela ou janela sem borda, não tela cheia exclusiva |
| O jogo está no 2º monitor | `python skillbar.py --monitor 2 --calibrar` |
| A barra some mesmo com o jogo aberto | O jogo precisa estar em primeiro plano. Ou use **Mostrar sempre** nas configurações |
| O buff não aparece | Redefina a área dos buffs cobrindo a linha toda (Buffs... > **Redefinir área**) |
| Quero começar do zero | Apague o `skillbar_config.json` e a pasta `buffs` |

Achou um bug? Abra uma [issue](https://github.com/famartins/BarraDeSkills/issues) com um
print da tela e o que aparece na janela preta do terminal.

---

## Detalhes técnicos

### Como funciona

- **Captura:** a cada quadro (padrão 30 FPS, ajustável), o programa captura com
  [`mss`](https://github.com/BoboTiG/python-mss) o retângulo que engloba as skills
  calibradas. Depois recorta cada ícone e monta uma faixa horizontal com Pillow. Com
  zoom, a ampliação usa *nearest neighbor* para manter o pixel art nítido.
- **Janela sobreposta:** é uma janela Tkinter sem borda, `topmost`, com os estilos Win32
  `WS_EX_NOACTIVATE` (não rouba o foco do jogo), `WS_EX_TOOLWINDOW` (não aparece na
  barra de tarefas) e `WS_EX_LAYERED`. O click-through liga o `WS_EX_TRANSPARENT`.
- **Sem eco na captura:** `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` impede que
  a própria barra apareça nas capturas, mesmo sobreposta às skills originais.
- **Visibilidade:** a cada 150 ms o programa compara o executável da janela em primeiro
  plano (`GetForegroundWindow` + `QueryFullProcessImageNameW`) com o configurado.
- **Reconhecimento de buffs** (`buffcore.py`, numpy): 10× por segundo, captura a área
  dos buffs e procura cada ícone cadastrado em duas etapas. A busca grossa compara 1 a
  cada 3 pixels em todas as posições, com `sliding_window_view`. A confirmação compara o
  ícone inteiro nos 12 melhores candidatos. O buff é aceito se o erro absoluto médio por
  canal for ≤ `buff_threshold` (padrão 14, numa escala de 0 a 255). Se a área marcada for
  pequena demais, a busca é ampliada para os lados automaticamente.
- **Cronômetro** (`BuffTracker`): o buff começa a contar quando aparece. Ele continua
  "ativo" por 1 s depois de sumir, para não piscar se algo cobrir o ícone. Se o jogo sai
  de foco, a contagem é congelada e retomada quando o jogo volta.
- **Buffs acima das skills:** é uma segunda janela sobreposta, alinhada à barra. O fundo
  usa uma *color key* (`LWA_COLORKEY`, cor `#ff00fe`), então só os ícones são visíveis e
  os cliques atravessam o resto.

### Arquivos

| Arquivo | Conteúdo |
|---|---|
| `skillbar.py` | Programa principal: calibração, barra, janela de buffs, configurações, atalhos |
| `buffcore.py` | Lógica de buffs sem dependência de Windows: busca de ícone, cronômetro, textos |
| `iniciar.bat` | Atalho para `python skillbar.py` |
| `requirements.txt` | `mss`, `Pillow`, `numpy` |
| `skillbar_config.json` | Criado no 1º uso. Configuração local, ignorada pelo git |
| `buffs/` | Criada ao cadastrar buffs. Ícones `.png` de referência, ignorada pelo git |

### Linha de comando

```
python skillbar.py                 inicia (calibra na primeira vez)
python skillbar.py --calibrar      refaz a calibração
python skillbar.py --monitor 2     usa o monitor 2 na calibração
python skillbar.py --janelas       lista as janelas abertas (executável e título)
python skillbar.py --jogo X.exe    só mostra a barra com X.exe em primeiro plano ("" desativa)
```

### Configuração (`skillbar_config.json`)

| Chave | Padrão | Descrição |
|---|---|---|
| `regions` | `[]` | `[x, y, largura, altura]` de cada skill, em pixels da tela |
| `zoom` / `gap` / `fps` | `1.0` / `4` / `30` | Ampliação, espaço entre ícones e atualizações por segundo |
| `pos` | automático | Posição `[x, y]` da barra |
| `click_through` | `false` | Cliques atravessam a barra |
| `exclude_from_capture` | `true` | A barra não aparece em capturas de tela |
| `game_process` / `game_title` | `""` | Executável ou trecho do título da janela do jogo |
| `buffs` | `[]` | `{name, duration, desc, file, skill}`. `skill` é o índice na barra (0 = 1ª) ou `null` |
| `buff_area` | `null` | `[x, y, largura, altura]` da linha de buffs no jogo |
| `buff_zoom` | `1.5` | Ampliação extra dos ícones de buff |
| `buff_threshold` | `14` | Tolerância do reconhecimento (menor = mais exato) |

O programa ativa *DPI awareness* por monitor, então as coordenadas são pixels reais
mesmo com escala do Windows acima de 100%.
