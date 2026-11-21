#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera dados/vocacoes.json a partir da tabela "Magias" da Bloodpedia.

So o mantenedor precisa rodar isto, quando a wiki mudar:
    python ferramentas/atualizar_wiki.py

Guarda apenas nome, tipo, nivel minimo e link do icone de cada magia, e o link
da arte de cada vocacao (pagina inicial). As imagens NAO sao guardadas no
repositorio: o programa baixa cada uma na primeira vez (veja wiki.py).
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
        magias.append({
            "nome": texto(campos["Magia"]),
            "slug": slug,
            "tipo": tipo,
            "nivel": nivel,
            "icone_url": urllib.parse.urljoin(SITE, img.group(1)),
        })
    return magias


def artes(home):
    """{nome_da_vocacao: url} das artes (ex.: .../BárbaroArtworkM.png) da pagina inicial."""
    out = {}
    for src in re.findall(r'<img[^>]+src="([^"]+ArtworkM\.png)"', home):
        nome = urllib.parse.unquote(src.rsplit("/", 1)[-1])[:-len("ArtworkM.png")]
        out.setdefault(nome, urllib.parse.urljoin(SITE, src))
    return out


def main():
    dados = {"fonte": SITE + "/wiki/", "vocacoes": []}
    arte = artes(baixar(SITE + "/"))
    for slug, nome in VOCACOES:
        magias = ler_magias(baixar("%s/wiki/%s/" % (SITE, slug)))
        print("%-10s %d magias" % (nome, len(magias)))
        if not magias:
            print("  ERRO: nenhuma magia lida; a wiki mudou de formato?")
            sys.exit(1)
        if nome not in arte:
            print("  aviso: sem arte para %s" % nome)
        dados["vocacoes"].append({"slug": slug, "nome": nome, "arte_url": arte.get(nome, ""),
                                  "magias": magias})
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    print("Salvo em", SAIDA)


if __name__ == "__main__":
    main()
