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

    OUTRA = (18, 959)    # posicao (na captura) de uma skill do Barbaro fora da lista

    def setUp(self):
        from PIL import ImageDraw, ImageEnhance, ImageFont
        self.Draw, self.Enh, self.Font = ImageDraw, ImageEnhance, ImageFont
        self.side = Image.open(FIXTURE).convert("RGB")
        self.slugs = list(ESPERADO)
        voc = wiki.find_vocacao(wiki.load_vocacoes(), "barbaro")
        if not all(wiki.has_icon("barbaro", m) for m in voc["magias"]):
            raise unittest.SkipTest("icones da wiki nao estao no cache")
        todos = {m["slug"]: Image.open(wiki.icon_path("barbaro", m)).convert("RGB")
                 for m in voc["magias"]}
        self.icons = [todos[s] for s in self.slugs]
        self.others = list(todos.values())
        self.regions = [[x, y, 44, 44] for x, y in ESPERADO.values()]

    def crops(self, img, regions):
        return [img.crop((x, y, x + w, y + h)) for x, y, w, h in regions]

    def tracker(self):
        return localizar.SlotTracker(self.icons, self.others)

    def run_check(self, img, regions, tracker=None, seconds=1.0, t0=0.0):
        """Verifica como o programa: a cada 0,3 s, por `seconds` segundos."""
        t = tracker or self.tracker()
        moved = {}
        for k in range(int(seconds / 0.3) + 1):
            m = t.check(self.crops(img, regions), regions, lambda: (img, 0, 0),
                        now=t0 + k * 0.3)
            for i, r in m.items():
                regions[i] = r
            moved.update(m)
        return t, moved

    def outra(self):
        x, y = self.OUTRA
        return self.side.crop((x, y, x + 44, y + 44))

    def em_recarga(self, img, slug, texto="19.9"):
        """O jogo em recarga: sem cor, escuro e com a contagem por cima."""
        x, y = ESPERADO[slug]
        c = img.crop((x, y, x + 44, y + 44))
        c = self.Enh.Brightness(self.Enh.Color(c).enhance(0)).enhance(0.45)
        self.Draw.Draw(c).text((10, 16), texto, fill="white",
                               font=self.Font.truetype("arial.ttf", 10))
        img.paste(c, (x, y))
        return img

    def test_tudo_no_lugar(self):
        t, moved = self.run_check(self.side, [list(r) for r in self.regions])
        self.assertEqual(moved, {})
        self.assertEqual(t.state, ["ok"] * 5)

    def test_troca_de_set_segue_a_skill(self):
        regs = [list(r) for r in self.regions]
        regs[0], regs[1] = regs[1], regs[0]
        t, moved = self.run_check(self.side, regs)
        self.assertEqual(regs, [list(r) for r in self.regions])
        self.assertEqual(sorted(moved), [0, 1])
        self.assertEqual(t.state, ["ok"] * 5)

    def test_outra_skill_no_lugar_fica_apagada(self):
        img = self.side.copy()
        img.paste(self.outra(), ESPERADO["vampirismo"])
        t, moved = self.run_check(img, [list(r) for r in self.regions])
        self.assertEqual(t.state[1], "missing")
        self.assertEqual([t.state[i] for i in (0, 2, 3, 4)], ["ok"] * 4)
        self.assertFalse(t.hidden())

    def test_bug_skill_usada_sem_cor_nao_fica_apagada(self):
        img = self.em_recarga(self.side.copy(), "ira-frenetica")
        self.assertGreater(localizar.match_score(img.crop((18, 759, 62, 803)),
                                                 self.icons[0]), localizar.MAYBE_SCORE)
        t, moved = self.run_check(img, [list(r) for r in self.regions], seconds=10)
        self.assertEqual(moved, {})
        self.assertEqual(t.state, ["ok"] * 5)

    def test_bug_set1_recarga_set2_volta_set1(self):
        regs = [list(r) for r in self.regions]
        set1 = self.side.copy()
        for slug in ("ira-frenetica", "vampirismo", "furia"):
            self.em_recarga(set1, slug)
        t, _ = self.run_check(set1, regs, seconds=3)                 # usou as skills
        self.assertEqual(t.state, ["ok"] * 5)
        set2 = self.side.copy()                                      # Set 2: outras skills
        for xy in ESPERADO.values():
            set2.paste(self.outra(), xy)
        t, _ = self.run_check(set2, regs, tracker=t, seconds=5, t0=3)
        self.assertEqual(t.state, ["missing"] * 5)
        self.assertFalse(t.hidden())                                 # mesma vocacao
        t, _ = self.run_check(set1, regs, tracker=t, seconds=1, t0=8)  # volta ao Set 1
        self.assertEqual(t.state, ["ok"] * 5)

    def test_todas_em_recarga_nao_apagam_nem_somem(self):
        img = self.side.copy()
        for slug in ESPERADO:
            self.em_recarga(img, slug)
        t, _ = self.run_check(img, [list(r) for r in self.regions], seconds=10)
        self.assertEqual(t.state, ["ok"] * 5)
        self.assertFalse(t.hidden())

    def test_outro_personagem_some_depois_de_firmar(self):
        outro = Image.new("RGB", self.side.size, (40, 32, 30))
        t, _ = self.run_check(outro, [list(r) for r in self.regions], seconds=1.5)
        self.assertFalse(t.hidden())          # pode ser so a recarga global
        t, _ = self.run_check(outro, [list(r) for r in self.regions], tracker=t,
                              seconds=2.0, t0=1.8)
        self.assertTrue(t.hidden())

    def test_conta_skills_de_um_preset_na_barra_lateral(self):
        self.assertEqual(localizar.count_found(self.side, self.icons, (44, 44)), 5)
        outro = Image.new("RGB", self.side.size, (40, 32, 30))
        self.assertEqual(localizar.count_found(outro, self.icons, (44, 44)), 0)


if __name__ == "__main__":
    unittest.main()
