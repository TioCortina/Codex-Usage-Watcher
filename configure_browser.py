#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from browser_common import APP_DIR, BROWSERS, default_browser_key, installed_browsers, profile_dir_for_browser

CONFIG = APP_DIR / "config.json"
EXAMPLE = APP_DIR / "config.example.json"


def readj(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save(cfg: dict):
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def choose(installed: list[dict], default_key: str | None):
    print()
    print("Navegadores compatibles detectados:")
    for i, item in enumerate(installed, 1):
        mark = " [predeterminado]" if item["key"] == default_key else ""
        print(f"  {i}. {item['display_name']}{mark}")

    default_index = 1
    if default_key:
        for i, item in enumerate(installed, 1):
            if item["key"] == default_key:
                default_index = i
                break

    print()
    while True:
        raw = input(f"Elige navegador [{default_index}]: ").strip()
        if not raw:
            return installed[default_index - 1]["key"]
        if raw.isdigit() and 1 <= int(raw) <= len(installed):
            return installed[int(raw) - 1]["key"]
        print("Opción inválida.")


def ensure(interactive: bool):
    cfg = readj(CONFIG) if CONFIG.exists() else readj(EXAMPLE)
    cfg.setdefault("browser", {})

    installed = installed_browsers()
    if not installed:
        print("ERROR: no encontré Brave, Google Chrome ni Microsoft Edge.")
        return 2

    keys = {item["key"] for item in installed}
    current = str(cfg["browser"].get("selected") or "").strip().lower()
    default = default_browser_key()

    if current in keys:
        selected = current
    elif default in keys:
        selected = default
    elif len(installed) == 1:
        selected = installed[0]["key"]
    elif interactive:
        selected = choose(installed, default)
    else:
        selected = next((k for k in ("edge", "chrome", "brave") if k in keys), None)

    if not selected:
        return 3

    cfg["browser"]["preferred"] = cfg["browser"].get("preferred") or "auto"
    cfg["browser"]["selected"] = selected
    cfg["browser"].setdefault("profile_root", "runtime/browser_profiles")
    cfg["browser"].setdefault("profile_dir", "")
    save(cfg)

    print(f"OK: navegador seleccionado: {BROWSERS[selected]['display_name']}")
    print(f"Perfil dedicado: {profile_dir_for_browser(cfg, selected)}")
    return 0


def configure():
    cfg = readj(CONFIG) if CONFIG.exists() else readj(EXAMPLE)
    cfg.setdefault("browser", {})
    installed = installed_browsers()
    if not installed:
        print("ERROR: no encontré navegadores compatibles.")
        return 2

    selected = choose(installed, default_browser_key())
    cfg["browser"]["preferred"] = selected
    cfg["browser"]["selected"] = selected
    cfg["browser"].setdefault("profile_root", "runtime/browser_profiles")
    cfg["browser"]["profile_dir"] = ""
    save(cfg)

    print()
    print(f"Guardado: {BROWSERS[selected]['display_name']}")
    print(f"Perfil dedicado: {profile_dir_for_browser(cfg, selected)}")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ensure", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()
    return ensure(args.interactive) if args.ensure else configure()


if __name__ == "__main__":
    raise SystemExit(main())
