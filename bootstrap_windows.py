#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
CONFIG = HERE / "config.json"
EXAMPLE = HERE / "config.example.json"
PROFILE_REL = Path("runtime/brave_codex_profile")
PROFILE = HERE / PROFILE_REL

def readj(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def merge(defaults, existing):
    if not isinstance(defaults, dict):
        return existing
    out = dict(defaults)
    if not isinstance(existing, dict):
        return out
    for key, value in existing.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge(out[key], value)
        else:
            out[key] = value
    return out

def candidate_dirs():
    dirs = []
    try:
        for p in PARENT.iterdir():
            if not p.is_dir() or p.resolve() == HERE.resolve():
                continue
            low = p.name.lower()
            if "codex" in low and ("usage" in low or "watcher" in low):
                dirs.append(p)
    except Exception:
        pass
    return dirs

def newest_config_candidate():
    found = []
    for d in candidate_dirs():
        p = d / "config.json"
        if p.exists():
            data = readj(p)
            topic = ((data.get("ntfy") or {}).get("topic") or "").strip()
            # Prefer a real configured ntfy file.
            score = 1 if topic else 0
            try:
                mtime = p.stat().st_mtime
            except Exception:
                mtime = 0
            found.append((score, mtime, p, data))
    if not found:
        return None
    found.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return found[0]

def profile_candidate():
    found = []
    for d in candidate_dirs():
        p = d / PROFILE_REL
        if p.exists() and p.is_dir():
            # A valid Chromium profile normally has Local State one level up
            # and/or a Default directory.
            score = 0
            if (p / "Local State").exists():
                score += 2
            if (p / "Default").exists():
                score += 1
            try:
                mtime = p.stat().st_mtime
            except Exception:
                mtime = 0
            found.append((score, mtime, p))
    if not found:
        return None
    found.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return found[0][2]

def copy_profile(src: Path, dst: Path):
    if dst.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    print(f"Migrando perfil dedicado desde:\n  {src}")
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns(
            "Cache", "Code Cache", "GPUCache", "DawnCache",
            "ShaderCache", "GrShaderCache", "Crashpad",
            "BrowserMetrics", "*.tmp"
        )
    )
    return True

def main():
    defaults = readj(EXAMPLE)

    if CONFIG.exists():
        existing = readj(CONFIG)
        CONFIG.write_text(
            json.dumps(merge(defaults, existing), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        topic = ((existing.get("ntfy") or {}).get("topic") or "").strip()
        print("OK: config.json existente conservado.")
        if topic:
            print("OK: configuración ntfy conservada.")
    else:
        cand = newest_config_candidate()
        if cand:
            _, _, path, data = cand
            CONFIG.write_text(
                json.dumps(merge(defaults, data), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            print(f"OK: configuración migrada desde:\n  {path}")
            if ((data.get("ntfy") or {}).get("topic") or "").strip():
                print("OK: configuración ntfy anterior migrada automáticamente.")
        else:
            CONFIG.write_text(
                json.dumps(defaults, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            print("INFO: no encontré config anterior. Se creó uno nuevo.")

    if PROFILE.exists():
        print("OK: perfil dedicado de Brave ya existe.")
        return 0

    src_profile = profile_candidate()
    if src_profile:
        try:
            if copy_profile(src_profile, PROFILE):
                print("OK: perfil dedicado migrado.")
                return 0
        except Exception as exc:
            print("AVISO: no pude migrar el perfil anterior:", exc)

    PROFILE.mkdir(parents=True, exist_ok=True)
    print("INFO: no hay perfil dedicado autenticado todavía.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
