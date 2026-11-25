# -*- coding: utf-8 -*-
"""
Identidade visual (tokens): cores, tipografia, raios e espacamentos.

Um lugar so para o tema; telas.py e overlay.py importam daqui.
Paleta "Arcano neon" (proposta B): roxo para selecao e verde-limao para as
acoes principais, sobre um fundo quase preto arroxeado.

    Fundo base   #0E0B16  janela e areas mais profundas
    Superficie   #1A1426  paineis e cards
    Card         #241C34  terceiro nivel (itens dentro dos paineis, hover)
    Borda        #3A2D57  divisores e contornos
    Texto        #F3EEFF  titulos e textos
    Secundario   #A99BC9  legendas e descricoes
    Roxo         #B57CFF  selecao: aba ativa, chips, sliders, card escolhido, Barra 1
    Verde-limao  #B6FF3B  acoes principais, toggles ligados, "ultimo usado", Barra 2

Texto escuro (#0E0B16) sobre o roxo (6,8:1) e sobre o verde-limao (16:1).
"""

import os

# -- cores --------------------------------------------------------------------
BG = "#0E0B16"           # fundo base
SURFACE = "#1A1426"      # paineis e cards
SURFACE_HOVER = "#241C34"  # terceiro nivel: itens dentro dos paineis / hover
BORDER = "#3A2D57"       # divisores e contornos
ACCENT = "#B57CFF"       # roxo: selecao
ACCENT_HOVER = "#C597FF"
PRIMARY = "#B6FF3B"      # verde-limao: acoes principais
PRIMARY_HOVER = "#CAFF70"
ON_ACCENT = "#0E0B16"    # texto sobre o roxo e sobre o verde-limao
SECONDARY = ACCENT       # borda no hover / card escolhido
HIGHLIGHT = PRIMARY      # destaques pontuais (selo "ultimo usado")

TEXT = "#F3EEFF"         # 17:1 sobre o fundo
DIM = "#A99BC9"          # 7:1 sobre a superficie
OK = PRIMARY
WARN = "#FFC857"
ERR = "#FF8FA3"
ERR_HOVER = "#3A1A2A"

# cor de cada barra (selos de ordem, B1/B2) e do texto sobre ela
BAR_COLORS = (ACCENT, PRIMARY)
ON_BAR = (ON_ACCENT, ON_ACCENT)

# etiquetas de tipo das magias (texto claro por cima, 6,7:1 ou mais)
TIPO_COR = {"Ataque": "#7A2E4A", "Cura": "#2E5E3A", "Suporte": "#3B3F8F"}

# -- sobreposicao no jogo ---------------------------------------------------
BAR_BG = BG                      # fundo das barras (entre os icones)
WARN_COLOR = "#e0302a"           # moldura do buff acabando (alerta: fica vermelho)
BOX_BORDER = BORDER              # caixa do modo so buffs
BOX_TITLE = ACCENT
BOX_DIM = DIM
BOX_CELL = SURFACE
TIP_BG = BG
TIP_BORDER = ACCENT
TIP_NAME = ACCENT
TIP_DESC = TEXT
TIP_TIME = WARN
MARK_LINE = PRIMARY              # tela de marcacao (bem visivel sobre o jogo)
MARK_TEXT = TEXT
MARK_BG = BG

# -- tipografia ---------------------------------------------------------------
FONT_FAMILY = "Inter"
FALLBACK_FAMILY = "Segoe UI"
TITLE, SUBTITLE, BODY, CAPTION = 24, 14, 13, 11

# -- raios e espacamentos -----------------------------------------------------
RADIUS = 14          # cards e paineis (12 a 16)
RADIUS_SM = 10       # botoes, campos
RADIUS_PILL = 12     # selos e chips
PAD = 16

_loaded = None


def load_fonts(res_dir):
    """Carrega a Inter que vai junto do programa (dados/fontes). Devolve a familia
    a usar: Inter, ou Segoe UI se nao der para carregar."""
    global _loaded
    if _loaded is not None:
        return _loaded
    _loaded = FALLBACK_FAMILY
    try:
        import customtkinter as ctk
        folder = os.path.join(res_dir, "dados", "fontes")
        ok = all(ctk.FontManager.load_font(os.path.join(folder, f))
                 for f in ("Inter-Regular.ttf", "Inter-SemiBold.ttf"))
        if ok:
            _loaded = FONT_FAMILY
    except Exception:
        pass
    return _loaded
