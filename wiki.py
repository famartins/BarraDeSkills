# -*- coding: utf-8 -*-
"""
Dados das vocacoes e magias (dados/vocacoes.json, gerado da Bloodpedia) e cache
local das imagens (icones das magias e o personagem de cada vocacao).

O personagem e montado como no provador de roupas da Bloodpedia: a folha de
sprites tem, em blocos de 128x128, a imagem base e uma mascara de cores; cada
cor da mascara (vermelho, verde, azul, amarelo, magenta, ciano) indica onde
aplicar a cor escolhida da roupa.

As imagens pertencem aos criadores do jogo, entao nao vao no repositorio: sao
baixadas da Bloodpedia na primeira vez e guardadas em cache/.
"""

import hashlib
import json
import os
import threading
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from config import BASE_DIR, RES_DIR


def normalize(text):
    """Para buscas: sem acento, minusculas e espacos simples ("Fúria" -> "furia")."""
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return " ".join(text.lower().split())

DATA_PATH = os.path.join(RES_DIR, "dados", "vocacoes.json")
CACHE_DIR = os.path.join(BASE_DIR, "cache", "icones")
ART_DIR = os.path.join(BASE_DIR, "cache", "personagens")
CANAIS = ("Red", "Green", "Blue", "Yellow", "Magenta", "Cyan")
USER_AGENT = "BarraDeSkills/0.8.4"


def load_vocacoes():
    """Lista de {slug, nome, personagem, magias: [{nome, slug, tipo, nivel, mana,
    icone_url}]}.
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
    """PNG do personagem da vocacao ja pintado (muda de nome se a roupa mudar)."""
    p = vocacao.get("personagem") or {}
    key = hashlib.sha1((p.get("sprite_url", "") + ".".join(p.get("cores", [])))
                       .encode("utf-8")).hexdigest()[:8]
    return os.path.join(ART_DIR, "%s-%s.png" % (vocacao["slug"], key))


def render_outfit(sheet, cores, tile=128, margin=2):
    """Primeiro quadro da folha de sprites, pintado com `cores` (6 cores hex, na
    ordem de CANAIS) e recortado em volta do personagem. Devolve PIL RGBA."""
    import numpy as np
    from PIL import Image
    a = np.asarray(sheet.convert("RGBA"))
    tiles = []
    for y in range(0, a.shape[0] - tile + 1, tile):
        for x in range(0, a.shape[1] - tile + 1, tile):
            t = a[y:y + tile, x:x + tile]
            if (t[..., 3] > 0).any():
                tiles.append(t)
            if len(tiles) == 2:
                break
        if len(tiles) == 2:
            break
    if len(tiles) < 2:
        return None
    base, mask = tiles
    rgb = {c: np.array([int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)])
           for c, h in zip(CANAIS, cores)}
    r, g, b = (mask[..., i] > 127 for i in range(3))
    on = mask[..., 3] > 0
    where = {"Yellow": on & r & g & ~b, "Magenta": on & r & b & ~g, "Cyan": on & g & b & ~r,
             "Red": on & r & ~g & ~b, "Green": on & g & ~r & ~b, "Blue": on & b & ~r & ~g}
    out = base.astype(np.float32)
    for c, m in where.items():
        out[m, :3] = np.minimum(255, base[m, :3] * rgb[c] * 2)
    img = Image.fromarray(out.astype(np.uint8), "RGBA")
    box = img.getbbox()
    if box:
        x0, y0, x1, y1 = box
        img = img.crop((max(0, x0 - margin), max(0, y0 - margin),
                        min(tile, x1 + margin), min(tile, y1 + margin)))
    return img


def download_personagem(vocacao, timeout=20):
    """Baixa a folha de sprites da roupa e salva o personagem pintado."""
    path = art_path(vocacao)
    if os.path.isfile(path):
        return path
    p = vocacao.get("personagem") or {}
    if not p.get("sprite_url") or len(p.get("cores", [])) != len(CANAIS):
        return None
    sheet_path = _download(p["sprite_url"], path[:-4] + "-folha.png", timeout)
    if not sheet_path:
        return None
    try:
        from PIL import Image
        img = render_outfit(Image.open(sheet_path), p["cores"])
        if img is None:
            return None
        tmp = path + ".tmp"
        img.save(tmp, "PNG")
        os.replace(tmp, path)
        return path
    except (OSError, ValueError):
        return None


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
    """Baixa e pinta em segundo plano os personagens das vocacoes que faltam."""
    jobs = [(v, lambda v=v: download_personagem(v))
            for v in vocacoes if not os.path.isfile(art_path(v))]
    return _run_async(jobs, on_each, on_done)
