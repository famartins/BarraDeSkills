# -*- coding: utf-8 -*-
"""
Logica dos buffs (sem nada de Windows, para ser facil de testar).

- find_template: procura o icone de um buff dentro de uma imagem da tela.
- BuffTracker:   controla desde quando cada buff esta ativo (para o cronometro).
- buff_time_text: texto de tempo mostrado no tooltip.
"""

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def find_template(area, tpl, threshold=14.0):
    """Procura `tpl` dentro de `area` (arrays HxWx3, uint8, RGB).

    Retorna (diferenca_media, x, y) do melhor encontro, ou None se nao achar.
    A diferenca e a media do erro absoluto por canal (0 = identico).
    """
    ah, aw = area.shape[:2]
    th, tw = tpl.shape[:2]
    if ah < th or aw < tw:
        return None

    wins = sliding_window_view(area, (th, tw, 3))[:, :, 0]  # (Ny, Nx, th, tw, 3)

    # 1) busca grossa: compara so alguns pixels em todas as posicoes
    step = 3
    sub = tpl[::step, ::step].astype(np.int16)
    coarse = np.abs(wins[:, :, ::step, ::step].astype(np.int16) - sub).mean(axis=(2, 3, 4))
    flat = coarse.ravel()
    k = min(12, flat.size)
    candidates = np.argpartition(flat, k - 1)[:k]

    # 2) confirma as melhores posicoes comparando o icone inteiro
    tpl16 = tpl.astype(np.int16)
    best = None
    for idx in candidates:
        if flat[idx] > threshold * 2.5:
            continue
        y, x = divmod(int(idx), coarse.shape[1])
        score = float(np.abs(area[y:y + th, x:x + tw].astype(np.int16) - tpl16).mean())
        if best is None or score < best[0]:
            best = (score, x, y)
    if best is not None and best[0] <= threshold:
        return best
    return None


def expand_buff_area(area, iw, ih, screen):
    """Area de busca dos buffs. Se a area marcada for estreita (menos de 3 icones)
    amplia para os lados; se for baixa (menos de 2 icones) amplia para baixo,
    cobrindo 3 linhas, porque com muitos buffs ativos a fila quebra de linha.
    `screen` = (left, top, width, height) da area de trabalho virtual."""
    x, y, w, h = area
    if w < iw * 3:
        x, w = x - iw * 8, w + iw * 16
    if h < ih * 2:
        y, h = y - 6, ih * 3 + 6 * 2 + 12   # 3 linhas + espacamento + folga
    sl, st, sw, sh = screen
    x0, y0 = max(sl, x), max(st, y)
    x1, y1 = min(sl + sw, x + w), min(st + sh, y + h)
    return x0, y0, max(0, x1 - x0), max(0, y1 - y0)


