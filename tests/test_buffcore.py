"""Testes da logica de buffs (rodar com: python -m unittest)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buffcore import BuffTracker, CastDetector, expand_buff_area  # noqa: E402

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


class CastDetectorTest(unittest.TestCase):
    def run_series(self, values):
        det = CastDetector()
        return [i for i, v in enumerate(values) if det.update(v)]

    def test_detecta_uso_quando_o_icone_escurece(self):
        series = [120] * 10 + [50] * 20 + [120] * 10
        self.assertEqual(self.run_series(series), [10])

    def test_dois_usos_seguidos(self):
        series = [120] * 10 + [50] * 10 + [120] * 10 + [45] * 10 + [118] * 5
        self.assertEqual(self.run_series(series), [10, 30])

    def test_nao_dispara_de_novo_durante_a_recarga(self):
        # recarga clareando aos poucos (sombra girando), sem voltar ao normal
        series = [120] * 10 + [50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
        self.assertEqual(self.run_series(series), [10])

    def test_oscilacao_pequena_nao_dispara(self):
        series = [120, 110, 125, 105, 118, 100, 122, 108] * 5
        self.assertEqual(self.run_series(series), [])

    def test_escurecimento_lento_nao_dispara(self):
        # ex.: a tela do jogo escurecendo aos poucos (noite)
        series = [120 - i for i in range(80)]
        self.assertEqual(self.run_series(series), [])

    def test_programa_aberto_com_a_skill_em_recarga(self):
        series = [50] * 10 + [120] * 10 + [50] * 5
        self.assertEqual(self.run_series(series), [20])


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
