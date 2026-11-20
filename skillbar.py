#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Barra de Skills
===============
Copia, em tempo real, pedacos da tela (os icones das skills) e monta tudo
numa barra horizontal, sempre visivel por cima do jogo.

O programa so LE a imagem da tela. Nao mexe na memoria do jogo e nao envia
cliques nem teclas para ele.

Uso:
    python skillbar.py              inicia (no primeiro uso abre o assistente)
    python skillbar.py --calibrar   marca os icones manualmente
    python skillbar.py --monitor 2  usa o monitor 2 (1 = principal)
    python skillbar.py --janelas    lista as janelas abertas (programa e titulo)
    python skillbar.py --jogo X.exe barra so aparece com o programa X.exe ativo

Atalhos (funcionam mesmo com o foco no jogo):
    Ctrl+Alt+F10   liga/desliga o click-through (cliques atravessam a barra)
    Ctrl+Alt+F11   abre a janela de configuracoes
    Ctrl+Alt+F12   cadastra um buff (com o buff ativo na tela)

Buffs: os icones dos buffs que voce cadastrar aparecem junto da skill escolhida
e, passando o mouse, mostram nome e tempo restante (cronometro baseado na duracao
que voce informar, reiniciado quando voce usa a skill de novo).

Arquivos: telas.py (telas), wiki.py (dados das vocacoes), localizar.py (achar as
magias na tela), buffcore.py (reconhecimento e cronometro dos buffs).
"""

import argparse
import ctypes
import json
import os
import sys
import time
import unicodedata
from ctypes import wintypes

if sys.platform != "win32":
    print("Este programa foi feito para Windows.")
    sys.exit(1)

try:
    import tkinter as tk
    from tkinter import messagebox
    import mss
    import numpy as np
    from PIL import Image, ImageTk
    import telas
    import wiki
    from buffcore import (BuffTracker, CastDetector, buff_time_text, expand_buff_area,
                          find_template)
except ImportError as exc:
    print("Faltam bibliotecas:", exc)
    print("Rode:  pip install -r requirements.txt   (ou use o iniciar.bat)")
    input("Pressione Enter para sair...")
    sys.exit(1)


def _norm(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(text.lower().split())


def match_by_name(buff_name, magias):
    """Slug da magia cujo nome comeca com (ou contem) o nome do buff, se for unica.
    magias = {slug: nome}."""
    n = _norm(buff_name)
    if len(n) < 3:
        return None
    for test in (lambda m: m == n, lambda m: m.startswith(n), lambda m: n in m):
        hits = [s for s, nome in magias.items() if test(_norm(nome))]
        if len(hits) == 1:
            return hits[0]
    return None


def alive(window):
    """True se a janela existe e nao foi fechada."""
    try:
        return window is not None and bool(window.winfo_exists())
    except Exception:
        return False


# --------------------------------------------------------------------------
# Windows (ctypes)
# --------------------------------------------------------------------------
user32 = ctypes.windll.user32

user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long
user32.SetLayeredWindowAttributes.argtypes = [
    wintypes.HWND, wintypes.DWORD, ctypes.c_ubyte, wintypes.DWORD]
user32.SetLayeredWindowAttributes.restype = wintypes.BOOL
user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
LWA_COLORKEY = 0x1
LWA_ALPHA = 0x2
WDA_EXCLUDEFROMCAPTURE = 0x11
# Cor "invisivel" das janelinhas de buff: pixels exatamente desta cor ficam
# transparentes (e os cliques atravessam). COLORREF = 0x00BBGGRR.
KEY_COLOR = "#ff00fe"
KEY_COLORREF = 0x00FE00FF
HWND_TOPMOST = wintypes.HWND(-1)
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x0001, 0x0002, 0x0010
VK_CONTROL, VK_MENU, VK_F10, VK_F11, VK_F12 = 0x11, 0x12, 0x79, 0x7A, 0x7B


def enable_dpi_awareness():
    """Faz as coordenadas do programa serem em pixels reais da tela."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def get_hwnd(widget):
    return user32.GetAncestor(widget.winfo_id(), 2)  # GA_ROOT


def style_overlay(widget, exclude_capture=True, colorkey=None):
    """Janela que nao rouba o foco do jogo, sem item na barra de tarefas.
    colorkey: COLORREF que fica transparente (None = janela toda opaca)."""
    hwnd = get_hwnd(widget)
    ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ex |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_LAYERED
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
    if colorkey is None:
        user32.SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA)
    else:
        user32.SetLayeredWindowAttributes(hwnd, colorkey, 255, LWA_ALPHA | LWA_COLORKEY)
    if exclude_capture:
        user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)


