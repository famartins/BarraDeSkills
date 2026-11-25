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


def slot_score(crop, icon, pad=3):
    """Diferenca entre o recorte de UMA skill na tela e o icone esperado da wiki
    (so o miolo, com folga de `pad` px para pequenos desalinhamentos)."""
    crop = crop.convert("RGB")
    w, h = crop.size
    if w < 8 or h < 8:
        return 255.0
    tpl = icon.convert("RGB").resize((w, h), Image.BILINEAR)
    x0, y0, x1, y1 = _core_box((w, h))
    core = np.asarray(tpl.crop((x0, y0, x1, y1)), dtype=np.int16)
    area = np.asarray(crop.crop((max(0, x0 - pad), max(0, y0 - pad),
                                 min(w, x1 + pad), min(h, y1 + pad))), dtype=np.int16)
    m = best_match(area, core, step=2, stride=1)
    return m[0] if m else 255.0


def match_score(crop, icon, pad=2, keep=0.7):
    """Como slot_score, mas tolerante a recarga: compensa o icone escurecido e
    ignora os 30% de pixels que mais diferem (contagem de tempo escrita por cima).
    0 = mesma skill; ate GOOD_SCORE = com certeza; acima de MAYBE_SCORE = outra."""
    crop = crop.convert("RGB")
    w, h = crop.size
    if w < 8 or h < 8:
        return 255.0
    x0, y0, x1, y1 = _core_box((w, h))
    core = np.asarray(icon.convert("RGB").resize((w, h), Image.BILINEAR)
                      .crop((x0, y0, x1, y1)), dtype=np.float32)
    core_med = float(np.median(core.mean(axis=2))) + 1.0
    a = np.asarray(crop, dtype=np.float32)
    n = int(core.shape[0] * core.shape[1] * keep)
    best = 255.0
    for dy in range(-pad, pad + 1):
        for dx in range(-pad, pad + 1):
            if y0 + dy < 0 or x0 + dx < 0 or y1 + dy > h or x1 + dx > w:
                continue
            c = a[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
            gain = min(4.0, max(1.0, core_med / (float(np.median(c.mean(axis=2))) + 1.0)))
            for g in (1.0, gain) if gain > 1.0 else (1.0,):
                d = np.abs(np.clip(c * g, 0, 255) - core).mean(axis=2).ravel()
                best = min(best, float(np.partition(d, n - 1)[:n].mean()))
    return best


def find_ready(area, icon, size):
    """Procura a skill PRONTA (icone normal) em `area` (PIL RGB, ex.: a barra
    lateral inteira), com o icone no tamanho `size` da tela.
    Retorna (diferenca, x, y) do canto do icone dentro da area, ou None."""
    w, h = size
    tpl = icon.convert("RGB").resize((w, h), Image.BILINEAR)
    box = _core_box((w, h))
    core = np.asarray(tpl.crop(box), dtype=np.int16)
    m = best_match(np.asarray(area.convert("RGB"), dtype=np.int16), core)
    if m is None:
        return None
    score, x, y = m
    return score, x - box[0], y - box[1]


class SlotTracker:
    """Acompanha onde esta cada skill do personagem na barra lateral do jogo.

    O jogo tem varios "Sets" de barra lateral e cada um poe as skills em lugares
    diferentes. A cada verificacao, para cada skill com icone conhecido:
    - continua no lugar                                 -> "ok"
    - mudou de lugar (achada pronta em outra posicao)   -> "ok" e nova regiao
    - nao bate mais com o icone                         -> depende do contexto

    Uma skill que deixa de bater SOZINHA quase sempre esta em recarga: o jogo
    escurece e tira a cor do icone e escreve a contagem por cima, e ai ela nao
    bate com o icone da wiki. Por isso so vira "missing" (fora deste Set, a barra
    mostra o icone apagado) quando ha prova de que a barra lateral mudou:
    - outra skill mudou de lugar nesta verificacao (troca de Set), ou
    - metade ou mais das skills nao bate por `settle` segundos seguidos (outro
      personagem; a recarga global, que escurece todas juntas, dura menos).
    Skills em recarga confirmada (`cooldown`, do detector de uso) nao contam para
    a maioria e so viram "missing" quando a maioria ja sumiu.
    Skills sem icone conhecido ficam sempre "ok" (so copia a tela)."""

    def __init__(self, icons, settle=2.5):
        self.icons = list(icons)
        self.state = ["ok"] * len(self.icons)
        self.settle = settle
        self.majority_since = None
        self._turn = 0

    def known(self):
        return [i for i, ic in enumerate(self.icons) if ic is not None]

    def all_missing(self):
        k = self.known()
        return bool(k) and all(self.state[i] == "missing" for i in k)

    def check(self, crops, regions, sidebar=None, max_search=4, cooldown=(), now=None):
        """crops/regions: recorte e [x, y, w, h] de cada skill (indice global).
        sidebar: funcao que devolve (imagem_PIL, x, y) da barra lateral, chamada
        so se precisar procurar. Procura no maximo `max_search` skills por vez
        (primeiro as que acabaram de sair do lugar; as que ja estavam sumidas vao
        em rodizio). cooldown: indices em recarga confirmada. now: relogio em
        segundos. Retorna {indice: nova_regiao} das que mudaram de lugar."""
        import time
        now = time.monotonic() if now is None else now
        cooldown = set(cooldown)
        known = self.known()
        moved = {}
        side = None
        scores = {i: match_score(crops[i], self.icons[i]) for i in known}
        bad = [i for i in known if scores[i] > GOOD_SCORE]
        fresh = [i for i in bad if self.state[i] == "ok" and i not in cooldown]
        old = [i for i in bad if self.state[i] != "ok"]
        if old:
            k = self._turn % len(old)
            old = old[k:] + old[:k]
        self._turn += 1
        search = set((fresh + old)[:max_search])
        failing, held = [], []
        for i in known:
            icon, (x, y, w, h) = self.icons[i], regions[i]
            if scores[i] <= GOOD_SCORE:
                self.state[i] = "ok"
                continue
            if sidebar is not None and i in search:
                if side is None:
                    side = sidebar() or False
                if side:
                    img, sx, sy = side
                    f = find_ready(img, icon, (w, h))
                    if f and f[0] <= GOOD_SCORE:
                        nx, ny = sx + f[1], sy + f[2]
                        if abs(nx - x) > w / 2 or abs(ny - y) > h / 2:
                            moved[i] = [nx, ny, w, h]
                            self.state[i] = "ok"
                            continue
            if i in cooldown:
                held.append(i)                # usada agora: e a recarga
                continue
            failing.append(i)

        if failing and len(failing) * 2 >= len(known):
            if self.majority_since is None:
                self.majority_since = now
        else:
            self.majority_since = None
        majority = (self.majority_since is not None
                    and now - self.majority_since >= self.settle)
        if moved or majority:
            for i in failing:
                self.state[i] = "missing"
        if majority:
            # a barra lateral inteira mudou (outro personagem): quem parecia estar em
            # recarga, mas tambem nao bate de jeito nenhum, sumiu junto
            for i in held:
                if scores[i] > MAYBE_SCORE:
                    self.state[i] = "missing"
        # sem prova de mudanca: quem nao bate fica como estava (recarga)
        return moved


def count_found(area, icons, size):
    """Quantas skills (prontas) de `icons` aparecem em `area`."""
    n = 0
    for ic in icons:
        f = find_ready(area, ic, size)
        if f and f[0] <= GOOD_SCORE:
            n += 1
    return n


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
