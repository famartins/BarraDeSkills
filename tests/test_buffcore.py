"""Testes da logica de buffs (rodar com: python -m unittest)."""

import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buffcore import (BuffTracker, CastDetector, confirm_casts,  # noqa: E402
                      expand_buff_area, renewal_time)

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


class CastDetectorExtraTest(unittest.TestCase):
    def test_escurecimento_em_alguns_quadros_tambem_conta(self):
        # o icone escurece aos poucos em 0,2 s (6 quadros), nao de uma vez
        def fade(t):
            if t < 2.0:
                return 120
            if t < 2.2:
                return 120 - (t - 2.0) / 0.2 * 70
            return 50 if t < 12 else 120
        self.assertEqual(len(simulate([fade], 15)), 1)

    def test_last_drop_so_guarda_escurecimento_longo(self):
        d = CastDetector()
        for k in range(300):
            t = k / FPS
            d.update(gcd(2.0)(t) if t < 5 else cooldown(6.0, 4)(t), t)
        self.assertAlmostEqual(d.last_drop, 6.0, delta=0.05)


class CastDetectorOutraCoisaNoLugarTest(unittest.TestCase):
    """Caso real (Vampirismo, icone escuro: 54 pronto, 26 em recarga): uma janela
    mais clara apareceu no lugar da skill e o programa passou a achar que ela
    estava sempre em recarga, sem perceber os usos seguintes."""

    def vamp(self, t):
        if 6 <= t < 11:
            return 72.0, False        # outra janela por cima (mais clara)
        for c in (2.0, 60.0, 130.0):
            if c <= t < c + 46:
                return 26.0 + (t - c) / 46 * 15, True   # recarga clareando aos poucos
        return 54.0, True

    def run_case(self, lag):
        d = CastDetector()
        casts, seen, next_chk = [], True, 0.0
        for k in range(int(180 * FPS)):
            t = k / FPS
            b, ok = self.vamp(t)
            if t >= next_chk:          # o programa confere o lugar a cada `lag` s
                seen, next_chk = ok, t + lag
            d.update(b, t, seen)
            casts += [round(c) for _i, c in confirm_casts([d], t)]
        return casts

    def test_percebe_todos_os_usos(self):
        for lag in (0.0, 0.3):
            self.assertEqual(self.run_case(lag), [2, 60, 130], lag)

    def test_recarga_eterna_se_resolve(self):
        d = CastDetector(max_cooling=10)
        d.update(200, 0.0)            # "normal" errado, alto demais
        for k in range(1, 400):
            d.update(50 if k < 5 else 54, k / FPS)
        self.assertFalse(d.cooling)


class RenewalTest(unittest.TestCase):
    def test_bug_reusou_perto_do_fim_e_nao_percebeu(self):
        # buff de 600 s; usado de novo aos 590 s (icone escureceu nesse instante)
        self.assertIsNone(renewal_time(0, 600, 601.0, last_drop=590.0))
        self.assertEqual(renewal_time(0, 600, 603.0, last_drop=590.0), 590.0)

    def test_sem_escurecimento_conta_do_fim_previsto(self):
        self.assertEqual(renewal_time(0, 600, 603.0), 600.0)
        self.assertEqual(renewal_time(0, 600, 603.0, last_drop=0.5), 600.0)

    def test_sem_duracao_nao_faz_nada(self):
        self.assertIsNone(renewal_time(0, 0, 5000.0))


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


class AprenderDuracaoTest(unittest.TestCase):
    def test_vale_o_tempo_que_mais_se_repete(self):
        from buffcore import learn_duration
        self.assertEqual(learn_duration([]), 0)
        self.assertEqual(learn_duration([90.4]), 90)
        self.assertEqual(learn_duration([90.4, 31.0]), 90)        # morreu: some antes
        self.assertEqual(learn_duration([31.0, 89.6, 90.8]), 90)
        self.assertEqual(learn_duration([90, 180, 91, 89]), 90)    # reuso nao percebido
        self.assertEqual(learn_duration([1.0, 2.0]), 0)            # piscadas nao contam

    def test_mede_so_se_viu_o_buff_o_tempo_todo(self):
        t = BuffTracker()
        for s in range(0, 61):
            t.update("a", True, float(s))
        self.assertAlmostEqual(t.measure("a"), 60.0)
        t2 = BuffTracker()
        t2.update("a", True, 0.0)
        t2.suspend()                                  # saiu do jogo no meio
        t2.update("a", True, 30.0)
        self.assertIsNone(t2.measure("a"))


class RecorteDoIconeTest(unittest.TestCase):
    def test_clique_acha_o_quadrado_do_icone(self):
        from buffcore import snap_icon
        rng = np.random.default_rng(0)
        scene = np.full((60, 120, 3), 30, np.uint8)
        x = 10
        rects = []
        for _ in range(5):
            ic = np.kron(rng.integers(60, 255, (4, 4, 3)), np.ones((4, 4, 1)))
            ic[0, :] = ic[-1, :] = ic[:, 0] = ic[:, -1] = 5      # moldura escura
            scene[20:36, x:x + 16] = ic
            rects.append((x, 20, 16, 16))
            x += 18
        for r in rects:
            got = snap_icon(scene, r[0] + 7, r[1] + 8)
            self.assertIsNotNone(got)
            # o miolo usado (2 px para dentro) fica dentro do icone certo
            gx, gy, gw, gh = got
            self.assertTrue(r[0] <= gx + 2 and gx + gw - 2 <= r[0] + 16, (got, r))
            self.assertTrue(r[1] <= gy + 2 and gy + gh - 2 <= r[1] + 16, (got, r))
        self.assertIsNone(snap_icon(scene, 5, 50))           # fundo liso: nada


class MedidaDepoisDeSairDoJogoTest(unittest.TestCase):
    def test_sair_do_jogo_sem_buff_ativo_nao_estraga_a_medida(self):
        t = BuffTracker()
        for s in range(0, 21):
            t.update("ira", True, float(s))
        t.suspend(20.5)                 # configuracoes abertas: buff ativo, medida perdida
        t.update("ira", True, 25.0)
        self.assertIsNone(t.measure("ira"))
        t.suspend(60.0)                 # buff ja tinha acabado: nao muda nada
        t.restart("ira", 100.0)         # usou a skill de novo: contagem nova
        for s in range(100, 192):
            t.update("ira", True, float(s))
        self.assertAlmostEqual(t.measure("ira"), 91.0)
