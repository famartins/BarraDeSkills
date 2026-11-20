# Barra de Skills

Copia os ícones das skills (a barra lateral do jogo) e monta uma barra horizontal
sempre visível por cima do jogo. Como é uma cópia da imagem da tela, o cooldown e
o nível aparecem do mesmo jeito que no jogo.

O programa **só lê a imagem da tela**. Não mexe na memória do jogo e não envia
cliques nem teclas. Você continua usando as skills pelas teclas de atalho normais.

## Instalação (uma vez só)

1. Instale o Python 3.10 ou mais novo em https://www.python.org/downloads/
   Na primeira tela do instalador, **marque "Add python.exe to PATH"**.
2. Nesta página do GitHub, clique no botão verde **Code** > **Download ZIP** e extraia
   a pasta em algum lugar (por exemplo `C:\SkillBar`).
3. Abra um terminal dentro da pasta (clique com o botão direito num espaço vazio
   da pasta e escolha "Abrir no Terminal") e rode:

   ```
   pip install -r requirements.txt
   ```

## Como usar

1. Abra o jogo **em modo janela** (ou janela sem borda).
2. Dê dois cliques em `iniciar.bat` (ou rode `python skillbar.py`).
3. Na primeira vez abre a **calibração**: a tela congela com um aviso no topo.
   - Na **1ª skill**, arraste um retângulo sobre o ícone.
   - Nas demais, só **clique no centro do ícone**. Elas usam o mesmo tamanho.
   - Marque **na ordem** em que quer ver na barra.
   - Botão direito ou Backspace desfaz a última. **Enter** conclui. **Esc** cancela.
4. A barra aparece na parte de baixo da tela. **Arraste com o botão esquerdo** para
   onde quiser. A posição fica salva.

## Mostrar a barra só quando o jogo estiver ativo

Por padrão a barra fica sempre visível. Para ela aparecer **só quando a janela do jogo
estiver em primeiro plano** (e sumir quando você abrir o navegador, por exemplo):

1. Abra o jogo e inicie a barra.
2. Botão direito na barra (ou Ctrl+Alt+F11) > **"Definir janela do jogo"**.
3. Em até 3 segundos, **clique na janela do jogo**. O programa grava qual executável é.

Pronto: ao trocar para outro programa a barra some, e ao voltar para o jogo ela
reaparece. Se o jogo abrir com outro nome de programa no futuro, é só definir de novo.

Alternativas pelo terminal:

- `python skillbar.py --janelas` lista as janelas abertas com o nome do programa.
- `python skillbar.py --jogo nome_do_programa.exe` define direto.
- `python skillbar.py --jogo ""` volta a deixar sempre visível.

Observação: a barra só aparece com o jogo **em primeiro plano**. Se o jogo estiver
visível em um monitor mas você estiver com outro programa selecionado, ela some.

## Buffs acima da barra (Ira, Fúria etc.)

Os ícones de buff que aparecem embaixo das infos do personagem podem ser copiados para
uma janelinha acima da barra de skills. Cada ícone só aparece enquanto o buff está ativo
no jogo, e ao passar o mouse sobre ele aparece um tooltip com o nome, a descrição e o
**tempo restante**.

**Importante sobre o tempo:** o tooltip do jogo só existe quando o mouse está sobre o ícone
original, então ele não pode ser copiado. O programa faz uma contagem própria: ele percebe o
momento em que o ícone aparece e conta a partir da **duração que você informar** no cadastro.

Se o programa não souber quando o buff começou (por exemplo, o buff já estava ativo antes de
você abrir o programa), a contagem começa quando ele o enxergar pela primeira vez.
Se você usar a skill de novo com o buff ainda ativo, o ícone não some, então a contagem não
reinicia sozinha. Nesse caso o tempo mostrado pode ficar defasado.

**Como cadastrar (uma vez por buff):**

