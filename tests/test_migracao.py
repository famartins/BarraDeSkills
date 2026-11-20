"""Testes da passagem pelo assistente (vinculo dos buffs com as magias)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import skillbar as sb  # noqa: E402

MAGIAS = {"ira-frenetica": "Ira Frenética", "vampirismo": "Vampirismo", "furia": "Fúria",
          "giro-fulminante": "Giro Fulminante", "giro-sanguinario": "Giro Sanguinário"}


class MatchByNameTest(unittest.TestCase):
    def test_nomes_curtos_e_sem_acento(self):
        self.assertEqual(sb.match_by_name("IRA", MAGIAS), "ira-frenetica")
        self.assertEqual(sb.match_by_name("VAMPIRISMO", MAGIAS), "vampirismo")
        self.assertEqual(sb.match_by_name("furia", MAGIAS), "furia")

    def test_ambiguo_ou_curto_nao_liga(self):
        self.assertIsNone(sb.match_by_name("Giro", MAGIAS))
        self.assertIsNone(sb.match_by_name("xx", MAGIAS))


class FinishWizardTest(unittest.TestCase):
    """Simula a config da v1 (buffs ligados por posicao) passando pelo assistente."""

    def make_app(self, cfg):
        app = sb.SkillBar.__new__(sb.SkillBar)   # sem abrir janelas
        app.cfg = dict(sb.DEFAULTS, **cfg)
        app.vocacoes = sb.wiki.load_vocacoes()
        app.load_buffs = lambda: None
        app.apply_new_regions = lambda: None
        return app

    def setUp(self):
        self._save = sb.save_config
        sb.save_config = lambda cfg: None

    def tearDown(self):
        sb.save_config = self._save

    def test_buffs_da_v1_religados_pelo_nome(self):
        app = self.make_app({"buffs": [{"name": "IRA", "skill": 1, "file": "a"},
                                       {"name": "VAMPIRISMO", "skill": 3, "file": "b"}]})
        app.finish_wizard("barbaro", ["furia", "vampirismo", "ira-frenetica"],
                          [[0, 0, 44, 44]] * 3, "vertical")
        ira, vamp = app.cfg["buffs"]
        self.assertEqual((ira["skill"], ira["skill_slug"]), (2, "ira-frenetica"))
        self.assertEqual((vamp["skill"], vamp["skill_slug"]), (1, "vampirismo"))
        self.assertEqual(app.cfg["orientation"], "vertical")

    def test_reordenar_mantem_o_buff_na_mesma_magia(self):
        app = self.make_app({"magias": ["ira-frenetica", "vampirismo"],
                             "buffs": [{"name": "X", "skill": 1, "file": "a"}]})
        app.finish_wizard("barbaro", ["vampirismo", "furia", "ira-frenetica"],
                          [[0, 0, 44, 44]] * 3, "horizontal")
        self.assertEqual(app.cfg["buffs"][0]["skill"], 0)   # continua no Vampirismo

    def test_magia_retirada_da_barra_solta_o_buff(self):
        app = self.make_app({"magias": ["ira-frenetica", "vampirismo"],
                             "buffs": [{"name": "X", "skill": 0, "file": "a"}]})
        app.finish_wizard("barbaro", ["vampirismo"], [[0, 0, 44, 44]], "horizontal")
        self.assertIsNone(app.cfg["buffs"][0]["skill"])


if __name__ == "__main__":
    unittest.main()
