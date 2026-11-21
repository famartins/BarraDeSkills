#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Barra de Skills
===============
Copia, em tempo real, os icones das skills do Bloodstone e monta uma ou duas
barras (horizontais ou verticais), sempre visiveis por cima do jogo. Os buffs
ativos aparecem junto da skill que os gera, piscam quando estao acabando e,
opcionalmente, apitam.

O programa so LE a imagem da tela. Nao mexe na memoria do jogo e nao envia
cliques nem teclas para ele.

Uso:
    python skillbar.py              inicia (no primeiro uso abre o assistente)
    python skillbar.py --calibrar   marca os icones da barra 1 manualmente
    python skillbar.py --monitor 2  usa o monitor 2 nas telas de marcacao
    python skillbar.py --janelas    lista as janelas abertas (programa e titulo)
    python skillbar.py --jogo X.exe barras so aparecem com o programa X.exe ativo

Atalhos (funcionam mesmo com o foco no jogo):
    Ctrl+Alt+F10   liga/desliga o click-through (cliques atravessam as barras)
    Ctrl+Alt+F11   abre as configuracoes
    Ctrl+Alt+F12   cadastra um buff (com o buff ativo na tela)

Arquivos: config.py (configuracao e personagens), overlay.py (janelas por cima
do jogo), telas.py (telas), wiki.py (dados das vocacoes), localizar.py (achar as
magias na tela), buffcore.py (reconhecimento e cronometro dos buffs).
"""

import argparse
import os
import sys
import threading
import time
import unicodedata

if sys.platform != "win32":
    print("Este programa foi feito para Windows.")
    sys.exit(1)

import config  # noqa: E402  (so biblioteca padrao)
from config import BASE_DIR, load_config  # noqa: E402

FROZEN = getattr(sys, "frozen", False)   # rodando como BarraDeSkills.exe


def log_path():
    """diagnostico.txt: indicado pelo iniciar.bat ou, no .exe, ao lado dele."""
    return os.environ.get("BARRA_LOG") or (
        os.path.join(BASE_DIR, "diagnostico.txt") if FROZEN else None)


def log_error(text):
    """Acrescenta uma linha ao diagnostico.txt."""
    path = log_path()
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(time.strftime("[%H:%M:%S] ") + text.rstrip() + "\n")
    except OSError:
        pass


try:
    import tkinter as tk
    from tkinter import messagebox
    import winsound
    import mss
    import numpy as np
    from PIL import Image
    import telas
    import wiki
    from buffcore import BuffTracker, CastDetector, expand_buff_area, find_template
    from overlay import (BROWSERS, Bar, BuffWindow, Calibrator, enable_dpi_awareness,
                         grab_image, key_down, list_windows, user32, window_info,
                         window_title, VK_CONTROL, VK_MENU, VK_F10, VK_F11, VK_F12)
except ImportError as exc:
    log_error("Faltam bibliotecas: %r" % exc)
    print("Faltam bibliotecas:", exc)
    print("Rode:  pip install -r requirements.txt   (ou use o iniciar.bat)")
    if sys.stdin is not None:
        input("Pressione Enter para sair...")
    sys.exit(1)


def _norm(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(text.lower().split())


def match_by_name(buff_name, magias):
    """Slug da magia cujo nome comeca com (ou contem) o nome do buff, se for unica.
    magias = {slug: nome}."""
    n = _norm(buff_name)
    if len(n) < 3:
        return None
    for test in (lambda m: m == n, lambda m: m.startswith(n), lambda m: n in m):
        hits = [s for s, nome in magias.items() if test(_norm(nome))]
        if len(hits) == 1:
            return hits[0]
    return None


def alive(window):
    """True se a janela existe e nao foi fechada."""
    try:
        return window is not None and bool(window.winfo_exists())
    except Exception:
        return False


def save_config(cfg):
    config.save_config(cfg)


DEFAULTS = config.DEFAULTS


# --------------------------------------------------------------------------
# Programa
# --------------------------------------------------------------------------
class SkillBar:
    def __init__(self, force_calibrate=False, monitor=None):
        self.cfg = load_config()
        if monitor:
            self.cfg["monitor"] = monitor
            save_config(self.cfg)
        self.force_calibrate = force_calibrate

        # janela raiz escondida: as barras e as telas sao janelas filhas dela
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Barra de Skills")
        self.root.report_callback_exception = self.on_tk_error

        self.sct = mss.mss()
        self.bars = []            # overlay.Bar de cada barra com skills
        self.cast_detectors = []  # um CastDetector por skill (indice global)
        self.paused = False
        self.settings = None      # telas.Settings aberta
        self.wizard = None        # telas.Wizard aberto
        self.hk = {}
        self.last_error = None
        self.bar_visible = True   # jogo em primeiro plano
        self.vocacoes = wiki.load_vocacoes()

        # buffs
        self.buffs = []
        self.tracker = BuffTracker()
        self.float_win = BuffWindow(self)   # buffs soltos / modo so buffs
        self.warned = set()       # buffs que ja apitaram nesta ativacao
        self.buff_err = None
        self.load_buffs()

    def on_tk_error(self, exc_type, exc, tb):
        import traceback
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        print("Erro:", text)
        log_error(text)

    def save(self):
        save_config(self.cfg)

    # -- ciclo de vida --
    def start(self):
        if self.force_calibrate:
            self.calibrate()
        self.build_bars()
        self.root.update()
        if self.needs_wizard():
            self.root.after(100, self.open_wizard)
        self.tick()
        self.poll_hotkeys()
        self.keep_on_top()
        self.update_visibility()
        self.buff_tick()
        try:
            self.root.mainloop()
        finally:
            save_config(self.cfg)

    def needs_wizard(self):
        """Primeiro uso, ou personagem que ainda nao escolheu a vocacao."""
        return not config.is_configured(self.cfg) or (
            not self.cfg.get("vocacao") and not self.cfg.get("wizard_skipped"))

    def quit(self):
        save_config(self.cfg)
        self.root.quit()

    def build_bars(self):
        """(Re)cria as janelas das barras a partir de cfg["bars"]."""
        for bar in self.bars:
            bar.destroy()
        self.bars = [Bar(self, i) for i, b in enumerate(self.cfg["bars"]) if b["regions"]]
        self.cast_detectors = []
        self.float_win.key = None

    def first_bar_window(self):
        shown = [b for b in self.bars if b.shown]
        return shown[0].win if shown else None

    # -- aparencia --
    def apply_styles(self):
        for bar in self.bars:
            bar.apply_style()
        self.float_win.apply_alpha()

    def set_opacity(self, value):
        self.cfg["opacity"] = max(0.2, min(1.0, float(value)))
        self.apply_styles()

    def set_click_through(self, on, save=True):
        self.cfg["click_through"] = bool(on)
        self.apply_styles()
        if alive(self.settings):
            self.settings.sync_click_through()
        if save:
            save_config(self.cfg)

    def toggle_click_through(self):
        self.set_click_through(not self.cfg["click_through"])

    def set_orientation(self, index, orientation):
        if 0 <= index < len(self.cfg["bars"]):
            self.cfg["bars"][index]["orientation"] = (
                "vertical" if orientation == "vertical" else "horizontal")
            for bar in self.bars:
                if bar.index == index:
                    bar.last_size = None   # forca remontar a barra
            save_config(self.cfg)

    def set_only_buffs(self, on):
        self.cfg["only_buffs"] = bool(on)
        if on:
            for bar in self.bars:
                bar.hide()
        self.float_win.key = None
        save_config(self.cfg)

    def on_wheel(self, e):
        step = 0.1 if e.delta > 0 else -0.1
        self.cfg["zoom"] = round(max(0.5, min(4.0, float(self.cfg["zoom"]) + step)), 1)
        save_config(self.cfg)

    # -- calibracao manual (alternativa ao assistente) --
    def calibrate(self):
        self.paused = True
        try:
            for bar in self.bars:
                bar.hide()
            self.root.update()
            time.sleep(0.35)
            result = Calibrator(self.root, self.cfg["monitor"]).run()
        finally:
            self.paused = False
        if not result:
            return False
        old = config.all_magias(self.cfg)
        if not self.cfg["bars"]:
            self.cfg["bars"].append(config.new_bar())
        # marcacao manual: nao sabemos o nome das skills
        self.cfg["bars"][0].update(regions=result, magias=[])
        self.relink_buffs(old, config.all_magias(self.cfg))
        save_config(self.cfg)
        return True

    def recalibrate(self):
        if alive(self.settings):
            self.settings.destroy()
        self.calibrate()
        self.load_buffs()
        self.build_bars()

    # -- personagens --
    def switch_profile(self, name, create=False):
        save_config(self.cfg)
        config.switch_profile(self.cfg, name, create=create)
        save_config(self.cfg)
        self.tracker = BuffTracker()
        self.warned = set()
        self.load_buffs()
        self.build_bars()

    def new_profile(self, name):
        self.switch_profile(name, create=True)

    def rename_profile(self, old, new):
        ok = config.rename_profile(self.cfg, old, new)
        if ok:
            save_config(self.cfg)
        return ok

    def delete_profile(self, name):
        config.delete_profile(self.cfg, name)
        save_config(self.cfg)
        self.tracker = BuffTracker()
        self.load_buffs()
        self.build_bars()

    # -- desenho das barras --
    def tick(self):
        t0 = time.perf_counter()
        if not self.paused and self.bar_visible and self.bars:
            try:
                self.render()
            except Exception as exc:  # nao deixa o programa cair por um frame ruim
                msg = repr(exc)
                if msg != self.last_error:
                    print("Erro ao atualizar a barra:", msg)
                    log_error("Erro ao atualizar a barra: " + msg)
                    self.last_error = msg
        fps = max(1, int(self.cfg["fps"]))
        delay = max(1, int(1000 / fps - (time.perf_counter() - t0) * 1000))
        self.root.after(delay, self.tick)

    def render(self):
        """Captura as skills, detecta quando foram usadas e redesenha as barras
        (no modo so buffs a captura continua, so para detectar o uso)."""
        all_crops = []
        for bar in self.bars:
            regs = bar.data["regions"]
            left, top = min(r[0] for r in regs), min(r[1] for r in regs)
            right = max(r[0] + r[2] for r in regs)
            bottom = max(r[1] + r[3] for r in regs)
            area = grab_image(self.sct, {"left": left, "top": top,
                                         "width": right - left, "height": bottom - top})
            crops = [area.crop((x - left, y - top, x - left + w, y - top + h))
                     for x, y, w, h in regs]
            all_crops += crops
            if not self.cfg.get("only_buffs"):
                bar.render(crops)
                bar.show()
        self.detect_casts(all_crops)

    def detect_casts(self, crops):
        """Percebe quando uma skill e usada (icone escurece) e reinicia o tempo do
        buff ligado a ela, caso ele ja esteja ativo (skill reusada antes de acabar)."""
        if not self.buffs:
            return
        if len(self.cast_detectors) != len(crops):
            self.cast_detectors = [CastDetector() for _ in crops]
        now = time.monotonic()
        for i, (c, det) in enumerate(zip(crops, self.cast_detectors)):
            if not det.update(np.asarray(c).mean()):
                continue
            for b in self.buffs:
                if (b.get("skill") == i and b.get("restart_on_cast", True)
                        and self.tracker.active(b["file"], now)):
                    self.tracker.restart(b["file"], now)
                    self.warned.discard(b["file"])

    # -- visibilidade: so aparece quando o jogo esta em primeiro plano --
    def game_is_active(self):
        proc = str(self.cfg.get("game_process", "")).strip().lower()
        title = str(self.cfg.get("game_title", "")).strip().lower()
        if not proc and not title:
            return True  # nada configurado: sempre visivel
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return self.bar_visible  # momento de transicao, mantem como esta
        pid, exe = window_info(hwnd)
        if pid == os.getpid():
            return True  # janelas do proprio programa (configuracoes etc.)
        if proc and exe.lower() != proc:
            return False
        if title and title not in window_title(hwnd).lower():
            return False
        return True

    def update_visibility(self):
        if not self.paused:
            try:
                want = self.game_is_active()
            except Exception:
                want = True
            if want != self.bar_visible:
                self.bar_visible = want
                if not want:
                    for bar in self.bars:
                        bar.hide()
                # ao voltar, tick() mostra as barras de novo
        self.root.after(150, self.update_visibility)

    def keep_on_top(self):
        if not self.paused:
            try:
                for bar in self.bars:
                    bar.raise_topmost()
                self.float_win.raise_topmost()
            except Exception:
                pass
        self.root.after(1500, self.keep_on_top)

    def poll_hotkeys(self):
        if not self.paused:
            combo = key_down(VK_CONTROL) and key_down(VK_MENU)
            for name, vk, action in (("ct", VK_F10, self.toggle_click_through),
                                     ("cfg", VK_F11, self.open_settings),
                                     ("buff", VK_F12, self.add_buff)):
                down = combo and key_down(vk)
                if down and not self.hk.get(name):
                    action()
                self.hk[name] = down
        self.root.after(50, self.poll_hotkeys)

    # -- buffs --
    def load_buffs(self):
        self.buffs = []
        for ci, b in enumerate(self.cfg.get("buffs", [])):
            try:
                img = Image.open(os.path.join(BASE_DIR, b["file"])).convert("RGB")
            except (OSError, KeyError):
                continue
            self.buffs.append({
                "ci": ci,
                "name": b.get("name", "Buff"),
                "duration": float(b.get("duration", 0) or 0),
                "desc": b.get("desc", ""),
                "skill": b.get("skill"),
                "restart_on_cast": b.get("restart_on_cast", True),
                "file": b["file"],
                "img": img,
                "arr": np.asarray(img),
            })

    def buff_tick(self):
        if not self.paused:
            try:
                self.scan_buffs()
            except Exception as exc:
                msg = repr(exc)
                if msg != self.buff_err:
                    print("Erro nos buffs:", msg)
                    log_error("Erro nos buffs: " + msg)
                    self.buff_err = msg
        self.root.after(100, self.buff_tick)

    def scan_buffs(self):
        now = time.monotonic()
        area = self.cfg.get("buff_area")
        if not area or not self.buffs or not self.bar_visible:
            if area and self.buffs:
                # jogo fora de foco: nao da para ver os icones; o cronometro segue valendo
                self.tracker.suspend()
            self.show_buffs([], now)
            return
        x, y, w, h = self.scan_area(area)
        shot = self.sct.grab({"left": x, "top": y, "width": w, "height": h})
        arr = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(
            shot.height, shot.width, 4)[:, :, 2::-1]   # BGRA -> RGB
        thr = float(self.cfg["buff_threshold"])
        active = []
        for b in self.buffs:
            found = find_template(arr, b["arr"], thr) is not None
            self.tracker.update(b["file"], found, now, b["duration"])
            if self.tracker.active(b["file"], now):
                active.append(b)
        self.warn_sound(active, now)
        self.show_buffs(active, now)

    def show_buffs(self, active, now):
        """Distribui os buffs ativos: junto da skill (na barra dela) ou soltos."""
        visible = self.bar_visible
        if self.cfg.get("only_buffs") or not self.bars:
            for bar in self.bars:
                bar.buff_win.update([], False, now)
            self.float_win.update([(b, None) for b in active], visible, now)
            return
        offsets = config.bar_offsets(self.cfg)
        placed = set()
        for bar in self.bars:
            off, n = offsets[bar.index], len(bar.data["regions"])
            items = []
            for b in active:
                s = b.get("skill")
                if isinstance(s, int) and off <= s < off + n:
                    items.append((b, s - off))
                    placed.add(b["file"])
            bar.buff_win.update(items, visible and bar.shown, now)
        loose = [(b, None) for b in active if b["file"] not in placed]
        self.float_win.update(loose, visible, now)

    def remaining(self, b, now):
        el = self.tracker.elapsed(b["file"], now)
        if el is None or not b["duration"]:
            return None
        return b["duration"] - el

    def warn_state(self, b, now):
        """0 = normal; 1/2 = acabando (alterna para piscar ~3 vezes por segundo)."""
        warn = float(self.cfg.get("warn_seconds") or 0)
        rem = self.remaining(b, now)
        if warn <= 0 or rem is None or rem > warn:
            return 0
        return 1 + int(now * 3) % 2

    def warn_sound(self, active, now):
        """Apito (opcional) uma vez quando cada buff comeca a piscar."""
        files = {b["file"] for b in active}
        self.warned &= files
        if not self.cfg.get("warn_sound"):
            return
        for b in active:
            if b["file"] not in self.warned and self.warn_state(b, now):
                self.warned.add(b["file"])
                self.beep()

    def beep(self):
        def run():
            try:
                winsound.Beep(1500, 110)
                winsound.Beep(1900, 160)
            except RuntimeError:
                pass
        threading.Thread(target=run, daemon=True).start()

    def scan_area(self, area):
        """Area realmente varrida (amplia sozinho se a marcada for pequena)."""
        iw = max((b["img"].width for b in self.buffs), default=16)
        ih = max((b["img"].height for b in self.buffs), default=16)
        vs = self.sct.monitors[0]
        return expand_buff_area(area, iw, ih, (vs["left"], vs["top"], vs["width"], vs["height"]))

    # -- marcacao na tela congelada --
    def ui_windows(self):
        """Janelas de configuracao/assistente abertas."""
        return [w for w in (self.settings, self.wizard) if alive(w)]

    def pick_rect(self, message, click_size=None):
        """Congela a tela e deixa marcar um retangulo (ou so clicar, com click_size).
        Retorna (retangulo_na_tela, recorte_da_imagem) ou (None, None)."""
        self.paused = True
        hidden = [w for w in self.ui_windows() if w.winfo_viewable()]
        rect = crop = None
        try:
            for w in hidden:
                w.withdraw()
            for bar in self.bars:
                bar.hide()
            self.float_win.hide()
            self.root.update()
            time.sleep(0.35)
            cal = Calibrator(self.root, self.cfg["monitor"], message=message, single=True,
                             click_size=click_size)
            result = cal.run()
            if result:
                x, y, w, h = cal.rects[0]
                crop = cal.base.crop((x, y, x + w, y + h))
                rect = result[0]
        finally:
            self.paused = False
            self.bar_visible = True
            for w in hidden:
                if alive(w):
                    w.deiconify()
        return rect, crop

    def grab(self, rect):
        x, y, w, h = rect
        return grab_image(self.sct, {"left": x, "top": y, "width": w, "height": h})

    # -- cadastro de buffs --
    def define_buff_area(self, step=""):
        rect, _ = self.pick_rect(
            "AREA DOS BUFFS %s\n"
            "Arraste um retangulo cobrindo TODAS AS LINHAS onde os icones de buff podem\n"
            "aparecer (ao lado do nivel do personagem), do 1o ate o ultimo espaco possivel.\n"
            "Com muitos buffs ativos a fila quebra para a 2a/3a linha: inclua-as tambem.\n"
            "Enter: confirmar.   Esc: cancelar." % step)
        if rect:
            self.cfg["buff_area"] = rect
            save_config(self.cfg)
            return True
        return False

    def add_buff(self):
        if self.paused or not config.is_configured(self.cfg):
            return
        two_steps = not self.cfg.get("buff_area")
        if two_steps and not self.define_buff_area("(1/2) - deixe o buff ATIVO no jogo"):
            return
        _rect, icon = self.pick_rect(
            "ADICIONAR BUFF %s\n"
            "Com o buff ATIVO na tela, arraste um retangulo bem justo sobre o ICONE dele.\n"
            "Enter: confirmar.   Esc: cancelar." % ("(2/2)" if two_steps else ""))
        if icon is None:
            return
        data = telas.BuffEditor(self, icon).run()
        if not data:
            return
        folder = os.path.join(BASE_DIR, "buffs")
        os.makedirs(folder, exist_ok=True)
        slug = "".join(c if c.isalnum() else "_" for c in data["name"].lower()).strip("_") or "buff"
        used = {b.get("file") for p in self.cfg["profiles"].values() for b in p.get("buffs", [])}
        used |= {b.get("file") for b in self.cfg["buffs"]}
        fname, n = "buffs/%s.png" % slug, 1
        while fname in used or os.path.exists(os.path.join(BASE_DIR, fname)):
            n += 1
            fname = "buffs/%s_%d.png" % (slug, n)
        icon.save(os.path.join(BASE_DIR, fname))
        self.cfg["buffs"].append(dict(self.with_skill_slug(data), file=fname))
        save_config(self.cfg)
        self.load_buffs()
        self.refresh_settings()

    def with_skill_slug(self, data):
        """Guarda tambem QUAL magia o buff segue, para o vinculo sobreviver se a
        ordem das barras mudar."""
        mags = config.all_magias(self.cfg)
        s = data.get("skill")
        data["skill_slug"] = mags[s] if isinstance(s, int) and 0 <= s < len(mags) else None
        return data

    def edit_buff(self, i):
        if not 0 <= i < len(self.buffs):
            return
        b = self.buffs[i]
        data = telas.BuffEditor(self, b["img"], b).run()
        if data:
            self.cfg["buffs"][b["ci"]].update(self.with_skill_slug(data))
            save_config(self.cfg)
            self.load_buffs()
            self.refresh_settings()

    def remove_buff(self, i):
        if not 0 <= i < len(self.buffs):
            return
        b = self.buffs[i]
        parent = self.settings if alive(self.settings) else self.root
        if not messagebox.askyesno("Remover buff", "Remover '%s'?" % b["name"], parent=parent):
            return
        self.cfg["buffs"].pop(b["ci"])
        save_config(self.cfg)
        in_use = any(x.get("file") == b["file"]
                     for p in self.cfg["profiles"].values() for x in p.get("buffs", []))
        if not in_use:
            try:
                os.remove(os.path.join(BASE_DIR, b["file"]))
            except OSError:
                pass
        self.tracker.s.pop(b["file"], None)
        self.load_buffs()
        self.refresh_settings()

    def refresh_settings(self):
        if alive(self.settings):
            self.settings.refresh_buffs()

    def redefine_area(self):
        if self.define_buff_area():
            self.refresh_settings()

    # -- skills das barras (para o editor de buff) --
    def skill_images(self):
        """Imagem atual de cada skill, na ordem global."""
        imgs = []
        for x, y, w, h in config.all_regions(self.cfg):
            try:
                imgs.append(grab_image(self.sct, {"left": x, "top": y, "width": w, "height": h}))
            except Exception:
                imgs.append(Image.new("RGB", (w, h), "#333333"))
        return imgs

    def skill_slots(self, images=True):
        """[(nome, imagem, magia_da_wiki_ou_None)] de cada skill, na ordem global
        (barra 1, depois barra 2)."""
        voc_slug = self.cfg.get("vocacao") or ""
        voc = wiki.find_vocacao(self.vocacoes, voc_slug)
        by = {m["slug"]: m for m in voc["magias"]} if voc else {}
        known = [by.get(s) if s else None for s in config.all_magias(self.cfg)]
        live = (self.skill_images() if images and not all(known) else [None] * len(known))
        two = sum(1 for b in self.cfg["bars"] if b["regions"]) > 1
        offsets = config.bar_offsets(self.cfg)
        out = []
        for i, (m, img) in enumerate(zip(known, live)):
            # icone da wiki quando a magia e conhecida: nitido mesmo com o jogo escondido
            if images and m is not None and wiki.has_icon(voc_slug, m):
                img = Image.open(wiki.icon_path(voc_slug, m)).convert("RGB")
            if images and img is None:
                img = Image.new("RGB", (44, 44), "#333333")
            name = m["nome"] if m else "Skill %d" % (i + 1)
            if two:
                bar_no = max(j for j, off in enumerate(offsets) if off <= i) + 1
                name = "B%d · %s" % (bar_no, name)
            out.append((name, img, m))
        return out

    # -- telas (assistente e configuracoes, em telas.py) --
    def open_settings(self):
        if self.paused:
            return
        if alive(self.wizard):
            self.wizard.bring_front()
            return
        if alive(self.settings):
            self.settings.bring_front()
            return
        self.settings = telas.Settings(self)

    def open_wizard(self, start_at=None):
        if alive(self.settings):
            self.settings.destroy()
        if alive(self.wizard):
            self.wizard.bring_front()
            return
        self.wizard = telas.Wizard(self, start_at=start_at)

    def wizard_closed(self, finished):
        self.wizard = None
        if not config.is_configured(self.cfg):
            others = [n for n in config.profile_names(self.cfg) if n != self.cfg["profile"]
                      and config.is_configured(self.cfg["profiles"][n])]
            if others:
                self.switch_profile(others[0])   # volta para um personagem pronto
            else:
                print("Nada configurado. Saindo.")
                self.quit()

    def skip_wizard(self):
        self.cfg["wizard_skipped"] = True
        save_config(self.cfg)

    def relink_buffs(self, old, magias):
        """Reposiciona cada buff na skill da SUA magia, pela ordem global nova.
        old/magias = slug de cada skill antes/depois (indice global).
        Sem magia conhecida ou fora das barras: o buff fica solto."""
        voc = wiki.find_vocacao(self.vocacoes, self.cfg.get("vocacao") or "")
        names = {m["slug"]: m["nome"] for m in voc["magias"]} if voc else {}
        for b in self.cfg["buffs"]:
            slug = b.get("skill_slug")
            s = b.get("skill")
            if not slug and isinstance(s, int) and 0 <= s < len(old):
                slug = old[s]
            if not slug:
                # buff de antes do assistente: tenta pelo nome ("IRA" -> "Ira Frenetica"),
                # entre TODAS as magias da vocacao (a dele pode ter saido da barra)
                slug = match_by_name(b.get("name", ""), names)
            b["skill_slug"] = slug
            # nunca deixa o buff em cima de outra skill que foi parar naquela posicao
            b["skill"] = magias.index(slug) if slug and slug in magias else None

    def finish_wizard(self, vocacao, bars, only_buffs=False):
        """Aplica o que foi escolhido no assistente.
        bars = [{"magias": [...], "regions": [...], "orientation": "..."}] (ate 2)."""
        old = config.all_magias(self.cfg)
        old_bars = self.cfg["bars"]
        new_bars = []
        for i, spec in enumerate(b for b in bars if b["regions"]):
            bar = config.new_bar(spec.get("orientation", "horizontal"))
            bar.update(regions=spec["regions"], magias=spec["magias"])
            if i < len(old_bars):
                bar["pos"] = old_bars[i].get("pos")
            new_bars.append(bar)
        self.cfg.update(vocacao=vocacao, bars=new_bars, only_buffs=bool(only_buffs))
        self.relink_buffs(old, config.all_magias(self.cfg))
        save_config(self.cfg)
        self.load_buffs()
        self.build_bars()

    # -- janela do jogo --
    def game_label_text(self):
        proc = self.cfg.get("game_process", "")
        title = self.cfg.get("game_title", "")
        if proc or title:
            return "Visível só com esta janela em primeiro plano:\n%s" % (
                proc or ("título contendo '%s'" % title))
        return "Desativado: a barra fica sempre visível."

    def capture_game_window(self, n, show):
        """Conta n segundos e grava qual programa esta em primeiro plano.
        show(texto) atualiza a tela e devolve False se ela foi fechada."""
        if n > 0:
            if show("Clique agora na janela do jogo... %d" % n):
                self.root.after(1000, lambda: self.capture_game_window(n - 1, show))
            return
        hwnd = user32.GetForegroundWindow()
        pid, exe = window_info(hwnd) if hwnd else (0, "")
        if not exe or pid == os.getpid():
            show("Não consegui detectar. Tente de novo e clique na janela do jogo.")
        elif exe.lower() in BROWSERS:
            show("Isso é um navegador (%s). Clique na janela do jogo e tente de novo." % exe)
        else:
            self.cfg["game_process"] = exe
            self.cfg["game_title"] = ""
            save_config(self.cfg)
            show(self.game_label_text())

    def clear_game_window(self, show):
        self.cfg["game_process"] = ""
        self.cfg["game_title"] = ""
        save_config(self.cfg)
        show(self.game_label_text())


# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Barra de Skills")
    parser.add_argument("--calibrar", action="store_true",
                        help="marca os icones da barra 1 manualmente ao iniciar")
    parser.add_argument("--monitor", type=int,
                        help="numero do monitor onde esta o jogo (1 = principal)")
    parser.add_argument("--janelas", action="store_true",
                        help="lista as janelas abertas (programa e titulo) e sai")
    parser.add_argument("--jogo", metavar="PROGRAMA.EXE",
                        help="mostra as barras so quando este programa estiver em "
                             "primeiro plano (use '' para desativar)")
    args = parser.parse_args()

    enable_dpi_awareness()

    if args.janelas:
        for exe, title in sorted(list_windows(), key=lambda w: w[0].lower()):
            print("%-28s %s" % (exe or "?", title))
        return
    if args.jogo is not None:
        cfg = load_config()
        cfg["game_process"] = args.jogo.strip()
        cfg["game_title"] = ""
        save_config(cfg)
        print("Janela do jogo definida como: %r" % (cfg["game_process"] or "(sempre visivel)"))
    SkillBar(force_calibrate=args.calibrar, monitor=args.monitor).start()


def run():
    """Roda o programa registrando qualquer erro no diagnostico.txt."""
    import faulthandler
    import traceback
    log = log_path()
    fh = None
    if log:
        try:   # travamentos graves (ex.: falha no Tk) tambem vao para o arquivo
            fh = open(log, "a", encoding="utf-8")
            faulthandler.enable(fh)
        except OSError:
            fh = None
    log_error("Iniciando (Python %s%s)" % (sys.version.split()[0], ", exe" if FROZEN else ""))
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        tb = traceback.format_exc()
        log_error(tb)
        print(tb)
        if FROZEN:   # sem janela preta no .exe: avisa numa caixa de mensagem
            try:
                messagebox.showerror(
                    "Barra de Skills",
                    "O programa encontrou um erro e vai fechar.\n\nOs detalhes foram "
                    "salvos em:\n%s" % log_path())
            except Exception:
                pass
        else:
            print("O erro acima tambem foi salvo em diagnostico.txt.")
        sys.exit(1)
    finally:
        if fh is not None:
            faulthandler.disable()
            fh.close()


if __name__ == "__main__":
    run()