def snap_icon(img, cx, cy, min_size=12, max_size=26, max_ratio=1.35):
    """Acha o quadrado do icone em volta de um clique em (cx, cy).

    Os icones de buff sao pequenos (~16 px) e recortar na mao sai torto. Aqui o
    programa testa todos os retangulos de `min_size` a `max_size` px que contem o
    clique e fica com o que tem as quatro bordas mais marcadas (troca brusca de cor
    entre dentro e fora). Usa a MAIS FRACA das quatro bordas como nota, para um
    traco forte no meio do desenho nao ganhar de uma moldura inteira.
    `img` = array HxWx3 (RGB). Retorna (x, y, w, h) ou None."""
    full = np.asarray(img)
    if not (0 <= cx < full.shape[1] and 0 <= cy < full.shape[0]):
        return None
    # so um pedaco em volta do clique (a imagem pode ser a tela inteira)
    ox, oy = max(0, cx - max_size - 2), max(0, cy - max_size - 2)
    a = full[oy:cy + max_size + 3, ox:cx + max_size + 3].astype(np.int32)
    cx, cy = cx - ox, cy - oy
    H, W = a.shape[:2]
    # gx[y, x]: diferenca entre os pixels x-1 e x; gy[y, x]: entre y-1 e y
    gx = np.zeros((H, W + 1))
    gx[:, 1:W] = np.abs(np.diff(a, axis=1)).sum(axis=2)
    gy = np.zeros((H + 1, W))
    gy[1:H, :] = np.abs(np.diff(a, axis=0)).sum(axis=2)
    cgx = np.vstack([np.zeros((1, W + 1)), np.cumsum(gx, axis=0)])   # soma por coluna
    cgy = np.hstack([np.zeros((H + 1, 1)), np.cumsum(gy, axis=1)])   # soma por linha
    cands = []
    for h in range(min_size, max_size + 1):
        for w in range(min_size, max_size + 1):
            if max(w, h) > max_ratio * min(w, h):
                continue
            x0s = np.arange(max(1, cx - w + 1), min(cx, W - w - 1) + 1)
            y0s = np.arange(max(1, cy - h + 1), min(cy, H - h - 1) + 1)
            if not len(x0s) or not len(y0s):
                continue
            X, Y = np.meshgrid(x0s, y0s)
            left = (cgx[Y + h, X] - cgx[Y, X]) / h
            right = (cgx[Y + h, X + w] - cgx[Y, X + w]) / h
            top = (cgy[Y, X + w] - cgy[Y, X]) / w
            bottom = (cgy[Y + h, X + w] - cgy[Y + h, X]) / w
            score = np.minimum(np.minimum(left, right), np.minimum(top, bottom))
            for i in np.argsort(score, axis=None)[-6:]:
                yi, xi = np.unravel_index(int(i), score.shape)
                cands.append((float(score[yi, xi]), int(X[yi, xi]), int(Y[yi, xi]), w, h))
    if not cands:
        return None
    cands.sort(reverse=True)
    top_score = cands[0][0]
    if top_score < 30:                    # nada com borda: clicou fora de um icone
        return None

    def ring_noise(c):
        """Variacao da faixa de 1 px logo FORA do quadrado. Em volta de um icone
        de verdade ha fundo ou o vao entre icones (quase liso); um quadrado que
        pega metade de dois icones tem desenho dos dois lados."""
        _s, x, y, w, h = c
        ring = np.concatenate([a[y - 1, x - 1:x + w + 1], a[y + h, x - 1:x + w + 1],
                               a[y:y + h, x - 1], a[y:y + h, x + w]])
        return float(np.abs(ring - np.median(ring, axis=0)).sum(axis=1).mean())
    # entre os quadrados de borda forte (ate 30% abaixo do melhor), o de entorno
    # mais liso
    good = [c for c in cands[:40] if c[0] >= 0.7 * top_score]
    best = min(good, key=lambda c: ring_noise(c) - 0.5 * c[0])
    return best[1] + ox, best[2] + oy, best[3], best[4]


ICON_SIZE = 18   # icones de buff/efeito do jogo: 18x18 px


def icon_view_rect(box, size=ICON_SIZE):
    """Quadrado do icone inteiro a partir do que snap_icon achou. O snap costuma
    pegar o desenho de dentro (14 ou 16 px, sem a moldura com cantos
    transparentes); o icone inteiro tem `size` px em volta do mesmo centro.
    Retorna (x, y, lado)."""
    x, y, w, h = box
    side = max(size, w, h)
    cx2, cy2 = 2 * x + w, 2 * y + h          # centro x2 (sem perder meio pixel)
    return (cx2 - side) // 2, (cy2 - side) // 2, side



