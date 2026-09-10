#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
CONFIG = HERE / "config.json"
EXAMPLE = HERE / "config.example.json"


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
    out = []
    try:
        for p in PARENT.iterdir():
            if p.is_dir() and p.resolve() != HERE.resolve():
                low = p.name.lower()
                if "codex" in low and ("usage" in low or "watcher" in low):
                    out.append(p)
    except Exception:
        pass
    return out


def newest_config_candidate():
    found = []
    for d in candidate_dirs():
        p = d / "config.json"
        if not p.exists():
            continue
        data = readj(p)
        topic = ((data.get("ntfy") or {}).get("topic") or "").strip()
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


def migrate_legacy_brave_profile():
    target = HERE / "runtime" / "browser_profiles" / "brave_codex_profile"
    if target.exists():
        return

    candidates = []
    same = HERE / "runtime" / "brave_codex_profile"
    if same.exists():
        candidates.append(same)

    for d in candidate_dirs():
        p = d / "runtime" / "brave_codex_profile"
        if p.exists():
            candidates.append(p)

    if not candidates:
        return

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    source = candidates[0]
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        shutil.copytree(
            source,
            target,
            ignore=shutil.ignore_patterns(
                "Cache", "Code Cache", "GPUCache", "DawnCache",
                "ShaderCache", "GrShaderCache", "Crashpad",
                "BrowserMetrics", "*.tmp"
            )
        )
        print(f"OK: perfil Brave anterior migrado desde:\n  {source}")
    except Exception as exc:
        print("AVISO: no pude migrar el perfil Brave anterior:", exc)


def main():
    defaults = readj(EXAMPLE)

    if CONFIG.exists():
        existing = readj(CONFIG)
        CONFIG.write_text(json.dumps(merge(defaults, existing), indent=2, ensure_ascii=False), encoding="utf-8")
        print("OK: config.json existente conservado.")
        if ((existing.get("ntfy") or {}).get("topic") or "").strip():
            print("OK: configuración ntfy conservada.")
    else:
        candidate = newest_config_candidate()
        if candidate:
            _, _, path, data = candidate
            CONFIG.write_text(json.dumps(merge(defaults, data), indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"OK: configuración anterior migrada desde:\n  {path}")
            if ((data.get("ntfy") or {}).get("topic") or "").strip():
                print("OK: configuración ntfy anterior migrada automáticamente.")
        else:
            CONFIG.write_text(json.dumps(defaults, indent=2, ensure_ascii=False), encoding="utf-8")
            print("INFO: config.json creado desde config.example.json.")

    migrate_legacy_brave_profile()
    (HERE / "runtime" / "browser_profiles").mkdir(parents=True, exist_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
