# -*- coding: utf-8 -*-
"""
Configuracao (skillbar_config.json), personagens e caminhos.

- Opcoes gerais (zoom, opacidade, area dos buffs...) valem para todos.
- Cada PERSONAGEM tem a sua vocacao, barras e buffs. O personagem ativo fica
  "aberto" no nivel de cima do dicionario (cfg["bars"], cfg["buffs"]...), e
  save_config guarda uma copia dele em cfg["profiles"][nome].

Sem nada de Windows, para ser facil de testar.
"""

import copy
import json
import os
import sys

# Pasta gravavel (config, buffs, cache) e pasta dos arquivos do programa (dados/).
# No .exe (PyInstaller) os dados ficam embutidos em sys._MEIPASS.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
    RES_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RES_DIR = BASE_DIR
CONFIG_PATH = os.path.join(BASE_DIR, "skillbar_config.json")

MAX_BARS = 2

# chaves que pertencem a cada personagem
PROFILE_DEFAULTS = {
    "vocacao": "",           # slug da vocacao
    "bars": [],              # ate 2: {"regions", "magias", "orientation", "pos"}
    "buffs": [],             # {"name","duration","desc","file","skill","skill_slug",
                             #  "restart_on_cast"}; skill = indice GLOBAL (barra 1, depois 2)
    "only_buffs": False,     # True = esconde as barras e mostra so os buffs
    "wizard_skipped": False,
}

DEFAULTS = {
    "monitor": 1,              # monitor das telas de marcacao (1 = principal)
    "zoom": 1.0,               # ampliacao das barras
    "gap": 4,                  # espaco entre os icones (px)
    "fps": 30,                 # atualizacoes por segundo
    "opacity": 1.0,            # 0.2 (quase transparente) a 1.0 (opaco)
    "click_through": False,    # cliques atravessam as barras
    "exclude_from_capture": True,  # as barras nao aparecem nas capturas de tela
    "bg": "#0b0b0b",           # cor de fundo das barras
    "game_process": "",        # ex.: "client_02.exe" - vazio = sempre visivel
    "game_title": "",          # trecho do titulo da janela do jogo (opcional)
    "sidebar_area": None,      # [x, y, w, h] da barra lateral de skills do jogo
    "buff_area": None,         # [x, y, w, h] onde os icones de buff aparecem no jogo
    "buff_pos": None,          # posicao da janelinha de buffs soltos
    "buff_threshold": 14,      # tolerancia do reconhecimento (menor = mais exato)
    "buff_zoom": 1.5,          # ampliacao extra dos icones de buff (eles sao pequenos)
    "warn_seconds": 10,        # buff pisca nos ultimos N segundos (0 = nunca)
    "warn_sound": False,       # apito quando o buff comeca a piscar
    "profile": "",             # personagem ativo
    "profiles": {},            # {nome: {chaves de PROFILE_DEFAULTS}}
}
DEFAULTS.update(copy.deepcopy(PROFILE_DEFAULTS))


def new_bar(orientation="horizontal"):
    return {"regions": [], "magias": [], "orientation": orientation, "pos": None}


def migrate(cfg):
    """Converte configuracoes antigas (uma barra so, sem personagens)."""
    if "regions" in cfg:   # v1/v2: regions/magias/orientation/pos no nivel de cima
        regions = cfg.pop("regions") or []
        bar = new_bar(cfg.pop("orientation", "horizontal") or "horizontal")
        bar.update(regions=regions, magias=cfg.pop("magias", []) or [],
                   pos=cfg.pop("pos", None))
        if regions and not cfg.get("bars"):
            cfg["bars"] = [bar]
    if not cfg.get("profile"):
        cfg["profile"] = "Principal"
    if cfg["profile"] not in cfg["profiles"]:
        cfg["profiles"][cfg["profile"]] = snapshot(cfg)
    return cfg


def load_config(path=None):
    cfg = copy.deepcopy(DEFAULTS)
    try:
        with open(path or CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return migrate(cfg)


def snapshot(cfg):
    """Copia das chaves do personagem ativo."""
    return {k: copy.deepcopy(cfg.get(k, v)) for k, v in PROFILE_DEFAULTS.items()}


def save_config(cfg, path=None):
    if cfg.get("profile"):
        cfg["profiles"][cfg["profile"]] = snapshot(cfg)
    path = path or CONFIG_PATH
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError as exc:
        print("Nao consegui salvar a configuracao:", exc)


# -- personagens --
def profile_names(cfg):
    return sorted(cfg["profiles"], key=str.lower)


def switch_profile(cfg, name, create=False):
    """Guarda o personagem ativo e abre `name` (criando-o vazio se create=True)."""
    if cfg.get("profile"):
        cfg["profiles"][cfg["profile"]] = snapshot(cfg)
    if name not in cfg["profiles"]:
        if not create:
            raise KeyError(name)
        cfg["profiles"][name] = copy.deepcopy(PROFILE_DEFAULTS)
    data = copy.deepcopy(PROFILE_DEFAULTS)
    data.update(copy.deepcopy(cfg["profiles"][name]))
    cfg.update(data)
    cfg["profile"] = name


def delete_profile(cfg, name):
    """Apaga um personagem. Se for o ativo, abre outro (ou um vazio)."""
    cfg["profiles"].pop(name, None)
    if cfg.get("profile") == name:
        cfg["profile"] = ""
        others = profile_names(cfg)
        if others:
            switch_profile(cfg, others[0])
        else:
            cfg.update(copy.deepcopy(PROFILE_DEFAULTS))
            cfg["profile"] = "Principal"
            cfg["profiles"]["Principal"] = snapshot(cfg)


def rename_profile(cfg, old, new):
    new = new.strip()
    if not new or new == old or new in cfg["profiles"]:
        return False
    cfg["profiles"][new] = cfg["profiles"].pop(old)
    if cfg.get("profile") == old:
        cfg["profile"] = new
    return True


# -- barras e skills --
def all_regions(cfg):
    """Regioes de todas as barras, na ordem global (barra 1, depois barra 2)."""
    return [r for bar in cfg["bars"] for r in bar["regions"]]


def all_magias(cfg):
    """Slug da magia de cada skill, na ordem global (None se desconhecida)."""
    out = []
    for bar in cfg["bars"]:
        mags = bar.get("magias") or []
        ok = len(mags) == len(bar["regions"])
        out += [mags[i] if ok else None for i in range(len(bar["regions"]))]
    return out


def bar_offsets(cfg):
    """Indice global da 1a skill de cada barra."""
    offs, n = [], 0
    for bar in cfg["bars"]:
        offs.append(n)
        n += len(bar["regions"])
    return offs


def has_skills(cfg):
    return any(bar["regions"] for bar in cfg["bars"])


def is_configured(cfg):
    """O personagem ativo ja tem algo para mostrar (barras ou modo so buffs)."""
    return has_skills(cfg) or bool(cfg.get("only_buffs"))
