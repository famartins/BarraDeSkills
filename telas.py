# -*- coding: utf-8 -*-
"""
Telas do programa (CustomTkinter, tema escuro):

- Assistente: personagem -> vocacao -> magias (barra 1 e 2, orientacao, so
  buffs) -> localizacao automatica e confirmacao -> pronto.
- Configuracoes: abas Personagem, Barras, Buffs, Jogo e Sobre.
- Editor de buff: nome, duracao, skill e reinicio ao usar a skill.

As janelas que ficam por cima do jogo (barras e buffs) continuam em Tk puro no
overlay.py, porque precisam de estilos especiais do Windows.
"""

import os
import webbrowser
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

import config
import localizar
import sistema
import wiki

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

VERSION = "2.3"
REPO_URL = "https://github.com/famartins/BarraDeSkills"
ICON_PATH = os.path.join(config.RES_DIR, "dados", "icone.ico")

# cores
ACCENT = "#b3261e"
ACCENT_HOVER = "#8e1c16"
BAR_COLORS = (ACCENT, "#2563eb")         # selo da barra 1 e da barra 2
BG = "#121215"
CARD = "#1d1d22"
CARD_HOVER = "#26262d"
BORDER = "#2f2f37"
TEXT = "#ececf1"
DIM = "#9a9aa8"
OK = "#3fb950"
WARN = "#d29922"
ERR = "#f85149"
TIPO_COR = {"Ataque": "#9a3412", "Cura": "#166534", "Suporte": "#1e40af"}

NONE_ICON = Image.new("RGB", (44, 44), "#2a2a31")


def F(size=13, weight="normal"):
    return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)


def cimg(pil, size):
    return ctk.CTkImage(light_image=pil, dark_image=pil, size=size)


def fit(pil, box):
    """Tamanho que cabe em `box` mantendo a proporcao."""
    w, h = pil.size
    k = min(box[0] / w, box[1] / h)
    return max(1, round(w * k)), max(1, round(h * k))


def accent_button(master, text, command, **kw):
    kw.setdefault("height", 36)
    return ctk.CTkButton(master, text=text, command=command, fg_color=ACCENT,
                         hover_color=ACCENT_HOVER, font=F(13, "bold"), **kw)


def ghost_button(master, text, command, **kw):
    kw.setdefault("height", 32)
    return ctk.CTkButton(master, text=text, command=command, fg_color="transparent",
                         border_width=1, border_color=BORDER, hover_color=CARD_HOVER,
                         text_color=TEXT, font=F(12), **kw)


def segmented(master, values, command=None, **kw):
    return ctk.CTkSegmentedButton(master, values=values, font=F(12), command=command,
                                  selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
                                  **kw)


def bind_tree(widget, event, func):
    """Liga o evento ao widget e a todos os filhos (para cards clicaveis)."""
    widget.bind(event, func, add="+")
    for child in widget.winfo_children():
        bind_tree(child, event, func)


def hover_card(card, on_click):
    def enter(_e):
        card.configure(border_color=ACCENT, fg_color=CARD_HOVER, cursor="hand2")

    def leave(_e):
        card.configure(border_color=BORDER, fg_color=CARD)

    bind_tree(card, "<Enter>", enter)
    bind_tree(card, "<Leave>", leave)
    bind_tree(card, "<Button-1>", lambda _e: on_click())


def load_icon(voc_slug, magia):
    try:
        return Image.open(wiki.icon_path(voc_slug, magia)).convert("RGB")
    except OSError:
        return None


PARCHMENT = (214, 200, 178, 255)


def load_art(voc):
    """Arte da vocacao (desenho a lapis com transparencia) sobre fundo de pergaminho,
    senao ela some no tema escuro."""
    try:
        art = Image.open(wiki.art_path(voc)).convert("RGBA")
    except OSError:
        return None
    bg = Image.new("RGBA", art.size, PARCHMENT)
    bg.alpha_composite(art)
    return bg.convert("RGB")


def shortcut_feedback(app, label):
    """Cria os atalhos e mostra o resultado em `label`."""
    label.configure(text="Criando...", text_color=DIM)
    label.update()
    made = sistema.create_shortcuts(ICON_PATH)
    if made:
        label.configure(text="✓ Atalhos criados: procure \"Barra de Skills\"", text_color=OK)
    else:
        label.configure(text="Não consegui criar os atalhos", text_color=ERR)


def ask_text(parent, title, text):
    dlg = ctk.CTkInputDialog(title=title, text=text, font=F(13),
                             button_fg_color=ACCENT, button_hover_color=ACCENT_HOVER)
    try:
        dlg.attributes("-topmost", True)
    except Exception:
        pass
    value = dlg.get_input()
    return value.strip() if value else ""


