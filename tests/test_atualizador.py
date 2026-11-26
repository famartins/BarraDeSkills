"""Testes da atualizacao pelo programa (sem internet: usa arquivos locais)."""

import hashlib
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import atualizador as at  # noqa: E402


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class VersaoTest(unittest.TestCase):
    def test_compara_versoes(self):
        self.assertEqual(at.parse_version("v0.8.4"), (0, 8, 4))
        self.assertTrue(at.is_newer("0.9", "0.8.4"))
        self.assertTrue(at.is_newer("v0.10", "0.9.3"))      # 10 > 9, nao texto
        self.assertFalse(at.is_newer("0.8.4", "0.8.4"))
        self.assertFalse(at.is_newer("0.8", "0.8.4"))
        self.assertFalse(at.is_newer("", "0.8.4"))

    def test_le_a_release_do_github(self):
        data = {"tag_name": "v0.9", "name": "Barra de Skills v0.9", "body": " novidades ",
                "html_url": "https://x/rel", "draft": False, "prerelease": False,
                "assets": [{"name": "outra.txt"},
                           {"name": "BarraDeSkills-v0.9-windows.zip", "size": 10,
                            "browser_download_url": "https://x/z.zip",
                            "digest": "sha256:ABC"}]}
        info = at.parse_release(data)
        self.assertEqual((info["version"], info["url"], info["size"], info["sha256"],
                          info["notes"]), ("0.9", "https://x/z.zip", 10, "abc", "novidades"))
        self.assertIsNone(at.parse_release(dict(data, assets=[])))
        self.assertIsNone(at.parse_release(dict(data, prerelease=True)))


class PastasTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.app = os.path.join(self.tmp, "instalado")
        self.new = os.path.join(self.tmp, "novo", "BarraDeSkills")
        # programa antigo + arquivos de quem usa
        write(os.path.join(self.app, at.EXE), "exe antigo")
        write(os.path.join(self.app, "_internal", "lib_velha.pyd"), "velha")
        write(os.path.join(self.app, "_internal", "base.dll"), "base antiga")
        write(os.path.join(self.app, "skillbar_config.json"), '{"meu": 1}')
        write(os.path.join(self.app, "buffs", "ira.png"), "png")
        write(os.path.join(self.app, "diagnostico.txt"), "log\n")
        # versao nova
        write(os.path.join(self.new, at.EXE), "exe novo")
        write(os.path.join(self.new, "_internal", "base.dll"), "base nova")
        write(os.path.join(self.new, "LEIA-ME.txt"), "leia")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def zip_new(self):
        path = os.path.join(self.tmp, "rel.zip")
        with zipfile.ZipFile(path, "w") as z:
            for folder, _d, files in os.walk(os.path.dirname(self.new)):
                for fn in files:
                    full = os.path.join(folder, fn)
                    z.write(full, os.path.relpath(full, os.path.dirname(self.new)))
        return path

    def test_troca_so_o_programa(self):
        self.assertTrue(at.apply_update(self.app, None, new_dir=self.new, start=False))
        self.assertEqual(read(os.path.join(self.app, at.EXE)), "exe novo")
        self.assertEqual(read(os.path.join(self.app, "_internal", "base.dll")), "base nova")
        self.assertFalse(os.path.exists(os.path.join(self.app, "_internal", "lib_velha.pyd")))
        self.assertEqual(read(os.path.join(self.app, "skillbar_config.json")), '{"meu": 1}')
        self.assertEqual(read(os.path.join(self.app, "buffs", "ira.png")), "png")
        self.assertIn("arquivos trocados", read(os.path.join(self.app, "diagnostico.txt")))
        self.assertEqual(sorted(os.listdir(self.app)),
                         sorted([at.EXE, "_internal", "LEIA-ME.txt", "skillbar_config.json",
                                 "buffs", "diagnostico.txt"]))      # nada de .velho

    def test_falha_no_meio_volta_o_antigo(self):
        real = at.shutil.copy2

        def boom(src, dst):
            raise OSError("arquivo preso")
        at.shutil.copy2 = boom
        at_retry = at._retry
        at._retry = lambda fn, tries=1, wait=0: fn()
        try:
            self.assertFalse(at.apply_update(self.app, None, new_dir=self.new, start=False))
        finally:
            at.shutil.copy2, at._retry = real, at_retry
        self.assertEqual(read(os.path.join(self.app, at.EXE)), "exe antigo")
        self.assertEqual(read(os.path.join(self.app, "_internal", "base.dll")), "base antiga")
        self.assertIn("versao anterior", read(os.path.join(self.app, "diagnostico.txt")))

    def test_baixa_confere_e_extrai(self):
        z = self.zip_new()
        data = pathlib.Path(z).read_bytes()
        info = {"version": "0.9", "url": pathlib.Path(z).as_uri(), "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest()}
        seen = []
        got = at.download(info, os.path.join(self.tmp, "baixado"), lambda d, t: seen.append(d))
        self.assertEqual(seen[-1], len(data))
        folder = at.extract(got, os.path.join(self.tmp, "extraido"))
        self.assertEqual(read(os.path.join(folder, at.EXE)), "exe novo")
        with self.assertRaises(IOError):          # arquivo diferente do publicado
            at.download(dict(info, sha256="0" * 64), os.path.join(self.tmp, "b2"))
        with self.assertRaises(IOError):          # tamanho errado
            at.download(dict(info, size=5, sha256=""), os.path.join(self.tmp, "b3"))

    def test_zip_sem_programa_ou_com_caminho_para_fora(self):
        bad = os.path.join(self.tmp, "ruim.zip")
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("../fora.txt", "x")
        with self.assertRaises(IOError):
            at.extract(bad, os.path.join(self.tmp, "e1"))
        empty = os.path.join(self.tmp, "vazio.zip")
        with zipfile.ZipFile(empty, "w") as z:
            z.writestr("leia.txt", "x")
        with self.assertRaises(IOError):
            at.extract(empty, os.path.join(self.tmp, "e2"))


if __name__ == "__main__":
    unittest.main()
