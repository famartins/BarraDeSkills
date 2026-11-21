# -*- coding: utf-8 -*-
"""
Dados das vocacoes e magias (dados/vocacoes.json, gerado da Bloodpedia) e cache
local das imagens (icones das magias e arte de cada vocacao).

As imagens pertencem aos criadores do jogo, entao nao vao no repositorio: sao
baixadas da Bloodpedia na primeira vez e guardadas em cache/.
"""

import json
import os
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from config import BASE_DIR, RES_DIR

DATA_PATH = os.path.join(RES_DIR, "dados", "vocacoes.json")
CACHE_DIR = os.path.join(BASE_DIR, "cache", "icones")
ART_DIR = os.path.join(BASE_DIR, "cache", "artes")
USER_AGENT = "BarraDeSkills/2.1"


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


def art_path(vocacao):
    return os.path.join(ART_DIR, vocacao["slug"] + ".png")


def _download(url, path, timeout=15):
    """Baixa um PNG para `path`. Retorna o caminho, ou None se falhar."""
    if os.path.isfile(path):
        return path
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
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


def download_icon(vocacao_slug, magia, timeout=15):
    return _download(magia["icone_url"], icon_path(vocacao_slug, magia), timeout)


def _run_async(jobs, on_each, on_done):
    """jobs = [(item, funcao_que_baixa)]. Callbacks rodam na thread de download:
    na interface, use root.after para voltar a thread do Tk."""
    def run():
        fails = 0
        with ThreadPoolExecutor(max_workers=6) as pool:
            for (item, _f), path in zip(jobs, pool.map(lambda j: j[1](), jobs)):
                fails += path is None
                if on_each:
                    on_each(item, path)
        if on_done:
            on_done(fails)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def download_icons_async(vocacao_slug, magias, on_each=None, on_done=None):
    """Baixa em segundo plano os icones que faltam."""
    jobs = [(m, lambda m=m: download_icon(vocacao_slug, m))
            for m in magias if not has_icon(vocacao_slug, m)]
    return _run_async(jobs, on_each, on_done)


def download_arts_async(vocacoes, on_each=None, on_done=None):
    """Baixa em segundo plano as artes das vocacoes que faltam."""
    jobs = [(v, lambda v=v: _download(v.get("arte_url"), art_path(v), timeout=20))
            for v in vocacoes if not os.path.isfile(art_path(v))]
    return _run_async(jobs, on_each, on_done)
