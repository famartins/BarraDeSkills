# -*- coding: utf-8 -*-
"""
Telas do programa (CustomTkinter, tema escuro):

- Assistente: vocacao -> magias (+ orientacao) -> localizacao automatica e
  confirmacao -> pronto.
- Configuracoes: abas Barra, Buffs, Jogo e Sobre.
- Editor de buff: nome, duracao, skill da barra e reinicio ao usar a skill.

As janelas que ficam por cima do jogo (barra e buffs) continuam em Tk puro no
skillbar.py, porque precisam de estilos especiais do Windows.
"""

import webbrowser

import customtkinter as ctk
from PIL import Image

import localizar
import wiki

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

VERSION = "2.0"
REPO_URL = "https://github.com/famartins/BarraDeSkills"

# cores
ACCENT = "#b3261e"
ACCENT_HOVER = "#8e1c16"
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


def accent_button(master, text, command, **kw):
    kw.setdefault("height", 36)
    return ctk.CTkButton(master, text=text, command=command, fg_color=ACCENT,
                         hover_color=ACCENT_HOVER, font=F(13, "bold"), **kw)


def ghost_button(master, text, command, **kw):
    kw.setdefault("height", 32)
    return ctk.CTkButton(master, text=text, command=command, fg_color="transparent",
                         border_width=1, border_color=BORDER, hover_color=CARD_HOVER,
                         text_color=TEXT, font=F(12), **kw)


def bind_tree(widget, event, func):
    """Liga o evento ao widget e a todos os filhos (para cards clicaveis)."""
    widget.bind(event, func, add="+")
    for child in widget.winfo_children():
        bind_tree(child, event, func)


