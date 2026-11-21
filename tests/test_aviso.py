"""Testes do aviso de buff acabando (piscar e apito)."""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import skillbar as sb  # noqa: E402
from buffcore import BuffTracker  # noqa: E402

BUFF = {"file": "ira", "duration": 90.0}


class AvisoTest(unittest.TestCase):
    def setUp(self):
        app = self.app = sb.SkillBar.__new__(sb.SkillBar)
        app.cfg = copy.deepcopy(config.DEFAULTS)
        app.tracker = BuffTracker()
        app.warned = set()
        self.beeps = 0

        def beep():
            self.beeps += 1
        app.beep = beep

    def ativo_desde(self, t0, ate):
        t = t0
        while t <= ate:
            self.app.tracker.update("ira", True, t, 90)
            t += 0.5

    def test_pisca_so_nos_ultimos_segundos(self):
        self.ativo_desde(0, 85)
        self.assertEqual(self.app.warn_state(BUFF, 70.0), 0)       # faltam 20 s
        self.assertIn(self.app.warn_state(BUFF, 85.0), (1, 2))     # faltam 5 s
        # alterna (pisca)
        states = {self.app.warn_state(BUFF, 85.0 + k / 6) for k in range(6)}
        self.assertEqual(states, {1, 2})

    def test_zero_desliga(self):
        self.app.cfg["warn_seconds"] = 0
        self.ativo_desde(0, 85)
        self.assertEqual(self.app.warn_state(BUFF, 85.0), 0)

    def test_sem_duracao_nao_pisca(self):
        self.ativo_desde(0, 85)
        self.assertEqual(self.app.warn_state({"file": "ira", "duration": 0}, 85.0), 0)

    def test_apita_uma_vez_por_ativacao(self):
        self.app.cfg["warn_sound"] = True
        self.ativo_desde(0, 85)
        for t in (82.0, 83.0, 84.0, 85.0):
            self.app.warn_sound([BUFF], t)
        self.assertEqual(self.beeps, 1)
        self.app.warn_sound([], 95.0)                 # buff acabou
        self.ativo_desde(100, 185)                    # usado de novo
        self.app.warn_sound([BUFF], 182.0)
        self.assertEqual(self.beeps, 2)

    def test_apito_desligado(self):
        self.ativo_desde(0, 85)
        self.app.warn_sound([BUFF], 85.0)
        self.assertEqual(self.beeps, 0)


if __name__ == "__main__":
    unittest.main()
