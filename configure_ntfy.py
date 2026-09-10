#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import secrets
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config.json"
EXAMPLE = HERE / "config.example.json"
TOPIC_RE = re.compile(r"^[A-Za-z0-9_-]{8,120}$")


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_config():
    if CONFIG.exists():
        return read_json(CONFIG)
    cfg = read_json(EXAMPLE)
    save_json(CONFIG, cfg)
    return cfg


def generate_topic():
    return "codex-usage-" + secrets.token_hex(16)


def ntfy_cfg(cfg):
    cfg.setdefault("ntfy", {})
    cfg["ntfy"].setdefault("server", "https://ntfy.sh")
    cfg["ntfy"].setdefault("topic", "")
    cfg["ntfy"].setdefault("token", "")
    cfg["ntfy"].setdefault("enabled", False)
    return cfg["ntfy"]


def send_test(cfg):
    n = ntfy_cfg(cfg)
    if not n.get("enabled") or not n.get("topic"):
        print("ntfy no está configurado.")
        return False
    payload = {
        "topic": n["topic"],
        "title": "Codex Usage Watcher",
        "message": "Prueba correcta: las alertas push están funcionando.",
        "priority": 5,
        "tags": ["white_check_mark", "test_tube"],
    }
    req = urllib.request.Request(
        n.get("server", "https://ntfy.sh").rstrip("/") + "/",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "CodexUsageWatcher/3.0"},
        method="POST",
    )
    token = (n.get("token") or "").strip()
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            ok = 200 <= r.status < 300
        print("Notificación de prueba enviada." if ok else "ntfy respondió con error.")
        return ok
    except Exception as exc:
        print("No pude enviar la prueba:", exc)
        return False


def ensure():
    cfg = load_config()
    n = ntfy_cfg(cfg)
    topic = (n.get("topic") or "").strip()
    if not topic:
        topic = generate_topic()
        n["topic"] = topic
        n["enabled"] = True
        save_json(CONFIG, cfg)
        print("Se generó un topic ntfy único para este equipo:")
    else:
        print("Se reutilizó el topic ntfy existente:")
    print(topic)
    print("Añade exactamente ese topic en la app ntfy del celular.")
    return 0


def interactive():
    cfg = load_config()
    n = ntfy_cfg(cfg)
    while True:
        current = (n.get("topic") or "").strip() or "(sin configurar)"
        print("\n=== ntfy ===")
        print("Topic actual:", current)
        print("1) Generar un topic nuevo y seguro")
        print("2) Usar un topic personalizado")
        print("3) Mostrar el topic actual")
        print("4) Enviar notificación de prueba")
        print("5) Desactivar ntfy")
        print("0) Salir")
        choice = input("> ").strip()
        if choice == "1":
            n["topic"] = generate_topic(); n["enabled"] = True
            save_json(CONFIG, cfg)
            print("Nuevo topic:", n["topic"])
        elif choice == "2":
            topic = input("Topic (8-120 caracteres, letras/números/_/-): ").strip()
            if not TOPIC_RE.fullmatch(topic):
                print("Topic inválido.")
                continue
            n["topic"] = topic; n["enabled"] = True
            save_json(CONFIG, cfg)
            print("Guardado.")
        elif choice == "3":
            print("Topic:", current)
        elif choice == "4":
            send_test(cfg)
        elif choice == "5":
            n["enabled"] = False
            save_json(CONFIG, cfg)
            print("ntfy desactivado.")
        elif choice == "0":
            return 0
        else:
            print("Opción inválida.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ensure", action="store_true")
    p.add_argument("--show", action="store_true")
    p.add_argument("--test", action="store_true")
    args = p.parse_args()
    if args.ensure:
        return ensure()
    cfg = load_config()
    if args.show:
        print((ntfy_cfg(cfg).get("topic") or "").strip())
        return 0
    if args.test:
        return 0 if send_test(cfg) else 1
    return interactive()

if __name__ == "__main__":
    raise SystemExit(main())
