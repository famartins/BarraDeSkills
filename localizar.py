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


def has_drawing(crop, min_std=8.0):
    """O recorte tem desenho (nao e uma cor lisa, como um slot vazio)?"""
    box = _core_box(crop.size)
    g = np.asarray(crop.convert("L").crop(box), dtype=np.float32)
    return float(g.std()) >= min_std


def _thumb(img, size):
    """Miniatura 8x8 do miolo (para escolher rapido os icones mais parecidos)."""
    w, h = size
    box = _core_box((w, h))
    return np.asarray(img.convert("RGB").resize((w, h), Image.BILINEAR).crop(box)
                      .resize((8, 8), Image.BILINEAR), dtype=np.float32)


class SlotTracker:
    """Acompanha onde esta cada skill do personagem na barra lateral do jogo.

    O jogo tem varios "Sets" de barra lateral e cada um poe as skills em lugares
    diferentes. A cada verificacao, cada skill com icone conhecido e avaliada de
    novo, sem depender do que foi decidido antes:
    - no lugar esta ela (normal ou escurecida)          -> "ok" (copia a tela)
    - ela esta PRONTA em outra posicao                  -> "ok" e segue para la
    - no lugar esta OUTRA skill da vocacao, pronta      -> "missing" (nao esta
      neste Set; a barra mostra o icone dela apagado)
    - qualquer outra coisa (recarga sem cor e com a contagem, slot vazio...)
                                                        -> "ok" (copia a tela)
    So vira "missing" com prova (outra skill no lugar): recarga nunca apaga a
    skill, nem depois de trocar de Set e voltar.

    Outro personagem (ou tela de selecao): nenhuma skill da vocacao aparece nos
    lugares das skills por `settle` segundos e, numa varredura da barra lateral
    inteira, nenhuma magia da vocacao aparece pronta -> hidden() (a barra some).
    A varredura evita esconder a barra quando todas as skills estao em recarga.
    `others` = icones de todas as magias da vocacao (para reconhecer as outras).
    Skills sem icone conhecido ficam sempre "ok" (so copia a tela)."""

    def __init__(self, icons, others=(), settle=2.5):
        self.icons = list(icons)
        self.others = [o for o in others if o is not None]
        self.state = ["ok"] * len(self.icons)
        self.settle = settle
        self.absent_since = None
        self.gone = False
        self._turn = 0
        self._thumbs = {}
        self._seen = {}          # i -> (miniatura do lugar, instante, estado, presente)
        self.scores = {}         # i -> diferenca do lugar para o icone (ultima verificacao)

    def seen(self, i):
        """No lugar da skill i esta ela mesma (pronta ou em recarga)? Ultima
        verificacao; skill sem icone conhecido conta como sim."""
        if i >= len(self.icons) or self.icons[i] is None:
            return True
        s = self.scores.get(i)
        return s is not None and s <= MAYBE_SCORE and self.state[i] == "ok"

    def known(self):
        return [i for i, ic in enumerate(self.icons) if ic is not None]

    def hidden(self):
        """Nenhuma skill da vocacao na tela ha `settle` segundos."""
        return self.gone

    all_missing = hidden   # nome antigo

    def _other_here(self, i, crop):
        """Outra skill da vocacao, pronta, ocupa o lugar da skill i?"""
        size = crop.size
        cands = [o for o in self.others if o is not self.icons[i]]
        if not cands or not has_drawing(crop):
            return False
        key = size
        if key not in self._thumbs:
            self._thumbs[key] = {id(o): _thumb(o, size) for o in self.others}
        th = self._thumbs[key]
        t = _thumb(crop, size)
        cands.sort(key=lambda o: float(np.abs(th[id(o)] - t).mean()))
        return any(match_score(crop, o) <= GOOD_SCORE for o in cands[:3])

    def _vocation_visible(self, img, size, k=2):
        """Alguma magia da vocacao aparece pronta na imagem da barra lateral?
        (em meia resolucao; para na primeira encontrada)"""
        a = np.asarray(img.convert("RGB").resize((max(1, img.width // k),
                                                  max(1, img.height // k)),
                                                 Image.BILINEAR), dtype=np.int16)
        w, h = max(4, size[0] // k), max(4, size[1] // k)
        box = _core_box((w, h))
        for ic in self.others or [i for i in self.icons if i is not None]:
            core = np.asarray(ic.convert("RGB").resize((w, h), Image.BILINEAR).crop(box),
                              dtype=np.int16)
            m = best_match(a, core, step=2, stride=1)
            if m and m[0] <= GOOD_SCORE:
                return True
        return False

    def check(self, crops, regions, sidebar=None, max_search=2, now=None,
              recheck=6.0):
        """crops/regions: recorte e [x, y, w, h] de cada skill (indice global).
        sidebar: funcao que devolve (imagem_PIL, x, y) da barra lateral, chamada
        so se precisar procurar (no maximo `max_search` skills por vez, em
        rodizio). now: relogio em segundos. Um lugar que nao mudou desde a ultima vez so e
        reavaliado a cada `recheck` s (procurar na barra lateral e caro).
        Retorna {indice: nova_regiao} das que mudaram."""
        import time
        now = time.monotonic() if now is None else now
        known = self.known()
        scores = {i: match_score(crops[i], self.icons[i]) for i in known}
        self.scores = scores
        thumbs, fresh = {}, set()
        for i in known:
            if scores[i] <= GOOD_SCORE:
                continue
            thumbs[i] = _thumb(crops[i], crops[i].size)
            last = self._seen.get(i)
            if (last is not None and last[0].shape == thumbs[i].shape
                    and float(np.abs(last[0] - thumbs[i]).mean()) < 8
                    and now - last[1] < recheck + 0.35 * (i % 6)):   # espalha
                fresh.add(i)                   # lugar igual: vale a conclusao anterior
        bad = [i for i in thumbs if i not in fresh]
        if bad:
            k = self._turn % len(bad)
            bad = bad[k:] + bad[:k]
        self._turn += 1
        search = set(bad[:max_search])
        moved = {}
        side = None
        present = False          # alguma skill da vocacao nos lugares das skills
        for i in known:
            x, y, w, h = regions[i]
            if scores[i] <= GOOD_SCORE:
                self.state[i] = "ok"
                present = True
                self._seen.pop(i, None)
                continue
            thumb = thumbs[i]
            if i in fresh:
                last = self._seen[i]
                self.state[i] = last[2]        # lugar igual: mesma conclusao
                present = present or last[3]
                continue
            if sidebar is not None and i in search:
                if side is None:
                    side = sidebar() or False
                if side:
                    img, sx, sy = side
                    f = find_ready(img, self.icons[i], (w, h))
                    if f and f[0] <= GOOD_SCORE:
                        nx, ny = sx + f[1], sy + f[2]
                        if abs(nx - x) > w / 2 or abs(ny - y) > h / 2:
                            moved[i] = [nx, ny, w, h]
                        self.state[i] = "ok"
                        present = True
                        continue
            other = self._other_here(i, crops[i])
            self.state[i] = "missing" if other else "ok"
            present = present or other
            if sidebar is None or i in search:
                # so guarda a conclusao depois de procurar na barra lateral; quem
                # ficou fora desta rodada de busca e procurado na proxima
                self._seen[i] = (thumb, now, self.state[i], other)

        if present or not known:
            self.absent_since = None
            self.gone = False
        elif self.absent_since is None:
            self.absent_since = now
        elif not self.gone and now - self.absent_since >= self.settle:
            # antes de esconder: talvez todas estejam em recarga; se alguma magia da
            # vocacao aparece pronta na barra lateral, e o mesmo personagem
            if side is None and sidebar is not None:
                side = sidebar() or False
            i0 = known[0]
            if side and self._vocation_visible(side[0], tuple(regions[i0][2:4])):
                self.absent_since = now
            else:
                self.gone = True
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
