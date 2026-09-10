#!/usr/bin/env python3
from __future__ import annotations
import json
import subprocess
from pathlib import Path

from brave_common import APP_DIR, find_brave, profile_dir_from_config

CONFIG = APP_DIR / "config.json"
URL = "https://chatgpt.com/codex/settings/usage"

def load_config():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return {}

def main():
    brave = find_brave()
    if not brave:
        print("ERROR: Brave no está instalado.")
        return 2

    cfg = load_config()
    profile = profile_dir_from_config(cfg)
    profile.mkdir(parents=True, exist_ok=True)

    print()
    print("Se abrirá UNA ventana visible de Brave para autenticar Codex Watcher.")
    print("1) Inicia sesión en ChatGPT si hace falta.")
    print("2) Confirma que Codex Usage muestre tus porcentajes.")
    print("3) CIERRA COMPLETAMENTE esa ventana de Brave.")
    print("4) Vuelve a esta consola y presiona una tecla.")
    print()

    subprocess.Popen([
        str(brave),
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "--new-window",
        URL,
    ])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
