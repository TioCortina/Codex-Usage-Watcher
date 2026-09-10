#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import signal
import sys
import threading
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

try:
    from plyer import notification
except Exception:
    notification = None


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
STATE_PATH = APP_DIR / "watcher_state.json"
STOP = threading.Event()

MONTHS = {
    "jan": 1, "january": 1, "ene": 1, "enero": 1,
    "feb": 2, "february": 2, "febrero": 2,
    "mar": 3, "march": 3, "marzo": 3,
    "apr": 4, "april": 4, "abr": 4, "abril": 4,
    "may": 5, "mayo": 5,
    "jun": 6, "june": 6, "junio": 6,
    "jul": 7, "july": 7, "julio": 7,
    "aug": 8, "august": 8, "ago": 8, "agosto": 8,
    "sep": 9, "sept": 9, "september": 9, "septiembre": 9,
    "oct": 10, "october": 10, "octubre": 10,
    "nov": 11, "november": 11, "noviembre": 11,
    "dec": 12, "december": 12, "dic": 12, "diciembre": 12,
}

@dataclass
class LimitInfo:
    remaining_percent: Optional[int] = None
    used_percent: Optional[int] = None
    reset_at: Optional[str] = None
    reset_date: Optional[str] = None
    reset_text: Optional[str] = None
    raw: Optional[str] = None

def now_tz(tz_name: str) -> datetime:
    # "local" (default in the public build) uses the Windows timezone.
    if not tz_name or str(tz_name).strip().lower() in {"local", "system", "auto"}:
        return datetime.now().astimezone()
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(tz_name))
        except Exception:
            pass
    return datetime.now().astimezone()

def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)

def load_config():
    if not CONFIG_PATH.exists():
        example = APP_DIR / "config.example.json"
        CONFIG_PATH.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    return load_json(CONFIG_PATH, {})

def clean_month(s: str) -> str:
    return (s.lower().strip(".")
            .replace("á","a").replace("é","e").replace("í","i")
            .replace("ó","o").replace("ú","u"))

def compact_lines(text: str):
    return [re.sub(r"\s+", " ", x).strip() for x in text.splitlines() if x.strip()]

def section_around(lines, keywords, before=1, after=12):
    keys = [k.lower() for k in keywords]
    for i, line in enumerate(lines):
        lo = line.lower()
        if any(k in lo for k in keys):
            return " | ".join(lines[max(0, i-before): min(len(lines), i+after+1)])
    return ""

def parse_percent(snippet: str):
    s = snippet.lower()

    for pat in (
        r"(\d{1,3})\s*%\s*(?:remaining|left|restante|disponible)",
        r"(?:remaining|left|restante|disponible)[^\d]{0,20}(\d{1,3})\s*%",
    ):
        m = re.search(pat, s, re.I)
        if m:
            rem = max(0, min(100, int(m.group(1))))
            return rem, 100-rem

    for pat in (
        r"(\d{1,3})\s*%\s*(?:used|usado|utilizado|consumido)",
        r"(?:used|usado|utilizado|consumido)[^\d]{0,20}(\d{1,3})\s*%",
    ):
        m = re.search(pat, s, re.I)
        if m:
            used = max(0, min(100, int(m.group(1))))
            return 100-used, used

    vals = [int(v) for v in re.findall(r"\b(\d{1,3})\s*%", snippet)]
    vals = [v for v in vals if 0 <= v <= 100]
    if vals:
        # La UI actual de Codex suele mostrar "remaining" junto al porcentaje.
        # Si faltó esa palabra por cómo se obtuvo el texto, conservamos el valor
        # como remaining pero dejamos raw para diagnóstico.
        return vals[0], 100-vals[0]
    return None, None

