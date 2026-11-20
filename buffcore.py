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
    - Se voce sai do jogo (suspend) e volta, o cronometro continua de onde estava,
      desde que a duracao configurada ainda nao tenha acabado.
    """

    def __init__(self, hold=1.0):
        self.hold = hold
        self.s = {}

    def suspend(self):
        for st in self.s.values():
            st["frozen"] = True

    def update(self, key, found, now, duration=0.0):
        st = self.s.setdefault(key, {"since": None, "last": None, "frozen": False})
        if not found:
            return
        was_active = st["last"] is not None and (now - st["last"]) <= self.hold
        if st["since"] is None:
            st["since"] = now
        elif not was_active:
            if st["frozen"]:
                still_running = (not duration) or (now - st["since"]) < duration + 1.0
                if not still_running:
                    st["since"] = now
            else:
                st["since"] = now  # sumiu de verdade e voltou: foi usado de novo
        st["last"] = now
        st["frozen"] = False

    def active(self, key, now):
        st = self.s.get(key)
        return bool(st and st["last"] is not None and (now - st["last"]) <= self.hold)

    def elapsed(self, key, now):
        st = self.s.get(key)
        if not st or st["since"] is None:
            return None
        return now - st["since"]
