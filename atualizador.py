# -*- coding: utf-8 -*-
"""
Atualizacao pelo proprio programa (so no .exe).

1. latest_release(): pergunta ao GitHub qual e a ultima versao publicada.
2. download() + extract(): baixa o ZIP da release (confere tamanho e sha256) e
   extrai numa pasta temporaria.
3. launch(): abre o .exe NOVO, que esta na pasta temporaria, no modo
   "--aplicar-atualizacao". O programa atual fecha.
4. apply_update() (rodando no .exe novo): espera o antigo fechar, troca os
   arquivos do programa na pasta instalada e abre o programa atualizado.

Os arquivos de quem usa (configuracao, buffs, cache, diagnostico) nunca sao
tocados: so o BarraDeSkills.exe, a pasta _internal/ e o LEIA-ME.txt sao trocados.
A troca e feita por renomeacao, com volta atras se algo falhar no meio.

Sem nada de tela, para ser facil de testar.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

REPO = "famartins/BarraDeSkills"
API_LATEST = "https://api.github.com/repos/%s/releases/latest" % REPO
EXE = "BarraDeSkills.exe"
# o que e do programa (o resto da pasta e de quem usa e fica como esta)
PROGRAM_FILES = (EXE, "_internal", "LEIA-ME.txt")
TEMP_DIR = os.path.join(tempfile.gettempdir(), "BarraDeSkills-atualizacao")
APPLY_FLAG = "--aplicar-atualizacao"


def parse_version(text):
    """'v0.8.4' -> (0, 8, 4). Texto sem numeros -> ()."""
    return tuple(int(n) for n in re.findall(r"\d+", str(text or ""))[:4])


def is_newer(latest, current):
    a, b = parse_version(latest), parse_version(current)
    return bool(a) and a > b


def _request(url, timeout, accept="application/vnd.github+json"):
    req = urllib.request.Request(url, headers={"User-Agent": "BarraDeSkills-atualizador",
                                               "Accept": accept})
    return urllib.request.urlopen(req, timeout=timeout)


def parse_release(data):
    """Do JSON da API do GitHub, so o que interessa. None se nao tiver o ZIP."""
    assets = [a for a in data.get("assets") or []
              if str(a.get("name", "")).lower().endswith("-windows.zip")]
    if not assets or data.get("draft") or data.get("prerelease"):
        return None
    a = assets[0]
    digest = str(a.get("digest") or "")
    return {
        "version": str(data.get("tag_name", "")).lstrip("vV"),
        "title": data.get("name") or data.get("tag_name") or "",
        "notes": (data.get("body") or "").strip(),
        "page": data.get("html_url") or "https://github.com/%s/releases" % REPO,
        "url": a.get("browser_download_url"),
        "size": int(a.get("size") or 0),
        "sha256": digest[7:].lower() if digest.lower().startswith("sha256:") else "",
    }


def latest_release(timeout=8):
    """A ultima release publicada, ou None (sem internet, sem release...)."""
    with _request(API_LATEST, timeout) as r:
        return parse_release(json.loads(r.read().decode("utf-8")))


def download(info, dest_dir, progress=None, timeout=30):
    """Baixa o ZIP da release para dest_dir. progress(baixado, total) e chamado
    durante o download. Confere tamanho e sha256 (quando o GitHub informa)."""
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, "BarraDeSkills-v%s.zip" % info["version"])
    h = hashlib.sha256()
    done = 0
    with _request(info["url"], timeout, accept="application/octet-stream") as r, \
            open(path, "wb") as f:
        total = info.get("size") or int(r.headers.get("Content-Length") or 0)
        while True:
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
            h.update(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    if info.get("size") and done != info["size"]:
        raise IOError("download incompleto (%d de %d bytes)" % (done, info["size"]))
    if info.get("sha256") and h.hexdigest() != info["sha256"]:
        raise IOError("o arquivo baixado esta diferente do publicado (sha256)")
    return path


def extract(zip_path, dest_dir):
    """Extrai o ZIP e devolve a pasta que tem o BarraDeSkills.exe e _internal/."""
    shutil.rmtree(dest_dir, ignore_errors=True)
    with zipfile.ZipFile(zip_path) as z:
        root = os.path.realpath(dest_dir)
        for name in z.namelist():          # nada de caminhos para fora da pasta
            target = os.path.realpath(os.path.join(dest_dir, name))
            if not (target == root or target.startswith(root + os.sep)):
                raise IOError("ZIP com caminho invalido: %s" % name)
        z.extractall(dest_dir)
    for folder, dirs, files in os.walk(dest_dir):
        if EXE in files and "_internal" in dirs:
            return folder
    raise IOError("o ZIP nao tem o %s" % EXE)


def launch(new_dir, app_dir, pid):
    """Abre o .exe novo (na pasta temporaria) para trocar os arquivos em app_dir
    assim que o processo `pid` (o programa atual) fechar."""
    exe = os.path.join(new_dir, EXE)
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
        subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen([exe, APPLY_FLAG, app_dir, str(pid)], cwd=new_dir,
                     creationflags=flags, close_fds=True)


def _pid_alive(pid):
    if not pid:
        return False
    import ctypes
    k = ctypes.WinDLL("kernel32")
    SYNCHRONIZE = 0x00100000
    h = k.OpenProcess(SYNCHRONIZE, False, int(pid))
    if not h:
        return False
    try:
        return k.WaitForSingleObject(h, 0) == 0x102   # WAIT_TIMEOUT: ainda rodando
    finally:
        k.CloseHandle(h)


def _retry(fn, tries=20, wait=0.5):
    """O antivirus ou o Windows as vezes seguram o arquivo por instantes."""
    for k in range(tries):
        try:
            return fn()
        except OSError:
            if k == tries - 1:
                raise
            time.sleep(wait)


def replace_files(new_dir, app_dir, log=print):
    """Troca os arquivos do programa em app_dir pelos de new_dir. Primeiro tira
    os antigos do caminho (renomeando para .velho), depois poe os novos; se algo
    falhar, devolve os antigos. Nunca mexe nos arquivos de quem usa."""
    moved, placed = [], []
    try:
        for name in PROGRAM_FILES:
            old = os.path.join(app_dir, name)
            if os.path.exists(old):
                bak = old + ".velho"
                if os.path.exists(bak):
                    _rm(bak)
                _retry(lambda: os.replace(old, bak))
                moved.append((old, bak))
        for name in PROGRAM_FILES:
            src = os.path.join(new_dir, name)
            dst = os.path.join(app_dir, name)
            if not os.path.exists(src):
                continue
            if os.path.isdir(src):
                _retry(lambda: shutil.copytree(src, dst))
            else:
                _retry(lambda: shutil.copy2(src, dst))
            placed.append(dst)
    except Exception:
        log("Atualizacao: falhou no meio, voltando os arquivos antigos")
        for dst in placed:
            _rm(dst)
        for old, bak in moved:
            if not os.path.exists(old):
                os.replace(bak, old)
        raise
    for _old, bak in moved:
        _rm(bak)


def _rm(path):
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)
    except OSError:
        pass   # fica para a proxima (ex.: arquivo preso pelo antivirus)


def _log_to(app_dir):
    def log(text):
        try:
            with open(os.path.join(app_dir, "diagnostico.txt"), "a", encoding="utf-8") as f:
                f.write("[%s] %s\n" % (time.strftime("%d/%m %H:%M:%S"), text))
        except OSError:
            pass
    return log


def apply_update(app_dir, pid, new_dir=None, start=True, wait=60.0):
    """Roda no .exe NOVO (pasta temporaria): espera o programa antigo fechar,
    troca os arquivos e abre o programa atualizado. Retorna True se trocou."""
    new_dir = new_dir or os.path.dirname(os.path.abspath(sys.executable))
    log = _log_to(app_dir)
    end = time.time() + wait
    while _pid_alive(pid) and time.time() < end:
        time.sleep(0.3)
    ok = False
    try:
        replace_files(new_dir, app_dir, log)
        log("Atualizacao: arquivos trocados")
        ok = True
    except Exception as exc:
        log("Atualizacao: nao deu para trocar os arquivos (%r). O programa continua "
            "na versao anterior." % exc)
    if start:
        exe = os.path.join(app_dir, EXE)
        if os.path.isfile(exe):
            subprocess.Popen([exe], cwd=app_dir, close_fds=True)
    return ok


def cleanup(current_exe):
    """Apaga os restos de uma atualizacao (se este programa nao roda de la)."""
    exe_dir = os.path.realpath(os.path.dirname(current_exe))
    root = os.path.realpath(TEMP_DIR)
    if exe_dir == root or exe_dir.startswith(root + os.sep):
        return
    shutil.rmtree(TEMP_DIR, ignore_errors=True)


def prepare(info, progress=None):
    """Baixa e extrai a versao nova. Devolve a pasta com o .exe novo."""
    work = os.path.join(TEMP_DIR, info["version"])
    zip_path = download(info, work, progress)
    return extract(zip_path, os.path.join(work, "novo"))
