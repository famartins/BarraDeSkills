# -*- coding: utf-8 -*-
"""
Tudo o que fica por cima do jogo: estilos de janela do Windows, a tela congelada
de marcacao (Calibrator), as barras de skills (Bar) e os buffs (BuffWindow).
"""

import ctypes
import os
import time
import tkinter as tk
from ctypes import wintypes

import mss
from PIL import Image, ImageTk

from buffcore import buff_time_text

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


def style_overlay(widget, exclude_capture=True, colorkey=None, alpha=1.0):
    """Janela que nao rouba o foco do jogo, sem item na barra de tarefas.
    colorkey: COLORREF que fica transparente (None = nenhuma cor transparente).
    alpha: opacidade da janela toda (0.0 a 1.0)."""
    hwnd = get_hwnd(widget)
    ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ex |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_LAYERED
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
    a = max(25, min(255, int(round(float(alpha) * 255))))
    if colorkey is None:
        user32.SetLayeredWindowAttributes(hwnd, 0, a, LWA_ALPHA)
    else:
        user32.SetLayeredWindowAttributes(hwnd, colorkey, a, LWA_ALPHA | LWA_COLORKEY)
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
WARN_COLOR = "#e0302a"   # moldura do buff que esta acabando


class BuffWindow:
    """Buffs ativos com tooltip (nome, descricao, tempo restante).

    - bar = uma Bar: mostra os buffs ligados as skills dela, cada um junto da sua
      skill (acima na horizontal, ao lado na vertical). O resto e transparente.
    - bar = None: janelinha solta e arrastavel, para buffs sem skill (ou para o
      modo "so buffs").
    """

    TIP_BG, TIP_BORDER = "#2a2118", "#6b5a48"

    def __init__(self, app, bar=None):
        self.app = app
        self.bar = bar
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
        self.slots = []      # (inicio, fim, buff) no eixo da faixa
        self.size = (0, 0)
        self.linked = False  # True = presa a uma barra (buffs junto das skills)
        self.x_off = 0       # deslocamento da faixa em relacao ao inicio da barra
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
                self.styled = True
                self.apply_alpha()
            self.shown = True

    def apply_alpha(self):
        if self.styled:
            style_overlay(self.win, self.app.cfg["exclude_from_capture"], KEY_COLORREF,
                          alpha=self.app.cfg["opacity"])

    def hide(self):
        if self.shown:
            self.win.withdraw()
            self.shown = False
        self.set_hover(None)

    def destroy(self):
        for w in (self.tip, self.win):
            try:
                if w is not None:
                    w.destroy()
            except tk.TclError:
                pass

    def raise_topmost(self):
        if self.shown:
            user32.SetWindowPos(get_hwnd(self.win), HWND_TOPMOST, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)

    def vertical(self):
        return self.bar is not None and self.bar.vertical()

    def update(self, items, visible, now):
        """items = [(buff, indice_da_skill_nesta_barra_ou_None)] dos buffs ativos."""
        if not visible or not items:
            self.hide()
            return
        cfg = self.app.cfg
        warn = tuple(self.app.warn_state(b, now) for b, _s in items)
        centers = tuple(self.bar.slot_centers) if self.bar else ()
        length = self.bar.bar_length if self.bar else 0
        key = (tuple((b["file"], s) for b, s in items), float(cfg["zoom"]),
               float(cfg["buff_zoom"]), int(cfg["gap"]), centers, length,
               self.vertical(), warn)
        if key != self.key:
            self.rebuild(items, warn, key)
        self.show()
        if self.linked or not cfg.get("buff_pos"):
            self.apply_geometry()   # acompanha a barra
        if self.hover is not None:
            self.refresh_tip(now)

    def rebuild(self, items, warn, key):
        """Monta a faixa. Trabalha num eixo "principal" (ao longo da barra: x na
        horizontal, y na vertical) e num eixo "cruzado" (para fora da barra).
        warn[i]: 0 = normal, 1 = acabando (moldura vermelha), 2 = idem, apagado."""
        cfg = self.app.cfg
        vert = self.vertical()
        gap = int(cfg["gap"])
        pad = max(1, round(2 * float(cfg["zoom"])))   # moldura em volta de cada icone
        z = float(cfg["zoom"]) * float(cfg["buff_zoom"])
        centers = self.bar.slot_centers if self.bar else []
        scaled = []
        for (b, s), w_state in zip(items, warn):
            w, h = b["img"].size
            sw, sh = max(1, round(w * z)), max(1, round(h * z))
            icon = b["img"].resize((sw, sh), RESAMPLE) if (sw, sh) != (w, h) else b["img"]
            if w_state == 2:
                icon = Image.blend(icon, Image.new("RGB", icon.size, "black"), 0.7)
            scaled.append((icon, b, s, w_state))

        def main_len(icon):
            return (icon.height if vert else icon.width) + 2 * pad

        groups, free = {}, []
        for it in scaled:
            s = it[2]
            if isinstance(s, int) and 0 <= s < len(centers):
                groups.setdefault(s, []).append(it)
            else:
                free.append(it)
        self.linked = bool(groups)

        place = []                           # (posicao no eixo principal, item)
        if self.linked:
            for s in sorted(groups):
                its = groups[s]
                tl = sum(main_len(i[0]) for i in its) + gap * (len(its) - 1)
                m = round(centers[s] - tl / 2)
                for it in its:
                    place.append((m, it))
                    m += main_len(it[0]) + gap
            m = self.bar.bar_length + gap    # buffs sem skill: depois do fim da barra
        else:
            m = 0
        for it in free:
            place.append((m, it))
            m += main_len(it[0]) + gap

        min_m = min(p[0] for p in place)
        total_main = max(p[0] + main_len(p[1][0]) for p in place) - min_m
        total_cross = max((i[0].width if vert else i[0].height) for i in scaled) + 2 * pad
        size = (total_cross, total_main) if vert else (total_main, total_cross)
        strip = Image.new("RGB", size, KEY_COLOR if self.linked else cfg["bg"])
        self.slots = []
        for m, (icon, b, _s, w_state) in place:
            m -= min_m
            cw, ch = icon.width + 2 * pad, icon.height + 2 * pad
            # encostado no lado da barra: embaixo (horizontal) ou a direita (vertical)
            x, y = (total_cross - cw, m) if vert else (m, total_cross - ch)
            strip.paste(WARN_COLOR if w_state else cfg["bg"], (x, y, x + cw, y + ch))
            strip.paste(icon, (x + pad, y + pad))
            self.slots.append((m, m + main_len(icon), b))
        self.x_off = min_m
        self.photo = ImageTk.PhotoImage(strip)
        self.label.configure(image=self.photo)
        self.size = strip.size
        self.key = key
        self.set_hover(self.hover if self.hover is not None and
                       self.hover < len(self.slots) else None)
        self.apply_geometry()

    def apply_geometry(self):
        w, h = self.size
        if w <= 0:
            return
        vs = self.app.sct.monitors[0]
        pos = self.app.cfg.get("buff_pos")
        bw = self.bar.win if self.bar is not None else self.app.first_bar_window()
        if not self.linked and pos:
            x, y = pos
        elif bw is None:
            # nenhuma barra (modo so buffs): centralizado, embaixo da tela
            x = vs["left"] + (vs["width"] - w) // 2
            y = vs["top"] + vs["height"] - h - 120
        elif self.vertical():
            # a esquerda da barra; se nao couber na tela, a direita
            x = bw.winfo_x() - w - 2
            if x < vs["left"]:
                x = bw.winfo_x() + bw.winfo_width() + 2
            y = bw.winfo_y() + self.x_off
        else:
            x = bw.winfo_x() + self.x_off
            y = bw.winfo_y() - h - (2 if self.linked else 6)
        x = max(vs["left"], min(x, vs["left"] + vs["width"] - w))
        y = max(vs["top"], min(y, vs["top"] + vs["height"] - h))
        self.win.geometry("%dx%d+%d+%d" % (w, h, x, y))

    # -- arrastar (so a janelinha solta) --
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
            self.app.save()

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
# Barra de skills
# --------------------------------------------------------------------------
class Bar:
    """Uma barra: janela sobreposta com a copia das skills dela."""

    def __init__(self, app, index):
        self.app = app
        self.index = index            # posicao em cfg["bars"]
        bg = app.cfg["bg"]
        win = self.win = tk.Toplevel(app.root)
        win.withdraw()
        win.title("Barra de Skills %d" % (index + 1))
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=bg)
        self.label = tk.Label(win, bd=0, highlightthickness=0, bg=bg)
        self.label.pack()
        self.label.bind("<ButtonPress-1>", self.on_press)
        self.label.bind("<B1-Motion>", self.on_motion)
        self.label.bind("<ButtonRelease-1>", self.on_release)
        self.label.bind("<Button-3>", lambda e: app.open_settings())
        self.label.bind("<MouseWheel>", app.on_wheel)
        self.photo = None
        self.last_size = None
        self.slot_centers = []   # centro de cada skill no eixo da barra, em pixels
        self.bar_length = 0      # comprimento da barra no seu eixo
        self.drag = None
        self.shown = False
        self.styled = False
        self.buff_win = BuffWindow(app, self)

    @property
    def data(self):
        return self.app.cfg["bars"][self.index]

    def vertical(self):
        return self.data.get("orientation") == "vertical"

    # -- janela --
    def show(self):
        if not self.shown and self.photo is not None:
            self.win.deiconify()
            self.win.update_idletasks()
            if not self.styled:
                self.styled = True
                self.apply_style()
            self.shown = True

    def hide(self):
        if self.shown:
            self.win.withdraw()
            self.shown = False
        self.buff_win.hide()

    def apply_style(self):
        """Opacidade, sem roubar foco, fora das capturas e click-through."""
        if not self.styled:
            return
        style_overlay(self.win, self.app.cfg["exclude_from_capture"],
                      alpha=self.app.cfg["opacity"])
        hwnd = get_hwnd(self.win)
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        on = self.app.cfg["click_through"]
        ex = (ex | WS_EX_TRANSPARENT) if on else (ex & ~WS_EX_TRANSPARENT)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
        self.buff_win.apply_alpha()

    def raise_topmost(self):
        if self.shown:
            user32.SetWindowPos(get_hwnd(self.win), HWND_TOPMOST, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        self.buff_win.raise_topmost()

    def destroy(self):
        self.buff_win.destroy()
        try:
            self.win.destroy()
        except tk.TclError:
            pass

    # -- desenho --
    def render(self, crops):
        """Monta a barra com os recortes das skills (na ordem da barra)."""
        cfg = self.app.cfg
        gap = int(cfg["gap"])
        vert = self.vertical()
        mains = [c.height if vert else c.width for c in crops]   # tamanho ao longo da barra
        total_main = sum(mains) + gap * (len(crops) + 1)
        total_cross = max((c.width if vert else c.height) for c in crops) + gap * 2
        total_w, total_h = (total_cross, total_main) if vert else (total_main, total_cross)
        strip = Image.new("RGB", (total_w, total_h), cfg["bg"])
        m = gap
        for c, ml in zip(crops, mains):
            if vert:
                strip.paste(c, ((total_w - c.width) // 2, m))
            else:
                strip.paste(c, (m, (total_h - c.height) // 2))
            m += ml + gap

        zoom = float(cfg["zoom"])
        if abs(zoom - 1.0) > 0.01:
            strip = strip.resize((max(1, round(total_w * zoom)),
                                  max(1, round(total_h * zoom))), RESAMPLE)

        if self.photo is not None and self.last_size == strip.size:
            self.photo.paste(strip)
            return
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

    def place_window(self, w, h):
        mons = self.app.sct.monitors
        vs = mons[0]
        pos = self.data.get("pos")
        if not pos:
            idx = self.app.cfg["monitor"] if 0 < self.app.cfg["monitor"] < len(mons) else 1
            m = mons[idx]
            # barra 1 embaixo, no centro; barra 2 um pouco acima dela
            pos = [m["left"] + (m["width"] - w) // 2,
                   m["top"] + m["height"] - h - 80 - self.index * (h + 60)]
        x = max(vs["left"], min(pos[0], vs["left"] + vs["width"] - w))
        y = max(vs["top"], min(pos[1], vs["top"] + vs["height"] - h))
        self.data["pos"] = [x, y]
        self.win.geometry("%dx%d+%d+%d" % (w, h, x, y))

    # -- mouse --
    def on_press(self, e):
        self.drag = (e.x_root - self.win.winfo_x(), e.y_root - self.win.winfo_y())

    def on_motion(self, e):
        if self.drag:
            self.win.geometry("+%d+%d" % (e.x_root - self.drag[0], e.y_root - self.drag[1]))

    def on_release(self, e):
        if self.drag:
            self.drag = None
            self.data["pos"] = [self.win.winfo_x(), self.win.winfo_y()]
            self.app.save()