1. Instale o `numpy` se ainda não tiver: `pip install -r requirements.txt`
2. Use a skill no jogo para o buff ficar **ativo**.
3. Aperte **Ctrl+Alt+F12** (ou: botão direito na barra > "Buffs..." > "Adicionar buff").
4. Na primeira vez, a tela congela duas vezes:
   - **1/2: área dos buffs.** Arraste um retângulo cobrindo a linha onde os ícones de buff
     aparecem (do primeiro ao último espaço possível), só um pouco mais alto que um ícone.
     Isso é feito uma vez só.
   - **2/2: o ícone.** Arraste um retângulo bem justo sobre o ícone do buff.
5. Aparece uma janelinha para você informar **nome**, **duração em segundos** e uma
   descrição opcional. Embaixo aparecem as skills da sua barra: **clique na skill que
   dá esse buff**. Salve.

Repita para cada buff que quiser.

**Onde o buff aparece:**

- **Ligado a uma skill:** enquanto o buff estiver ativo, o ícone dele aparece **logo
  acima daquela skill** na barra. Ele acompanha a barra quando você a arrasta. O espaço
  em volta é transparente, então não cobre o jogo.
- **Sem skill ("Nenhuma"):** fica na janelinha acima da barra, como antes, e dá para
  arrastá-la. Se houver buffs ligados a skills ativos ao mesmo tempo, os sem skill vão
  para a direita da barra.

Para ligar um buff que você já cadastrou a uma skill: botão direito na barra > "Buffs..." >
selecione o buff > **Editar...** > clique na skill > Salvar.

**Área dos buffs:** ela precisa cobrir a **linha inteira** de buffs, não só um ícone. Os
buffs trocam de posição na fila conforme aparecem e somem, e fora da área eles não são
reconhecidos. Se a área estiver pequena demais (só um ícone), o programa amplia a busca
sozinho para os lados, mas o mais seguro é usar "Buffs..." > "Redefinir área dos buffs".

**Tamanho:** os ícones de buff do jogo são bem pequenos, então na barra eles aparecem
ampliados (1,5× por padrão, um pouco menores que as skills). Ajuste em "Buffs..." > "Tamanho dos ícones de buff".

Dicas:

- Marque o retângulo do ícone o mais justo possível. O reconhecimento compara os pixels.
- Se mudar o tamanho da janela do jogo ou da interface, cadastre os buffs de novo.
- Se um buff não for reconhecido ou aparecer o ícone errado, me diga qual foi.

## Controles

| Ação | Como |
|---|---|
| Mover a barra | Arrastar com o botão esquerdo |
| Abrir configurações (zoom, espaço, FPS, recalibrar, sair) | Botão direito na barra, ou **Ctrl+Alt+F11** |
| Click-through (cliques atravessam a barra) | **Ctrl+Alt+F10** liga e desliga |
| Cadastrar um buff (com o buff ativo no jogo) | **Ctrl+Alt+F12** |
| Refazer a calibração | Configurações > Recalibrar, ou `python skillbar.py --calibrar` |

## Dicas e problemas comuns

- **Mudou ou moveu a janela do jogo?** Os ícones são lidos de posições fixas da tela.
  Se a janela mudar de lugar ou de tamanho, refaça a calibração.
- **Jogo em tela cheia exclusiva:** a barra não aparece por cima. Use janela ou janela
  sem borda.
- **Mais de um monitor:** a calibração usa o monitor 1 (principal). Se o jogo estiver
  em outro, rode `python skillbar.py --monitor 2 --calibrar`.
- **A barra aparece borrada ou deslocada:** me diga a escala de exibição do Windows
  (Configurações > Sistema > Vídeo) e a resolução do monitor.
- **Quer deixar a barra mais "invisível" no clique:** ative o click-through. Para voltar,
  use Ctrl+Alt+F10.
- As configurações ficam em `skillbar_config.json`, na mesma pasta. Para voltar ao
  padrão, apague esse arquivo.
- Por ler a tela, esse tipo de programa costuma ser seguro, mas as regras de cada jogo
  valem mais do que qualquer expectativa minha. Vale conferir as do Bloodstone.
