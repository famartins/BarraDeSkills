# -*- coding: utf-8 -*-
"""
Dados das vocacoes e magias (dados/vocacoes.json, gerado da Bloodpedia) e cache
local dos icones.

Os icones pertencem aos criadores do jogo, entao nao vao no repositorio: sao
baixados da Bloodpedia na primeira vez e guardados em cache/icones/.
"""

import json
import os
import sys
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_PATH = os.path.join(BASE_DIR, "dados", "vocacoes.json")
CACHE_DIR = os.path.join(BASE_DIR, "cache", "icones")


def load_vocacoes():
    """Lista de {slug, nome, arte_url, magias: [{nome, slug, tipo, nivel, icone_url}]}.
    Lista vazia se o arquivo nao existir."""
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)["vocacoes"]
    except (OSError, ValueError, KeyError):
        return []


def find_vocacao(vocacoes, slug):
    return next((v for v in vocacoes if v["slug"] == slug), None)


def icon_path(vocacao_slug, magia):
    return os.path.join(CACHE_DIR, vocacao_slug, magia["slug"] + ".png")


def has_icon(vocacao_slug, magia):
    return os.path.isfile(icon_path(vocacao_slug, magia))


def download_icon(vocacao_slug, magia, timeout=15):
    """Baixa um icone para o cache. Retorna o caminho, ou None se falhar."""
    path = icon_path(vocacao_slug, magia)
    if os.path.isfile(path):
        return path
    try:
        req = urllib.request.Request(magia["icone_url"],
                                     headers={"User-Agent": "BarraDeSkills/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        if not data.startswith(b"\x89PNG"):
            return None
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        return path
    except (OSError, ValueError):
        return None


def download_icons_async(vocacao_slug, magias, on_each=None, on_done=None):
    """Baixa em segundo plano os icones que faltam.
    on_each(magia, caminho_ou_None) e on_done(n_falhas) sao chamados na thread
    de download: na interface, use root.after para voltar a thread do Tk."""
    missing = [m for m in magias if not has_icon(vocacao_slug, m)]

    def run():
        fails = 0
        with ThreadPoolExecutor(max_workers=6) as pool:
            for m, path in zip(missing, pool.map(
                    lambda m: download_icon(vocacao_slug, m), missing)):
                fails += path is None
                if on_each:
                    on_each(m, path)
        if on_done:
            on_done(fails)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t
