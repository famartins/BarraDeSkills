"""Testes da passagem pelo assistente (vinculo dos buffs com as magias)."""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import skillbar as sb  # noqa: E402

MAGIAS = {"ira-frenetica": "Ira Frenética", "vampirismo": "Vampirismo", "furia": "Fúria",
          "giro-fulminante": "Giro Fulminante", "giro-sanguinario": "Giro Sanguinário"}
R = [0, 0, 44, 44]


def bar(magias, orientation="horizontal"):
    return {"magias": list(magias), "regions": [R] * len(magias), "orientation": orientation}


class MatchByNameTest(unittest.TestCase):
    def test_nomes_curtos_e_sem_acento(self):
        self.assertEqual(sb.match_by_name("IRA", MAGIAS), "ira-frenetica")
        self.assertEqual(sb.match_by_name("VAMPIRISMO", MAGIAS), "vampirismo")
        self.assertEqual(sb.match_by_name("furia", MAGIAS), "furia")

    def test_ambiguo_ou_curto_nao_liga(self):
        self.assertIsNone(sb.match_by_name("Giro", MAGIAS))
        self.assertIsNone(sb.match_by_name("xx", MAGIAS))


class FinishWizardTest(unittest.TestCase):
    """Simula configuracoes passando pelo assistente (sem abrir janelas)."""

    def make_app(self, raw):
        cfg = copy.deepcopy(config.DEFAULTS)
        cfg.update(copy.deepcopy(raw))
        app = sb.SkillBar.__new__(sb.SkillBar)
        app.cfg = config.migrate(cfg)
        app.vocacoes = sb.wiki.load_vocacoes()
        app.load_buffs = lambda: None
        app.build_bars = lambda: None
        return app

    def setUp(self):
        self._save = sb.save_config
        sb.save_config = lambda cfg: None

    def tearDown(self):
        sb.save_config = self._save

    def test_buffs_da_v1_religados_pelo_nome(self):
        app = self.make_app({"regions": [R] * 4,
                             "buffs": [{"name": "IRA", "skill": 1, "file": "a"},
                                       {"name": "VAMPIRISMO", "skill": 3, "file": "b"}]})
        app.finish_wizard("barbaro", [bar(["furia", "vampirismo", "ira-frenetica"],
                                          "vertical")])
        ira, vamp = app.cfg["buffs"]
        self.assertEqual((ira["skill"], ira["skill_slug"]), (2, "ira-frenetica"))
        self.assertEqual((vamp["skill"], vamp["skill_slug"]), (1, "vampirismo"))
        self.assertEqual(app.cfg["bars"][0]["orientation"], "vertical")

    def test_bug_buff_da_v1_cuja_magia_saiu_da_barra(self):
        # IRA estava na posicao 1 da barra antiga; a Ira Frenetica nao esta na nova.
        # Antes: o buff continuava na posicao 1, em cima de outra skill.
        app = self.make_app({"regions": [R] * 2,
                             "buffs": [{"name": "IRA", "skill": 1, "file": "a"}]})
        app.finish_wizard("barbaro", [bar(["furia", "vampirismo"])])
        b = app.cfg["buffs"][0]
        self.assertIsNone(b["skill"])
        self.assertEqual(b["skill_slug"], "ira-frenetica")   # volta se a magia voltar

    def test_buff_sem_magia_identificavel_fica_solto(self):
        app = self.make_app({"regions": [R],
                             "buffs": [{"name": "Buff", "skill": 0, "file": "a"}]})
        app.finish_wizard("barbaro", [bar(["furia"])])
        self.assertIsNone(app.cfg["buffs"][0]["skill"])

    def test_reordenar_mantem_o_buff_na_mesma_magia(self):
        app = self.make_app({"bars": [bar(["ira-frenetica", "vampirismo"])],
                             "buffs": [{"name": "X", "skill": 1, "file": "a"}]})
        app.finish_wizard("barbaro", [bar(["vampirismo", "furia", "ira-frenetica"])])
        self.assertEqual(app.cfg["buffs"][0]["skill"], 0)   # continua no Vampirismo

    def test_magia_retirada_da_barra_solta_o_buff(self):
        app = self.make_app({"bars": [bar(["ira-frenetica", "vampirismo"])],
                             "buffs": [{"name": "X", "skill": 0, "file": "a"}]})
        app.finish_wizard("barbaro", [bar(["vampirismo"])])
        self.assertIsNone(app.cfg["buffs"][0]["skill"])

    def test_buff_na_segunda_barra_usa_indice_global(self):
        app = self.make_app({"bars": [bar(["ira-frenetica"])],
                             "buffs": [{"name": "X", "skill": 0, "file": "a"}]})
        app.finish_wizard("barbaro", [bar(["furia", "giro-fulminante"]),
                                      bar(["ira-frenetica"])])
        self.assertEqual(app.cfg["buffs"][0]["skill"], 2)   # 2 skills na barra 1 + 0
        self.assertEqual(config.bar_offsets(app.cfg), [0, 2])

    def test_barra_vazia_e_descartada(self):
        app = self.make_app({})
        app.finish_wizard("barbaro", [bar([]), bar(["furia"])], only_buffs=False)
        self.assertEqual(len(app.cfg["bars"]), 1)
        self.assertEqual(app.cfg["bars"][0]["magias"], ["furia"])

    def test_so_buffs_sem_magias(self):
        app = self.make_app({})
        app.finish_wizard("barbaro", [bar([]), bar([])], only_buffs=True)
        self.assertEqual(app.cfg["bars"], [])
        self.assertTrue(config.is_configured(app.cfg))


if __name__ == "__main__":
    unittest.main()
