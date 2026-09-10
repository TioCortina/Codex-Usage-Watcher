from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

APP_DIR = Path(__file__).resolve().parent

BROWSERS = {
    "brave": {
        "display_name": "Brave",
        "exe_name": "brave.exe",
        "relative_paths": [
            ("PROGRAMFILES", "BraveSoftware/Brave-Browser/Application/brave.exe"),
            ("PROGRAMFILES(X86)", "BraveSoftware/Brave-Browser/Application/brave.exe"),
            ("LOCALAPPDATA", "BraveSoftware/Brave-Browser/Application/brave.exe"),
        ],
        "prog_id_hints": ["bravehtml"],
    },
    "chrome": {
        "display_name": "Google Chrome",
        "exe_name": "chrome.exe",
        "relative_paths": [
            ("PROGRAMFILES", "Google/Chrome/Application/chrome.exe"),
            ("PROGRAMFILES(X86)", "Google/Chrome/Application/chrome.exe"),
            ("LOCALAPPDATA", "Google/Chrome/Application/chrome.exe"),
        ],
        "prog_id_hints": ["chromehtml"],
    },
    "edge": {
        "display_name": "Microsoft Edge",
        "exe_name": "msedge.exe",
        "relative_paths": [
            ("PROGRAMFILES", "Microsoft/Edge/Application/msedge.exe"),
            ("PROGRAMFILES(X86)", "Microsoft/Edge/Application/msedge.exe"),
            ("LOCALAPPDATA", "Microsoft/Edge/Application/msedge.exe"),
        ],
        "prog_id_hints": ["microsoftedge", "msedgehtm"],
    },
}


def _path_for_browser(key: str) -> Optional[Path]:
    spec = BROWSERS.get(key)
    if not spec:
        return None
    seen = set()
    for env_name, rel in spec["relative_paths"]:
        root = os.environ.get(env_name)
        if not root:
            continue
        p = (Path(root) / rel).resolve()
        token = str(p).lower()
        if token in seen:
            continue
        seen.add(token)
        if p.exists():
            return p
    return None


def installed_browsers() -> list[dict]:
    out = []
    for key, spec in BROWSERS.items():
        exe = _path_for_browser(key)
        if exe:
            out.append({
                "key": key,
                "display_name": spec["display_name"],
                "exe": exe,
                "exe_name": spec["exe_name"],
            })
    return out


def default_browser_key() -> Optional[str]:
    if os.name != "nt":
        return None
    try:
        import winreg
        path = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
        low = str(prog_id).lower()
        for browser_key, spec in BROWSERS.items():
            if any(hint in low for hint in spec["prog_id_hints"]) and _path_for_browser(browser_key):
                return browser_key
    except Exception:
        pass
    return None


def selected_browser_key(cfg: dict) -> Optional[str]:
    browser_cfg = cfg.get("browser") or {}
    installed = {b["key"] for b in installed_browsers()}

    selected = str(browser_cfg.get("selected") or "").strip().lower()
    if selected in installed:
        return selected

    preferred = str(browser_cfg.get("preferred") or "auto").strip().lower()
    if preferred in installed:
        return preferred

    default = default_browser_key()
    if default in installed:
        return default

    if len(installed) == 1:
        return next(iter(installed))

    for key in ("edge", "chrome", "brave"):
        if key in installed:
            return key
    return None


def find_browser(cfg: dict) -> Optional[dict]:
    key = selected_browser_key(cfg)
    if not key:
        return None
    exe = _path_for_browser(key)
    if not exe:
        return None
    return {
        "key": key,
        "display_name": BROWSERS[key]["display_name"],
        "exe": exe,
        "exe_name": BROWSERS[key]["exe_name"],
    }


def profile_dir_for_browser(cfg: dict, browser_key: str) -> Path:
    browser_cfg = cfg.get("browser") or {}

    explicit = str(browser_cfg.get("profile_dir") or "").strip()
    if explicit:
        p = Path(explicit).expanduser()
        if not p.is_absolute():
            p = APP_DIR / p
        return p.resolve()

    # Backward compatibility for a previous Brave-only installation.
    legacy = str(((cfg.get("background_capture") or {}).get("dedicated_profile_dir")) or "").strip()
    if browser_key == "brave" and legacy:
        p = Path(legacy).expanduser()
        if not p.is_absolute():
            p = APP_DIR / p
        if p.exists():
            return p.resolve()

    root = Path(str(browser_cfg.get("profile_root") or "runtime/browser_profiles")).expanduser()
    if not root.is_absolute():
        root = APP_DIR / root
    return (root / f"{browser_key}_codex_profile").resolve()


def profile_dir_from_config(cfg: dict) -> Path:
    browser = find_browser(cfg)
    if not browser:
        return (APP_DIR / "runtime" / "browser_profiles" / "unknown_codex_profile").resolve()
    return profile_dir_for_browser(cfg, browser["key"])
