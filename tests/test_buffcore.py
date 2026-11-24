"""Testes da logica de buffs (rodar com: python -m unittest)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buffcore import (BuffTracker, CastDetector, confirm_casts,  # noqa: E402
                      expand_buff_area)

SCREEN = (0, 0, 2560, 1440)


class ExpandBuffAreaTest(unittest.TestCase):
    def test_area_de_um_icone_cresce_para_os_lados_e_3_linhas(self):
        x, y, w, h = expand_buff_area([291, 122, 16, 15], 18, 16, SCREEN)
        self.assertLessEqual(x, 291 - 18 * 8)
        self.assertGreaterEqual(x + w, 291 + 16 + 18 * 8)
        self.assertLessEqual(y, 122)
        self.assertGreaterEqual(y + h, 122 + 16 * 3)   # cobre 3 linhas para baixo

    def test_area_grande_fica_igual(self):
        self.assertEqual(expand_buff_area([100, 100, 300, 60], 18, 16, SCREEN),
                         (100, 100, 300, 60))

    def test_linha_larga_mas_baixa_cresce_so_para_baixo(self):
        x, y, w, h = expand_buff_area([100, 100, 300, 18], 18, 16, SCREEN)
        self.assertEqual((x, w), (100, 300))
        self.assertGreaterEqual(h, 16 * 3)

    def test_respeita_a_borda_da_tela(self):
        x, y, w, h = expand_buff_area([5, 2, 16, 15], 18, 16, SCREEN)
        self.assertEqual((x, y), (0, 0))


FPS = 30


def simulate(skills, seconds):
    """skills = lista de funcoes t -> brilho (uma por skill). Roda a 30 quadros/s e
    devolve [(indice_da_skill, instante_do_uso)] confirmados."""
    dets = [CastDetector() for _ in skills]
    out = []
    for k in range(int(seconds * FPS)):
        t = k / FPS
        for f, d in zip(skills, dets):
            d.update(f(t), t)
        out += [(i, round(ct, 2)) for i, ct in confirm_casts(dets, t)]
    return out


def ready(_t):
    return 120


def cooldown(start, length, dark=50):
    """Skill usada em `start`: fica escura por `length` segundos."""
    return lambda t: dark if start <= t < start + length else 120


def gcd(start, length=0.8, dark=60):
    """Recarga global: escurece por pouco tempo quando QUALQUER skill e usada."""
    return lambda t: dark if start <= t < start + length else 120


def both(*fs):
    return lambda t: min(f(t) for f in fs)


class CastDetectorTest(unittest.TestCase):
    def test_uso_real_e_confirmado_no_instante_em_que_escureceu(self):
        self.assertEqual(simulate([cooldown(1.0, 10)], 15), [(0, 1.0)])

    def test_dois_usos_seguidos(self):
        sk = both(cooldown(1.0, 5), cooldown(10.0, 5))
        self.assertEqual(simulate([sk], 20), [(0, 1.0), (0, 10.0)])

    def test_bug_recarga_global_nao_conta_como_uso(self):
        # usou a skill 1; o Vampirismo (skill 0) so escurece pela recarga global
        vamp = gcd(2.0)
        other = both(gcd(2.0), cooldown(2.0, 6))
        self.assertEqual(simulate([vamp, other], 12), [(1, 2.0)])

    def test_recarga_global_longa_tambem_nao_conta(self):
        # recarga global de 2 s (mais que o minimo de 1,5 s): todas escuras juntas
        vamp = gcd(2.0, length=2.0)
        other = both(gcd(2.0, length=2.0), cooldown(2.0, 6))
        third = gcd(2.0, length=2.0)
        self.assertEqual(simulate([vamp, other, third], 12), [(1, 2.0)])

    def test_escurecimento_rapido_sozinho_nao_conta(self):
        self.assertEqual(simulate([gcd(2.0, length=0.5)], 6), [])

    def test_oscilacao_pequena_nao_dispara(self):
        self.assertEqual(simulate([lambda t: 120 - 15 * (int(t * FPS) % 2)], 5), [])

    def test_escurecimento_lento_nao_dispara(self):
        # ex.: a tela do jogo escurecendo aos poucos (noite)
        self.assertEqual(simulate([lambda t: 120 - 8 * t], 10), [])

    def test_programa_aberto_com_a_skill_em_recarga(self):
        sk = lambda t: 50 if t < 1 else (120 if t < 3 else 50)   # noqa: E731
        self.assertEqual(simulate([sk], 8), [(0, 3.0)])


class BuffTrackerFlickerTest(unittest.TestCase):
    def feed(self, t, start, end, visible=True, dur=600):
        while start <= end:
            t.update("vamp", visible, start, dur)
            start = round(start + 0.1, 2)

    def test_bug_icone_some_por_instantes_nao_zera_o_tempo(self):
        t = BuffTracker()
        self.feed(t, 0, 100)
        self.feed(t, 100.1, 102.5, visible=False)   # 2,5 s sem enxergar o icone
        self.feed(t, 102.6, 110)
        self.assertAlmostEqual(t.elapsed("vamp", 110), 110, delta=0.2)

    def test_sumiu_de_verdade_e_voltou_recomeca(self):
        t = BuffTracker()
        self.feed(t, 0, 100)
        self.feed(t, 100.1, 120, visible=False)     # 20 s sem o buff
        self.feed(t, 120.1, 130)
        self.assertAlmostEqual(t.elapsed("vamp", 130), 9.9, delta=0.2)

    def test_acabou_e_usou_logo_em_seguida_recomeca(self):
        t = BuffTracker()
        self.feed(t, 0, 600, dur=600)
        self.feed(t, 600.1, 601, visible=False, dur=600)
        self.feed(t, 601.1, 605, dur=600)
        self.assertAlmostEqual(t.elapsed("vamp", 605), 3.9, delta=0.2)

    def test_eventos(self):
        t = BuffTracker()
        self.assertEqual(t.update("vamp", True, 0, 600), "novo")
        self.assertIsNone(t.update("vamp", True, 0.1, 600))


class BuffTrackerRestartTest(unittest.TestCase):
    def test_restart_zera_o_tempo(self):
        t = BuffTracker()
        for i in range(601):                  # buff visivel, quadro a quadro, ate 300 s
            t.update("vamp", True, i * 0.5, 600)
        self.assertAlmostEqual(t.elapsed("vamp", 300.0), 300.0)
        t.restart("vamp", 300.0)
        self.assertAlmostEqual(t.elapsed("vamp", 310.0), 10.0)

    def test_restart_de_buff_desconhecido_nao_quebra(self):
        BuffTracker().restart("nada", 1.0)


if __name__ == "__main__":
    unittest.main()