def parse_clock(text: str):
    matches = re.findall(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", text)
    if matches:
        h, m = matches[-1]
        return int(h), int(m)

    matches = re.findall(r"\b(1[0-2]|0?[1-9]):([0-5]\d)\s*([ap]\.?m\.?)\b", text, re.I)
    if matches:
        h, m, ap = matches[-1]
        h, m = int(h), int(m)
        if ap.lower().startswith("p") and h != 12:
            h += 12
        if ap.lower().startswith("a") and h == 12:
            h = 0
        return h, m
    return None

def parse_date(text: str, now: datetime):
    low = text.lower()

    m = re.search(r"\b([0-3]?\d)\s+([a-záéíóú]{3,12})(?:\s+(\d{4}))?\b", low, re.I)
    if m:
        day = int(m.group(1))
        mon = MONTHS.get(clean_month(m.group(2)))
        if mon:
            year = int(m.group(3)) if m.group(3) else now.year
            try:
                candidate = datetime(year, mon, day, tzinfo=now.tzinfo)
                if not m.group(3) and candidate.date() < now.date() - timedelta(days=2):
                    year += 1
                return year, mon, day
            except Exception:
                pass

    m = re.search(r"\b([a-záéíóú]{3,12})\s+([0-3]?\d)(?:,?\s+(\d{4}))?\b", low, re.I)
    if m:
        mon = MONTHS.get(clean_month(m.group(1)))
        day = int(m.group(2))
        if mon:
            year = int(m.group(3)) if m.group(3) else now.year
            try:
                candidate = datetime(year, mon, day, tzinfo=now.tzinfo)
                if not m.group(3) and candidate.date() < now.date() - timedelta(days=2):
                    year += 1
                return year, mon, day
            except Exception:
                pass

    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", low)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None

def infer_reset(snippet: str, now: datetime, kind: str):
    if not snippet:
        return None, None

    m = re.search(r"(?:reset(?:s|ting)?|restablece|reinicia|renueva)[^|]{0,100}", snippet, re.I)
    reset_text = m.group(0).strip(" |") if m else snippet[:220]

    clock = parse_clock(reset_text)
    date = parse_date(reset_text, now)

    if date:
        y, mo, d = date
        if clock:
            h, mi = clock
            try:
                return now.replace(year=y, month=mo, day=d, hour=h, minute=mi, second=0, microsecond=0).isoformat(), reset_text
            except Exception:
                return None, reset_text
        return None, reset_text

    if kind == "five_hour" and clock:
        h, mi = clock
        dt = now.replace(hour=h, minute=mi, second=0, microsecond=0)
        if dt <= now - timedelta(minutes=2):
            dt += timedelta(days=1)
        return dt.isoformat(), reset_text

    return None, reset_text

def parse_limit(snippet: str, now: datetime, kind: str):
    rem, used = parse_percent(snippet)
    reset_at, reset_text = infer_reset(snippet, now, kind)

    reset_date = None
    # La fecha se obtiene siempre desde el texto REAL capturado del UI.
    # Nunca se fija "Sep 15" ni ninguna otra fecha en el código.
    date_parts = parse_date(reset_text or snippet or "", now)
    if date_parts:
        y, mo, d = date_parts
        try:
            reset_date = f"{y:04d}-{mo:02d}-{d:02d}"
        except Exception:
            reset_date = None
    elif reset_at:
        try:
            reset_date = datetime.fromisoformat(reset_at).date().isoformat()
        except Exception:
            pass

    return LimitInfo(
        remaining_percent=rem,
        used_percent=used,
        reset_at=reset_at,
        reset_date=reset_date,
        reset_text=reset_text,
        raw=snippet or None,
    )

def budget_mode(weekly):
    if weekly is None: return "unknown"
    if weekly >= 50: return "normal"
    if weekly >= 25: return "moderado"
    if weekly >= 10: return "ahorro"
    return "reserva"

def recommendation(five, weekly):
    mode = budget_mode(weekly)
    if mode == "reserva":
        return "Reserva semanal crítica: Luna para tareas pequeñas; Terra solo si hace falta; Sol para bloqueos importantes."
    if mode == "ahorro":
        return "Modo ahorro: Luna para tareas pequeñas, Terra para desarrollo necesario y Sol solo para problemas complejos."
    if mode == "moderado":
        return "Cuota semanal moderada: aprovecha Codex con tareas claras y evita iteraciones innecesarias."
    if mode == "normal":
        return "Cuota semanal saludable: Luna/Terra normalmente; reserva Sol para arquitectura o bugs difíciles."
    return "No hay suficiente información semanal para recomendar consumo."

def desktop_notify(title, message):
    print(f"[ALERTA LOCAL] {title}: {message}")
    if notification:
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Codex Usage Watcher",
                timeout=12
            )
        except Exception:
            pass


def ntfy_config(cfg):
    n = cfg.get("ntfy") or {}
    return {
        "enabled": bool(n.get("enabled", False)),
        "server": str(n.get("server", "https://ntfy.sh")).rstrip("/"),
        "topic": str(n.get("topic", "")).strip(),
        "token": str(n.get("token", "")).strip(),
    }


