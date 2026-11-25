# -*- coding: utf-8 -*-
"""
Identidade visual (tokens): cores, tipografia, raios e espacamentos.

Um lugar so para o tema; telas.py e overlay.py importam daqui.
Paleta de carvao quente com acento em ouro e tons de pergaminho
(proposta-identidade-visual.md):

    Fundo base        #15120F  janela e areas mais profundas
    Superficie        #1F1A16  cards, paineis e campos de busca
    Borda             #3A3129  divisores e contornos
    Texto principal   #EDE3D0  titulos e textos (pergaminho)
    Texto secundario  #A89A84  legendas e descricoes
    Acento            #D4A03C  botoes principais, aba ativa, toggles ligados
    Barra 1           #C8452F  vermelho ferrugem
    Barra 2           #3A7BD5  azul

Texto escuro sobre o ouro (~8:1); branco sobre o ouro fica ilegivel.
No azul da Barra 2 o texto e escuro e em negrito (4,4:1, o ponto mais fraco).
"""

import os

# -- cores --------------------------------------------------------------------
BG = "#15120F"           # fundo base
SURFACE = "#1F1A16"      # cards e paineis
SURFACE_HOVER = "#2A231D"  # terceiro nivel: card em destaque / hover
BORDER = "#3A3129"       # divisores e contornos
SECONDARY = "#8A6A2E"    # borda no hover: leve brilho dourado
ACCENT = "#D4A03C"
ACCENT_HOVER = "#E0B252"
ON_ACCENT = "#15120F"    # texto sobre o ouro (~8:1)
HIGHLIGHT = ACCENT       # destaques pontuais (selo "ultimo usado", titulos de dica)

TEXT = "#EDE3D0"         # 14,7:1 sobre o fundo
DIM = "#A89A84"          # 6,3:1 sobre a superficie
OK = "#7FB069"
WARN = "#E8B04A"
ERR = "#E06C5A"
ERR_HOVER = "#3A1E19"

# cor de cada barra (selos de ordem, B1/B2) e do texto sobre ela
BAR_COLORS = ("#C8452F", "#3A7BD5")
ON_BAR = ("#FFFFFF", BG)

# etiquetas de tipo das magias (texto pergaminho por cima, 6:1 ou mais)
TIPO_COR = {"Ataque": "#7A2E22", "Cura": "#2F5A3A", "Suporte": "#25466E"}

# -- sobreposicao no jogo ---------------------------------------------------
BAR_BG = BG                      # fundo das barras (entre os icones)
OLD_BAR_BG = ("#0b0b0b", "#002e34")   # fundos antigos: migrados para o novo
WARN_COLOR = "#e0302a"           # moldura do buff acabando (alerta: fica vermelho)
BOX_BORDER = BORDER              # caixa do modo so buffs
BOX_TITLE = ACCENT
BOX_DIM = DIM
BOX_CELL = SURFACE
TIP_BG = BG
TIP_BORDER = SECONDARY
TIP_NAME = ACCENT
TIP_DESC = TEXT
TIP_TIME = WARN
MARK_LINE = ACCENT               # tela de marcacao
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
