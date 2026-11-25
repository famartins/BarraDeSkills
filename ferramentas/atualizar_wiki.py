#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera dados/vocacoes.json a partir da tabela "Magias" da Bloodpedia.

So o mantenedor precisa rodar isto, quando a wiki mudar:
    python ferramentas/atualizar_wiki.py

Guarda apenas nome, tipo, nivel minimo, mana e link do icone de cada magia, e de
cada vocacao a roupa do personagem mostrado na escolha de vocacao (provador de
roupas da Bloodpedia: link da folha de sprites e as 6 cores). As imagens NAO sao
guardadas no repositorio: o programa baixa cada uma na primeira vez (wiki.py).
A duracao dos buffs nao vem da wiki: o tempo citado la nao e a duracao real.
"""

import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

SITE = "https://bloodpedia.vercel.app"
OUTFITS = "https://www.bloodpedia.com.br/outfits/"
# roupa de cada vocacao na tela de escolha: (genero, nome da skin), parado, de frente
PERSONAGENS = {
    "cavaleiro": ("Homem", "Founders Gold"),
    "barbaro": ("Homem", "Cristal"),
    "arqueiro": ("Homem", "Founders Gold"),
    "xama": ("Mulher", "Founders Gold"),
    "mago": ("Mulher", "Founders Gold"),
}
CANAIS = ("Red", "Green", "Blue", "Yellow", "Magenta", "Cyan")
VOCACOES = [
    ("cavaleiro", "Cavaleiro"),
    ("barbaro", "Bárbaro"),
    ("arqueiro", "Arqueiro"),
    ("xama", "Xamã"),
    ("mago", "Mago"),
]
SAIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "dados", "vocacoes.json")

ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
CELL = re.compile(r'<td class="field_([^"]+)">(.*?)</td>', re.S)
TAG = re.compile(r"<[^>]+>")


def baixar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "BarraDeSkills/2.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def texto(fragmento):
    return html.unescape(TAG.sub("", fragmento)).strip()


def ler_magias(pagina):
    magias, vistos = [], set()
    for linha in ROW.findall(pagina):
        campos = {k: v for k, v in CELL.findall(linha)}
        if "Magia" not in campos:
            continue
        link = re.search(r'href="/wiki/([^/"]+)/?"', campos["Magia"])
        img = re.search(r'<img src="([^"]+)"', linha)
        if not link or not img:
            continue
        slug = link.group(1)
        if slug in vistos:
            continue
        vistos.add(slug)
        tipo = texto(campos.get("Tipo", ""))
        try:
            nivel = int(texto(campos.get("Lvl_1", "")) or 0)
        except ValueError:
            nivel = 0
        try:
            mana = int(texto(campos.get("Mana", "")) or 0)
        except ValueError:
            mana = 0
        magias.append({
            "nome": texto(campos["Magia"]),
            "slug": slug,
            "tipo": tipo,
            "nivel": nivel,
            "mana": mana,
            "icone_url": urllib.parse.urljoin(SITE, img.group(1)),
        })
    return magias


def personagens(pagina):
    """{nome_da_vocacao: {skin, genero, sprite_url, cores}} do provador de roupas.
    Cores como o provador usa: as da skin (ou as padrao) com o magenta 18."""
    m = re.search(r'<script[^>]*id="outfit-data"[^>]*>(.*?)</script>', pagina, re.S)
    dados = json.loads(m.group(1))
    pal = dados["palette"]
    out = {}
    for slug, nome in VOCACOES:
        genero, skin = PERSONAGENS[slug]
        achou = [s for s in dados["skins"] if s["vocation"] == nome and s["name"] == skin
                 and s["gender"] in (genero, "Ambos")]
        if not achou or "Back" not in achou[0]["sprites"].get("Parado", {}):
            print("  aviso: sem a roupa %s (%s) para %s" % (skin, genero, nome))
            continue
        s = achou[0]
        cores = dict(s.get("colors") or dados["defaultColors"])
        cores["Magenta"] = 18
        out[nome] = {"skin": skin, "genero": genero,
                     "sprite_url": OUTFITS + s["sprites"]["Parado"]["Back"],
                     "cores": ["#" + pal[cores[c]] for c in CANAIS]}
    return out


def main():
    dados = {"fonte": SITE + "/wiki/", "vocacoes": []}
    roupa = personagens(baixar(OUTFITS))
    for slug, nome in VOCACOES:
        magias = ler_magias(baixar("%s/wiki/%s/" % (SITE, slug)))
        print("%-10s %d magias" % (nome, len(magias)))
        if not magias:
            print("  ERRO: nenhuma magia lida; a wiki mudou de formato?")
            sys.exit(1)
        dados["vocacoes"].append({"slug": slug, "nome": nome,
                                  "personagem": roupa.get(nome, {}), "magias": magias})
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    print("Salvo em", SAIDA)


if __name__ == "__main__":
    main()