class CastDetector:
    """Percebe quando uma skill escurece, olhando o brilho medio do icone dela.

    No Bloodstone o icone escurece quando a skill entra em recarga e volta ao
    normal quando ela fica pronta. Uma queda BRUSCA de brilho (em poucos quadros)
    para abaixo de `drop` x o brilho normal marca o inicio (`pending`). Se o brilho
    voltar a `recover` x o normal antes de a queda ser confirmada (veja
    confirm_casts), foi so um escurecimento rapido, como a recarga global que o
    jogo aplica em todas as skills quando QUALQUER uma e usada.
    """

    def __init__(self, drop=0.75, recover=0.9, span=0.5, gap=0.5, max_cooling=180.0):
        self.drop = drop
        self.recover = recover
        self.span = span      # "brusca" = em ate `span` segundos (vale para qualquer FPS)
        self.gap = gap        # sem quadros por mais que isso: recomeca a comparacao
        self.max_cooling = max_cooling   # nenhuma recarga dura mais que isso
        self.base = None      # brilho com a skill pronta
        self.recent = []      # (instante, brilho) dos ultimos `span` segundos
        self.cooling = False
        self.pending = None   # instante da queda ainda nao confirmada
        self.drop_at = None   # instante da queda atual (enquanto escuro)
        self.last_drop = None  # inicio do ultimo escurecimento que durou >= `long` s
        self.long = 1.5
        self.last_t = None
        self.undo = 0.6       # quanto tempo de quadros desfazer ao perceber outra coisa
        self.history = []     # (instante, base, cooling, drop_at) antes de cada quadro

    def update(self, brightness, now, seen=True):
        """Recebe o brilho do quadro atual. Retorna True se o icone acabou de escurecer.

        seen=False: no lugar da skill aparece outra coisa (janela por cima, tela de
        carregamento). Esse quadro e ignorado: nao conta como uso e, principalmente,
        nao muda o brilho normal. Antes, um brilho de fora deixava o "normal" alto
        demais e a skill parecia em recarga para sempre (os usos seguintes nao eram
        mais percebidos: caso do Vampirismo, que tem o icone escuro)."""
        b = float(brightness)
        if not seen and self.last_t is not None:
            # acabou de perceber (com atraso de ate `undo` s): desfaz o que esses
            # ultimos quadros de fora mudaram
            old = [s for s in self.history if now - s[0] >= self.undo]
            if old:
                _t, self.base, self.cooling, self.drop_at = old[-1]
            self.history = []
        if seen:
            self.history = [s for s in self.history if now - s[0] <= self.undo + 1.0]
            self.history.append((now, self.base, self.cooling, self.drop_at))
        if not seen or (self.last_t is not None and now - self.last_t > self.gap):
            self.recent = []          # comparar so com quadros seguidos da propria skill
            self.pending = None
        self.last_t = now if seen else None
        if not seen:
            return False
        dropped = False
        if self.base is None:
            self.base = b
        elif self.cooling:
            if self.drop_at is not None and now - self.drop_at >= self.long:
                self.last_drop = self.drop_at   # escuro por um tempo: parece uso real
            if b >= self.base * self.recover:
                self.cooling = False
                self.pending = None   # voltou ao normal: nao era (mais) uma recarga
            elif self.drop_at is None or now - self.drop_at > self.max_cooling:
                self.cooling = False  # "recarga" longa demais: o normal estava errado
                self.base = b
        elif b < self.base * self.drop and self.recent and b < max(
                v for _, v in self.recent) * self.drop:
            self.cooling = True
            self.pending = now
            self.drop_at = now
            dropped = True
        else:
            # acompanha a iluminacao normal: sobe rapido, desce devagar
            self.base += (b - self.base) * (0.3 if b > self.base else 0.02)
        self.recent = [(t, v) for t, v in self.recent if now - t <= self.span] + [(now, b)]
        return dropped


def confirm_casts(detectors, now, min_dark=1.5, group_window=0.3, max_wait=8.0):
    """Quais skills foram mesmo usadas: [(indice, instante_do_uso)].

    Uma queda so vira "skill usada" quando o icone continua escuro por pelo menos
    `min_dark` segundos E as outras skills que escureceram junto com ela (ate
    `group_window` s de diferenca) ja voltaram ao normal. Assim a recarga global
    (todas escurecem por instantes quando qualquer skill e usada) nao conta como
    uso; a skill realmente usada continua escura e e confirmada logo depois.
    Quedas que nao se resolvem em `max_wait` s sao descartadas."""
    out = []
    for i, d in enumerate(detectors):
        if d.pending is None:
            continue
        age = now - d.pending
        if age > max_wait:
            d.pending = None
            continue
        if age < min_dark:
            continue
        together = any(j != i and e.pending is not None
                       and abs(e.pending - d.pending) <= group_window
                       for j, e in enumerate(detectors))
        if together:
            continue
        out.append((i, d.pending))
        d.pending = None
    return out


def renewal_time(since, duration, now, last_drop=None, grace=2.0):
    """Buff ainda visivel depois do fim da contagem: foi renovado sem o programa
    perceber o uso da skill. Retorna o novo inicio da contagem, ou None se ainda
    nao passou do fim (+ `grace` s de folga).

    Usa o ultimo escurecimento da skill durante o buff, se houver (melhor palpite
    do instante do reuso); senao, conta a partir do fim previsto."""
    if not duration or since is None or now - since <= duration + grace:
        return None
    if last_drop is not None and since + 1.0 < last_drop <= now:
        return last_drop
    return since + duration