def send_ntfy(cfg, title, message, priority=4, tags=None):
    """Envía una notificación push al topic configurado en ntfy."""
    n = ntfy_config(cfg)
    if not n["enabled"] or not n["topic"]:
        return False

    payload = {
        "topic": n["topic"],
        "title": str(title),
        "message": str(message),
        "priority": int(priority),
    }
    if tags:
        payload["tags"] = list(tags)

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        n["server"] + "/",
        data=body,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "CodexUsageWatcher/3.0",
        },
        method="POST",
    )
    if n["token"]:
        req.add_header("Authorization", f"Bearer {n['token']}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = 200 <= getattr(resp, "status", 200) < 300
            if ok:
                print(f"[PUSH] {title}")
            return ok
    except Exception as exc:
        print(f"[WARN] No se pudo enviar push ntfy: {exc}")
        return False


def alert(cfg, title, message, priority=4, tags=None):
    """Alerta local + push al teléfono, sin hacer fallar el watcher si ntfy cae."""
    desktop_notify(title, message)
    send_ntfy(cfg, title, message, priority=priority, tags=tags)


def maybe_alert(data, cfg):
    state = load_json(STATE_PATH, {})
    now = now_tz(cfg.get("timezone", "local"))
    five = data.get("five_hour", {})
    weekly = data.get("weekly", {})

    five_rem = five.get("remaining_percent")
    weekly_rem = weekly.get("remaining_percent")
    reset_at = five.get("reset_at")

    jump_threshold = int(cfg.get("reset_detection_jump_percent", 25))
    alerts_cfg = cfg.get("alerts") or {}

    # ---------------------------------------------------------
    # 1) CUOTA BAJA: VENTANA 5H
    # ---------------------------------------------------------
    five_low_thresholds = sorted(
        {int(x) for x in alerts_cfg.get("five_hour_remaining_percent", [20, 10, 5])},
        reverse=True
    )
    five_cycle_key = five.get("reset_at") or five.get("reset_text") or "unknown-5h-cycle"
    five_low_sent = state.setdefault("five_hour_low_sent", {}).setdefault(five_cycle_key, [])

    if isinstance(five_rem, int):
        # Solo envía el umbral más urgente pendiente.
        for threshold in sorted(five_low_thresholds):
            if five_rem <= threshold and threshold not in five_low_sent:
                priority = 5 if threshold <= 10 else 4
                alert(
                    cfg,
                    "🚨 URGENTE — Codex 5h casi agotado" if threshold <= 10 else "⚠️ Codex 5h bajo",
                    f"Queda {five_rem}% de la ventana de 5 horas. "
                    f"Semanal: {weekly_rem if weekly_rem is not None else '?'}%. "
                    f"Reset: {five.get('reset_at') or five.get('reset_text') or '?'}.",
                    priority=priority,
                    tags=["warning", "hourglass"]
                )
                five_low_sent.append(threshold)
                break

    # ---------------------------------------------------------
    # 2) CUOTA BAJA: SEMANAL
    # ---------------------------------------------------------
    weekly_low_thresholds = sorted(
        {int(x) for x in alerts_cfg.get("weekly_remaining_percent", [20, 10, 5])},
        reverse=True
    )
    weekly_cycle_key = weekly.get("reset_date") or weekly.get("reset_text") or "unknown-weekly-cycle"
    weekly_low_sent = state.setdefault("weekly_low_sent", {}).setdefault(weekly_cycle_key, [])

    if isinstance(weekly_rem, int):
        for threshold in sorted(weekly_low_thresholds):
            if weekly_rem <= threshold and threshold not in weekly_low_sent:
                priority = 5 if threshold <= 10 else 4
                alert(
                    cfg,
                    "🚨 URGENTE — Codex semanal casi agotado" if threshold <= 10 else "⚠️ Codex semanal bajo",
                    f"Queda {weekly_rem}% de la cuota semanal. "
                    f"Ventana 5h: {five_rem if five_rem is not None else '?'}%. "
                    f"Próximo reset semanal: {weekly.get('reset_date') or weekly.get('reset_text') or '?'}. "
                    f"{data.get('recommendation','')}",
                    priority=priority,
                    tags=["rotating_light", "calendar"]
                )
                weekly_low_sent.append(threshold)
                break

    # ---------------------------------------------------------
    # 3) RESET 5H CERCA
    # ---------------------------------------------------------
    if reset_at:
        try:
            dt = datetime.fromisoformat(reset_at)
            mins = (dt - now).total_seconds() / 60
            thresholds = sorted(
                {int(x) for x in alerts_cfg.get("reset_minutes", [60, 30, 15])},
                reverse=True
            )
            cycle = state.setdefault("reset_5h_sent", {}).setdefault(reset_at, [])

            # Dispara solo el umbral más cercano que aún no haya sido enviado.
            eligible = [t for t in thresholds if 0 < mins <= t and t not in cycle]
            if eligible:
                threshold = min(eligible)
                alert(
                    cfg,
                    f"⏳ Codex: reset 5h en ~{int(round(mins))} min",
                    f"5h restante: {five_rem if five_rem is not None else '?'}% · "
                    f"Semanal: {weekly_rem if weekly_rem is not None else '?'}%. "
                    f"{data.get('recommendation','')}",
                    priority=4 if mins <= 30 else 3,
                    tags=["hourglass_flowing_sand"]
                )
                cycle.append(threshold)
        except Exception:
            pass

    # Estado anterior.
    prev = state.get("last_usage") or {}
    prev_five = prev.get("five_hour") or {}
    prev_weekly = prev.get("weekly") or {}

    prev_5h_rem = prev_five.get("remaining_percent")
    prev_weekly_rem = prev_weekly.get("remaining_percent")

    # ---------------------------------------------------------
    # 4) NUEVA VENTANA 5H DETECTADA
    # ---------------------------------------------------------
    if isinstance(prev_5h_rem, int) and isinstance(five_rem, int):
        if five_rem >= prev_5h_rem + jump_threshold:
            cycle_key = five.get("reset_at") or five.get("reset_text") or f"5h-{data.get('fetched_at')}"
            if state.get("last_announced_5h_cycle") != cycle_key:
                alert(
                    cfg,
                    "✅ Codex: nueva ventana de 5h",
                    f"La cuota de 5h subió {prev_5h_rem}%→{five_rem}%. "
                    f"Semanal: {weekly_rem if weekly_rem is not None else '?'}%.",
                    priority=3,
                    tags=["white_check_mark"]
                )
                state["last_announced_5h_cycle"] = cycle_key

    # ---------------------------------------------------------
    # 5) RESET SEMANAL DINÁMICO
    # ---------------------------------------------------------
    prev_weekly_date = prev_weekly.get("reset_date")
    cur_weekly_date = weekly.get("reset_date")
    prev_weekly_text = prev_weekly.get("reset_text")
    cur_weekly_text = weekly.get("reset_text")

    weekly_reset_detected = False
    reasons = []

    if isinstance(prev_weekly_rem, int) and isinstance(weekly_rem, int):
        if weekly_rem >= prev_weekly_rem + jump_threshold:
            weekly_reset_detected = True
            reasons.append(f"{prev_weekly_rem}%→{weekly_rem}%")

    if prev_weekly_date and cur_weekly_date and prev_weekly_date != cur_weekly_date:
        weekly_reset_detected = True
        reasons.append(f"{prev_weekly_date}→{cur_weekly_date}")

    if (
        prev_weekly_text and cur_weekly_text
        and prev_weekly_text != cur_weekly_text
        and isinstance(prev_weekly_rem, int)
        and isinstance(weekly_rem, int)
        and weekly_rem > prev_weekly_rem
    ):
        weekly_reset_detected = True
        reasons.append("cambió el texto de reset")

    weekly_cycle = cur_weekly_date or cur_weekly_text
    if weekly_reset_detected and weekly_cycle != state.get("last_announced_weekly_cycle"):
        alert(
            cfg,
            "✅ Codex: cuota semanal renovada",
            f"Semanal: {weekly_rem if weekly_rem is not None else '?'}%. "
            f"Próximo reset: {weekly_cycle or '?'}. "
            f"Detectado por: {', '.join(reasons)}.",
            priority=4,
            tags=["tada", "calendar"]
        )
        state["last_announced_weekly_cycle"] = weekly_cycle
        data["weekly_reset_detected"] = True
        data["weekly_reset_detection_reason"] = reasons
    else:
        data["weekly_reset_detected"] = False
        data["weekly_reset_detection_reason"] = []

    # ---------------------------------------------------------
    # 6) ACTUALIZAR ESTADO
    # ---------------------------------------------------------
    state["last_usage"] = {
        "five_hour": {
            "remaining_percent": five_rem,
            "reset_at": five.get("reset_at"),
            "reset_date": five.get("reset_date"),
            "reset_text": five.get("reset_text"),
        },
        "weekly": {
            "remaining_percent": weekly_rem,
            "reset_at": weekly.get("reset_at"),
            "reset_date": weekly.get("reset_date"),
            "reset_text": weekly.get("reset_text"),
        }
    }

    # Limpieza de ciclos antiguos para que el archivo no crezca indefinidamente.
    for key in ("five_hour_low_sent", "weekly_low_sent", "reset_5h_sent"):
        bucket = state.get(key, {})
        if isinstance(bucket, dict) and len(bucket) > 20:
            keys = list(bucket.keys())
            for old in keys[:-10]:
                bucket.pop(old, None)

    save_json(STATE_PATH, state)

def parse_page_text(raw_text: str, cfg: dict):
    now = now_tz(cfg.get("timezone", "local"))
    lines = compact_lines(raw_text)

    # Empieza exactamente en cada encabezado para evitar que el reset de 5h
    # se filtre al bloque semanal cuando ambos aparecen uno debajo del otro.
    five_snip = section_around(
        lines,
        ["5-hour", "5 hour", "5-hour usage", "5h", "5 h", "5 horas"],
        before=0, after=14
    )
    weekly_snip = section_around(
        lines,
        ["weekly usage", "weekly", "week usage", "semanal", "7-day", "7 day"],
        before=0, after=14
    )

    five = parse_limit(five_snip, now, "five_hour")
    weekly = parse_limit(weekly_snip, now, "weekly")

    lower = raw_text.lower()
    auth_hint = None
    if "log in" in lower or "sign in" in lower or "iniciar sesión" in lower:
        auth_hint = "La sesión del navegador no parece estar iniciada en ChatGPT."

    data = {
        "schema_version": 2,
        "source": "codex_usage_capture",
        "fetched_at": now.isoformat(),
        "timezone": cfg.get("timezone", "local"),
        "five_hour": asdict(five),
        "weekly": asdict(weekly),
        "budget_mode": budget_mode(weekly.remaining_percent),
        "recommendation": recommendation(five.remaining_percent, weekly.remaining_percent),
        "auth_hint": auth_hint,
        "parse_ok": five.remaining_percent is not None or weekly.remaining_percent is not None,
    }
    return data

def output_path(cfg):
    p = Path(cfg.get("output_path", "codex_usage.json")).expanduser()
    if not p.is_absolute():
        p = APP_DIR / p
    return p

class Handler(BaseHTTPRequestHandler):
    server_version = "CodexUsageWatcher/3.0"

    def log_message(self, fmt, *args):
        print("[HTTP]", fmt % args)

    def _headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_OPTIONS(self):
        self._headers(204)

    def do_GET(self):
        cfg = load_config()
        if self.path == "/health":
            self._headers()
            self.wfile.write(b'{"ok":true}')
            return
        if self.path == "/status":
            p = output_path(cfg)
            if p.exists():
                self._headers()
                self.wfile.write(p.read_bytes())
            else:
                self._headers(404)
                self.wfile.write(b'{"error":"no data yet"}')
            return
        self._headers(404)
        self.wfile.write(b'{"error":"not found"}')

    def do_POST(self):
        if self.path != "/usage":
            self._headers(404)
            self.wfile.write(b'{"error":"not found"}')
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            raw_text = payload.get("text", "")
            if not isinstance(raw_text, str) or not raw_text.strip():
                raise ValueError("payload.text vacío")

            cfg = load_config()
            data = parse_page_text(raw_text, cfg)
            data["browser_url"] = payload.get("url")
            data["extension_captured_at"] = payload.get("captured_at")

            save_json(output_path(cfg), data)

            diag = APP_DIR / "last_page_text.txt"
            diag.write_text(raw_text, encoding="utf-8")

            maybe_alert(data, cfg)

            print(
                f"[USAGE] "
                f"5h={data['five_hour']['remaining_percent']}% "
                f"weekly={data['weekly']['remaining_percent']}% "
                f"reset5h={data['five_hour']['reset_at'] or data['five_hour']['reset_text'] or '?'} "
                f"resetWeekly={data['weekly']['reset_date'] or data['weekly']['reset_at'] or data['weekly']['reset_text'] or '?'}"
            )

            self._headers()
            self.wfile.write(json.dumps({"ok": True, "parse_ok": data["parse_ok"]}).encode("utf-8"))
        except Exception as exc:
            self._headers(400)
            self.wfile.write(json.dumps({"ok": False, "error": str(exc)}).encode("utf-8"))

def main():
    cfg = load_config()
    host = "127.0.0.1"
    port = int(cfg.get("local_port", 8765))
    server = ThreadingHTTPServer((host, port), Handler)

    def stop(*_):
        STOP.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop)

    print("Codex Usage Watcher v3.0 (diagnóstico)")
    print(f"Escuchando solo localmente: http://{host}:{port}")
    print(f"JSON: {output_path(cfg)}")
    print("Modo diagnóstico. La automatización v2.6 usa codex_headless_capture.py.")
    print("Ctrl+C para salir.")

    server.serve_forever()

if __name__ == "__main__":
    main()
