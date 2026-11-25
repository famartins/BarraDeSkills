"""Testes da localizacao automatica.

Usa uma captura real da barra lateral do Barbaro em cache/teste/ (fora do git,
porque as imagens sao do jogo). Sem ela, ou sem os icones da wiki no cache,
os testes que dependem dela sao pulados.
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PIL import Image  # noqa: E402

import localizar  # noqa: E402
import wiki  # noqa: E402

FIXTURE = os.path.join(ROOT, "cache", "teste", "barra_lateral_barbaro.png")
# posicoes (x, y) conferidas a olho na captura
ESPERADO = {"ira-frenetica": (18, 759), "vampirismo": (18, 859), "furia": (18, 809),
            "apocalipse": (18, 509), "golpe-triplo": (18, 559)}


def _carregar(slugs):
    voc = wiki.find_vocacao(wiki.load_vocacoes(), "barbaro")
    magias = [m for m in voc["magias"] if m["slug"] in slugs]
    if not all(wiki.has_icon("barbaro", m) for m in magias):
        raise unittest.SkipTest("icones da wiki nao estao no cache")
    return magias, [Image.open(wiki.icon_path("barbaro", m)) for m in magias]


@unittest.skipUnless(os.path.isfile(FIXTURE), "sem captura de teste em cache/teste/")
class LocalizarTest(unittest.TestCase):
    def setUp(self):
        self.area = Image.open(FIXTURE).convert("RGB")

    def test_acha_as_magias_na_posicao_certa(self):
        magias, icons = _carregar(list(ESPERADO) + ["esmagar"])
        scale, res = localizar.locate(self.area, icons)
        self.assertAlmostEqual(scale, 1.0)
        for m, r in zip(magias, res):
            if m["slug"] == "esmagar":            # nao esta na barra lateral
                self.assertEqual(r["status"], "nao_achou")
            else:
                self.assertEqual(r["status"], "ok", m["slug"])
                self.assertEqual(r["box"][:2], ESPERADO[m["slug"]], m["slug"])

    def test_icone_sem_cor_vira_duvida(self):
        _m, icons = _carregar(["golpe-colossal"])
        _s, res = localizar.locate(self.area, icons)
        self.assertEqual(res[0]["status"], "duvida")

    def test_outra_resolucao(self):
        magias, icons = _carregar(list(ESPERADO))
        small = self.area.resize((round(self.area.width * 0.75),
                                  round(self.area.height * 0.75)), Image.BILINEAR)
        _s, res = localizar.locate(small, icons)
        for m, r in zip(magias, res):
            ex, ey = ESPERADO[m["slug"]]
            self.assertEqual(r["status"], "ok", m["slug"])
            self.assertLessEqual(abs(r["box"][1] - ey * 0.75), 3, m["slug"])


@unittest.skipUnless(os.path.isfile(FIXTURE), "sem captura de teste em cache/teste/")
class PersonagemCertoTest(unittest.TestCase):
    """A barra so aparece se as skills na tela forem as do personagem escolhido."""

    def setUp(self):
        area = Image.open(FIXTURE).convert("RGB")
        self.slugs = list(ESPERADO)
        self.crops = [area.crop((x, y, x + 44, y + 44)) for x, y in ESPERADO.values()]
        _m, icons = _carregar(self.slugs)
        by = dict(zip([m["slug"] for m in _m], icons))
        self.icons = [by[s] for s in self.slugs]

    def test_skills_do_personagem_batem(self):
        self.assertTrue(localizar.skills_match(self.crops, self.icons))

    def test_bug_outro_personagem_logado_nao_bate(self):
        # mesmas posicoes, mas com icones de outras skills (como o Arqueiro logado
        # usando o preset do Barbaro)
        trocados = self.icons[1:] + self.icons[:1]
        self.assertFalse(localizar.skills_match(self.crops, trocados))

    def test_uma_skill_em_recarga_ainda_conta_como_certo(self):
        from PIL import ImageEnhance
        escuras = [ImageEnhance.Brightness(c).enhance(0.35) for c in self.crops]
        escuras[2] = self.crops[2]
        self.assertTrue(localizar.skills_match(escuras, self.icons))

    def test_sem_icones_conhecidos_nao_decide(self):
        self.assertIsNone(localizar.skills_match(self.crops, [None] * 5))


if __name__ == "__main__":
    unittest.main()
