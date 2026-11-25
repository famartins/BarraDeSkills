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


class CastDetector:
    """Percebe quando uma skill escurece, olhando o brilho medio do icone dela.

    No Bloodstone o icone escurece quando a skill entra em recarga e volta ao
    normal quando ela fica pronta. Uma queda BRUSCA de brilho (em poucos quadros)
    para abaixo de `drop` x o brilho normal marca o inicio (`pending`). Se o brilho
    voltar a `recover` x o normal antes de a queda ser confirmada (veja
    confirm_casts), foi so um escurecimento rapido, como a recarga global que o
    jogo aplica em todas as skills quando QUALQUER uma e usada.
    """

    def __init__(self, drop=0.75, recover=0.9, span=0.5):
        self.drop = drop
        self.recover = recover
        self.span = span      # "brusca" = em ate `span` segundos (vale para qualquer FPS)
        self.base = None      # brilho com a skill pronta
        self.recent = []      # (instante, brilho) dos ultimos `span` segundos
        self.cooling = False
        self.pending = None   # instante da queda ainda nao confirmada
        self.drop_at = None   # instante da queda atual (enquanto escuro)
        self.last_drop = None  # inicio do ultimo escurecimento que durou >= `long` s
        self.long = 1.5
        self.confirmed = False  # a queda atual foi confirmada como uso (confirm_casts)

    def in_cooldown(self):
        """A skill foi usada (uso confirmado) e o icone ainda esta escuro."""
        return self.cooling and self.confirmed

    def update(self, brightness, now):
        """Recebe o brilho do quadro atual. Retorna True se o icone acabou de escurecer."""
        b = float(brightness)
        dropped = False
        if self.base is None:
            self.base = b
        elif self.cooling:
            if self.drop_at is not None and now - self.drop_at >= self.long:
                self.last_drop = self.drop_at   # escuro por um tempo: parece uso real
            if b >= self.base * self.recover:
                self.cooling = False
                self.confirmed = False
                self.pending = None   # voltou ao normal: nao era (mais) uma recarga
        elif b < self.base * self.drop and b < max(
                [v for _, v in self.recent] or [b]) * self.drop:
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
        d.confirmed = True
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
        self.flicker = flicker
        self.s = {}

    def suspend(self):
        for st in self.s.values():
            st["frozen"] = True

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
            still_running = (not duration) or (now - st["since"]) < duration + 1.0
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

    def active(self, key, now):
        st = self.s.get(key)
        return bool(st and st["last"] is not None and (now - st["last"]) <= self.hold)

    def elapsed(self, key, now):
        st = self.s.get(key)
        if not st or st["since"] is None:
            return None
        return now - st["since"]
