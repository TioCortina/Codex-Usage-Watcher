#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess

from browser_common import APP_DIR, find_browser, profile_dir_for_browser

CONFIG = APP_DIR / "config.json"
URL = "https://chatgpt.com/codex/settings/usage"


def load_config():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main():
    cfg = load_config()
    browser = find_browser(cfg)

    if not browser:
        print("ERROR: no encontré el navegador seleccionado.")
        print("Ejecuta CONFIGURE_BROWSER.bat.")
        return 2

    profile = profile_dir_for_browser(cfg, browser["key"])
    profile.mkdir(parents=True, exist_ok=True)

    print()
    print(f"Se abrirá UNA ventana visible de {browser['display_name']} para autenticar Codex Watcher.")
    print("1) Inicia sesión en ChatGPT si hace falta.")
    print("2) Confirma que Codex Usage muestre tus porcentajes.")
    print(f"3) CIERRA COMPLETAMENTE esa ventana de {browser['display_name']}.")
    print("4) Vuelve a esta consola y presiona una tecla.")
    print()

    subprocess.Popen([
        str(browser["exe"]),
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "--new-window",
        URL,
    ])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
