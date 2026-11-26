#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o executavel (sem janela preta) e o ZIP para publicar em Releases no GitHub.

    pip install pyinstaller
    python ferramentas/gerar_exe.py

Resultado: dist/BarraDeSkills-vX.Y-windows.zip, com a pasta BarraDeSkills/ dentro
(BarraDeSkills.exe + _internal/). Quem baixa so extrai e da dois cliques no .exe:
nao precisa instalar Python.

Usa o modo "pasta" (onedir) e nao "arquivo unico": abre mais rapido e costuma
gerar menos alarme falso de antivirus.
"""

import os
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
DIST = os.path.join(ROOT, "dist")
NAME = "BarraDeSkills"
# arquivos do usuario que o .exe cria ao lado dele (nunca vao no ZIP)
USER_FILES = ("skillbar_config.json", "buffs", "cache", "diagnostico.txt")

LEIA_ME = """Barra de Skills {version} - Bloodstone

COMO USAR
1. Extraia esta pasta (botao direito no ZIP > Extrair tudo...). Nao rode de dentro do ZIP.
2. De dois cliques em BarraDeSkills.exe.
3. Na primeira vez abre um assistente: nome do personagem, vocacao e magias.

Se o Windows mostrar "O Windows protegeu o computador": clique em "Mais informacoes"
e depois em "Executar assim mesmo". O programa nao e assinado digitalmente.

ATUALIZAR
Quando sair uma versao nova, o programa avisa ao abrir: clique em "Atualizar agora".
Ou em Configuracoes > Sobre > "Procurar atualizacao". Sua configuracao, personagens
e buffs sao mantidos.

Se algo der errado, o arquivo diagnostico.txt (criado nesta pasta) diz o motivo.
Mande ele numa issue: {repo}/issues

O programa so le a imagem da tela: nao mexe na memoria do jogo e nao envia
cliques nem teclas.
"""


def version():
    with open(os.path.join(ROOT, "telas.py"), encoding="utf-8") as f:
        return re.search(r'^VERSION = "([^"]+)"', f.read(), re.M).group(1)


def make_icon(path):
    """Icone simples: tres 'skills' numa barra, nas cores do programa."""
    from PIL import Image, ImageDraw
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, 248, 248), radius=48, fill=(18, 18, 21, 255))
    colors = [(179, 38, 30), (217, 160, 40), (37, 99, 235)]
    for i, c in enumerate(colors):
        x = 30 + i * 68
        d.rounded_rectangle((x, 92, x + 56, 164), radius=10, fill=c + (255,))
        d.rounded_rectangle((x + 8, 100, x + 48, 156), radius=6, outline=(255, 255, 255, 90),
                            width=3)
    d.rounded_rectangle((26, 178, 230, 190), radius=6, fill=(179, 38, 30, 255))
    img.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128),
                          (256, 256)])


def main():
    ver = version()
    os.makedirs(BUILD, exist_ok=True)
    icon = os.path.join(ROOT, "dados", "icone.ico")   # vai junto em dados/ (janelas)
    if not os.path.isfile(icon):
        make_icon(icon)
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
           "--onedir", "--name", NAME, "--icon", icon,
           "--distpath", DIST, "--workpath", os.path.join(BUILD, "pyinstaller"),
           "--specpath", BUILD,
           "--add-data", "%s%sdados" % (os.path.join(ROOT, "dados"), os.pathsep),
           "--collect-data", "customtkinter",
           "--hidden-import", "pystray._win32",
           os.path.join(ROOT, "skillbar.py")]
    app_dir = os.path.join(DIST, NAME)
    # quem roda o .exe direto de dist/ tem a configuracao la dentro: guarda antes de
    # o PyInstaller apagar a pasta e devolve depois
    keep = os.path.join(BUILD, "preservar")
    shutil.rmtree(keep, ignore_errors=True)
    os.makedirs(keep)
    for item in USER_FILES:
        src = os.path.join(app_dir, item)
        if os.path.exists(src):
            shutil.move(src, os.path.join(keep, item))
            print("guardado:", item)
    try:
        print(" ".join(cmd))
        subprocess.check_call(cmd, cwd=ROOT)
    finally:
        os.makedirs(app_dir, exist_ok=True)
        for item in os.listdir(keep):
            dst = os.path.join(app_dir, item)
            if not os.path.exists(dst):
                shutil.move(os.path.join(keep, item), dst)
                print("devolvido:", item)

    with open(os.path.join(app_dir, "LEIA-ME.txt"), "w", encoding="utf-8") as f:
        f.write(LEIA_ME.format(version=ver, repo="https://github.com/famartins/BarraDeSkills"))
    zip_path = os.path.join(DIST, "%s-v%s-windows.zip" % (NAME, ver))
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, dirs, files in os.walk(app_dir):
            if folder == app_dir:   # nunca leva a configuracao/buffs de quem gerou
                dirs[:] = [d for d in dirs if d not in USER_FILES]
                files = [f for f in files if f not in USER_FILES]
            for fn in files:
                full = os.path.join(folder, fn)
                z.write(full, os.path.relpath(full, DIST))
    mb = os.path.getsize(zip_path) / 1e6
    print("\nPronto: %s (%.1f MB)" % (zip_path, mb))
    print("Publique em: https://github.com/famartins/BarraDeSkills/releases/new")


if __name__ == "__main__":
    if sys.argv[1:] == ["--versao"]:      # usado pela publicacao automatica
        print(version())
    else:
        main()
