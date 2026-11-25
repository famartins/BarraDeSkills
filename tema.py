# -*- coding: utf-8 -*-
"""
Identidade visual (tokens): cores, tipografia, raios e espacamentos.

Um lugar so para o tema; telas.py e overlay.py importam daqui.
Paleta verde-escura com acentos neon (proposta-identidade-visual.md):

    Fundo base   #002E34  janela e areas mais profundas
    Superficie   #004443  cards, paineis e campos
    Secundaria   #00755C  bordas ativas, hover e estados intermediarios
    Acento       #00C16C  botoes principais, selecao, abas ativas, toggles
    Destaque     #90FF17  uso pontual: pronto/ok, foco, atencao

Texto escuro sobre o acento (branco sobre #00C16C fica abaixo de 3:1).
"""

import os

# -- cores --------------------------------------------------------------------
BG = "#002E34"           # fundo base
SURFACE = "#004443"      # cards e paineis
SURFACE_HOVER = "#0A524F"
BORDER = "#0E5A57"       # borda sutil (repouso)
SECONDARY = "#00755C"    # borda ativa, hover
ACCENT = "#00C16C"
ACCENT_HOVER = "#2BD483"
ON_ACCENT = "#002E34"    # texto sobre o acento (~6:1)
HIGHLIGHT = "#90FF17"    # destaque neon, so em detalhes

TEXT = "#E8F6F2"         # 9,9:1 sobre a superficie
DIM = "#9CC7BE"          # 5,9:1 sobre a superficie
OK = HIGHLIGHT
WARN = "#FFC857"
ERR = "#FF8A8A"
ERR_HOVER = "#4A2326"

# cor de cada barra (selos de ordem, B1/B2)
BAR_COLORS = (ACCENT, "#22D3EE")
ON_BAR = (ON_ACCENT, ON_ACCENT)

# etiquetas de tipo das magias
TIPO_COR = {"Ataque": "#7A3B2E", "Cura": SECONDARY, "Suporte": "#1D5C78"}

# -- sobreposicao no jogo ---------------------------------------------------
BAR_BG = BG                      # fundo das barras (entre os icones)
OLD_BAR_BG = "#0b0b0b"           # fundo antigo: migrado para o novo
WARN_COLOR = "#e0302a"           # moldura do buff acabando (alerta: fica vermelho)
BOX_BORDER = SECONDARY           # caixa do modo so buffs
BOX_TITLE = HIGHLIGHT
BOX_DIM = DIM
BOX_CELL = SURFACE
TIP_BG = BG
TIP_BORDER = SECONDARY
TIP_NAME = HIGHLIGHT
TIP_DESC = TEXT
TIP_TIME = WARN
MARK_LINE = HIGHLIGHT            # tela de marcacao
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
