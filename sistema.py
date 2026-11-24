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


def launch_target():
    """(programa, argumentos, pasta) para abrir a Barra de Skills: o .exe ou, pelo
    codigo-fonte, o pythonw (sem janela preta) com o skillbar.py."""
    if getattr(sys, "frozen", False):
        return sys.executable, "", os.path.dirname(sys.executable)
    folder = os.path.dirname(os.path.abspath(__file__))
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return (pyw if os.path.isfile(pyw) else sys.executable,
            '"%s"' % os.path.join(folder, "skillbar.py"), folder)


def autostart_command():
    """Comando que o Windows roda ao entrar, com --esperar (fica na bandeja ate o
    jogo abrir)."""
    exe, args, _folder = launch_target()
    return ('"%s" %s --esperar' % (exe, args)).replace("  ", " ")


# PowerShell cria os atalhos (.lnk) pelo objeto WScript.Shell do Windows. Os valores
# vao por variaveis de ambiente para nao ter problema com aspas nos caminhos.
_SHORTCUT_PS = r"""
$sh = New-Object -ComObject WScript.Shell
$out = @()
$places = @([Environment]::GetFolderPath('Desktop'),
            (Join-Path ([Environment]::GetFolderPath('Programs')) ''))
foreach ($dir in $places) {
    if (-not $dir) { continue }
    $path = Join-Path $dir ($env:BS_NAME + '.lnk')
    $lnk = $sh.CreateShortcut($path)
    $lnk.TargetPath = $env:BS_TARGET
    $lnk.Arguments = $env:BS_ARGS
    $lnk.WorkingDirectory = $env:BS_DIR
    $lnk.IconLocation = $env:BS_ICON
    $lnk.Description = 'Barra de Skills para Bloodstone'
    $lnk.Save()
    $out += $path
}
$out -join "`n"
"""


def create_shortcuts(icon_path, name="Barra de Skills"):
    """Cria (ou atualiza) atalhos na Area de Trabalho e no Menu Iniciar.
    Retorna a lista de atalhos criados (vazia se falhar)."""
    import subprocess
    exe, args, folder = launch_target()
    env = dict(os.environ, BS_NAME=name, BS_TARGET=exe, BS_ARGS=args, BS_DIR=folder,
               BS_ICON=icon_path if os.path.isfile(icon_path) else exe)
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-Command", _SHORTCUT_PS],
            env=env, capture_output=True, text=True, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return []
    return [p for p in out.stdout.splitlines() if p.strip().lower().endswith(".lnk")]


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
