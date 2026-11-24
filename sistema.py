# -*- coding: utf-8 -*-
"""
Integracao com o Windows:

- SingleInstance: impede duas copias abertas (a segunda so avisa a primeira).
- Tray: icone perto do relogio (bandeja) com o menu do programa.
- find_game_window / client_rect: acha a janela do jogo e a posicao da area dela.
- autostart: abrir junto com o Windows (chave Run do usuario, sem admin).
"""

import ctypes
import os
import sys
import winreg
from ctypes import wintypes

from overlay import window_info, window_title

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL,
                                  wintypes.LPCWSTR]
kernel32.CreateEventW.restype = wintypes.HANDLE
kernel32.SetEvent.argtypes = [wintypes.HANDLE]
kernel32.SetEvent.restype = wintypes.BOOL
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.GetLastError.restype = wintypes.DWORD
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetClientRect.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.ClientToScreen.restype = wintypes.BOOL
_ENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [_ENUM, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL

ERROR_ALREADY_EXISTS = 183
WAIT_OBJECT_0 = 0
APP_NAME = "BarraDeSkills"
DEFAULT_GAME_TITLE = "bloodstone"   # titulo: "BloodStone - The Ancient Curse [...]"


# --------------------------------------------------------------------------
# Uma copia so
# --------------------------------------------------------------------------
class SingleInstance:
    """A primeira copia cria um mutex; as seguintes percebem e so 'tocam a
    campainha' (um evento), para a primeira aparecer, e fecham."""

    def __init__(self, name=APP_NAME):
        self.mutex = kernel32.CreateMutexW(None, False, "Local\\%s_instancia" % name)
        self.already_running = kernel32.GetLastError() == ERROR_ALREADY_EXISTS
        # evento de reset automatico: cada SetEvent acorda a primeira copia uma vez
        self.event = kernel32.CreateEventW(None, False, False, "Local\\%s_mostrar" % name)

    def wake_other(self):
        kernel32.SetEvent(self.event)

    def woken(self):
        """True se outra copia pediu para esta aparecer (consome o aviso)."""
        return kernel32.WaitForSingleObject(self.event, 0) == WAIT_OBJECT_0


# --------------------------------------------------------------------------
# Janela do jogo
# --------------------------------------------------------------------------
def find_game_window(process="", title=""):
    """hwnd da maior janela visivel do jogo (pelo executavel ou trecho do titulo),
    ou None. Sem nada configurado, procura 'BloodStone' no titulo."""
    process = (process or "").strip().lower()
    title = (title or "").strip().lower() or (DEFAULT_GAME_TITLE if not process else "")
    found = []

    def cb(hwnd, _l):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        if process and window_info(hwnd)[1].lower() != process:
            return True
        if title and title not in window_title(hwnd).lower():
            return True
        r = client_rect(hwnd)
        if r and r[2] > 200 and r[3] > 200:
            found.append((r[2] * r[3], hwnd))
        return True

    user32.EnumWindows(_ENUM(cb), 0)
    return max(found)[1] if found else None


def client_rect(hwnd):
    """(x, y, largura, altura) da area interna da janela, em pixels da tela;
    None se a janela sumiu ou esta minimizada."""
    if not hwnd or not user32.IsWindow(hwnd) or user32.IsIconic(hwnd):
        return None
    rc = wintypes.RECT()
    pt = wintypes.POINT(0, 0)
    if not user32.GetClientRect(hwnd, ctypes.byref(rc)) or \
            not user32.ClientToScreen(hwnd, ctypes.byref(pt)):
        return None
    return pt.x, pt.y, rc.right - rc.left, rc.bottom - rc.top


# --------------------------------------------------------------------------
# Abrir com o Windows
# --------------------------------------------------------------------------
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def autostart_command():
    """Comando que o Windows roda ao entrar: o .exe (ou pythonw + skillbar.py),
    com --esperar (fica na bandeja ate o jogo abrir)."""
    if getattr(sys, "frozen", False):
        return '"%s" --esperar' % sys.executable
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skillbar.py")
    return '"%s" "%s" --esperar' % (pyw if os.path.isfile(pyw) else sys.executable, script)


def autostart_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            value, _t = winreg.QueryValueEx(k, APP_NAME)
            return bool(value)
    except OSError:
        return False


def set_autostart(on):
    """Liga/desliga. Retorna True se deu certo."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, autostart_command())
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------
# Icone na bandeja
# --------------------------------------------------------------------------
class Tray:
    """Icone perto do relogio. O pystray roda numa thread propria: os cliques NAO
    mexem no Tk direto, so colocam um pedido em `requests` (uma fila que o
    programa le no loop do Tk)."""

    def __init__(self, image, requests, items, title="Barra de Skills"):
        """items = [(texto, pedido, checked_ou_None)]; o 1o item e o do clique duplo."""
        self.requests = requests
        self.icon = None
        try:
            import pystray
        except ImportError:
            return
        # o pystray exige funcoes com exatamente (icon, item) / (item): sem
        # parametros extras, por isso as fabricas abaixo
        def action(req):
            return lambda _icon, _item: self.requests.put(req)

        def is_checked(func):
            return lambda _item: bool(func())

        menu = []
        for i, (text, req, checked) in enumerate(items):
            if text == "-":
                menu.append(pystray.Menu.SEPARATOR)
                continue
            menu.append(pystray.MenuItem(text, action(req),
                                         checked=is_checked(checked) if checked else None,
                                         default=(i == 0)))
        self.icon = pystray.Icon(APP_NAME, image, title, pystray.Menu(*menu))

    def start(self):
        if self.icon is not None:
            self.icon.run_detached()

    def notify(self, text):
        try:
            if self.icon is not None:
                self.icon.notify(text, "Barra de Skills")
        except Exception:
            pass

    def stop(self):
        try:
            if self.icon is not None:
                self.icon.stop()
        except Exception:
            pass
