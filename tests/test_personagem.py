"""Testes do personagem pintado como no provador de roupas da Bloodpedia."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image  # noqa: E402

import wiki  # noqa: E402

CORES = ["#CE4040", "#41CE57", "#405ACE", "#CDCE40", "#F0F0C5", "#40C1CE"]


def folha():
    """Folha 256x128: bloco 1 = base cinza (100), bloco 2 = mascara.
    Pixel (40,40) marcado de vermelho na mascara, (41,40) sem mascara."""
    img = Image.new("RGBA", (256, 128), (0, 0, 0, 0))
    for x in (40, 41):
        img.putpixel((x, 40), (100, 100, 100, 255))
    img.putpixel((128 + 40, 40), (255, 0, 0, 255))
    return img


class RenderOutfitTest(unittest.TestCase):
    def test_pinta_onde_a_mascara_manda_e_recorta(self):
        out = wiki.render_outfit(folha(), CORES, margin=0)
        self.assertEqual(out.size, (2, 1))                    # so o personagem
        r, g, b, a = out.getpixel((0, 0))
        self.assertEqual((r, g, b, a), (161, 50, 50, 255))    # 100 * cor * 2
        self.assertEqual(out.getpixel((1, 0)), (100, 100, 100, 255))   # sem mascara

    def test_folha_vazia(self):
        self.assertIsNone(wiki.render_outfit(Image.new("RGBA", (128, 128)), CORES))

    def test_todas_as_vocacoes_tem_roupa(self):
        for v in wiki.load_vocacoes():
            p = v.get("personagem") or {}
            self.assertTrue(p.get("sprite_url"), v["slug"])
            self.assertEqual(len(p.get("cores", [])), 6, v["slug"])


if __name__ == "__main__":
    unittest.main()
