"""Testes da configuracao: migracao das versoes antigas e personagens."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402

R = [18, 759, 44, 44]


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "cfg.json")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_migra_configuracao_da_v2(self):
        self.write({"regions": [R, R], "magias": ["furia", "vampirismo"],
                    "orientation": "vertical", "pos": [10, 20], "vocacao": "barbaro",
                    "zoom": 0.9, "buffs": [{"name": "IRA", "skill": 1, "file": "b.png"}]})
        cfg = config.load_config(self.path)
        self.assertNotIn("regions", cfg)
        self.assertEqual(len(cfg["bars"]), 1)
        b = cfg["bars"][0]
        self.assertEqual((b["regions"], b["magias"], b["orientation"], b["pos"]),
                         ([R, R], ["furia", "vampirismo"], "vertical", [10, 20]))
        self.assertEqual(cfg["profile"], "Principal")
        self.assertEqual(cfg["profiles"]["Principal"]["vocacao"], "barbaro")
        self.assertEqual(cfg["zoom"], 0.9)            # opcoes gerais preservadas
        self.assertEqual(len(cfg["buffs"]), 1)

    def test_primeiro_uso(self):
        cfg = config.load_config(self.path)           # arquivo nao existe
        self.assertFalse(config.is_configured(cfg))
        self.assertEqual(cfg["bars"], [])
        self.assertEqual((cfg["profile"], cfg["profiles"]), ("", {}))   # nenhum vazio
        config.switch_profile(cfg, "Cherykan", create=True)
        self.assertEqual(config.profile_names(cfg), ["Cherykan"])

    def test_personagens_sao_independentes(self):
        cfg = config.load_config(self.path)
        config.switch_profile(cfg, "Principal", create=True)
        cfg.update(vocacao="barbaro", bars=[{"regions": [R], "magias": ["furia"],
                                             "orientation": "horizontal", "pos": None}])
        config.switch_profile(cfg, "Maguinho", create=True)
        self.assertEqual(cfg["bars"], [])             # personagem novo, vazio
        self.assertEqual(cfg["vocacao"], "")
        cfg["vocacao"] = "mago"
        config.switch_profile(cfg, "Principal")
        self.assertEqual(cfg["vocacao"], "barbaro")   # voltou o do outro
        self.assertEqual(cfg["bars"][0]["magias"], ["furia"])
        config.save_config(cfg, self.path)
        again = config.load_config(self.path)
        self.assertEqual(again["profiles"]["Maguinho"]["vocacao"], "mago")
        self.assertEqual(again["profile"], "Principal")

    def test_apagar_personagem_ativo_abre_outro(self):
        cfg = config.load_config(self.path)
        config.switch_profile(cfg, "A", create=True)
        cfg["vocacao"] = "mago"
        config.switch_profile(cfg, "B", create=True)
        config.delete_profile(cfg, "B")
        self.assertNotIn("B", cfg["profiles"])
        self.assertIn(cfg["profile"], ("A", "Principal"))

    def test_renomear(self):
        cfg = config.load_config(self.path)
        config.switch_profile(cfg, "Principal", create=True)
        self.assertTrue(config.rename_profile(cfg, "Principal", "Cherykan"))
        self.assertEqual(cfg["profile"], "Cherykan")
        self.assertFalse(config.rename_profile(cfg, "Cherykan", ""))

    def test_indices_globais(self):
        cfg = config.load_config(self.path)
        cfg["bars"] = [{"regions": [R, R], "magias": ["a", "b"]},
                       {"regions": [R], "magias": []}]        # sem nomes: desconhecida
        self.assertEqual(config.all_magias(cfg), ["a", "b", None])
        self.assertEqual(config.bar_offsets(cfg), [0, 2])
        self.assertEqual(len(config.all_regions(cfg)), 3)



class FundoDasBarrasTest(unittest.TestCase):
    def test_fundo_preto_antigo_vira_o_do_tema(self):
        import config as c
        self.assertEqual(c.migrate({"bg": "#0b0b0b"})["bg"], "#002E34")

    def test_cor_escolhida_pela_pessoa_fica(self):
        import config as c
        self.assertEqual(c.migrate({"bg": "#123456"})["bg"], "#123456")


if __name__ == "__main__":
    unittest.main()