def load_icon(voc_slug, magia):
    try:
        return Image.open(wiki.icon_path(voc_slug, magia)).convert("RGB")
    except OSError:
        return None


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
    def __init__(self, app):
        super().__init__(app, "Barra de Skills", (980, 680))
        self.vocacoes = wiki.load_vocacoes()
        self.voc = None
        self.selected = []          # slugs na ordem da barra
        self.orientation = app.cfg.get("orientation", "horizontal")
        self.images = {}            # slug -> PIL
        self.page = None
        self.finished = False
        self.protocol("WM_DELETE_WINDOW", self.close)
        if app.cfg.get("vocacao"):
            self.voc = wiki.find_vocacao(self.vocacoes, app.cfg["vocacao"])
            self.selected = list(app.cfg.get("magias") or [])
        self.show_vocacao()

    def close(self):
        self.destroy()
        self.app.wizard_closed(self.finished)

    def set_page(self, frame):
        if self.page is not None:
            self.page.destroy()
        self.page = frame
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
                     justify="left", wraplength=820).pack(fill="x")
        return top

    # -- 1) vocacao --
    def show_vocacao(self):
        page = ctk.CTkFrame(self, fg_color="transparent")
        self.set_page(page)
        self.header(page, "Escolha sua vocação",
                    "A barra vai mostrar as magias dela por cima do jogo, com recarga e nível "
                    "iguais aos do jogo. O programa só lê a imagem da tela.")
        if not self.vocacoes:
            ctk.CTkLabel(page, text="Não encontrei dados/vocacoes.json. Baixe o programa de novo.",
                         text_color=ERR, font=F(14)).pack(pady=40)
            return
        grid = ctk.CTkFrame(page, fg_color="transparent")
        grid.pack(expand=True)
        self.voc_icons = {}
        for i, voc in enumerate(self.vocacoes):
            card = ctk.CTkFrame(grid, width=168, height=210, fg_color=CARD, corner_radius=14,
                                border_width=2, border_color=BORDER)
            card.grid(row=0, column=i, padx=8, pady=10)
            card.grid_propagate(False)
            card.pack_propagate(False)
            icon = ctk.CTkLabel(card, text="", image=cimg(NONE_ICON, (72, 72)))
            icon.pack(pady=(30, 14))
            ctk.CTkLabel(card, text=voc["nome"], font=F(18, "bold"), text_color=TEXT).pack()
            ctk.CTkLabel(card, text="%d magias" % len(voc["magias"]), font=F(12),
                         text_color=DIM).pack()
            self.voc_icons[voc["slug"]] = icon

            def enter(_e, c=card):
                c.configure(border_color=ACCENT, fg_color=CARD_HOVER)

            def leave(_e, c=card):
                c.configure(border_color=BORDER, fg_color=CARD)

            bind_tree(card, "<Enter>", enter)
            bind_tree(card, "<Leave>", leave)
            bind_tree(card, "<Button-1>", lambda _e, v=voc: self.pick_vocacao(v))
            bind_tree(card, "<Enter>", lambda _e, c=card: c.configure(cursor="hand2"))

            # icone representativo: a magia de ataque de nivel mais alto
            rep = max((m for m in voc["magias"] if m["tipo"] == "Ataque"),
                      key=lambda m: m["nivel"], default=voc["magias"][0])
            wiki.download_icons_async(voc["slug"], [rep], on_done=lambda _f, s=voc["slug"], m=rep:
                                      self.after(0, self._set_voc_icon, s, m))

        foot = ctk.CTkFrame(page, fg_color="transparent")
        foot.pack(fill="x", side="bottom")
        if self.app.cfg.get("regions"):
            ghost_button(foot, "Pular: manter minha barra atual", self.skip,
                         width=240).pack(side="right")
        ctk.CTkLabel(foot, text="Dados e ícones: Bloodpedia (bloodpedia.vercel.app)",
                     font=F(11), text_color=DIM).pack(side="left")

    def _set_voc_icon(self, voc_slug, magia):
        img = load_icon(voc_slug, magia)
        lbl = self.voc_icons.get(voc_slug)
        if img is not None and lbl is not None and lbl.winfo_exists():
            lbl.configure(image=cimg(img, (72, 72)))

    def skip(self):
        self.app.skip_wizard()
        self.finished = True
        self.close()

    def pick_vocacao(self, voc):
        if self.voc is None or self.voc["slug"] != voc["slug"]:
            self.selected = []
        self.voc = voc
        self.show_magias()

    # -- 2) magias --
    def show_magias(self):
        voc = self.voc
        page = ctk.CTkFrame(self, fg_color="transparent")
        self.set_page(page)
        self.header(page, "Magias do %s" % voc["nome"],
                    "Clique nas magias que quer na barra. A ordem dos cliques é a ordem na "
                    "barra (o número no canto). Clique de novo para tirar.",
                    back=self.show_vocacao)

        bar = ctk.CTkFrame(page, fg_color="transparent")
        bar.pack(fill="x", pady=(16, 8))
        self.filter = ctk.CTkSegmentedButton(
            bar, values=["Todas", "Ataque", "Cura", "Suporte"], font=F(12),
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
            command=lambda _v: self.layout_cards())
        self.filter.set("Todas")
        self.filter.pack(side="left")
        self.count_lbl = ctk.CTkLabel(bar, text="", font=F(13), text_color=DIM)
        self.count_lbl.pack(side="right")

        self.scroll = ctk.CTkScrollableFrame(page, fg_color=CARD, corner_radius=12)
        self.scroll.pack(fill="both", expand=True)
        for c in range(6):
            self.scroll.grid_columnconfigure(c, weight=1)

        self.cards = {}
        for m in voc["magias"]:
            self.cards[m["slug"]] = self._magia_card(m)
        self.layout_cards()
        self.refresh_selection()

        foot = ctk.CTkFrame(page, fg_color="transparent")
        foot.pack(fill="x", pady=(14, 0))
        ctk.CTkLabel(foot, text="Barra:", font=F(13), text_color=TEXT).pack(side="left")
        self.orient = ctk.CTkSegmentedButton(
            foot, values=["Horizontal", "Vertical"], font=F(12),
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER)
        self.orient.set("Vertical" if self.orientation == "vertical" else "Horizontal")
        self.orient.pack(side="left", padx=10)
        self.next_btn = accent_button(foot, "Próximo: achar na tela  →", self.show_localizar,
                                      width=220)
        self.next_btn.pack(side="right")
        self.refresh_selection()

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
        badge = ctk.CTkLabel(card, text="", width=24, height=24, corner_radius=12,
                             fg_color=ACCENT, text_color="white", font=F(12, "bold"))
        card.icon, card.badge = icon, badge
        bind_tree(card, "<Button-1>", lambda _e, s=m["slug"]: self.toggle(s))
        bind_tree(card, "<Enter>", lambda _e, c=card: c.configure(cursor="hand2"))
        return card

    def _icon_ready(self, m):
        img = load_icon(self.voc["slug"], m)
        card = self.cards.get(m["slug"])
        if img is not None and card is not None and card.winfo_exists():
            self.images[m["slug"]] = img
            card.icon.configure(image=cimg(img, (44, 44)))

    def _icons_done(self, fails):
        if fails and self.count_lbl.winfo_exists():
            self.count_lbl.configure(
                text="%d ícones não baixaram (sem internet?). Dá para continuar." % fails,
                text_color=WARN)
        self.refresh_selection()

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

    def toggle(self, slug):
        if slug in self.selected:
            self.selected.remove(slug)
        else:
            self.selected.append(slug)
        self.refresh_selection()

    def refresh_selection(self):
        if not hasattr(self, "cards"):
            return
        self.selected = [s for s in self.selected if s in self.cards]
        for slug, card in self.cards.items():
            if slug in self.selected:
                card.configure(border_color=ACCENT, fg_color=CARD_HOVER)
                card.badge.configure(text=str(self.selected.index(slug) + 1))
                card.badge.place(x=6, y=6)
            else:
                card.configure(border_color=BORDER, fg_color=BG)
                card.badge.place_forget()
        n = len(self.selected)
        if hasattr(self, "next_btn"):
            self.next_btn.configure(state="normal" if n else "disabled")
            self.count_lbl.configure(text="%d selecionada%s" % (n, "" if n == 1 else "s"),
                                     text_color=DIM)

    # -- 3) localizar e confirmar --
    def magias_sel(self):
        by = {m["slug"]: m for m in self.voc["magias"]}
        return [by[s] for s in self.selected]

    def show_localizar(self):
        self.orientation = "vertical" if self.orient.get() == "Vertical" else "horizontal"
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

    def ask_sidebar(self):
        for w in self.loc_body.winfo_children() + self.loc_foot.winfo_children():
            w.destroy()
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
        for w in self.loc_body.winfo_children() + self.loc_foot.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.loc_body, text="Procurando as magias na tela...", font=F(16),
                     text_color=DIM).pack(expand=True)
        self.update()
        mags = self.magias_sel()
        icons = [self.images.get(m["slug"]) or load_icon(self.voc["slug"], m) for m in mags]
        area = self.app.cfg["sidebar_area"]
        shot = self.run_hidden(self.app.grab, area)
        ax, ay = area[0], area[1]
        found = [None] * len(mags)
        have = [i for i, ic in enumerate(icons) if ic is not None]
        self.scale = 1.0
        if have:
            self.scale, res = localizar.locate(shot, [icons[i] for i in have])
            for i, r in zip(have, res):
                found[i] = r
        self.results = []
        for m, icon, r in zip(mags, icons, found):
            item = {"magia": m, "icon": icon, "shot": None, "region": None,
                    "status": "nao_achou", "removed": False}
            if r is not None and r["status"] != "nao_achou":
                x, y, w, h = r["box"]
                item["region"] = [ax + x, ay + y, w, h]
                item["shot"] = shot.crop((x, y, x + w, y + h))
                item["status"] = r["status"]
            self.results.append(item)
        self.show_confirm()

    def show_confirm(self):
        for w in self.loc_body.winfo_children() + self.loc_foot.winfo_children():
            w.destroy()
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
                    for it in self.results) and any(not it["removed"] for it in self.results)
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
        ctk.CTkLabel(row, text=str(i + 1), width=28, font=F(14, "bold"),
                     text_color=DIM).pack(side="left", padx=(10, 4))
        ctk.CTkLabel(row, text="", image=cimg(it["icon"] or NONE_ICON, (40, 40))
                     ).pack(side="left", padx=4, pady=6)
        ctk.CTkLabel(row, text="→", font=F(16), text_color=DIM).pack(side="left", padx=4)
        ctk.CTkLabel(row, text="", image=cimg(it["shot"] or NONE_ICON, (40, 40))
                     ).pack(side="left", padx=4)
        ctk.CTkLabel(row, text=it["magia"]["nome"], font=F(14, "bold"),
                     text_color=DIM if dim else TEXT, width=200, anchor="w"
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
        items = [it for it in self.results if not it["removed"]]
        self.app.finish_wizard(self.voc["slug"], [it["magia"]["slug"] for it in items],
                               [it["region"] for it in items], self.orientation)
        self.finished = True
        self.show_done()

    def show_done(self):
        page = ctk.CTkFrame(self, fg_color="transparent")
        self.set_page(page)
        box = ctk.CTkFrame(page, fg_color=CARD, corner_radius=14)
        box.pack(expand=True, ipadx=40, ipady=26)
        ctk.CTkLabel(box, text="Pronto!", font=F(28, "bold"), text_color=TEXT).pack(pady=(8, 4))
        ctk.CTkLabel(box, justify="left", font=F(14), text_color=DIM, text=(
            "• A barra já está na tela. Arraste-a com o botão esquerdo para onde quiser.\n"
            "• Roda do mouse sobre a barra: zoom.   Botão direito: configurações.\n"
            "• Buffs (Ira, Vampirismo...): com o buff ativo no jogo, aperte Ctrl+Alt+F12.\n"
            "  Na primeira vez, marque a área onde os buffs aparecem (todas as linhas).")
        ).pack(padx=24, pady=8)
        accent_button(box, "Fechar", self.close, width=160).pack(pady=(14, 4))


# --------------------------------------------------------------------------
# Editor de buff
# --------------------------------------------------------------------------
class BuffEditor(Window):
    """Modal. run() devolve {name, duration, desc, skill, restart_on_cast} ou None."""

    def __init__(self, app, icon, buff=None):
        super().__init__(app, "Buff", (560, 560))
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
        self.dur = self._entry(fields, "Duração (segundos)  —  0 = sem contagem")
        self.desc = self._entry(fields, "Descrição (opcional)")

        ctk.CTkLabel(frm, text="Mostrar junto de qual skill da barra?", font=F(13, "bold"),
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
                              width=96, height=86, font=F(10),
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
        if not fill or idx < 0:
            return
        m = self.slots[idx][2]
        if m is None:
            return
        if not self.name.get().strip():
            self.name.insert(0, m["nome"])

    def save(self):
        try:
            duration = float(self.dur.get().replace(",", ".").strip() or 0)
            if duration < 0:
                raise ValueError
        except ValueError:
            self.err.configure(text="Duração inválida: use um número de segundos (ex.: 90).")
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
    def __init__(self, app):
        super().__init__(app, "Barra de Skills - Configurações", (620, 640))
        self.tabs = ctk.CTkTabview(self, fg_color=CARD, segmented_button_selected_color=ACCENT,
                                   segmented_button_selected_hover_color=ACCENT_HOVER)
        self.tabs.pack(fill="both", expand=True, padx=16, pady=(10, 0))
        for name in ("Barra", "Buffs", "Jogo", "Sobre"):
            self.tabs.add(name)
        self.build_barra(self.tabs.tab("Barra"))
        self.build_buffs(self.tabs.tab("Buffs"))
        self.build_jogo(self.tabs.tab("Jogo"))
        self.build_sobre(self.tabs.tab("Sobre"))
        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.pack(fill="x", padx=16, pady=12)
        ctk.CTkButton(foot, text="Sair do programa", command=app.quit, fg_color="transparent",
                      border_width=1, border_color=ERR, text_color=ERR, hover_color="#3a1515",
                      font=F(12), width=140).pack(side="left")
        accent_button(foot, "Fechar", self.destroy, width=110).pack(side="right")

    # -- Barra --
    def build_barra(self, tab):
        cfg = self.app.cfg
        voc = wiki.find_vocacao(wiki.load_vocacoes(), cfg.get("vocacao") or "")
        card = ctk.CTkFrame(tab, fg_color=BG, corner_radius=10)
        card.pack(fill="x", pady=(4, 10))
        txt = ("%s  ·  %d magias na barra" % (voc["nome"], len(cfg.get("regions") or []))
               if voc else "%d skills na barra" % len(cfg.get("regions") or []))
        ctk.CTkLabel(card, text=txt, font=F(14, "bold"), text_color=TEXT
                     ).pack(side="left", padx=14, pady=12)
        accent_button(card, "Trocar vocação/magias", self.app.open_wizard,
                      width=180, height=32).pack(side="right", padx=10)

        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text="Orientação", font=F(13), text_color=TEXT).pack(side="left")
        seg = ctk.CTkSegmentedButton(
            row, values=["Horizontal", "Vertical"], font=F(12), selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
            command=lambda v: self.app.set_orientation(v.lower()))
        seg.set("Vertical" if cfg.get("orientation") == "vertical" else "Horizontal")
        seg.pack(side="right")

        self._slider(tab, "Zoom", "zoom", 0.5, 4.0, 0.1, "%.1fx")
        self._slider(tab, "Espaço entre ícones", "gap", 0, 20, 1, "%d px")
        self._slider(tab, "Atualizações por segundo", "fps", 5, 60, 1, "%d")

        sw = ctk.CTkSwitch(tab, text="Click-through: cliques atravessam a barra  (Ctrl+Alt+F10)",
                           font=F(12), progress_color=ACCENT,
                           command=lambda: self.app.set_click_through(bool(sw.get())))
        if cfg.get("click_through"):
            sw.select()
        sw.pack(anchor="w", pady=(12, 6))
        self.ct_switch = sw
        ghost_button(tab, "Recalibrar manualmente (marcar cada ícone na tela)",
                     self.app.recalibrate).pack(fill="x", pady=(10, 0))

    def _slider(self, parent, label, key, lo, hi, step, fmt):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(row, text=label, font=F(13), text_color=TEXT).pack(side="left")
        val = ctk.CTkLabel(row, text=fmt % self.app.cfg[key], font=F(13, "bold"),
                           text_color=TEXT, width=60, anchor="e")
        val.pack(side="right")
        steps = int(round((hi - lo) / step))
        s = ctk.CTkSlider(parent, from_=lo, to=hi, number_of_steps=steps,
                          button_color=ACCENT, button_hover_color=ACCENT_HOVER,
                          progress_color=ACCENT)
        s.set(self.app.cfg[key])

        def changed(v):
            v = round(v / step) * step
            self.app.cfg[key] = float(v) if isinstance(step, float) else int(round(v))
            val.configure(text=fmt % self.app.cfg[key])

        s.configure(command=changed)
        s.bind("<ButtonRelease-1>", lambda e: self.app.save())
        s.pack(fill="x")

    # -- Buffs --
    def build_buffs(self, tab):
        ctk.CTkLabel(tab, justify="left", anchor="w", font=F(12), text_color=DIM,
                     wraplength=540, text=(
                         "Com o buff ATIVO no jogo, aperte Ctrl+Alt+F12 (ou o botão abaixo) "
                         "para cadastrar. Ele aparece em cima da skill escolhida enquanto "
                         "estiver ativo; passe o mouse para ver o tempo.")).pack(fill="x")
        self.buff_rows = ctk.CTkScrollableFrame(tab, fg_color=BG, corner_radius=10, height=200)
        self.buff_rows.pack(fill="both", expand=True, pady=8)
        accent_button(tab, "+ Adicionar buff", self.app.add_buff).pack(fill="x")
        self._slider(tab, "Tamanho dos ícones de buff", "buff_zoom", 1.0, 5.0, 0.1, "%.1fx")
        area = ctk.CTkFrame(tab, fg_color="transparent")
        area.pack(fill="x", pady=(10, 0))
        self.area_lbl = ctk.CTkLabel(area, text="", font=F(12), text_color=DIM, anchor="w",
                                     justify="left", wraplength=360)
        self.area_lbl.pack(side="left")
        ghost_button(area, "Redefinir área dos buffs", self.app.redefine_area,
                     width=180).pack(side="right")
        self.refresh_buffs()

    def refresh_buffs(self):
        if not self.winfo_exists():
            return
        for w in self.buff_rows.winfo_children():
            w.destroy()
        names = [s[0] for s in self.app.skill_slots(images=False)]
        if not self.app.buffs:
            ctk.CTkLabel(self.buff_rows, text="Nenhum buff cadastrado ainda.", font=F(12),
                         text_color=DIM).pack(pady=20)
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
                     wraplength=540, text=(
                         "A barra pode aparecer só quando o jogo estiver em primeiro plano "
                         "(e sumir ao abrir o navegador, por exemplo).")).pack(fill="x")
        self.game_lbl = ctk.CTkLabel(tab, text=self.app.game_label_text(), font=F(14, "bold"),
                                     text_color=TEXT, anchor="w", justify="left",
                                     wraplength=540)
        self.game_lbl.pack(fill="x", pady=14)
        accent_button(tab, "Definir janela do jogo (clique nela em 3 s)",
                      lambda: self.app.capture_game_window(3, self.set_game_text)
                      ).pack(fill="x")
        ghost_button(tab, "Mostrar sempre (desativar)",
                     lambda: self.app.clear_game_window(self.set_game_text)
                     ).pack(fill="x", pady=8)

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
                     wraplength=520).pack()
        sc = ctk.CTkFrame(tab, fg_color=BG, corner_radius=10)
        sc.pack(fill="x", pady=16)
        for k, v in (("Arrastar", "mover a barra"), ("Roda do mouse", "zoom da barra"),
                     ("Botão direito", "configurações"), ("Ctrl+Alt+F10", "click-through"),
                     ("Ctrl+Alt+F11", "configurações"), ("Ctrl+Alt+F12", "cadastrar buff")):
            r = ctk.CTkFrame(sc, fg_color="transparent")
            r.pack(fill="x", padx=14, pady=3)
            ctk.CTkLabel(r, text=k, font=F(12, "bold"), text_color=TEXT, width=130,
                         anchor="w").pack(side="left")
            ctk.CTkLabel(r, text=v, font=F(12), text_color=DIM, anchor="w").pack(side="left")
        ghost_button(tab, "Abrir página do projeto no GitHub",
                     lambda: webbrowser.open(REPO_URL)).pack(fill="x")
        ctk.CTkLabel(tab, text="Dados e ícones das magias: Bloodpedia, projeto da comunidade.\n"
                     "Bloodstone e suas imagens pertencem aos seus criadores.",
                     font=F(11), text_color=DIM).pack(pady=12)
