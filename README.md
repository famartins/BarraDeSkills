# Barra de Skills para Bloodstone

Coloca as skills do Bloodstone em **uma ou duas barras** (horizontais ou verticais) onde
você quiser na tela, para acompanhar as recargas sem olhar para a lateral. Os buffs
ativos (Ira, Vampirismo etc.) aparecem junto da skill que os gera e **piscam quando
estão acabando**.

- **Só lê a imagem da tela.** Não mexe na memória do jogo e não envia cliques nem teclas.
- A recarga e o nível aparecem igual ao jogo, porque a barra é uma cópia da imagem.
- Você escolhe a vocação e as magias, e o programa **acha sozinho** onde elas estão.
- Um **perfil por personagem**: cada um guarda a sua vocação, barras e buffs.
- Windows apenas. O jogo precisa estar **em janela** ou **janela sem borda**.

> Programas que leem a tela costumam ser tranquilos, mas confira as regras do jogo antes de usar.

## Instalação

**Requisitos:** Windows 10 (versão 2004 ou mais nova) ou Windows 11. Não precisa instalar
Python.

1. Na página de **[Releases](https://github.com/famartins/BarraDeSkills/releases/latest)**,
   baixe o arquivo **`BarraDeSkills-vX.Y-windows.zip`**.
2. Botão direito no ZIP > **Extrair tudo...**, para uma pasta como `C:\BarraDeSkills`.
   Não rode o programa de dentro do ZIP.
3. Dê dois cliques em **`BarraDeSkills.exe`**.

Na primeira vez, o Windows pode mostrar **"O Windows protegeu o computador"**. Clique em
**Mais informações** > **Executar assim mesmo**. O aviso aparece porque o programa não é
assinado digitalmente.

**Para atualizar:** a partir da 0.9, o programa avisa ao abrir quando sai uma versão
nova. Clique em **Atualizar agora**: ele baixa, fecha, troca os arquivos e abre de novo.
Para procurar na hora: **Configurações** > **Sobre** > **Procurar atualização**. Sua
configuração, personagens e buffs são mantidos.

Quem está na 0.8.4 ou antes precisa atualizar à mão uma última vez: baixe o ZIP novo e
extraia **por cima** da pasta antiga.

<details>
<summary>Rodar pelo código-fonte (com Python)</summary>

1. Instale o Python 3.10 ou mais novo em <https://www.python.org/downloads/>, marcando
   **"Add python.exe to PATH"**.
2. Baixe o código (**Code > Download ZIP**, ou `git clone`) e extraia.
3. Dê dois cliques em `iniciar.bat`. Ele instala as dependências sozinho na primeira vez.
   Para instalar manualmente: `pip install -r requirements.txt`.

</details>

## Primeiro uso

Abra o jogo em janela e abra o programa. Um assistente pede:

1. **Personagem:** digite o nome do personagem e clique em **Criar**. Toda vez que o
   programa abre, ele mostra os personagens salvos para você escolher com qual jogar
   (**Usar**).
2. **Vocação:** Cavaleiro, Bárbaro, Arqueiro, Xamã ou Mago.
3. **Magias:**
   - No alto, escolha **Barra 1** ou **Barra 2** e clique nas magias de cada uma. A ordem
     dos cliques é a ordem na barra. Cada barra tem a sua orientação (**Horizontal** ou
     **Vertical**).
   - O botão **Separar** põe as magias de Ataque na barra 1 e as demais na barra 2.
   - **Só buffs:** esconde as barras de skills e mostra só os buffs, numa caixa
     arrastável com o nome do personagem.
4. **Achar na tela:** na primeira vez, a tela congela e você arrasta um retângulo sobre a
   **coluna inteira de skills** do jogo. O programa procura cada magia ali.
5. **Confirmar:** confira se o ícone da wiki bate com o da tela.
   - ✓ verde: encontrada.
   - ⚠ amarelo: confira e clique em **É a mesma**.
   - ✗ vermelho: use **Marcar** e clique no ícone, ou **Tirar da barra**.
6. **Pronto.** Arraste cada barra para onde quiser. A posição fica salva.

Recomendado: botão direito na barra > aba **Jogo** > **Definir janela do jogo**, para as
barras sumirem quando você trocar de programa.

**Ícone perto do relógio:** o programa fica no ícone da bandeja do Windows, perto do
relógio. Fechar as janelas não o encerra. Clique com o botão direito no ícone para abrir
**Configurações**, **Trocar personagem** ou **Sair**. Se você abrir o programa de novo, ele
não abre uma segunda cópia: só traz para frente a que já está aberta.

**Abrir com o Windows:** na aba **Jogo** (ou no menu do ícone), ligue **Abrir com o
Windows**. O programa fica esperando no ícone e mostra a escolha de personagem quando o
jogo abre.

**Janela do jogo mudou de lugar?** O programa percebe e ajusta sozinho as posições das
skills e da área dos buffs. Dá para desligar isso na aba **Jogo**.

Para mudar depois: botão direito na barra > aba **Personagem**. Lá ficam **Trocar
personagem** (lista dos salvos), criar, renomear, apagar e **Trocar vocação/magias**.

### Buffs

Faça uma vez para cada buff:

1. Use a skill para o buff ficar **ativo** e aperte **Ctrl+Alt+F12**.
2. Na primeira vez, marque a **área dos buffs**: um retângulo cobrindo **todas as linhas**
   onde eles podem aparecer (ao lado do nível do personagem). Com muitos buffs, a fila
   quebra para a 2ª linha.
3. Arraste um retângulo **justo** sobre o ícone do buff.
4. **Clique na skill** que dá esse buff e informe a **duração real** do buff, em segundos.
   A wiki mostra o tempo de recarga da skill, não a duração do buff. O nome vem
   sugerido. Salve.

O buff aparece junto da skill enquanto estiver ativo. Passe o mouse para ver o tempo
restante.

- **Acabando:** nos últimos 10 segundos, o buff **pisca** com uma moldura vermelha. Dá
  para mudar o tempo (ou desligar) e ligar um **apito** na aba **Buffs** das configurações.
- **Usou a skill de novo antes do buff acabar?** O programa percebe que o ícone da skill
  escureceu (entrou em recarga) e **reinicia o tempo** do buff. Dá para desligar isso por
  buff em **Editar**.
- **Limitação:** o tempo é uma contagem do próprio programa, a partir da duração
  informada, porque o tooltip do jogo não pode ser copiado.

## Atalhos

| Ação | Como |
|---|---|
| Mover uma barra | Arrastar com o botão esquerdo |
| Zoom das barras | Roda do mouse sobre a barra |
| Configurações | Botão direito na barra ou **Ctrl+Alt+F11** |
| Click-through (cliques atravessam as barras) | **Ctrl+Alt+F10** |
| Cadastrar buff | **Ctrl+Alt+F12** |
| Configurações, trocar personagem, sair | Botão direito no ícone perto do relógio |

Nas configurações (aba **Barras**) também ficam **opacidade**, zoom, espaço entre ícones,
atualizações por segundo, a orientação de cada barra e a opção **Mostrar as barras e buffs
em prints e gravações**. Por padrão, as barras ficam fora dos prints (Lightshot, OBS etc.).

## Problemas comuns

| Sintoma | Solução |
|---|---|
| O programa não abre ou fecha sozinho | Veja o **`diagnostico.txt`**, criado na pasta do programa, e mande-o numa issue. Se o arquivo nem for criado, o Windows ou o antivírus bloqueou o programa: botão direito no ZIP > **Propriedades** > marque **Desbloquear**, extraia de novo e libere a pasta no antivírus |
| Aviso "O Windows protegeu o computador" | **Mais informações** > **Executar assim mesmo** |
| Ícones errados depois de mover o jogo | O ajuste é automático (aba **Jogo** > **Acompanhar a janela do jogo**). Se ainda estiverem errados, ou se o tamanho da interface mudou: **Trocar vocação/magias** > **Procurar de novo** |
| O assistente não acha uma magia | Use **Marcar**. Se a magia ainda não foi aprendida ou está bloqueada, o ícone fica diferente |
| As imagens da wiki não aparecem | Elas são baixadas na primeira vez. Confira a internet. Dá para continuar sem elas |
| A barra não aparece por cima do jogo | Use modo janela ou janela sem borda, não tela cheia exclusiva |
| O jogo está no 2º monitor | `BarraDeSkills.exe --monitor 2` (ou `python skillbar.py --monitor 2`) |
| A barra some mesmo com o jogo aberto | O jogo precisa estar em primeiro plano. Ou use **Mostrar sempre** na aba Jogo |
| O buff não aparece | Redefina a área dos buffs cobrindo todas as linhas (aba Buffs > **Redefinir área**) |
| Quero começar do zero | Apague o `skillbar_config.json` e a pasta `buffs` |

Achou um bug? Abra uma [issue](https://github.com/famartins/BarraDeSkills/issues) com um
print da tela e o `diagnostico.txt`.

---

## Detalhes técnicos

### Como funciona

- **Captura:** a cada quadro (padrão 30 FPS, ajustável), o programa captura com
  [`mss`](https://github.com/BoboTiG/python-mss) o retângulo que engloba as skills de cada
  barra. Depois recorta cada ícone e monta a faixa com Pillow. Com zoom, a ampliação usa
  *nearest neighbor* para manter o pixel art nítido.
- **Janelas sobrepostas** (`overlay.py`): uma janela Tkinter por barra, sem borda e
  `topmost`, com os estilos Win32 `WS_EX_NOACTIVATE` (não rouba o foco do jogo),
  `WS_EX_TOOLWINDOW` (não aparece na barra de tarefas) e `WS_EX_LAYERED` (opacidade, via
  `SetLayeredWindowAttributes`). O click-through liga o `WS_EX_TRANSPARENT`.
- **Sem eco na captura:** `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` impede que
  as próprias barras apareçam nas capturas, mesmo sobrepostas às skills originais.
- **Telas:** [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (`telas.py`),
  com a identidade visual em `tema.py`: paleta "Arcano neon", com fundo quase preto
  arroxeado (`#0E0B16`, painéis `#1A1426`, cards `#241C34`, borda `#3A2D57`), texto
  `#F3EEFF` e `#A99BC9`, roxo `#B57CFF` para seleção (aba ativa, chips, sliders, Barra 1)
  e verde-limão `#B6FF3B` para as ações principais (botões, toggles, Barra 2), sempre com
  texto escuro por cima. Raios de 10–14 px e a fonte [Inter](https://rsms.me/inter/)
  (licença SIL OFL, em `dados/fontes/`). As barras e buffs sobre o jogo usam as mesmas
  cores; a moldura do buff acabando continua vermelha.
- **Personagem de cada vocação** (tela de escolha): montado como no
  [provador de roupas da Bloodpedia](https://www.bloodpedia.com.br/outfits/). A folha de
  sprites traz, em blocos de 128×128, a imagem base e uma máscara de cores; `wiki.py`
  pinta cada cor da máscara com a cor da roupa e guarda o resultado em
  `cache/personagens/`. A roupa de cada vocação fica em `vocacoes.json` (`personagem`).
- **Personagens** (`config.py`): as opções gerais valem para todos. Vocação, barras e
  buffs pertencem a cada personagem. O personagem ativo fica no nível de cima da
  configuração, e uma cópia dele é guardada em `profiles` a cada gravação. Configurações
  antigas (uma barra só) são migradas sozinhas para o personagem "Principal".
- **Dados das vocações:** `ferramentas/atualizar_wiki.py` lê a tabela "Magias" das
  páginas da [Bloodpedia](https://bloodpedia.vercel.app/) e a arte de cada vocação da
  página inicial, e gera `dados/vocacoes.json`. As imagens pertencem aos criadores do
  jogo e **não vão no repositório nem no executável**: `wiki.py` baixa cada uma na
  primeira vez para `cache/`.
- **Localização automática** (`localizar.py`, numpy):
  - Compara só o **miolo** de cada ícone da wiki (sem os cantos onde o jogo desenha a
    tecla de atalho e o "Lv").
  - A escala tela/wiki é estimada uma vez, testando de 0,5× a 2,5×. Atalho: 1,0×, o
    caso comum, porque os ícones da wiki têm 44 px, como no jogo em 1440p.
  - A busca grossa amostra pixels e posições com `sliding_window_view` e refina em volta
    dos melhores candidatos.
  - Classificação pelo erro absoluto médio: até 12 = encontrada, até 30 = dúvida, acima
    disso = não encontrada.
- **Reconhecimento de buffs** (`buffcore.py`): 10× por segundo, captura a área dos buffs
  e procura cada ícone cadastrado. O buff é aceito se o erro médio for ≤ `buff_threshold`.
  Se a área marcada for pequena, a busca cresce para os lados e para baixo (3 linhas).
- **Cronômetro** (`BuffTracker`): o buff começa a contar quando aparece. Ele continua
  "ativo" por 1 s depois de sumir, para não piscar se algo cobrir o ícone. Se o jogo sai
  de foco, a contagem é congelada e retomada quando o jogo volta.
- **Aviso de fim:** com o tempo restante ≤ `warn_seconds`, a moldura do buff fica
  vermelha e o ícone alterna com uma versão apagada, cerca de 3 vezes por segundo. O apito
  (`winsound.Beep`, numa thread) toca uma vez por ativação.
- **Reinício ao reusar** (`CastDetector`): acompanha o brilho médio de cada skill. Uma
  queda brusca (abaixo de 75% do normal, em até 3 quadros) indica que a skill entrou em
  recarga. Depois disso, não dispara de novo até o brilho voltar a 90%. Escurecimentos
  lentos não contam.
- **Buffs junto das skills:** uma janela por barra, alinhada a ela (acima na horizontal,
  ao lado na vertical). O fundo usa uma *color key* (`LWA_COLORKEY`, cor `#ff00fe`), então
  só os ícones são visíveis e os cliques atravessam o resto. Buffs sem skill vão para uma
  janelinha solta e arrastável. No modo só buffs, ela vira uma caixa fixa com título, que
  fica na tela mesmo sem buff ativo.
- **Diagnóstico:** o programa registra a inicialização, os eventos dos buffs e qualquer
  erro, inclusive travamentos graves (`faulthandler`), em `diagnostico.txt`. Passando de
  512 KB, o arquivo é encurtado para as últimas 2.000 linhas. No `.exe`, que não tem
  janela preta, um erro fatal também aparece numa caixa de mensagem.
- **Uma cópia só** (`sistema.py`): a primeira cópia cria um *mutex* nomeado. As
  seguintes percebem, sinalizam um evento nomeado, que faz a primeira vir para frente, e
  fecham.
- **Bandeja:** ícone com [`pystray`](https://github.com/moses-palmer/pystray), numa
  thread própria. Os cliques viram pedidos numa fila que o loop do Tk lê 4× por segundo.
- **Acompanhar a janela do jogo:** 4× por segundo, o programa localiza a janela do jogo
  (pelo executável definido ou por "BloodStone" no título) e lê a origem da área interna
  (`GetClientRect` + `ClientToScreen`). Se ela andou, as regiões das skills (de todos os
  personagens), a barra lateral e a área dos buffs são deslocadas pela mesma diferença. A
  referência fica em `game_anchor`.
- **Abrir com o Windows:** valor `BarraDeSkills` em
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, sem precisar de administrador,
  com o argumento `--esperar`.

### Arquivos

| Arquivo | Conteúdo |
|---|---|
| `skillbar.py` | Programa principal: ciclo, personagens, buffs, aviso, atalhos |
| `overlay.py` | Janelas por cima do jogo: barras, buffs, tela de marcação, estilos Win32 |
| `telas.py` | Assistente, configurações e editor de buff (CustomTkinter) |
| `tema.py` | Identidade visual: cores, fonte, raios e espaçamentos |
| `config.py` | Configuração, personagens e migração (sem Windows, testável) |
| `wiki.py` | Carrega `dados/vocacoes.json` e mantém o cache de imagens |
| `localizar.py` | Acha as magias na barra lateral do jogo |
| `buffcore.py` | Busca de ícone, cronômetro, detecção de uso da skill e área de busca |
| `atualizador.py` | Procura versão nova no GitHub, baixa, confere e troca os arquivos |
| `.github/workflows/publicar.yml` | Gera e publica a release sozinho quando a versão muda |
| `sistema.py` | Windows: cópia única, ícone na bandeja, janela do jogo, abrir com o Windows |
| `dados/` | `vocacoes.json` (gerado da Bloodpedia), `icone.ico` e a fonte Inter (`fontes/`) |
| `ferramentas/atualizar_wiki.py` | Regera o `vocacoes.json` quando a wiki mudar |
| `ferramentas/gerar_exe.py` | Gera o executável e o ZIP para Releases |
| `tests/` | Testes: `python -m unittest discover -s tests` |
| `iniciar.bat` | Roda pelo código-fonte: confere o Python e instala as dependências |
| `skillbar_config.json`, `buffs/`, `cache/`, `diagnostico.txt` | Criados no uso. Locais, ignorados pelo git |

### Gerar o executável

```
pip install pyinstaller
python ferramentas/gerar_exe.py
```

O resultado é `dist/BarraDeSkills-vX.Y-windows.zip` (os ZIPs de versões antigas são apagados), com `BarraDeSkills.exe` e a pasta
`_internal/`. O build usa o modo pasta (`--onedir`) e `--windowed`, sem console. Os
arquivos de `dados/` e os do CustomTkinter vão embutidos. A versão vem de `VERSION`, em
`telas.py`.

### Publicar uma versão

1. Mude `VERSION` em `telas.py` (ex.: `"0.9"` → `"0.9.1"`).
2. No GitHub Desktop, faça o commit. O **título e a descrição do commit viram o texto da
   release**, que aparece na janela de atualização dos usuários.
3. Dê **Push**.

O GitHub Actions (`.github/workflows/publicar.yml`) roda os testes, gera o `.exe` e cria a
release `vX.Y` com o ZIP. Leva uns 5 minutos; acompanhe na aba **Actions** do
repositório. Commits sem mudar a versão não publicam nada. Se a release dessa versão já
existir, também não.

Os programas abertos dos usuários veem a versão nova ao abrir e oferecem **Atualizar
agora**. O atualizador baixa o ZIP da release, confere o tamanho e o sha256 informados
pelo GitHub, e o `.exe` novo (rodando da pasta temporária) espera o antigo fechar.
Depois troca só o `BarraDeSkills.exe`, a pasta `_internal/` e o `LEIA-ME.txt`, com volta
atrás se falhar no meio, e abre o programa de novo.

**Versões:** enquanto o programa estiver em teste, as versões são `0.x` (0.4, 0.5...). A
`1.0` marca o lançamento. Não marque a release como *Pre-release*: o link
`releases/latest`, usado no README e mandado aos amigos, ignora pre-releases.

### Linha de comando

```
BarraDeSkills.exe (ou python skillbar.py)    inicia
  --calibrar      marca os ícones da barra 1 manualmente, sem o assistente
  --monitor 2     usa o monitor 2 nas telas de marcação
  --janelas       lista as janelas abertas (executável e título)
  --jogo X.exe    só mostra as barras com X.exe em primeiro plano ("" desativa)
  --esperar       fica no ícone perto do relógio até o jogo abrir
```

### Configuração (`skillbar_config.json`)

**Gerais:**

| Chave | Padrão | Descrição |
|---|---|---|
| `zoom` / `gap` / `fps` | `1.0` / `4` / `30` | Ampliação, espaço entre ícones e atualizações por segundo |
| `opacity` | `1.0` | Opacidade das barras e buffs (0,2 a 1,0) |
| `click_through` | `false` | Cliques atravessam as barras |
| `exclude_from_capture` | `true` | As barras não aparecem em prints e gravações (desligue para aparecerem) |
| `game_process` / `game_title` | `""` | Executável ou trecho do título da janela do jogo |
| `sidebar_area` | `null` | `[x, y, largura, altura]` da barra lateral de skills do jogo |
| `buff_area` | `null` | `[x, y, largura, altura]` da área de buffs no jogo |
| `buff_pos` | `null` | Posição da janelinha de buffs soltos |
| `buff_zoom` | `1.5` | Ampliação extra dos ícones de buff |
| `buff_threshold` | `14` | Tolerância do reconhecimento (menor = mais exato) |
| `warn_seconds` / `warn_sound` | `10` / `false` | Piscar nos últimos N segundos (0 = nunca) e apito |
| `profile` / `profiles` | `""` / `{}` | Personagem ativo e os dados de cada personagem |
| `track_game` / `game_anchor` | `true` / `null` | Acompanhar a janela do jogo e a posição de referência dela |

**De cada personagem** (no nível de cima para o ativo e em `profiles`):

| Chave | Descrição |
|---|---|
| `vocacao` | Slug da vocação (ex.: `barbaro`) |
| `bars` | Até 2 barras: `{regions, magias, orientation, pos}` |
| `buffs` | `{name, duration, desc, file, skill, skill_slug, restart_on_cast}`. `skill` é o índice **global** da skill (barra 1, depois barra 2) ou `null`. `skill_slug` mantém o vínculo se a ordem mudar |
| `only_buffs` | Esconde as barras e mostra só os buffs |
| `buff_vertical` | Janelinha de buffs em coluna (um ícone embaixo do outro) |

O programa ativa *DPI awareness* por monitor, então as coordenadas são pixels reais
mesmo com escala do Windows acima de 100%.