def key_down(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


# --- identificacao de janelas (para mostrar a barra so quando o jogo esta ativo) ---
kernel32 = ctypes.windll.kernel32
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
BROWSERS = ("chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe", "vivaldi.exe")


def window_title(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value


def window_info(hwnd):
    """Retorna (pid, nome_do_exe) da janela."""
    pid = wintypes.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    exe = ""
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if handle:
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                exe = os.path.basename(buf.value)
        finally:
            kernel32.CloseHandle(handle)
    return pid.value, exe


def list_windows():
    """Lista (exe, titulo) das janelas visiveis."""
    found = []

    def callback(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            title = window_title(hwnd)
            if title.strip():
                found.append((window_info(hwnd)[1], title))
        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return found


# --------------------------------------------------------------------------
# Configuracao
# --------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "skillbar_config.json")

DEFAULTS = {
    "monitor": 1,              # monitor usado na calibracao (1 = principal)
    "regions": [],             # [[x, y, largura, altura], ...] em pixels da tela
    "zoom": 1.0,               # ampliacao da barra
    "gap": 4,                  # espaco entre os icones (px)
    "fps": 30,                 # atualizacoes por segundo
    "pos": None,               # posicao da barra [x, y]
    "click_through": False,    # cliques atravessam a barra
    "exclude_from_capture": True,  # a barra nao aparece na propria captura
    "bg": "#0b0b0b",           # cor de fundo da barra
    "game_process": "",        # ex.: "bloodstone.exe" - vazio = barra sempre visivel
    "game_title": "",          # trecho do titulo da janela do jogo (opcional)
    "buffs": [],               # [{"name","duration","desc","file","skill"}, ...]
                               # skill = indice (0 = 1a) da skill da barra acima da qual
                               # o buff aparece; None = janelinha separada
    "buff_area": None,         # [x, y, w, h] onde os icones de buff aparecem no jogo
    "buff_pos": None,          # posicao da janelinha de buffs (None = acima da barra)
    "buff_threshold": 14,      # tolerancia do reconhecimento (menor = mais exato)
    "orientation": "horizontal",  # "horizontal" ou "vertical"
    "vocacao": "",             # slug da vocacao escolhida no assistente
    "magias": [],              # slugs das magias, na ordem da barra
    "sidebar_area": None,      # [x, y, w, h] da barra lateral de skills do jogo
    "wizard_skipped": False,   # quem ja tinha barra e pulou o assistente
    "buff_zoom": 1.5,         # ampliacao extra dos icones de buff (eles sao pequenos)
}


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    tmp = CONFIG_PATH + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        os.replace(tmp, CONFIG_PATH)
    except OSError as exc:
        print("Nao consegui salvar a configuracao:", exc)


RESAMPLE = getattr(Image, "Resampling", Image).NEAREST


def grab_image(sct, box):
    shot = sct.grab(box)
    return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


# --------------------------------------------------------------------------
# Calibracao: tela congelada onde voce marca os icones
# --------------------------------------------------------------------------
class Calibrator:
    def __init__(self, root, monitor_index, message=None, single=False, click_size=None):
        self.root = root
        self.single = single      # True = marca um unico retangulo
        self.click_size = click_size  # (w, h): no modo single, um clique marca esse tamanho
        self.message = message
        with mss.mss() as sct:
            mons = sct.monitors
            idx = monitor_index if 0 < monitor_index < len(mons) else 1
            self.mon = dict(mons[idx])
            base = grab_image(sct, self.mon)

        self.base = base          # imagem original (sem escurecer), para recortes
        self.width, self.height = base.size
        dim = Image.blend(base, Image.new("RGB", base.size, "black"), 0.25)

        self.rects = []        # (x, y, w, h) relativos ao monitor
        self.result = None
        self.drag_start = None
        self.temp = None

        top = self.top = tk.Toplevel(root)
        top.overrideredirect(True)
        top.geometry("%dx%d+%d+%d" % (
            self.width, self.height, self.mon["left"], self.mon["top"]))
        top.attributes("-topmost", True)

        self.canvas = tk.Canvas(top, width=self.width, height=self.height,
                                highlightthickness=0, bd=0, cursor="crosshair")
        self.canvas.pack()
        self.photo = ImageTk.PhotoImage(dim)
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")

        self._build_banner()

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", lambda e: self.undo())
        for w in (top, self.canvas):
            w.bind("<Return>", lambda e: self.finish())
            w.bind("<Escape>", lambda e: self.cancel())
            w.bind("<BackSpace>", lambda e: self.undo())

    def _build_banner(self):
        bg = "#101820"
        bar = tk.Frame(self.canvas, bg=bg, padx=14, pady=10)
        msg = self.message or (
               "CALIBRACAO - marque as skills NA ORDEM em que quer na barra\n"
               "1a skill: ARRASTE um retangulo sobre o icone.   "
               "Demais: basta CLICAR no centro do icone (usa o mesmo tamanho).\n"
               "Botao direito ou Backspace: desfaz a ultima.   "
               "Enter: concluir.   Esc: cancelar.")
        tk.Label(bar, text=msg, bg=bg, fg="white", font=("Segoe UI", 11),
                 justify="center").pack()
        row = tk.Frame(bar, bg=bg)
        row.pack(pady=(8, 0))
        self.status = tk.Label(row, text="0 skills marcadas", bg=bg,
                               fg="#00ff66", font=("Segoe UI", 11, "bold"))
        self.status.pack(side="left", padx=(0, 16))
        tk.Button(row, text="Desfazer", command=self.undo).pack(side="left", padx=4)
        tk.Button(row, text="Concluir (Enter)", command=self.finish).pack(side="left", padx=4)
        tk.Button(row, text="Cancelar (Esc)", command=self.cancel).pack(side="left", padx=4)
        self.canvas.create_window(self.width // 2, 12, window=bar, anchor="n")

    # -- desenho --
    def redraw(self):
        self.canvas.delete("rect")
        for i, (x, y, w, h) in enumerate(self.rects, 1):
            self.canvas.create_rectangle(x, y, x + w, y + h, outline="#00ff66",
                                         width=2, tags="rect")
            self.canvas.create_text(x + 3, y + 1, text=str(i), anchor="nw",
                                    fill="#ffee00", font=("Segoe UI", 10, "bold"),
                                    tags="rect")
        if self.single:
            self.status.config(text="area marcada" if self.rects else "nada marcado")
        else:
            self.status.config(text="%d skills marcadas" % len(self.rects))

    # -- mouse --
    def on_press(self, e):
        self.drag_start = (e.x, e.y)
        self.temp = self.canvas.create_rectangle(
            e.x, e.y, e.x, e.y, outline="#00ff66", width=2, dash=(4, 3))

    def on_drag(self, e):
        if self.temp and self.drag_start:
            sx, sy = self.drag_start
            self.canvas.coords(self.temp, sx, sy, e.x, e.y)

    def on_release(self, e):
        if self.temp:
            self.canvas.delete(self.temp)
            self.temp = None
        if not self.drag_start:
            return
        sx, sy = self.drag_start
        self.drag_start = None
        x0, x1 = sorted((sx, e.x))
        y0, y1 = sorted((sy, e.y))
        w, h = x1 - x0, y1 - y0
        if w >= 8 and h >= 8:
            if self.single:
                self.rects = []
            self.rects.append((x0, y0, w, h))
        elif self.single and self.click_size:
            w, h = self.click_size
            x = max(0, min(self.width - w, e.x - w // 2))
            y = max(0, min(self.height - h, e.y - h // 2))
            self.rects = [(x, y, w, h)]
        elif self.rects and not self.single:
            w, h = self.rects[0][2], self.rects[0][3]
            x = max(0, min(self.width - w, e.x - w // 2))
            y = max(0, min(self.height - h, e.y - h // 2))
            self.rects.append((x, y, w, h))
        self.redraw()

    # -- acoes --
    def undo(self):
        if self.rects:
            self.rects.pop()
            self.redraw()

    def finish(self):
        if not self.rects:
            self.cancel()
            return
        ox, oy = self.mon["left"], self.mon["top"]
        self.result = [[ox + x, oy + y, w, h] for x, y, w, h in self.rects]
        self.top.destroy()

    def cancel(self):
        self.result = None
        self.top.destroy()

    def _focus(self):
        try:
            self.top.focus_force()
            self.canvas.focus_set()
        except tk.TclError:
            pass

    def run(self):
        self.top.after(150, self._focus)
        self.root.wait_window(self.top)
        return self.result


# --------------------------------------------------------------------------
# Buffs: janela com os buffs ativos e tooltip
# --------------------------------------------------------------------------
class BuffWindow:
    """Faixa acima da barra com os buffs ativos. Passe o mouse para ver o tempo.

    - Buff ligado a uma skill: aparece centralizado logo acima dela (o resto da faixa
      fica transparente) e acompanha a barra.
    - Buff sem skill: vai para a direita da barra (se houver buffs ligados) ou para a
      janelinha arrastavel de antes.
    """

    TIP_BG, TIP_BORDER = "#2a2118", "#6b5a48"

    def __init__(self, app):
        self.app = app
        bg = app.cfg["bg"]
        win = self.win = tk.Toplevel(app.root)
        win.withdraw()
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=bg)
        self.label = tk.Label(win, bd=0, highlightthickness=0, bg=bg)
        self.label.pack()
        self.label.bind("<Motion>", self.on_motion)
        self.label.bind("<Leave>", lambda e: self.set_hover(None))
        self.label.bind("<ButtonPress-1>", self.on_press)
        self.label.bind("<B1-Motion>", self.on_drag)
        self.label.bind("<ButtonRelease-1>", self.on_release)
        self.label.bind("<Button-3>", lambda e: app.open_settings())

        self.shown = False
        self.styled = False
        self.key = None
        self.slots = []      # (x0, x1, buff) em pixels da janela
        self.size = (0, 0)
        self.linked = False  # True = ha buff ligado a skill (faixa presa a barra)
        self.x_off = 0       # deslocamento da faixa em relacao a borda esquerda da barra
        self.photo = None
        self.hover = None
        self.drag = None
        self.tip = None
        self.tip_styled = False

    # -- exibicao --
    def show(self):
        if not self.shown:
            self.win.deiconify()
            self.win.update_idletasks()
            if not self.styled:
                style_overlay(self.win, self.app.cfg["exclude_from_capture"], KEY_COLORREF)
                self.styled = True
            self.shown = True

    def hide(self):
        if self.shown:
            self.win.withdraw()
            self.shown = False
        self.set_hover(None)

    def raise_topmost(self):
        if self.shown:
            user32.SetWindowPos(get_hwnd(self.win), HWND_TOPMOST, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)

    def update(self, active, visible, now):
        """active = lista de buffs ativos agora (na ordem de cadastro)."""
        if not visible or not active:
            self.hide()
            return
        cfg = self.app.cfg
        key = (tuple((b["file"], b.get("skill")) for b in active), float(cfg["zoom"]),
               float(cfg["buff_zoom"]), int(cfg["gap"]), tuple(self.app.slot_centers),
               self.app.bar_length, self.vertical())
        if key != self.key:
            self.rebuild(active, key)
        self.show()
        if self.linked or not cfg.get("buff_pos"):
            self.apply_geometry()   # acompanha a barra de skills
        if self.hover is not None:
            self.refresh_tip(now)

    def vertical(self):
        return self.app.cfg.get("orientation") == "vertical"

    def rebuild(self, active, key):
        """Monta a faixa. Trabalha num eixo "principal" (ao longo da barra: x na
        horizontal, y na vertical) e num eixo "cruzado" (para fora da barra)."""
        cfg = self.app.cfg
        vert = self.vertical()
        gap = int(cfg["gap"])
        pad = max(1, round(2 * float(cfg["zoom"])))   # moldura escura em volta de cada icone
        z = float(cfg["zoom"]) * float(cfg["buff_zoom"])
        centers = self.app.slot_centers
        scaled = []
        for b in active:
            w, h = b["img"].size
            sw, sh = max(1, round(w * z)), max(1, round(h * z))
            scaled.append((b["img"].resize((sw, sh), RESAMPLE) if (sw, sh) != (w, h)
                           else b["img"], b))

        def main_len(icon):
            return (icon.height if vert else icon.width) + 2 * pad

        groups, free = {}, []
        for icon, b in scaled:
            s = b.get("skill")
            if isinstance(s, int) and 0 <= s < len(centers):
                groups.setdefault(s, []).append((icon, b))
            else:
                free.append((icon, b))
        self.linked = bool(groups)

        place = []                           # (posicao no eixo principal, icone, buff)
        if self.linked:
            for s in sorted(groups):
                items = groups[s]
                tl = sum(main_len(i) for i, _ in items) + gap * (len(items) - 1)
                m = round(centers[s] - tl / 2)
                for icon, b in items:
                    place.append((m, icon, b))
                    m += main_len(icon) + gap
            m = self.app.bar_length + gap    # buffs sem skill: depois do fim da barra
        else:
            m = 0
        for icon, b in free:
            place.append((m, icon, b))
            m += main_len(icon) + gap

        min_m = min(p[0] for p in place)
        total_main = max(p[0] + main_len(p[1]) for p in place) - min_m
        total_cross = max((i.width if vert else i.height) for i, _ in scaled) + 2 * pad
        size = (total_cross, total_main) if vert else (total_main, total_cross)
        strip = Image.new("RGB", size, KEY_COLOR if self.linked else cfg["bg"])
        self.slots = []
        for m, icon, b in place:
            m -= min_m
            cw, ch = icon.width + 2 * pad, icon.height + 2 * pad
            # encostado no lado da barra: embaixo (horizontal) ou a direita (vertical)
            x, y = (total_cross - cw, m) if vert else (m, total_cross - ch)
            strip.paste(cfg["bg"], (x, y, x + cw, y + ch))
            strip.paste(icon, (x + pad, y + pad))
            self.slots.append((m, m + main_len(icon), b))
        self.x_off = min_m
        self.photo = ImageTk.PhotoImage(strip)
        self.label.configure(image=self.photo)
        self.size = strip.size
        self.key = key
        self.set_hover(None)
        self.apply_geometry()

    def apply_geometry(self):
        w, h = self.size
        if w <= 0:
            return
        root = self.app.root
        vs = self.app.sct.monitors[0]
        pos = self.app.cfg.get("buff_pos")
        if pos and not self.linked:
            x, y = pos
        elif self.vertical():
            # a esquerda da barra; se nao couber na tela, a direita
            x = root.winfo_x() - w - 2
            if x < vs["left"]:
                x = root.winfo_x() + root.winfo_width() + 2
            y = root.winfo_y() + self.x_off
        else:
            x = root.winfo_x() + self.x_off
            y = root.winfo_y() - h - (2 if self.linked else 6)
        x = max(vs["left"], min(x, vs["left"] + vs["width"] - w))
        y = max(vs["top"], min(y, vs["top"] + vs["height"] - h))
        self.win.geometry("%dx%d+%d+%d" % (w, h, x, y))

    # -- arrastar --
    def on_press(self, e):
        self.set_hover(None)
        if self.linked:
            return   # presa as skills: para mover, arraste a barra
        self.drag = (e.x_root - self.win.winfo_x(), e.y_root - self.win.winfo_y())

    def on_drag(self, e):
        if self.drag:
            self.win.geometry("+%d+%d" % (e.x_root - self.drag[0], e.y_root - self.drag[1]))

    def on_release(self, e):
        if self.drag:
            self.drag = None
            self.app.cfg["buff_pos"] = [self.win.winfo_x(), self.win.winfo_y()]
            save_config(self.app.cfg)

    # -- tooltip --
    def slot_at(self, m):
        for i, (m0, m1, _b) in enumerate(self.slots):
            if m0 <= m < m1:
                return i
        return None

    def on_motion(self, e):
        if not self.drag:
            self.set_hover(self.slot_at(e.y if self.vertical() else e.x))

    def set_hover(self, idx):
        self.hover = idx
        if idx is None:
            if self.tip is not None:
                self.tip.withdraw()
        else:
            self.refresh_tip(time.monotonic())

    def _ensure_tip(self):
        if self.tip is not None:
            return
        t = self.tip = tk.Toplevel(self.win)
        t.withdraw()
        t.overrideredirect(True)
        t.attributes("-topmost", True)
        t.configure(bg=self.TIP_BORDER)
        inner = tk.Frame(t, bg=self.TIP_BG, padx=9, pady=6)
        inner.pack(padx=1, pady=1)
        self.tip_name = tk.Label(inner, bg=self.TIP_BG, fg="#f2c75c", anchor="w",
                                 justify="left", font=("Segoe UI", 10, "bold"))
        self.tip_desc = tk.Label(inner, bg=self.TIP_BG, fg="#e8e0d4", anchor="w",
                                 justify="left", wraplength=280, font=("Segoe UI", 9))
        self.tip_time = tk.Label(inner, bg=self.TIP_BG, fg="#ff4d3d", anchor="w",
                                 justify="left", font=("Segoe UI", 9))
        self.tip_name.pack(anchor="w")
        self.tip_time.pack(anchor="w")

    def refresh_tip(self, now):
        if self.hover is None or self.hover >= len(self.slots):
            self.set_hover(None)
            return
        x0, _x1, b = self.slots[self.hover]
        self._ensure_tip()
        self.tip_name.config(text=b["name"])
        self.tip_time.config(text=buff_time_text(
            self.app.tracker.elapsed(b["file"], now), b["duration"]))
        self.tip_desc.pack_forget()
        if b["desc"]:
            self.tip_desc.config(text=b["desc"])
            self.tip_desc.pack(anchor="w", before=self.tip_time)
        self.tip.update_idletasks()
        tw, th = self.tip.winfo_reqwidth(), self.tip.winfo_reqheight()
        if self.vertical():
            x = self.win.winfo_x() - tw - 6
            if x < 0:
                x = self.win.winfo_x() + self.size[0] + 6
            y = self.win.winfo_y() + x0
        else:
            x = self.win.winfo_x() + x0
            y = self.win.winfo_y() - th - 6
            if y < 0:
                y = self.win.winfo_y() + self.size[1] + 6
        self.tip.geometry("+%d+%d" % (x, y))
        self.tip.deiconify()
        if not self.tip_styled:
            self.tip.update_idletasks()
            style_overlay(self.tip, self.app.cfg["exclude_from_capture"])
            self.tip_styled = True


# --------------------------------------------------------------------------
# Barra
# --------------------------------------------------------------------------
class SkillBar:
    def __init__(self, force_calibrate=False, monitor=None):
        self.cfg = load_config()
        if monitor:
            self.cfg["monitor"] = monitor
            save_config(self.cfg)
        self.force_calibrate = force_calibrate

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Barra de Skills")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=self.cfg["bg"])

        self.label = tk.Label(self.root, bd=0, highlightthickness=0,
                              bg=self.cfg["bg"])
        self.label.pack()
        self.label.bind("<ButtonPress-1>", self.on_press)
        self.label.bind("<B1-Motion>", self.on_motion)
        self.label.bind("<ButtonRelease-1>", self.on_release)
        self.label.bind("<Button-3>", lambda e: self.open_settings())
        self.label.bind("<MouseWheel>", self.on_wheel)

        self.sct = mss.mss()
        self.photo = None
        self.last_size = None
        self.slot_centers = []   # centro de cada skill no eixo da barra, em pixels
        self.bar_length = 0      # comprimento da barra no seu eixo
        self.cast_detectors = []  # um CastDetector por skill
        self.paused = False
        self.settings = None     # telas.Settings aberta
        self.wizard = None       # telas.Wizard aberto
        self.drag = None
        self.hk = {}
        self.last_error = None
        self.bar_visible = True
        self.vocacoes = wiki.load_vocacoes()

        # buffs
        self.buffs = []
        self.tracker = BuffTracker()
        self.buff_win = BuffWindow(self)
        self.buff_err = None
        self.load_buffs()

    # -- ciclo de vida --
    def start(self):
        if self.force_calibrate:
            self.calibrate()
        # assistente: no primeiro uso, ou para quem ainda nao escolheu a vocacao
        need_wizard = not self.cfg["regions"] or (
            not self.cfg.get("vocacao") and not self.cfg.get("wizard_skipped"))
        if self.cfg["regions"]:
            self.render()
            self.root.deiconify()
        self.root.update()
        self.apply_window_styles()
        if need_wizard:
            self.root.after(100, self.open_wizard)
        self.tick()
        self.poll_hotkeys()
        self.keep_on_top()
        self.update_visibility()
        self.buff_tick()
        try:
            self.root.mainloop()
        finally:
            save_config(self.cfg)

    def quit(self):
        save_config(self.cfg)
        self.root.quit()

    def apply_window_styles(self):
        hwnd = get_hwnd(self.root)
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_LAYERED
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
        user32.SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA)
        if self.cfg["exclude_from_capture"]:
            # Evita que a barra apareca dentro da propria captura (Win10 2004+).
            user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        self.set_click_through(self.cfg["click_through"], save=False)

    def set_click_through(self, on, save=True):
        self.cfg["click_through"] = bool(on)
        hwnd = get_hwnd(self.root)
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex = (ex | WS_EX_TRANSPARENT) if on else (ex & ~WS_EX_TRANSPARENT)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
        if alive(self.settings):
            self.settings.ct_switch.select() if on else self.settings.ct_switch.deselect()
        if save:
            save_config(self.cfg)

    def toggle_click_through(self):
        self.set_click_through(not self.cfg["click_through"])

    # -- calibracao --
    def calibrate(self):
        self.paused = True
        try:
            self.root.withdraw()
            self.root.update()
            time.sleep(0.35)
            result = Calibrator(self.root, self.cfg["monitor"]).run()
        finally:
            self.paused = False
        if result:
            self.cfg["regions"] = result
            self.cfg["magias"] = []   # marcacao manual: nao sabemos o nome das skills
            self.last_size = None
            self.photo = None
            self.cast_detectors = []
            save_config(self.cfg)
            return True
        return False

    def recalibrate(self):
        """Marcacao manual de cada icone (alternativa ao assistente)."""
        if alive(self.settings):
            self.settings.destroy()
        if self.buff_win is not None:
            self.buff_win.hide()
        self.calibrate()
        self.apply_new_regions()

    # -- buffs --
    def load_buffs(self):
        self.buffs = []
        for ci, b in enumerate(self.cfg.get("buffs", [])):
            try:
                img = Image.open(os.path.join(BASE_DIR, b["file"])).convert("RGB")
            except (OSError, KeyError):
                continue
            self.buffs.append({
                "ci": ci,
                "name": b.get("name", "Buff"),
                "duration": float(b.get("duration", 0) or 0),
                "desc": b.get("desc", ""),
                "skill": b.get("skill"),
                "restart_on_cast": b.get("restart_on_cast", True),
                "file": b["file"],
                "img": img,
                "arr": np.asarray(img),
            })

    def buff_tick(self):
        if not self.paused and self.buff_win is not None:
            try:
                self.scan_buffs()
            except Exception as exc:
                msg = repr(exc)
                if msg != self.buff_err:
                    print("Erro nos buffs:", msg)
                    self.buff_err = msg
        self.root.after(100, self.buff_tick)

    def scan_buffs(self):
        now = time.monotonic()
        area = self.cfg.get("buff_area")
        if not area or not self.buffs:
            self.buff_win.update([], False, now)
            return
        if not self.bar_visible:
            # jogo fora de foco: nao da para ver os icones; o cronometro segue valendo
            self.tracker.suspend()
            self.buff_win.update([], False, now)
            return
        x, y, w, h = self.scan_area(area)
        shot = self.sct.grab({"left": x, "top": y, "width": w, "height": h})
        arr = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(
            shot.height, shot.width, 4)[:, :, 2::-1]   # BGRA -> RGB
        thr = float(self.cfg["buff_threshold"])
        active = []
        for b in self.buffs:
            found = find_template(arr, b["arr"], thr) is not None
            self.tracker.update(b["file"], found, now, b["duration"])
            if self.tracker.active(b["file"], now):
                active.append(b)
        self.buff_win.update(active, True, now)

    def ui_windows(self):
        """Janelas de configuracao/assistente abertas."""
        return [w for w in (self.settings, self.wizard) if alive(w)]

    def pick_rect(self, message, click_size=None):
        """Congela a tela e deixa marcar um retangulo (ou so clicar, com click_size).
        Retorna (retangulo_na_tela, recorte_da_imagem) ou (None, None)."""
        self.paused = True
        hidden = [w for w in self.ui_windows() if w.winfo_viewable()]
        rect = crop = None
        try:
            for w in hidden:
                w.withdraw()
            if self.buff_win is not None:
                self.buff_win.hide()
            self.root.withdraw()
            self.root.update()
            time.sleep(0.35)
            cal = Calibrator(self.root, self.cfg["monitor"], message=message, single=True,
                             click_size=click_size)
            result = cal.run()
            if result:
                x, y, w, h = cal.rects[0]
                crop = cal.base.crop((x, y, x + w, y + h))
                rect = result[0]
        finally:
            self.paused = False
            self.bar_visible = True
            if self.cfg["regions"]:
                self.root.deiconify()
                self.root.update_idletasks()
            for w in hidden:
                if alive(w):
                    w.deiconify()
        return rect, crop

    def grab(self, rect):
        x, y, w, h = rect
        return grab_image(self.sct, {"left": x, "top": y, "width": w, "height": h})

    def save(self):
        save_config(self.cfg)

    def define_buff_area(self, step=""):
        rect, _ = self.pick_rect(
            "AREA DOS BUFFS %s\n"
            "Arraste um retangulo cobrindo TODAS AS LINHAS onde os icones de buff podem\n"
            "aparecer (ao lado do nivel do personagem), do 1o ate o ultimo espaco possivel.\n"
            "Com muitos buffs ativos a fila quebra para a 2a/3a linha: inclua-as tambem.\n"
            "Enter: confirmar.   Esc: cancelar." % step)
        if rect:
            self.cfg["buff_area"] = rect
            save_config(self.cfg)
            return True
        return False

    def add_buff(self):
        if self.paused or not self.cfg["regions"]:
            return
        two_steps = not self.cfg.get("buff_area")
        if two_steps and not self.define_buff_area("(1/2) - deixe o buff ATIVO no jogo"):
            return
        _rect, icon = self.pick_rect(
            "ADICIONAR BUFF %s\n"
            "Com o buff ATIVO na tela, arraste um retangulo bem justo sobre o ICONE dele.\n"
            "Enter: confirmar.   Esc: cancelar." % ("(2/2)" if two_steps else ""))
        if icon is None:
            return
        data = telas.BuffEditor(self, icon).run()
        if not data:
            return
        folder = os.path.join(BASE_DIR, "buffs")
        os.makedirs(folder, exist_ok=True)
        slug = "".join(c if c.isalnum() else "_" for c in data["name"].lower()).strip("_") or "buff"
        used = {b.get("file") for b in self.cfg["buffs"]}
        fname, n = "buffs/%s.png" % slug, 1
        while fname in used or os.path.exists(os.path.join(BASE_DIR, fname)):
            n += 1
            fname = "buffs/%s_%d.png" % (slug, n)
        icon.save(os.path.join(BASE_DIR, fname))
        self.cfg["buffs"].append(dict(self.with_skill_slug(data), file=fname))
        save_config(self.cfg)
        self.load_buffs()
        self.refresh_settings()

    def with_skill_slug(self, data):
        """Guarda tambem QUAL magia o buff segue, para o vinculo sobreviver se a
        ordem da barra mudar."""
        mags = self.cfg.get("magias") or []
        s = data.get("skill")
        data["skill_slug"] = mags[s] if isinstance(s, int) and 0 <= s < len(mags) else None
        return data

    def skill_images(self):
        """Imagem atual de cada skill da barra (na ordem da barra)."""
        imgs = []
        for x, y, w, h in self.cfg["regions"]:
            try:
                imgs.append(grab_image(self.sct, {"left": x, "top": y, "width": w, "height": h}))
            except Exception:
                imgs.append(Image.new("RGB", (w, h), "#333333"))
        return imgs

    def skill_slots(self, images=True):
        """[(nome, imagem, magia_da_wiki_ou_None)] de cada skill, na ordem da barra."""
        regs = self.cfg["regions"]
        mags = self.cfg.get("magias") or []
        voc = wiki.find_vocacao(self.vocacoes, self.cfg.get("vocacao") or "")
        by = {m["slug"]: m for m in voc["magias"]} if voc else {}
        known = [by.get(mags[i]) if len(mags) == len(regs) else None for i in range(len(regs))]
        live = (self.skill_images() if images and not all(known) else [None] * len(regs))
        out = []
        voc_slug = self.cfg.get("vocacao") or ""
        for i, (m, img) in enumerate(zip(known, live)):
            # icone da wiki quando a magia e conhecida: nitido mesmo com o jogo escondido
            if images and m is not None and wiki.has_icon(voc_slug, m):
                img = Image.open(wiki.icon_path(voc_slug, m)).convert("RGB")
            if images and img is None:
                img = Image.new("RGB", (44, 44), "#333333")
            out.append((m["nome"] if m else "Skill %d" % (i + 1), img, m))
        return out

    def scan_area(self, area):
        """Area realmente varrida (amplia sozinho se a marcada for pequena)."""
        iw = max((b["img"].width for b in self.buffs), default=16)
        ih = max((b["img"].height for b in self.buffs), default=16)
        vs = self.sct.monitors[0]
        return expand_buff_area(area, iw, ih, (vs["left"], vs["top"], vs["width"], vs["height"]))

    def edit_buff(self, i):
        if not 0 <= i < len(self.buffs):
            return
        b = self.buffs[i]
        data = telas.BuffEditor(self, b["img"], b).run()
        if data:
            self.cfg["buffs"][b["ci"]].update(self.with_skill_slug(data))
            save_config(self.cfg)
            self.load_buffs()
            self.refresh_settings()

    def remove_buff(self, i):
        if not 0 <= i < len(self.buffs):
            return
        b = self.buffs[i]
        parent = self.settings if alive(self.settings) else self.root
        if not messagebox.askyesno("Remover buff", "Remover '%s'?" % b["name"], parent=parent):
            return
        self.cfg["buffs"].pop(b["ci"])
        save_config(self.cfg)
        try:
            os.remove(os.path.join(BASE_DIR, b["file"]))
        except OSError:
            pass
        if self.tracker is not None:
            self.tracker.s.pop(b["file"], None)
        self.load_buffs()
        self.refresh_settings()

    def refresh_settings(self):
        if alive(self.settings):
            self.settings.refresh_buffs()

    def reset_buff_pos(self):
        self.cfg["buff_pos"] = None
        save_config(self.cfg)
        if self.buff_win is not None:
            self.buff_win.key = None   # forca reposicionar

    def redefine_area(self):
        if self.define_buff_area():
            self.refresh_settings()

    # -- desenho da barra --
    def render(self):
        regs = self.cfg["regions"]
        if not regs:
            return
        gap = int(self.cfg["gap"])
        left = min(r[0] for r in regs)
        top = min(r[1] for r in regs)
        right = max(r[0] + r[2] for r in regs)
        bottom = max(r[1] + r[3] for r in regs)

        area = grab_image(self.sct, {"left": left, "top": top,
                                     "width": right - left, "height": bottom - top})
        crops = [area.crop((x - left, y - top, x - left + w, y - top + h))
                 for x, y, w, h in regs]
        self.detect_casts(crops)

        vert = self.cfg.get("orientation") == "vertical"
        mains = [c.height if vert else c.width for c in crops]   # tamanho ao longo da barra
        total_main = sum(mains) + gap * (len(crops) + 1)
        total_cross = max((c.width if vert else c.height) for c in crops) + gap * 2
        total_w, total_h = (total_cross, total_main) if vert else (total_main, total_cross)
        strip = Image.new("RGB", (total_w, total_h), self.cfg["bg"])
        m = gap
        for c, ml in zip(crops, mains):
            if vert:
                strip.paste(c, ((total_w - c.width) // 2, m))
            else:
                strip.paste(c, (m, (total_h - c.height) // 2))
            m += ml + gap

        zoom = float(self.cfg["zoom"])
        if abs(zoom - 1.0) > 0.01:
            strip = strip.resize((max(1, round(total_w * zoom)),
                                  max(1, round(total_h * zoom))), RESAMPLE)

        if self.photo is not None and self.last_size == strip.size:
            self.photo.paste(strip)
        else:
            self.photo = ImageTk.PhotoImage(strip)
            self.label.configure(image=self.photo)
            self.last_size = strip.size
            self.place_window(*strip.size)
            # onde cada skill ficou na barra, no eixo da barra (para os buffs)
            k = (strip.height / total_h) if vert else (strip.width / total_w)
            centers, m = [], gap
            for ml in mains:
                centers.append(round((m + ml / 2) * k))
                m += ml + gap
            self.slot_centers = centers
            self.bar_length = strip.height if vert else strip.width

    def detect_casts(self, crops):
        """Percebe quando uma skill e usada (icone escurece) e reinicia o tempo do
        buff ligado a ela, caso ele ja esteja ativo (skill reusada antes de acabar)."""
        if not self.buffs:
            return
        if len(self.cast_detectors) != len(crops):
            self.cast_detectors = [CastDetector() for _ in crops]
        now = time.monotonic()
        for i, (c, det) in enumerate(zip(crops, self.cast_detectors)):
            if not det.update(np.asarray(c).mean()):
                continue
            for b in self.buffs:
                if (b.get("skill") == i and b.get("restart_on_cast", True)
                        and self.tracker.active(b["file"], now)):
                    self.tracker.restart(b["file"], now)

    def place_window(self, w, h):
        mons = self.sct.monitors
        vs = mons[0]
        pos = self.cfg.get("pos")
        if not pos:
            idx = self.cfg["monitor"] if 0 < self.cfg["monitor"] < len(mons) else 1
            m = mons[idx]
            pos = [m["left"] + (m["width"] - w) // 2,
                   m["top"] + m["height"] - h - 80]
        x = max(vs["left"], min(pos[0], vs["left"] + vs["width"] - w))
        y = max(vs["top"], min(pos[1], vs["top"] + vs["height"] - h))
        self.cfg["pos"] = [x, y]
        self.root.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def tick(self):
        t0 = time.perf_counter()
        if not self.paused and self.bar_visible:
            try:
                self.render()
            except Exception as exc:  # nao deixa o programa cair por um frame ruim
                msg = repr(exc)
                if msg != self.last_error:
                    print("Erro ao atualizar a barra:", msg)
                    self.last_error = msg
        fps = max(1, int(self.cfg["fps"]))
        delay = max(1, int(1000 / fps - (time.perf_counter() - t0) * 1000))
        self.root.after(delay, self.tick)

    # -- visibilidade: so aparece quando o jogo esta em primeiro plano --
    def game_is_active(self):
        proc = str(self.cfg.get("game_process", "")).strip().lower()
        title = str(self.cfg.get("game_title", "")).strip().lower()
        if not proc and not title:
            return True  # nada configurado: sempre visivel
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return self.bar_visible  # momento de transicao, mantem como esta
        pid, exe = window_info(hwnd)
        if pid == os.getpid():
            return True  # janelas do proprio programa (configuracoes etc.)
        if proc and exe.lower() != proc:
            return False
        if title and title not in window_title(hwnd).lower():
            return False
        return True

    def update_visibility(self):
        if not self.paused:
            try:
                want = self.game_is_active()
            except Exception:
                want = True
            if want != self.bar_visible:
                self.bar_visible = want
                if want and self.cfg["regions"]:
                    self.root.deiconify()
                    self.root.update_idletasks()
                else:
                    self.root.withdraw()
        self.root.after(150, self.update_visibility)

    def keep_on_top(self):
        if not self.paused:
            try:
                user32.SetWindowPos(get_hwnd(self.root), HWND_TOPMOST, 0, 0, 0, 0,
                                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
                if self.buff_win is not None:
                    self.buff_win.raise_topmost()
            except Exception:
                pass
        self.root.after(1500, self.keep_on_top)

    def poll_hotkeys(self):
        if not self.paused:
            combo = key_down(VK_CONTROL) and key_down(VK_MENU)
            for name, vk, action in (("ct", VK_F10, self.toggle_click_through),
                                     ("cfg", VK_F11, self.open_settings),
                                     ("buff", VK_F12, self.add_buff)):
                down = combo and key_down(vk)
                if down and not self.hk.get(name):
                    action()
                self.hk[name] = down
        self.root.after(50, self.poll_hotkeys)

    # -- mouse na barra --
    def on_press(self, e):
        self.drag = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def on_motion(self, e):
        if self.drag:
            x, y = e.x_root - self.drag[0], e.y_root - self.drag[1]
            self.root.geometry("+%d+%d" % (x, y))

    def on_release(self, e):
        if self.drag:
            self.drag = None
            self.cfg["pos"] = [self.root.winfo_x(), self.root.winfo_y()]
            save_config(self.cfg)

    def on_wheel(self, e):
        step = 0.1 if e.delta > 0 else -0.1
        self.cfg["zoom"] = round(max(0.5, min(4.0, float(self.cfg["zoom"]) + step)), 1)
        save_config(self.cfg)

    # -- telas (assistente e configuracoes, em telas.py) --
    def open_settings(self):
        if self.paused:
            return
        if alive(self.wizard):
            self.wizard.bring_front()
            return
        if alive(self.settings):
            self.settings.bring_front()
            return
        self.settings = telas.Settings(self)

    def open_wizard(self):
        if alive(self.settings):
            self.settings.destroy()
        if alive(self.wizard):
            self.wizard.bring_front()
            return
        self.wizard = telas.Wizard(self)

    def wizard_closed(self, finished):
        self.wizard = None
        if not self.cfg["regions"]:
            print("Nenhuma skill escolhida. Saindo.")
            self.quit()

    def skip_wizard(self):
        self.cfg["wizard_skipped"] = True
        save_config(self.cfg)

    def finish_wizard(self, vocacao, magias, regions, orientation):
        """Aplica o que foi escolhido no assistente."""
        old = self.cfg.get("magias") or []
        voc = wiki.find_vocacao(self.vocacoes, vocacao)
        names = {m["slug"]: m["nome"] for m in voc["magias"]} if voc else {}
        for b in self.cfg["buffs"]:
            # mantem cada buff em cima da MESMA magia, mesmo que a ordem tenha mudado
            slug = b.get("skill_slug")
            s = b.get("skill")
            if not slug and isinstance(s, int) and 0 <= s < len(old):
                slug = old[s]
            if not slug:
                # buff de antes do assistente: tenta pelo nome ("IRA" -> "Ira Frenetica")
                slug = match_by_name(b.get("name", ""), {k: names[k] for k in magias
                                                          if k in names})
            if slug:
                b["skill_slug"] = slug
                b["skill"] = magias.index(slug) if slug in magias else None
        self.cfg.update(vocacao=vocacao, magias=magias, regions=regions,
                        orientation=orientation)
        save_config(self.cfg)
        self.load_buffs()
        self.apply_new_regions()

    def apply_new_regions(self):
        self.last_size = None
        self.photo = None
        self.cast_detectors = []
        self.bar_visible = True
        if self.cfg["regions"]:
            self.render()
            self.root.deiconify()
            self.root.update_idletasks()

    def set_orientation(self, orientation):
        self.cfg["orientation"] = "vertical" if orientation == "vertical" else "horizontal"
        self.last_size = None   # forca remontar a barra
        save_config(self.cfg)

    def game_label_text(self):
        proc = self.cfg.get("game_process", "")
        title = self.cfg.get("game_title", "")
        if proc or title:
            return "Visível só com esta janela em primeiro plano:\n%s" % (
                proc or ("título contendo '%s'" % title))
        return "Desativado: a barra fica sempre visível."

    def capture_game_window(self, n, show):
        """Conta n segundos e grava qual programa esta em primeiro plano.
        show(texto) atualiza a tela e devolve False se ela foi fechada."""
        if n > 0:
            if show("Clique agora na janela do jogo... %d" % n):
                self.root.after(1000, lambda: self.capture_game_window(n - 1, show))
            return
        hwnd = user32.GetForegroundWindow()
        pid, exe = window_info(hwnd) if hwnd else (0, "")
        if not exe or pid == os.getpid():
            show("Não consegui detectar. Tente de novo e clique na janela do jogo.")
        elif exe.lower() in BROWSERS:
            show("Isso é um navegador (%s). Clique na janela do jogo e tente de novo." % exe)
        else:
            self.cfg["game_process"] = exe
            self.cfg["game_title"] = ""
            save_config(self.cfg)
            show(self.game_label_text())

    def clear_game_window(self, show):
        self.cfg["game_process"] = ""
        self.cfg["game_title"] = ""
        save_config(self.cfg)
        show(self.game_label_text())


# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Barra de Skills")
    parser.add_argument("--calibrar", action="store_true",
                        help="refaz a calibracao ao iniciar")
    parser.add_argument("--monitor", type=int,
                        help="numero do monitor onde esta o jogo (1 = principal)")
    parser.add_argument("--janelas", action="store_true",
                        help="lista as janelas abertas (programa e titulo) e sai")
    parser.add_argument("--jogo", metavar="PROGRAMA.EXE",
                        help="mostra a barra so quando este programa estiver em "
                             "primeiro plano (use '' para desativar)")
    args = parser.parse_args()

    enable_dpi_awareness()

    if args.janelas:
        for exe, title in sorted(list_windows(), key=lambda w: w[0].lower()):
            print("%-28s %s" % (exe or "?", title))
        return
    if args.jogo is not None:
        cfg = load_config()
        cfg["game_process"] = args.jogo.strip()
        cfg["game_title"] = ""
        save_config(cfg)
        print("Janela do jogo definida como: %r" % (cfg["game_process"] or "(sempre visivel)"))
    SkillBar(force_calibrate=args.calibrar, monitor=args.monitor).start()


if __name__ == "__main__":
    main()