class Window(ctk.CTkToplevel):
    """Janela base: tema escuro, sempre por cima do jogo, centralizada."""

    def __init__(self, app, title, size):
        super().__init__(app.root)
        self.app = app
        self.title(title)
        self.configure(fg_color=BG)
        self.attributes("-topmost", True)
        w, h = size
        self.geometry("%dx%d+%d+%d" % (w, h, max(0, (self.winfo_screenwidth() - w) // 2),
                                         max(0, (self.winfo_screenheight() - h) // 3)))
        self.minsize(w, h)
        self.after(250, self.bring_front)
        # o CustomTkinter poe o icone dele ~200 ms depois de abrir; troca pelo nosso
        self.after(300, self.set_icon)

    def set_icon(self):
        try:
            self.iconbitmap(ICON_PATH)
        except Exception:
            pass

    def bring_front(self):
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def run_hidden(self, func, *args):
        """Esconde esta janela enquanto `func` roda (ex.: tela congelada)."""
        self.withdraw()
        self.update()
        try:
            return func(*args)
        finally:
            self.bring_front()


# --------------------------------------------------------------------------
# Assistente
# --------------------------------------------------------------------------
class Wizard(Window):
    def __init__(self, app, start_at=None):
        super().__init__(app, "Barra de Skills", (1020, 700))
        self.vocacoes = wiki.load_vocacoes()
        self.images = {}            # slug da magia -> PIL
        self.page = None
        self.finished = False
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.load_state()
        # artes das vocacoes: baixa ja, para os cards de personagem tambem
        wiki.download_arts_async(self.vocacoes, on_done=lambda n: self.after(0, self._arts_done))
        if start_at == "vocacao":
            self.show_vocacao()
        else:
            self.show_personagem()

    def _arts_done(self):
        """Artes baixadas: redesenha a tela de personagens, se for a atual."""
        try:
            if (self.winfo_exists() and getattr(self, "page_name", "") == "personagem"
                    and not self.new_name.get()):      # nao apaga o que esta digitando
                self.show_personagem()
        except Exception:
            pass

    def load_state(self):
        """Escolhas atuais do personagem ativo (para editar em vez de recomecar)."""
        cfg = self.app.cfg
        self.voc = wiki.find_vocacao(self.vocacoes, cfg.get("vocacao") or "")
        bars = cfg["bars"]
        self.sel = [list(bars[i].get("magias") or []) if i < len(bars) else []
                    for i in range(config.MAX_BARS)]
        self.orient = [bars[i].get("orientation", "horizontal") if i < len(bars)
                       else "horizontal" for i in range(config.MAX_BARS)]
        self.only_buffs = bool(cfg.get("only_buffs"))
        self.cur_bar = 0

    def close(self):
        self.destroy()
        self.app.wizard_closed(self.finished)

    def set_page(self, frame, name=""):
        if self.page is not None:
            self.page.destroy()
        self.page = frame
        self.page_name = name
        frame.pack(fill="both", expand=True, padx=28, pady=22)

    def header(self, parent, title, subtitle, back=None):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x")
        if back:
            ghost_button(top, "← Voltar", back, width=90).pack(side="left", padx=(0, 14))
        box = ctk.CTkFrame(top, fg_color="transparent")
        box.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(box, text=title, font=F(24, "bold"), text_color=TEXT,
                     anchor="w").pack(fill="x")
        ctk.CTkLabel(box, text=subtitle, font=F(13), text_color=DIM, anchor="w",
                     justify="left", wraplength=840).pack(fill="x")
        return top

    # -- 0) personagem --
    def show_personagem(self):
        page = ctk.CTkFrame(self, fg_color="transparent")
        self.set_page(page, "personagem")
        self.header(page, "Quem vai jogar?",
                    "Personagens salvos: cada um guarda a sua vocação, barras e buffs. "
                    "Clique em Usar para jogar com ele, ou crie um novo com o nome do "
                    "personagem.")
        grid = ctk.CTkScrollableFrame(page, fg_color="transparent")
        grid.pack(fill="both", expand=True, pady=(16, 0))
        cfg = self.app.cfg
        cards = 0
        for name in config.profile_names(cfg):
            data = cfg["profiles"][name] if name != cfg["profile"] else config.snapshot(cfg)
            self._profile_card(grid, name, data).grid(row=cards // 4, column=cards % 4,
                                                      padx=8, pady=8, sticky="n")
            cards += 1

        new = ctk.CTkFrame(grid, width=210, height=250, fg_color=CARD, corner_radius=14,
                           border_width=2, border_color=BORDER)
        new.grid(row=cards // 4, column=cards % 4, padx=8, pady=8, sticky="n")
        new.pack_propagate(False)
        ctk.CTkLabel(new, text="+", font=F(44, "bold"), text_color=DIM).pack(pady=(26, 0))
        ctk.CTkLabel(new, text="Novo personagem", font=F(15, "bold"), text_color=TEXT).pack()
        self.new_name = ctk.CTkEntry(new, placeholder_text="Nome do personagem", font=F(13),
                                     height=32, width=176)
        self.new_name.pack(pady=(14, 6))
        self.new_name.bind("<Return>", lambda e: self.create_profile())
        self.new_err = ctk.CTkLabel(new, text="", font=F(11), text_color=ERR)
        self.new_err.pack()
        accent_button(new, "Criar", self.create_profile, width=176, height=32).pack()

        foot = ctk.CTkFrame(page, fg_color="transparent")
        foot.pack(fill="x", side="bottom", pady=(10, 0))
        ctk.CTkLabel(foot, text="Dados e imagens: Bloodpedia (bloodpedia.vercel.app)",
                     font=F(11), text_color=DIM).pack(side="left")
        if config.is_configured(cfg) and cfg.get("profile"):
            ghost_button(foot, "Continuar com %s" % cfg["profile"], self.close,
                         width=220).pack(side="right")

    def _profile_card(self, parent, name, data):
        card = ctk.CTkFrame(parent, width=210, height=250, fg_color=CARD, corner_radius=14,
                            border_width=2, border_color=BORDER)
        card.pack_propagate(False)
        voc = wiki.find_vocacao(self.vocacoes, data.get("vocacao") or "")
        art = load_art(voc) if voc else None
        pic = ctk.CTkLabel(card, text="" if art else "?", font=F(40, "bold"),
                           text_color=DIM, height=120,
                           image=cimg(art, fit(art, (150, 120))) if art else None)
        pic.pack(pady=(14, 6))
        active = name == self.app.cfg["profile"]
        ctk.CTkLabel(card, text=name, font=F(15, "bold"), text_color=TEXT,
                     wraplength=190).pack()
        if active:
            ctk.CTkLabel(card, text="último usado", font=F(10), text_color=OK,
                         height=14).pack()
        n = sum(len(b["regions"]) for b in data.get("bars", []))
        info = ("%s · %d magias" % (voc["nome"], n)) if voc else (
            "%d skills" % n if n else "Ainda não configurado")
        if data.get("only_buffs"):
            info += " · só buffs"
        ctk.CTkLabel(card, text=info, font=F(11), text_color=DIM).pack()
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(side="bottom", pady=10)
        ready = config.is_configured(data)
        if ready:
            accent_button(row, "Usar", lambda: self.use_profile(name), width=84,
                          height=30).pack(side="left", padx=3)
        ghost_button(row, "Editar" if ready else "Configurar",
                     lambda: self.edit_profile(name), width=84, height=30
                     ).pack(side="left", padx=3)
        return card

    def create_profile(self):
        name = self.new_name.get().strip()
        if not name:
            self.new_err.configure(text="Digite o nome do personagem.")
            return
        if name in self.app.cfg["profiles"]:
            self.new_err.configure(text="Esse nome já existe.")
            return
        self.app.new_profile(name)
        self.load_state()
        self.show_vocacao()

    def use_profile(self, name):
        if name != self.app.cfg["profile"]:
            self.app.switch_profile(name)
        self.finished = True
        self.close()

    def edit_profile(self, name):
        if name != self.app.cfg["profile"]:
            self.app.switch_profile(name)
        self.load_state()
        self.show_vocacao()

    # -- 1) vocacao --
    def show_vocacao(self):
        page = ctk.CTkFrame(self, fg_color="transparent")
        self.set_page(page)
        self.header(page, "%s: escolha a vocação" % self.app.cfg["profile"],
                    "A barra vai mostrar as magias dela por cima do jogo, com recarga e nível "
                    "iguais aos do jogo. O programa só lê a imagem da tela.",
                    back=self.show_personagem)
        if not self.vocacoes:
            ctk.CTkLabel(page, text="Não encontrei dados/vocacoes.json. Baixe o programa de novo.",
                         text_color=ERR, font=F(14)).pack(pady=40)
            return
        grid = ctk.CTkFrame(page, fg_color="transparent")
        grid.pack(expand=True)
        self.voc_pics = {}
        for i, voc in enumerate(self.vocacoes):
            card = ctk.CTkFrame(grid, width=178, height=330, fg_color=CARD, corner_radius=14,
                                border_width=2, border_color=BORDER)
            card.grid(row=0, column=i, padx=7, pady=10)
            card.pack_propagate(False)
            art = load_art(voc)
            pic = ctk.CTkLabel(card, text="", height=240,
                               image=cimg(art, fit(art, (160, 240))) if art else None)
            pic.pack(pady=(14, 8))
            ctk.CTkLabel(card, text=voc["nome"], font=F(18, "bold"), text_color=TEXT).pack()
            ctk.CTkLabel(card, text="%d magias" % len(voc["magias"]), font=F(12),
                         text_color=DIM).pack()
            self.voc_pics[voc["slug"]] = pic
            hover_card(card, lambda v=voc: self.pick_vocacao(v))
        wiki.download_arts_async(self.vocacoes,
                                 on_each=lambda v, _p: self.after(0, self._art_ready, v))
        foot = ctk.CTkFrame(page, fg_color="transparent")
        foot.pack(fill="x", side="bottom")
        if config.has_skills(self.app.cfg) and not self.app.cfg.get("vocacao"):
            ghost_button(foot, "Pular: manter minha barra atual", self.skip,
                         width=240).pack(side="right")

    def _art_ready(self, voc):
        pic = self.voc_pics.get(voc["slug"]) if hasattr(self, "voc_pics") else None
        art = load_art(voc)
        if art is not None and pic is not None and pic.winfo_exists():
            pic.configure(image=cimg(art, fit(art, (160, 240))))

    def skip(self):
        self.app.skip_wizard()
        self.finished = True
        self.close()

    def pick_vocacao(self, voc):
        if self.voc is None or self.voc["slug"] != voc["slug"]:
            self.sel = [[] for _ in range(config.MAX_BARS)]
        self.voc = voc
        self.show_magias()

    # -- 2) magias --
    def show_magias(self):
        voc = self.voc
        page = ctk.CTkFrame(self, fg_color="transparent")
        self.set_page(page)
        self.header(page, "Magias do %s" % voc["nome"],
                    "Escolha a barra no alto e clique nas magias dela. A ordem dos cliques é "
                    "a ordem na barra (o número no canto). Clique de novo para tirar.",
                    back=self.show_vocacao)

        top = ctk.CTkFrame(page, fg_color="transparent")
        top.pack(fill="x", pady=(14, 6))
        self.bar_seg = segmented(top, ["Barra 1", "Barra 2"], command=self.pick_bar)
        self.bar_seg.set("Barra %d" % (self.cur_bar + 1))
        self.bar_seg.pack(side="left")
        ctk.CTkLabel(top, text="Orientação:", font=F(12), text_color=DIM
                     ).pack(side="left", padx=(16, 6))
        self.orient_seg = segmented(top, ["Horizontal", "Vertical"], command=self.set_orient)
        self.orient_seg.pack(side="left")
        ghost_button(top, "Separar: Ataque na barra 1, resto na barra 2", self.auto_split,
                     width=300).pack(side="right")

        bar2 = ctk.CTkFrame(page, fg_color="transparent")
        bar2.pack(fill="x", pady=(0, 8))
        self.filter = segmented(bar2, ["Todas", "Ataque", "Cura", "Suporte"],
                                command=lambda _v: self.layout_cards())
        self.filter.set("Todas")
        self.filter.pack(side="left")
        self.count_lbl = ctk.CTkLabel(bar2, text="", font=F(13), text_color=DIM)
        self.count_lbl.pack(side="right")

        self.scroll = ctk.CTkScrollableFrame(page, fg_color=CARD, corner_radius=12)
        self.scroll.pack(fill="both", expand=True)
        for c in range(6):
            self.scroll.grid_columnconfigure(c, weight=1)
        self.cards = {}
        for m in voc["magias"]:
            self.cards[m["slug"]] = self._magia_card(m)
        self.layout_cards()

        foot = ctk.CTkFrame(page, fg_color="transparent")
        foot.pack(fill="x", pady=(14, 0))
        self.only_sw = ctk.CTkSwitch(
            foot, text="Só buffs (esconder as barras de skills)", font=F(12),
            progress_color=ACCENT, command=self.refresh_selection)
        if self.only_buffs:
            self.only_sw.select()
        self.only_sw.pack(side="left")
        self.next_btn = accent_button(foot, "Próximo: achar na tela  →", self.show_localizar,
                                      width=220)
        self.next_btn.pack(side="right")
        self.pick_bar(self.bar_seg.get())

        missing = [m for m in voc["magias"] if not wiki.has_icon(voc["slug"], m)]
        if missing:
            self.count_lbl.configure(text="Baixando ícones da wiki...")
            wiki.download_icons_async(
                voc["slug"], missing,
                on_each=lambda m, _p: self.after(0, self._icon_ready, m),
                on_done=lambda f: self.after(0, self._icons_done, f))

    def _magia_card(self, m):
        card = ctk.CTkFrame(self.scroll, width=138, height=132, fg_color=BG, corner_radius=10,
                            border_width=2, border_color=BORDER)
        card.grid_propagate(False)
        card.pack_propagate(False)
        img = load_icon(self.voc["slug"], m)
        if img is not None:
            self.images[m["slug"]] = img
        icon = ctk.CTkLabel(card, text="", image=cimg(img or NONE_ICON, (44, 44)))
        icon.pack(pady=(12, 4))
        ctk.CTkLabel(card, text=m["nome"], font=F(12, "bold"), text_color=TEXT,
                     wraplength=124).pack()
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(pady=(2, 0))
        ctk.CTkLabel(info, text=" %s " % m["tipo"], font=F(10), corner_radius=6,
                     fg_color=TIPO_COR.get(m["tipo"], BORDER), text_color=TEXT,
                     height=18).pack(side="left", padx=2)
        if m["nivel"]:
            ctk.CTkLabel(info, text="Nv %d" % m["nivel"], font=F(10),
                         text_color=DIM).pack(side="left", padx=2)
        badge = ctk.CTkLabel(card, text="", width=34, height=24, corner_radius=12,
                             fg_color=ACCENT, text_color="white", font=F(11, "bold"))
        card.icon, card.badge = icon, badge
        bind_tree(card, "<Button-1>", lambda _e, s=m["slug"]: self.toggle(s))
        bind_tree(card, "<Enter>", lambda _e, c=card: c.configure(cursor="hand2"))
        return card

    def _icon_ready(self, m):
        img = load_icon(self.voc["slug"], m)
        card = self.cards.get(m["slug"]) if hasattr(self, "cards") else None
        if img is not None and card is not None and card.winfo_exists():
            self.images[m["slug"]] = img
            card.icon.configure(image=cimg(img, (44, 44)))

    def _icons_done(self, fails):
        if fails and self.count_lbl.winfo_exists():
            self.count_lbl.configure(
                text="%d ícones não baixaram (sem internet?). Dá para continuar." % fails,
                text_color=WARN)

    def layout_cards(self):
        tipo = self.filter.get()
        for card in self.cards.values():
            card.grid_forget()
        i = 0
        for m in self.voc["magias"]:
            if tipo != "Todas" and m["tipo"] != tipo:
                continue
            self.cards[m["slug"]].grid(row=i // 6, column=i % 6, padx=6, pady=6)
            i += 1

    def pick_bar(self, value):
        self.cur_bar = 1 if value == "Barra 2" else 0
        self.orient_seg.set("Vertical" if self.orient[self.cur_bar] == "vertical"
                            else "Horizontal")
        self.refresh_selection()

    def set_orient(self, value):
        self.orient[self.cur_bar] = "vertical" if value == "Vertical" else "horizontal"

    def toggle(self, slug):
        cur, other = self.sel[self.cur_bar], self.sel[1 - self.cur_bar]
        if slug in cur:
            cur.remove(slug)
        else:
            if slug in other:
                other.remove(slug)      # passa para a barra atual
            cur.append(slug)
        self.refresh_selection()

    def auto_split(self):
        by = {m["slug"]: m for m in self.voc["magias"]}
        allsel = [s for s in self.sel[0] + self.sel[1] if s in by]
        self.sel[0] = [s for s in allsel if by[s]["tipo"] == "Ataque"]
        self.sel[1] = [s for s in allsel if by[s]["tipo"] != "Ataque"]
        self.refresh_selection()

    def refresh_selection(self):
        if not hasattr(self, "cards"):
            return
        self.sel = [[s for s in bar if s in self.cards] for bar in self.sel]
        for slug, card in self.cards.items():
            where = next((i for i, bar in enumerate(self.sel) if slug in bar), None)
            if where is None:
                card.configure(border_color=BORDER, fg_color=BG)
                card.badge.place_forget()
                continue
            color = BAR_COLORS[where]
            card.configure(border_color=color,
                           fg_color=CARD_HOVER if where == self.cur_bar else BG)
            card.badge.configure(fg_color=color,
                                 text="%d·%d" % (where + 1, self.sel[where].index(slug) + 1))
            card.badge.place(x=6, y=6)
        n1, n2 = len(self.sel[0]), len(self.sel[1])
        self.only_buffs = bool(self.only_sw.get()) if hasattr(self, "only_sw") else \
            self.only_buffs
        if hasattr(self, "next_btn"):
            ok = (n1 + n2) > 0 or self.only_buffs
            self.next_btn.configure(state="normal" if ok else "disabled",
                                    fg_color=ACCENT if ok else BORDER)
            self.next_btn.configure(text="Próximo: achar na tela  →" if n1 + n2
                                    else "Concluir  ✓")
        self.count_lbl.configure(text="Barra 1: %d   ·   Barra 2: %d" % (n1, n2),
                                 text_color=DIM)

    # -- 3) localizar e confirmar --
    def chosen(self):
        """[(indice_da_barra, magia)] na ordem: barra 1, depois barra 2."""
        by = {m["slug"]: m for m in self.voc["magias"]}
        return [(i, by[s]) for i, bar in enumerate(self.sel) for s in bar if s in by]

    def show_localizar(self):
        if not self.chosen():          # so buffs, sem magias: nada para achar
            self.results = []
            self.finish()
            return
        page = ctk.CTkFrame(self, fg_color="transparent")
        self.set_page(page)
        self.header(page, "Achar as magias na tela",
                    "Deixe o jogo aberto, com a barra lateral de skills visível. O programa "
                    "procura sozinho onde cada magia está.", back=self.show_magias)
        self.loc_body = ctk.CTkFrame(page, fg_color="transparent")
        self.loc_body.pack(fill="both", expand=True, pady=(16, 0))
        self.loc_foot = ctk.CTkFrame(page, fg_color="transparent")
        self.loc_foot.pack(fill="x", pady=(14, 0))
        self.results = None
        if self.app.cfg.get("sidebar_area"):
            self.after(200, self.run_locate)
        else:
            self.ask_sidebar()

    def clear_loc(self):
        for w in self.loc_body.winfo_children() + self.loc_foot.winfo_children():
            w.destroy()

    def ask_sidebar(self):
        self.clear_loc()
        box = ctk.CTkFrame(self.loc_body, fg_color=CARD, corner_radius=12)
        box.pack(expand=True, ipadx=30, ipady=24)
        ctk.CTkLabel(box, text="Marque a barra lateral de skills do jogo", font=F(18, "bold"),
                     text_color=TEXT).pack(pady=(10, 6))
        ctk.CTkLabel(box, justify="left", font=F(13), text_color=DIM, text=(
            "1. Deixe o jogo visível, com a barra de skills da esquerda aparecendo.\n"
            "2. Clique no botão abaixo: a tela congela.\n"
            "3. Arraste um retângulo cobrindo a coluna inteira de skills (de cima a baixo).\n"
            "4. Aperte Enter.\n\nIsso é feito uma vez só.")).pack(padx=20)
        accent_button(box, "Marcar a barra lateral", self.mark_sidebar,
                      width=240).pack(pady=(18, 6))

    def mark_sidebar(self):
        rect, _crop = self.run_hidden(
            self.app.pick_rect,
            "BARRA LATERAL DE SKILLS\nArraste um retangulo cobrindo a COLUNA INTEIRA de "
            "skills do jogo (de cima a baixo).\nEnter: confirmar.   Esc: cancelar.")
        if rect:
            self.app.cfg["sidebar_area"] = rect
            self.app.save()
            self.run_locate()

    def run_locate(self):
        self.clear_loc()
        ctk.CTkLabel(self.loc_body, text="Procurando as magias na tela...", font=F(16),
                     text_color=DIM).pack(expand=True)
        self.update()
        chosen = self.chosen()
        icons = [self.images.get(m["slug"]) or load_icon(self.voc["slug"], m)
                 for _b, m in chosen]
        area = self.app.cfg["sidebar_area"]
        shot = self.run_hidden(self.app.grab, area)
        ax, ay = area[0], area[1]
        found = [None] * len(chosen)
        have = [i for i, ic in enumerate(icons) if ic is not None]
        self.scale = 1.0
        if have:
            self.scale, res = localizar.locate(shot, [icons[i] for i in have])
            for i, r in zip(have, res):
                found[i] = r
        self.results = []
        for (bar, m), icon, r in zip(chosen, icons, found):
            item = {"bar": bar, "magia": m, "icon": icon, "shot": None, "region": None,
                    "status": "nao_achou", "removed": False}
            if r is not None and r["status"] != "nao_achou":
                x, y, w, h = r["box"]
                item["region"] = [ax + x, ay + y, w, h]
                item["shot"] = shot.crop((x, y, x + w, y + h))
                item["status"] = r["status"]
            self.results.append(item)
        self.show_confirm()

    def show_confirm(self):
        self.clear_loc()
        n_ok = sum(1 for it in self.results if it["status"] == "ok")
        ctk.CTkLabel(self.loc_body, anchor="w", font=F(13), text_color=DIM, text=(
            "Encontrei %d de %d. Confira se o ícone da wiki (esquerda) é o mesmo da tela "
            "(direita). Se algum estiver errado ou faltando, use \"Marcar\"."
            % (n_ok, len(self.results)))).pack(fill="x", pady=(0, 8))
        rows = ctk.CTkScrollableFrame(self.loc_body, fg_color=CARD, corner_radius=12)
        rows.pack(fill="both", expand=True)
        for i, it in enumerate(self.results):
            self._confirm_row(rows, i, it)

        ghost_button(self.loc_foot, "Marcar a barra lateral de novo", self.ask_sidebar,
                     width=230).pack(side="left")
        ghost_button(self.loc_foot, "Procurar de novo", self.run_locate,
                     width=150).pack(side="left", padx=8)
        ready = all(it["removed"] or it["status"] in ("ok", "manual", "aceito")
                    for it in self.results) and (
            any(not it["removed"] for it in self.results) or self.only_buffs)
        btn = accent_button(self.loc_foot, "Concluir  ✓", self.finish, width=160)
        btn.pack(side="right")
        if not ready:
            btn.configure(state="disabled", fg_color=BORDER)
            ctk.CTkLabel(self.loc_foot, text="Resolva os itens em amarelo/vermelho",
                         font=F(12), text_color=WARN).pack(side="right", padx=12)

    def _confirm_row(self, parent, i, it):
        row = ctk.CTkFrame(parent, fg_color=BG, corner_radius=10)
        row.pack(fill="x", padx=6, pady=4)
        dim = it["removed"]
        ctk.CTkLabel(row, text="B%d" % (it["bar"] + 1), width=34, height=22, corner_radius=8,
                     fg_color=BAR_COLORS[it["bar"]], text_color="white",
                     font=F(11, "bold")).pack(side="left", padx=(10, 6))
        ctk.CTkLabel(row, text="", image=cimg(it["icon"] or NONE_ICON, (40, 40))
                     ).pack(side="left", padx=4, pady=6)
        ctk.CTkLabel(row, text="→", font=F(16), text_color=DIM).pack(side="left", padx=4)
        ctk.CTkLabel(row, text="", image=cimg(it["shot"] or NONE_ICON, (40, 40))
                     ).pack(side="left", padx=4)
        ctk.CTkLabel(row, text=it["magia"]["nome"], font=F(14, "bold"),
                     text_color=DIM if dim else TEXT, width=190, anchor="w"
                     ).pack(side="left", padx=12)
        status = {
            "ok": ("✓ Encontrada", OK), "manual": ("✓ Marcada por você", OK),
            "aceito": ("✓ Confirmada", OK), "duvida": ("⚠ Confira: é a mesma?", WARN),
            "nao_achou": ("✗ Não encontrada", ERR)}[it["status"]]
        if dim:
            status = ("Fora da barra", DIM)
        ctk.CTkLabel(row, text=status[0], font=F(12, "bold"), text_color=status[1],
                     width=170, anchor="w").pack(side="left")
        btns = ctk.CTkFrame(row, fg_color="transparent")
        btns.pack(side="right", padx=8)
        if dim:
            ghost_button(btns, "Pôr de volta", lambda: self._set(i, removed=False),
                         width=110).pack(side="right", padx=3)
            return
        ghost_button(btns, "Tirar da barra", lambda: self._set(i, removed=True),
                     width=110).pack(side="right", padx=3)
        ghost_button(btns, "Marcar", lambda: self.mark_manual(i),
                     width=80).pack(side="right", padx=3)
        if it["status"] == "duvida":
            accent_button(btns, "É a mesma", lambda: self._set(i, status="aceito"),
                          width=100, height=32).pack(side="right", padx=3)

    def _set(self, i, **kw):
        self.results[i].update(kw)
        self.show_confirm()

    def mark_manual(self, i):
        it = self.results[i]
        size = round(44 * self.scale)
        rect, crop = self.run_hidden(
            self.app.pick_rect,
            "MARCAR: %s\nClique no CENTRO do icone dessa magia na barra lateral\n"
            "(ou arraste um retangulo sobre ele).   Enter: confirmar.   Esc: cancelar."
            % it["magia"]["nome"].upper(), (size, size))
        if rect:
            it.update(region=rect, shot=crop, status="manual")
        self.show_confirm()

    def finish(self):
        bars = []
        for b in range(config.MAX_BARS):
            items = [it for it in self.results if it["bar"] == b and not it["removed"]]
            bars.append({"magias": [it["magia"]["slug"] for it in items],
                         "regions": [it["region"] for it in items],
                         "orientation": self.orient[b]})
        self.app.finish_wizard(self.voc["slug"], bars, self.only_buffs)
        self.finished = True
        self.show_done()

    def show_done(self):
        page = ctk.CTkFrame(self, fg_color="transparent")
        self.set_page(page)
        box = ctk.CTkFrame(page, fg_color=CARD, corner_radius=14)
        box.pack(expand=True, ipadx=40, ipady=26)
        ctk.CTkLabel(box, text="Pronto!", font=F(28, "bold"), text_color=TEXT).pack(pady=(8, 4))
        tips = ("• Os buffs aparecem numa janelinha, que você pode arrastar.\n"
                if self.only_buffs else
                "• As barras já estão na tela. Arraste cada uma com o botão esquerdo.\n"
                "• Roda do mouse sobre a barra: zoom.   Botão direito: configurações.\n")
        tips += ("• Buffs (Ira, Vampirismo...): com o buff ativo no jogo, aperte Ctrl+Alt+F12.\n"
                 "  Na primeira vez, marque a área onde os buffs aparecem (todas as linhas).")
        ctk.CTkLabel(box, justify="left", font=F(14), text_color=DIM, text=tips
                     ).pack(padx=24, pady=8)
        sc = ctk.CTkFrame(box, fg_color="transparent")
        sc.pack(pady=(6, 0))
        lbl = ctk.CTkLabel(box, text="", font=F(11), text_color=DIM)
        ghost_button(sc, "Criar atalho na Área de Trabalho e no Menu Iniciar",
                     lambda: shortcut_feedback(self.app, lbl), width=340).pack()
        lbl.pack()
        accent_button(box, "Fechar", self.close, width=160).pack(pady=(14, 4))


# --------------------------------------------------------------------------
# Editor de buff
# --------------------------------------------------------------------------
class BuffEditor(Window):
    """Modal. run() devolve {name, duration, desc, skill, restart_on_cast} ou None."""

    def __init__(self, app, icon, buff=None):
        super().__init__(app, "Buff", (580, 560))
        self.result = None
        self.slots = app.skill_slots()      # [(nome, imagem PIL, magia_ou_None)]
        frm = ctk.CTkFrame(self, fg_color="transparent")
        frm.pack(fill="both", expand=True, padx=22, pady=18)

        top = ctk.CTkFrame(frm, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text="", image=cimg(icon, (icon.width * 4, icon.height * 4))
                     ).pack(side="left", padx=(0, 16))
        fields = ctk.CTkFrame(top, fg_color="transparent")
        fields.pack(side="left", fill="x", expand=True)
        self.name = self._entry(fields, "Nome")
        self.dur = self._entry(fields, "Duração do buff em segundos (0 = sem contagem)")
        self.desc = self._entry(fields, "Descrição (opcional)")

        ctk.CTkLabel(frm, text="Mostrar junto de qual skill?", font=F(13, "bold"),
                     text_color=TEXT, anchor="w").pack(fill="x", pady=(16, 4))
        cur = buff.get("skill") if buff else None
        self.skill = ctk.IntVar(value=cur if isinstance(cur, int)
                                and 0 <= cur < len(self.slots) else -1)
        grid = ctk.CTkScrollableFrame(frm, fg_color=CARD, corner_radius=10, height=150,
                                      orientation="horizontal")
        grid.pack(fill="x")
        self.skill_btns = []
        none = ctk.CTkButton(grid, text="Nenhuma\n(janelinha)", width=90, height=86,
                             font=F(11), command=lambda: self.pick_skill(-1))
        none.pack(side="left", padx=4, pady=6)
        self.skill_btns.append((-1, none))
        for i, (label, img, _m) in enumerate(self.slots):
            b = ctk.CTkButton(grid, text=label, image=cimg(img, (40, 40)), compound="top",
                              width=104, height=86, font=F(10),
                              command=lambda i=i: self.pick_skill(i))
            b.pack(side="left", padx=4, pady=6)
            self.skill_btns.append((i, b))

        self.restart = ctk.CTkSwitch(
            frm, text="Reiniciar o tempo quando eu usar a skill de novo",
            font=F(12), progress_color=ACCENT)
        self.restart.pack(anchor="w", pady=(14, 0))
        if not buff or buff.get("restart_on_cast", True):
            self.restart.select()

        self.err = ctk.CTkLabel(frm, text="", text_color=ERR, font=F(12))
        self.err.pack(anchor="w", pady=(6, 0))
        foot = ctk.CTkFrame(frm, fg_color="transparent")
        foot.pack(fill="x", side="bottom")
        accent_button(foot, "Salvar", self.save, width=120).pack(side="right")
        ghost_button(foot, "Cancelar", self.destroy, width=100).pack(side="right", padx=8)

        if buff:
            self.name.insert(0, buff.get("name", ""))
            self.dur.insert(0, "%g" % buff.get("duration", 0))
            self.desc.insert(0, buff.get("desc", ""))
        self.pick_skill(self.skill.get(), fill=not buff)
        self.bind("<Return>", lambda e: self.save())
        self.bind("<Escape>", lambda e: self.destroy())

    def _entry(self, parent, label):
        ctk.CTkLabel(parent, text=label, font=F(12), text_color=DIM, anchor="w"
                     ).pack(fill="x")
        e = ctk.CTkEntry(parent, font=F(13), height=32)
        e.pack(fill="x", pady=(0, 6))
        return e

    def pick_skill(self, idx, fill=True):
        self.skill.set(idx)
        for i, b in self.skill_btns:
            b.configure(fg_color=ACCENT if i == idx else CARD_HOVER,
                        hover_color=ACCENT_HOVER if i == idx else BORDER)
        if fill and idx >= 0 and self.slots[idx][2] is not None \
                and not self.name.get().strip():
            self.name.insert(0, self.slots[idx][2]["nome"])

    def save(self):
        text = self.dur.get().replace(",", ".").strip()
        try:
            duration = float(text)
            if duration < 0:
                raise ValueError
        except ValueError:
            self.err.configure(text="Informe a duração do buff em segundos (ex.: 90). "
                                    "A wiki mostra a recarga, não a duração.")
            return
        idx = self.skill.get()
        self.result = {"name": self.name.get().strip() or "Buff", "duration": duration,
                       "desc": self.desc.get().strip(),
                       "skill": idx if idx >= 0 else None,
                       "restart_on_cast": bool(self.restart.get())}
        self.destroy()

    def run(self):
        self.after(300, self.grab_set)
        self.wait_window()
        return self.result


# --------------------------------------------------------------------------
# Configuracoes
# --------------------------------------------------------------------------
class Settings(Window):
    TABS = ("Personagem", "Barras", "Buffs", "Jogo", "Sobre")

    def __init__(self, app, tab="Personagem"):
        super().__init__(app, "Barra de Skills - Configurações", (640, 680))
        self.tabs = ctk.CTkTabview(self, fg_color=CARD, segmented_button_selected_color=ACCENT,
                                   segmented_button_selected_hover_color=ACCENT_HOVER)
        self.tabs.pack(fill="both", expand=True, padx=16, pady=(10, 0))
        for name in self.TABS:
            self.tabs.add(name)
        self.build_personagem(self.tabs.tab("Personagem"))
        self.build_barras(self.tabs.tab("Barras"))
        self.build_buffs(self.tabs.tab("Buffs"))
        self.build_jogo(self.tabs.tab("Jogo"))
        self.build_sobre(self.tabs.tab("Sobre"))
        self.tabs.set(tab)
        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.pack(fill="x", padx=16, pady=12)
        ctk.CTkButton(foot, text="Sair do programa", command=app.quit, fg_color="transparent",
                      border_width=1, border_color=ERR, text_color=ERR, hover_color="#3a1515",
                      font=F(12), width=140).pack(side="left")
        accent_button(foot, "Fechar", self.destroy, width=110).pack(side="right")

    def reopen(self, tab):
        """Recria a janela (ex.: depois de trocar de personagem)."""
        app = self.app
        self.destroy()
        app.settings = Settings(app, tab)

    # -- Personagem --
    def build_personagem(self, tab):
        cfg = self.app.cfg
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=(4, 10))
        box = ctk.CTkFrame(row, fg_color="transparent")
        box.pack(side="left")
        ctk.CTkLabel(box, text="Jogando com", font=F(12), text_color=DIM, anchor="w"
                     ).pack(fill="x")
        ctk.CTkLabel(box, text=cfg.get("profile") or "—", font=F(20, "bold"),
                     text_color=TEXT, anchor="w").pack(fill="x")
        n = len(cfg["profiles"])
        accent_button(row, "Trocar personagem (%d salvo%s)" % (n, "" if n == 1 else "s"),
                      self.app.open_wizard, width=240).pack(side="right")

        btns = ctk.CTkFrame(tab, fg_color="transparent")
        btns.pack(fill="x")
        ghost_button(btns, "+ Novo personagem", self.new_profile
                     ).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ghost_button(btns, "Renomear", self.rename).pack(side="left", fill="x", expand=True,
                                                          padx=4)
        ghost_button(btns, "Apagar", self.delete).pack(side="left", fill="x", expand=True,
                                                        padx=(4, 0))

        voc = wiki.find_vocacao(wiki.load_vocacoes(), cfg.get("vocacao") or "")
        card = ctk.CTkFrame(tab, fg_color=BG, corner_radius=10)
        card.pack(fill="x", pady=14)
        art = load_art(voc) if voc else None
        if art:
            ctk.CTkLabel(card, text="", image=cimg(art, fit(art, (70, 90)))
                         ).pack(side="left", padx=12, pady=10)
        bars = [b for b in cfg["bars"] if b["regions"]]
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", padx=12, pady=12)
        ctk.CTkLabel(info, text="%s  ·  %s" % (cfg.get("profile") or "—",
                                              voc["nome"] if voc else "sem vocação"),
                     font=F(15, "bold"), text_color=TEXT, anchor="w").pack(fill="x")
        txt = ("   ".join("Barra %d: %d magias" % (i + 1, len(b["regions"]))
                          for i, b in enumerate(bars)) or "Nenhuma barra")
        if cfg.get("only_buffs"):
            txt += "   (só buffs)"
        ctk.CTkLabel(info, text=txt, font=F(12), text_color=DIM, anchor="w").pack(fill="x")
        ghost_button(card, "Trocar vocação/magias",
                     lambda: self.app.open_wizard(start_at="vocacao"),
                     width=190).pack(side="right", padx=10)

        sw = ctk.CTkSwitch(tab, text="Só buffs: esconder as barras de skills e mostrar só os "
                           "buffs numa janelinha", font=F(12), progress_color=ACCENT,
                           command=lambda: self.app.set_only_buffs(bool(sw.get())))
        if cfg.get("only_buffs"):
            sw.select()
        sw.pack(anchor="w", pady=(4, 0))

    def new_profile(self):
        name = ask_text(self, "Novo personagem", "Nome do personagem:")
        if not name:
            return
        if name in self.app.cfg["profiles"]:
            messagebox.showinfo("Personagem", "Esse nome já existe.", parent=self)
            return
        self.app.new_profile(name)
        self.app.open_wizard(start_at="vocacao")

    def rename(self):
        old = self.app.cfg["profile"]
        new = ask_text(self, "Renomear", "Novo nome para \"%s\":" % old)
        if new and not self.app.rename_profile(old, new):
            messagebox.showinfo("Personagem", "Nome inválido ou já usado.", parent=self)
        self.reopen("Personagem")

    def delete(self):
        name = self.app.cfg["profile"]
        if not messagebox.askyesno("Apagar personagem",
                                   "Apagar o personagem \"%s\" com as barras e buffs dele?"
                                   % name, parent=self):
            return
        self.app.delete_profile(name)
        if self.app.needs_wizard():
            self.app.open_wizard()
        else:
            self.reopen("Personagem")

    # -- Barras --
    def build_barras(self, tab):
        cfg = self.app.cfg
        for i, bar in enumerate(cfg["bars"]):
            if not bar["regions"]:
                continue
            row = ctk.CTkFrame(tab, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text="Barra %d (%d magias)" % (i + 1, len(bar["regions"])),
                         font=F(13), text_color=TEXT).pack(side="left")
            seg = segmented(row, ["Horizontal", "Vertical"],
                            command=lambda v, i=i: self.app.set_orientation(i, v.lower()))
            seg.set("Vertical" if bar.get("orientation") == "vertical" else "Horizontal")
            seg.pack(side="right")

        self._slider(tab, "Opacidade", "opacity", 0.2, 1.0, 0.05,
                     lambda v: "%d%%" % round(v * 100), on_change=self.app.set_opacity)
        self._slider(tab, "Zoom", "zoom", 0.5, 4.0, 0.1, lambda v: "%.1fx" % v)
        self._slider(tab, "Espaço entre ícones", "gap", 0, 20, 1, lambda v: "%d px" % v)
        self._slider(tab, "Atualizações por segundo", "fps", 5, 60, 1, lambda v: "%d" % v)

        self.ct_switch = ctk.CTkSwitch(
            tab, text="Click-through: cliques atravessam as barras  (Ctrl+Alt+F10)",
            font=F(12), progress_color=ACCENT,
            command=lambda: self.app.set_click_through(bool(self.ct_switch.get())))
        self.sync_click_through()
        self.ct_switch.pack(anchor="w", pady=(12, 6))
        ghost_button(tab, "Recalibrar a barra 1 manualmente (marcar cada ícone na tela)",
                     self.app.recalibrate).pack(fill="x", pady=(10, 0))

    def sync_click_through(self):
        if self.app.cfg.get("click_through"):
            self.ct_switch.select()
        else:
            self.ct_switch.deselect()

    def _slider(self, parent, label, key, lo, hi, step, fmt, on_change=None):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(row, text=label, font=F(13), text_color=TEXT).pack(side="left")
        val = ctk.CTkLabel(row, text=fmt(self.app.cfg[key]), font=F(13, "bold"),
                           text_color=TEXT, width=70, anchor="e")
        val.pack(side="right")
        steps = int(round((hi - lo) / step))
        s = ctk.CTkSlider(parent, from_=lo, to=hi, number_of_steps=steps,
                          button_color=ACCENT, button_hover_color=ACCENT_HOVER,
                          progress_color=ACCENT)
        s.set(self.app.cfg[key])

        def changed(v):
            v = round(v / step) * step
            v = float(v) if isinstance(step, float) else int(round(v))
            if on_change:
                on_change(v)
            else:
                self.app.cfg[key] = v
            val.configure(text=fmt(self.app.cfg[key]))

        s.configure(command=changed)
        s.bind("<ButtonRelease-1>", lambda e: self.app.save())
        s.pack(fill="x")

    # -- Buffs --
    def build_buffs(self, tab):
        ctk.CTkLabel(tab, justify="left", anchor="w", font=F(12), text_color=DIM,
                     wraplength=560, text=(
                         "Com o buff ATIVO no jogo, aperte Ctrl+Alt+F12 (ou o botão abaixo) "
                         "para cadastrar. Ele aparece junto da skill escolhida enquanto "
                         "estiver ativo; passe o mouse para ver o tempo.")).pack(fill="x")
        self.buff_rows = ctk.CTkScrollableFrame(tab, fg_color=BG, corner_radius=10, height=150)
        self.buff_rows.pack(fill="both", expand=True, pady=8)
        accent_button(tab, "+ Adicionar buff", self.app.add_buff).pack(fill="x")
        self._slider(tab, "Tamanho dos ícones de buff", "buff_zoom", 1.0, 5.0, 0.1,
                     lambda v: "%.1fx" % v)
        self._slider(tab, "Piscar quando faltar", "warn_seconds", 0, 30, 1,
                     lambda v: "%d s" % v if v else "nunca")
        snd = ctk.CTkFrame(tab, fg_color="transparent")
        snd.pack(fill="x", pady=(8, 0))
        sw = ctk.CTkSwitch(snd, text="Apito quando o buff começar a piscar", font=F(12),
                           progress_color=ACCENT,
                           command=lambda: self._set("warn_sound", bool(sw.get())))
        if self.app.cfg.get("warn_sound"):
            sw.select()
        sw.pack(side="left")
        ghost_button(snd, "Testar apito", self.app.beep, width=110).pack(side="right")
        area = ctk.CTkFrame(tab, fg_color="transparent")
        area.pack(fill="x", pady=(10, 0))
        self.area_lbl = ctk.CTkLabel(area, text="", font=F(12), text_color=DIM, anchor="w",
                                     justify="left", wraplength=360)
        self.area_lbl.pack(side="left")
        ghost_button(area, "Redefinir área dos buffs", self.app.redefine_area,
                     width=180).pack(side="right")
        self.refresh_buffs()

    def _set(self, key, value):
        self.app.cfg[key] = value
        self.app.save()

    def refresh_buffs(self):
        if not self.winfo_exists():
            return
        for w in self.buff_rows.winfo_children():
            w.destroy()
        names = [s[0] for s in self.app.skill_slots(images=False)]
        if not self.app.buffs:
            ctk.CTkLabel(self.buff_rows, text="Nenhum buff cadastrado para este personagem.",
                         font=F(12), text_color=DIM).pack(pady=20)
        for i, b in enumerate(self.app.buffs):
            row = ctk.CTkFrame(self.buff_rows, fg_color=CARD, corner_radius=8)
            row.pack(fill="x", padx=4, pady=3)
            img = b["img"]
            ctk.CTkLabel(row, text="", image=cimg(img, (img.width * 2, img.height * 2))
                         ).pack(side="left", padx=10, pady=6)
            s = b.get("skill")
            where = ("junto de %s" % names[s]) if isinstance(s, int) and s < len(names) \
                else "janelinha"
            dur = ("%g s" % b["duration"]) if b["duration"] else "sem contagem"
            box = ctk.CTkFrame(row, fg_color="transparent")
            box.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(box, text=b["name"], font=F(13, "bold"), text_color=TEXT,
                         anchor="w").pack(fill="x")
            ctk.CTkLabel(box, text="%s  ·  %s" % (dur, where), font=F(11), text_color=DIM,
                         anchor="w").pack(fill="x")
            ghost_button(row, "Remover", lambda i=i: self.app.remove_buff(i),
                         width=80, height=28).pack(side="right", padx=6)
            ghost_button(row, "Editar", lambda i=i: self.app.edit_buff(i),
                         width=70, height=28).pack(side="right")
        area = self.app.cfg.get("buff_area")
        self.area_lbl.configure(text=("Área dos buffs: %dx%d px" % (area[2], area[3])) if area
                                else "Área dos buffs: será pedida no primeiro cadastro")

    # -- Jogo --
    def build_jogo(self, tab):
        ctk.CTkLabel(tab, justify="left", anchor="w", font=F(12), text_color=DIM,
                     wraplength=560, text=(
                         "As barras podem aparecer só quando o jogo estiver em primeiro plano "
                         "(e sumir ao abrir o navegador, por exemplo).")).pack(fill="x")
        self.game_lbl = ctk.CTkLabel(tab, text=self.app.game_label_text(), font=F(14, "bold"),
                                     text_color=TEXT, anchor="w", justify="left",
                                     wraplength=560)
        self.game_lbl.pack(fill="x", pady=14)
        accent_button(tab, "Definir janela do jogo (clique nela em 3 s)",
                      lambda: self.app.capture_game_window(3, self.set_game_text)
                      ).pack(fill="x")
        ghost_button(tab, "Mostrar sempre (desativar)",
                     lambda: self.app.clear_game_window(self.set_game_text)
                     ).pack(fill="x", pady=8)

        track = ctk.CTkSwitch(
            tab, text="Acompanhar a janela do jogo: se ela mudar de lugar, as posições das "
            "skills e dos buffs se ajustam sozinhas", font=F(12), progress_color=ACCENT,
            command=lambda: self._set("track_game", bool(track.get())))
        if self.app.cfg.get("track_game", True):
            track.select()
        track.pack(anchor="w", pady=(14, 6))
        self.auto_sw = ctk.CTkSwitch(
            tab, text="Abrir com o Windows: fica no ícone perto do relógio e mostra a "
            "escolha de personagem quando o jogo abrir", font=F(12), progress_color=ACCENT,
            command=lambda: self.app.set_autostart(bool(self.auto_sw.get())))
        self.sync_autostart()
        self.auto_sw.pack(anchor="w", pady=6)
        sc = ctk.CTkFrame(tab, fg_color="transparent")
        sc.pack(fill="x", pady=(8, 0))
        ghost_button(sc, "Criar atalho na Área de Trabalho e no Menu Iniciar",
                     lambda: shortcut_feedback(self.app, self.shortcut_lbl)
                     ).pack(side="left")
        self.shortcut_lbl = ctk.CTkLabel(sc, text="", font=F(11), text_color=DIM)
        self.shortcut_lbl.pack(side="left", padx=10)
        ctk.CTkLabel(tab, justify="left", anchor="w", font=F(11), text_color=DIM,
                     wraplength=560, text=(
                         "Fechar as janelas não encerra o programa: ele continua no ícone "
                         "perto do relógio. Para sair, clique com o botão direito no ícone > "
                         "Sair, ou use \"Sair do programa\" aqui embaixo.")
                     ).pack(fill="x", pady=(10, 0))

    def sync_autostart(self):
        if sistema.autostart_enabled():
            self.auto_sw.select()
        else:
            self.auto_sw.deselect()

    def set_game_text(self, text):
        try:
            if self.winfo_exists():
                self.game_lbl.configure(text=text)
                return True
        except Exception:
            pass
        return False

    # -- Sobre --
    def build_sobre(self, tab):
        ctk.CTkLabel(tab, text="Barra de Skills %s" % VERSION, font=F(20, "bold"),
                     text_color=TEXT).pack(pady=(10, 2))
        ctk.CTkLabel(tab, text="Só lê a imagem da tela: não mexe na memória do jogo e não "
                     "envia cliques nem teclas.", font=F(12), text_color=DIM,
                     wraplength=540).pack()
        sc = ctk.CTkFrame(tab, fg_color=BG, corner_radius=10)
        sc.pack(fill="x", pady=16)
        for k, v in (("Arrastar", "mover a barra"), ("Roda do mouse", "zoom das barras"),
                     ("Botão direito", "configurações"), ("Ctrl+Alt+F10", "click-through"),
                     ("Ctrl+Alt+F11", "configurações"), ("Ctrl+Alt+F12", "cadastrar buff")):
            r = ctk.CTkFrame(sc, fg_color="transparent")
            r.pack(fill="x", padx=14, pady=3)
            ctk.CTkLabel(r, text=k, font=F(12, "bold"), text_color=TEXT, width=130,
                         anchor="w").pack(side="left")
            ctk.CTkLabel(r, text=v, font=F(12), text_color=DIM, anchor="w").pack(side="left")
        ghost_button(tab, "Abrir página do projeto no GitHub",
                     lambda: webbrowser.open(REPO_URL)).pack(fill="x")
        ctk.CTkLabel(tab, text="Dados e imagens das magias e vocações: Bloodpedia, projeto da "
                     "comunidade.\nBloodstone e suas imagens pertencem aos seus criadores.",
                     font=F(11), text_color=DIM).pack(pady=12)
