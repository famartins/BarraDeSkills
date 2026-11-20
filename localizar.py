# -*- coding: utf-8 -*-
"""
Localiza automaticamente as magias na barra lateral do jogo, comparando com os
icones da wiki (sem nada de Windows, para ser facil de testar).

O jogo desenha por cima dos icones a tecla de atalho (canto superior direito) e
o nivel ("Lv 2", embaixo a esquerda). Por isso so o MIOLO do icone e comparado.
O tamanho do icone na tela depende da resolucao, entao a escala e estimada.
"""

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image

# miolo usado na comparacao (fracoes do icone): evita os textos dos cantos
CORE = (0.22, 0.18, 0.78, 0.68)   # x0, y0, x1, y1

# diferenca media (0-255): ate GOOD_SCORE = encontrada com seguranca; ate MAYBE_SCORE
# = provavel (o icone pode estar em recarga ou escurecido): pede confirmacao.
# No teste real: magias presentes deram 0-2 (25 com o icone alterado), ausentes 35+.
GOOD_SCORE = 12.0
MAYBE_SCORE = 30.0


def _core_box(size):
    w, h = size
    x0, y0, x1, y1 = CORE
    return round(w * x0), round(h * y0), round(w * x1), round(h * y1)


def _template(icon, scale):
    """Icone da wiki redimensionado para a escala da tela -> (miolo int16, caixa)."""
    w, h = icon.size
    sw, sh = max(4, round(w * scale)), max(4, round(h * scale))
    img = icon.resize((sw, sh), Image.BILINEAR) if (sw, sh) != (w, h) else icon
    box = _core_box((sw, sh))
    core = np.asarray(img.crop(box), dtype=np.int16)
    return core, box, (sw, sh)


def best_match(area, core, step=3, stride=2):
    """Melhor posicao de `core` dentro de `area` (arrays int16 HxWx3).
    Busca grossa (1 a cada `step` pixels do icone, 1 a cada `stride` posicoes) e
    depois refina em volta dos melhores candidatos comparando o miolo inteiro.
    Retorna (diferenca_media, x, y) ou None se nao couber."""
    ah, aw = area.shape[:2]
    th, tw = core.shape[:2]
    if ah < th or aw < tw:
        return None
    wins = sliding_window_view(area, (th, tw, 3))[::stride, ::stride, 0]
    coarse = np.abs(wins[:, :, ::step, ::step] - core[::step, ::step]).mean(axis=(2, 3, 4))
    flat = coarse.ravel()
    k = min(6, flat.size)
    best = None
    seen = set()
    for idx in np.argpartition(flat, k - 1)[:k]:
        cy, cx = divmod(int(idx), coarse.shape[1])
        cy, cx = cy * stride, cx * stride
        for y in range(max(0, cy - stride + 1), min(ah - th, cy + stride - 1) + 1):
            for x in range(max(0, cx - stride + 1), min(aw - tw, cx + stride - 1) + 1):
                if (x, y) in seen:
                    continue
                seen.add((x, y))
                score = float(np.abs(area[y:y + th, x:x + tw] - core).mean())
                if best is None or score < best[0]:
                    best = (score, x, y)
    return best


def estimate_scale(area, icons, lo=0.5, hi=2.5):
    """Escala tela/wiki que melhor encaixa os icones (usa ate 4 deles)."""
    sample = icons[:4]

    def cost(s):
        # usa o MELHOR encaixe da amostra: basta uma magia estar na barra lateral
        best = 255.0
        for icon in sample:
            core, _box, _size = _template(icon, s)
            m = best_match(area, core, step=4, stride=3)
            if m:
                best = min(best, m[0])
        return best

    # caso mais comum: a wiki usa o mesmo tamanho do jogo
    if cost(1.0) < 6:
        return 1.0
    grid = np.arange(lo, hi + 1e-9, 0.1)
    s0 = min(grid, key=cost)
    fine = np.arange(max(lo, s0 - 0.08), min(hi, s0 + 0.08) + 1e-9, 0.02)
    return float(min(fine, key=cost))


def locate(area_img, icons, scale=None):
    """Procura cada icone (PIL RGB da wiki) dentro de `area_img` (PIL RGB da tela).

    Retorna (escala, resultados), com um resultado por icone:
        {"box": (x, y, w, h) relativo a area, "score": diferenca, "status": s}
    ou None quando nao coube. status: "ok" (seguro), "duvida" (confirme) ou
    "nao_achou". Dois icones no mesmo lugar: o pior vira "nao_achou".
    """
    area = np.asarray(area_img.convert("RGB"), dtype=np.int16)
    icons = [i.convert("RGB") for i in icons]
    if not icons:
        return 1.0, []
    if scale is None:
        scale = estimate_scale(area, icons)
    results = []
    for icon in icons:
        core, box, (sw, sh) = _template(icon, scale)
        m = best_match(area, core)
        if m is None:
            results.append(None)
            continue
        score, x, y = m
        status = ("ok" if score <= GOOD_SCORE else
                  "duvida" if score <= MAYBE_SCORE else "nao_achou")
        results.append({"box": (x - box[0], y - box[1], sw, sh), "score": score,
                        "status": status})
    _mark_conflicts(results)
    return scale, results


def _mark_conflicts(results):
    """Dois icones no mesmo lugar: o de maior diferenca vira 'nao_achou'."""
    for i, a in enumerate(results):
        for b in results[i + 1:]:
            if a is None or b is None:
                continue
            ax, ay, aw, ah = a["box"]
            bx, by, _bw, _bh = b["box"]
            if abs(ax - bx) < aw / 2 and abs(ay - by) < ah / 2:
                worse = a if a["score"] > b["score"] else b
                worse["status"] = "nao_achou"
