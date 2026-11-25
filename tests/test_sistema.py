"""Testes: janela do jogo se movendo, diagnostico limitado e copia unica."""

import copy
import os
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import sistema  # noqa: E402
import skillbar as sb  # noqa: E402


class ShiftPositionsTest(unittest.TestCase):
    def test_desloca_tudo_que_foi_marcado_no_jogo(self):
        cfg = copy.deepcopy(config.DEFAULTS)
        config.switch_profile(cfg, "A", create=True)
        cfg["bars"] = [{"regions": [[10, 20, 44, 44]], "pos": [500, 600]}]
        config.switch_profile(cfg, "B", create=True)          # A fica guardado
        cfg["bars"] = [{"regions": [[30, 40, 44, 44]], "pos": [1, 2]}]
        cfg.update(sidebar_area=[0, 0, 90, 900], buff_area=[100, 50, 300, 60],
                   buff_pos=[7, 8])
        config.shift_positions(cfg, 25, -5)
        self.assertEqual(cfg["bars"][0]["regions"][0][:2], [55, 35])             # ativo (B)
        self.assertEqual(cfg["profiles"]["A"]["bars"][0]["regions"][0][:2], [35, 15])
        self.assertEqual(cfg["sidebar_area"][:2], [25, -5])
        self.assertEqual(cfg["buff_area"][:2], [125, 45])
        # o que voce arrastou na tela nao muda
        self.assertEqual(cfg["bars"][0]["pos"], [1, 2])
        self.assertEqual(cfg["buff_pos"], [7, 8])
        # tamanhos intactos
        self.assertEqual(cfg["bars"][0]["regions"][0][2:], [44, 44])

    def test_sem_nada_marcado_nao_quebra(self):
        cfg = copy.deepcopy(config.DEFAULTS)
        config.shift_positions(cfg, 5, 5)


class TrimLogTest(unittest.TestCase):
    def test_encurta_para_as_ultimas_linhas(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "diagnostico.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.writelines("linha %d\n" % i for i in range(10000))
            sb.trim_log(path, max_bytes=1000, keep=50)
            with open(path, encoding="utf-8") as f:
                lines = f.read().splitlines()
            self.assertEqual(len(lines), 51)                   # aviso + 50 linhas
            self.assertEqual(lines[-1], "linha 9999")

    def test_pequeno_fica_igual(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "diagnostico.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("ok\n")
            sb.trim_log(path)
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "ok\n")


class SingleInstanceTest(unittest.TestCase):
    def test_segunda_copia_percebe_e_acorda_a_primeira(self):
        name = "BarraTeste_" + uuid.uuid4().hex
        first = sistema.SingleInstance(name)
        self.assertFalse(first.already_running)
        second = sistema.SingleInstance(name)
        self.assertTrue(second.already_running)
        self.assertFalse(first.woken())
        second.wake_other()
        self.assertTrue(first.woken())
        self.assertFalse(first.woken())                        # aviso consumido


class TrackGameTest(unittest.TestCase):
    """track_game com a janela do jogo simulada."""

    def setUp(self):
        app = self.app = sb.SkillBar.__new__(sb.SkillBar)
        app.cfg = copy.deepcopy(config.DEFAULTS)
        app.cfg["bars"] = [{"regions": [[18, 759, 44, 44]], "pos": [900, 1300]}]
        app.cfg["buff_area"] = [280, 120, 200, 60]
        app.paused = False
        app.waiting = False
        app.game_hwnd = 1
        self.opened = 0

        def open_wizard():
            self.opened += 1
        app.open_wizard = open_wizard
        self.rect = (0, 23, 2560, 1369)
        self._orig = (sistema.client_rect, sistema.find_game_window, sb.save_config)
        sistema.client_rect = lambda h: self.rect if h else None
        sistema.find_game_window = lambda *a: 1 if self.rect else None
        sb.save_config = lambda cfg: None

    def tearDown(self):
        sistema.client_rect, sistema.find_game_window, sb.save_config = self._orig

    def test_janela_andou_posicoes_acompanham(self):
        self.app.track_game()                       # 1a vez: grava a referencia
        self.assertEqual(self.app.cfg["game_anchor"], [0, 23])
        self.rect = (300, 100, 2560, 1369)          # arrastou a janela do jogo
        self.app.track_game()
        self.assertEqual(self.app.cfg["bars"][0]["regions"][0][:2], [318, 836])
        self.assertEqual(self.app.cfg["buff_area"][:2], [580, 197])
        self.assertEqual(self.app.cfg["bars"][0]["pos"], [900, 1300])   # barra fica

    def test_desligado_nao_mexe(self):
        self.app.cfg["track_game"] = False
        self.app.cfg["game_anchor"] = [0, 23]
        self.rect = (300, 100, 2560, 1369)
        self.app.track_game()
        self.assertEqual(self.app.cfg["bars"][0]["regions"][0][:2], [18, 759])

    def test_esperando_o_jogo(self):
        self.app.waiting = True
        self.rect = None                            # jogo fechado
        self.app.game_hwnd = None
        self.app.track_game()
        self.assertEqual(self.opened, 0)
        self.rect = (0, 23, 2560, 1369)             # jogo abriu
        self.app.track_game()
        self.assertEqual(self.opened, 1)
        self.assertFalse(self.app.waiting)


class GameWindowTest(unittest.TestCase):
    def setUp(self):
        # o jogo pode estar aberto neste computador: usa um titulo que nao existe
        self._orig = sistema.DEFAULT_GAME_TITLE
        sistema.DEFAULT_GAME_TITLE = "nao_existe_titulo_123"

    def tearDown(self):
        sistema.DEFAULT_GAME_TITLE = self._orig

    def test_janela_inexistente(self):
        self.assertIsNone(sistema.find_game_window("nao_existe_123.exe"))
        self.assertIsNone(sistema.client_rect(None))


class ExeRenomeadoTest(unittest.TestCase):
    """O jogo continua reconhecido se o executavel for renomeado."""

    def setUp(self):
        self._orig = (sistema.window_info, sistema.window_title)
        self.win = {}
        sistema.window_info = lambda h: self.win[h][:2]
        sistema.window_title = lambda h: self.win[h][2]

    def tearDown(self):
        sistema.window_info, sistema.window_title = self._orig

    def test_reconhece_pelo_titulo_com_outro_exe(self):
        self.win[1] = (10, "client.exe", "BloodStone - The Ancient Curse [v1.49]")
        self.assertTrue(sistema.is_game_window(1, "client_02.exe"))

    def test_mesmo_exe(self):
        self.win[1] = (10, "client_02.exe", "Inventory")
        self.assertTrue(sistema.is_game_window(1, "client_02.exe"))

    def test_outra_janela_nao_e_o_jogo(self):
        self.win[1] = (11, "chrome.exe", "Bloodpedia - Wiki")
        self.assertFalse(sistema.is_game_window(1, "client_02.exe"))


if __name__ == "__main__":
    unittest.main()