def learn_duration(samples, tol=3.0, minimum=3.0):
    """Duracao do buff a partir das vezes em que ele acabou sozinho (segundos).

    As medidas parecidas (ate `tol` s de diferenca) formam um grupo; vale o grupo com
    mais medidas e, no empate, o de tempo maior. Assim uma vez que o buff sumiu antes
    da hora (morte) ou durou o dobro (reuso que o programa nao viu) nao estraga o
    valor depois que houver outras medidas. Retorna segundos inteiros ou 0."""
    vals = sorted(float(v) for v in samples if v and float(v) >= minimum)
    if not vals:
        return 0
    best = None
    for v in vals:
        group = [u for u in vals if abs(u - v) <= tol]
        key = (len(group), max(group))
        if best is None or key > best[0]:
            best = (key, group)
    group = best[1]
    mid = len(group) // 2
    median = group[mid] if len(group) % 2 else (group[mid - 1] + group[mid]) / 2
    return int(round(median))


def fmt_time(seconds):
    s = max(0, int(seconds))
    return "%dm %ds" % (s // 60, s % 60)


def buff_time_text(elapsed, duration):
    """Texto de tempo do tooltip. `elapsed` = segundos desde que o buff apareceu."""
    if elapsed is None:
        return ""
    if duration and duration > 0:
        return "Restante: " + fmt_time(duration - elapsed)
    return "Ativo ha " + fmt_time(elapsed)


class BuffTracker:
    """Guarda, para cada buff, desde quando ele esta ativo.

    - Um buff continua "ativo" por `hold` segundos depois da ultima vez que foi visto
      (evita piscar quando algo, como um tooltip do jogo, cobre o icone por instantes).
    - Se o icone some por pouco tempo (ate `flicker` s: icone piscando, tooltip
      por cima, fila de buffs se reorganizando) e volta, o cronometro CONTINUA:
      nao e um novo uso. Reusar a skill e percebido pelo CastDetector.
    - Se voce sai do jogo (suspend) e volta, o cronometro continua de onde estava,
      desde que a duracao configurada ainda nao tenha acabado.
    """

    def __init__(self, hold=1.0, flicker=4.0):
        self.hold = hold
        self.end_hold = 0.25
        self.flicker = flicker
        self.s = {}

    def suspend(self, now=None):
        """Nao da para ver os buffs (jogo fora de foco). So os ativos agora sao
        afetados ("congelados"): o cronometro deles continua na volta. Se o buff
        acabar sem ser visto de novo, nao da para saber quando acabou."""
        for st in self.s.values():
            if now is not None and (st["last"] is None or now - st["last"] > self.hold):
                continue
            st["frozen"] = True

    def measure(self, key):
        """Quanto o buff durou (do inicio da contagem ate a ultima vez que foi visto).
        None se ele acabou enquanto o jogo estava fora de foco (congelado): ai nao da
        para saber quando acabou. Serve para aprender a duracao."""
        st = self.s.get(key)
        if not st or st["since"] is None or st["last"] is None or st["frozen"]:
            return None
        return st["last"] - st["since"]

    def update(self, key, found, now, duration=0.0):
        """Retorna "novo" quando o cronometro (re)comecou neste quadro, senao None."""
        st = self.s.setdefault(key, {"since": None, "last": None, "frozen": False})
        if not found:
            return None
        event = None
        was_active = st["last"] is not None and (now - st["last"]) <= self.hold
        if st["since"] is None:
            st["since"] = now
            event = "novo"
        elif not was_active:
            if duration:
                still_running = (now - st["since"]) < duration + 1.0
            else:   # duracao ainda nao conhecida: so continua se voltou logo
                still_running = (now - st["last"]) <= 30.0
            short_gap = (now - st["last"]) <= self.flicker
            if not (still_running and (st["frozen"] or short_gap)):
                st["since"] = now  # sumiu de verdade e voltou: foi usado de novo
                event = "novo"
        st["last"] = now
        st["frozen"] = False
        return event

    def restart(self, key, now):
        """A skill do buff foi usada de novo: o cronometro volta ao inicio."""
        st = self.s.get(key)
        if st is not None and st["since"] is not None:
            st["since"] = now

    def since(self, key):
        st = self.s.get(key)
        return st["since"] if st else None

    def active(self, key, now, duration=0.0):
        """Visto ha no maximo `hold` s. Perto do fim da contagem (ultimo 1 s ou
        depois) a folga cai para `end_hold`: o icone saiu do jogo porque o buff
        acabou, entao some na hora, sem atraso."""
        st = self.s.get(key)
        if not st or st["last"] is None:
            return False
        hold = self.hold
        if duration and st["since"] is not None and now - st["since"] >= duration - 1.0:
            hold = self.end_hold
        return (now - st["last"]) <= hold

    def elapsed(self, key, now):
        st = self.s.get(key)
        if not st or st["since"] is None:
            return None
        return now - st["since"]
