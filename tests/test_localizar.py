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
class SlotTrackerTest(unittest.TestCase):
    """A barra segue as skills escolhidas quando o Set da barra lateral muda."""

    def setUp(self):
        from PIL import ImageDraw, ImageEnhance, ImageFont
        self.Draw, self.Enh, self.Font = ImageDraw, ImageEnhance, ImageFont
        self.side = Image.open(FIXTURE).convert("RGB")
        self.slugs = list(ESPERADO)
        magias, icons = _carregar(self.slugs)
        by = dict(zip([m["slug"] for m in magias], icons))
        self.icons = [by[s].convert("RGB") for s in self.slugs]
        self.regions = [[x, y, 44, 44] for x, y in ESPERADO.values()]

    def crops(self, img, regions):
        return [img.crop((x, y, x + w, y + h)) for x, y, w, h in regions]

    def run_check(self, img, regions, tracker=None):
        t = tracker or localizar.SlotTracker(self.icons)
        moved = {}
        for _ in range(3):       # algumas verificacoes, como no programa
            m = t.check(self.crops(img, regions), regions, lambda: (img, 0, 0))
            for i, r in m.items():
                regions[i] = r
            moved.update(m)
        return t, moved

    def test_tudo_no_lugar(self):
        t, moved = self.run_check(self.side, [list(r) for r in self.regions])
        self.assertEqual(moved, {})
        self.assertEqual(t.state, ["ok"] * 5)

    def test_bug_troca_de_set_segue_a_skill(self):
        # posicoes salvas trocadas entre si (como se o Set mudasse a ordem)
        regs = [list(r) for r in self.regions]
        regs[0], regs[1] = regs[1], regs[0]
        t, moved = self.run_check(self.side, regs)
        self.assertEqual(regs, [list(r) for r in self.regions])
        self.assertEqual(sorted(moved), [0, 1])
        self.assertEqual(t.state, ["ok"] * 5)

    def test_skill_fora_do_set_fica_apagada(self):
        img = self.side.copy()
        x, y = ESPERADO["vampirismo"]
        img.paste(self.side.crop((18, 959, 62, 1003)), (x, y))   # outra coisa no lugar
        t, moved = self.run_check(img, [list(r) for r in self.regions])
        self.assertEqual(t.state[1], "missing")
        self.assertEqual([t.state[i] for i in (0, 2, 3, 4)], ["ok"] * 4)
        self.assertFalse(t.all_missing())

    def test_recarga_com_contagem_nao_conta_como_troca(self):
        img = self.side.copy()
        font = self.Font.truetype("arial.ttf", 10)
        for x, y in ESPERADO.values():
            c = self.Enh.Brightness(img.crop((x, y, x + 44, y + 44))).enhance(0.4)
            self.Draw.Draw(c).text((10, 16), "19.9s", fill="white", font=font)
            img.paste(c, (x, y))
        t, moved = self.run_check(img, [list(r) for r in self.regions])
        self.assertEqual(moved, {})
        self.assertEqual(t.state, ["ok"] * 5)

    def test_outro_personagem_tudo_sumido(self):
        outro = Image.new("RGB", self.side.size, (40, 32, 30))
        t, _ = self.run_check(outro, [list(r) for r in self.regions])
        self.assertTrue(t.all_missing())

    def test_conta_skills_de_um_preset_na_barra_lateral(self):
        self.assertEqual(localizar.count_found(self.side, self.icons, (44, 44)), 5)
        outro = Image.new("RGB", self.side.size, (40, 32, 30))
        self.assertEqual(localizar.count_found(outro, self.icons, (44, 44)), 0)


if __name__ == "__main__":
    unittest.main()
