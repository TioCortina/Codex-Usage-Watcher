from __future__ import annotations
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DEFAULT_PROFILE_DIR = APP_DIR / "runtime" / "brave_codex_profile"

def find_brave() -> Path | None:
    candidates = []
    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        root = os.environ.get(env_name)
        if root:
            candidates.append(Path(root) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe")
    for path in candidates:
        if path.exists():
            return path
    return None

def profile_dir_from_config(cfg: dict) -> Path:
    raw = (
        ((cfg.get("background_capture") or {}).get("dedicated_profile_dir"))
        or "runtime/brave_codex_profile"
    )
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = APP_DIR / p
    return p.resolve()
