#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYTHON = HERE / ".venv" / "Scripts" / "python.exe"
CAPTURE = HERE / "codex_hidden_capture.py"
STATUS = HERE / "hidden_last_run.json"

def read_status():
    try:
        return json.loads(STATUS.read_text(encoding="utf-8"))
    except Exception:
        return {}

def main():
    if not PYTHON.exists():
        return 90

    proc = subprocess.run([str(PYTHON), str(CAPTURE)], cwd=str(HERE))
    if proc.returncode == 0:
        return 0

    status = read_status()
    stage = status.get("stage")
    # Installer uses 20 to mean "requires visible authentication".
    if stage in ("authentication", "challenge", "capture_timeout"):
        return 20
    return proc.returncode or 21

if __name__ == "__main__":
    raise SystemExit(main())
