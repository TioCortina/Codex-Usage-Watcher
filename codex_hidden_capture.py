#!/usr/bin/env python3
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import threading
import time
import urllib.request
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path

try:
    import websocket
except Exception:
    websocket = None

from browser_common import APP_DIR, find_browser, profile_dir_for_browser
import codex_usage_server as core

STATUS_PATH = APP_DIR / "hidden_last_run.json"
ERROR_STATE_PATH = APP_DIR / "hidden_error_state.json"
URL = "https://chatgpt.com/codex/settings/usage"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

TH32CS_SNAPPROCESS = 0x00000002
SW_HIDE = 0

class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]

def save_status(data: dict):
    data = dict(data)
    data["updated_at"] = datetime.now().astimezone().isoformat()
    core.save_json(STATUS_PATH, data)

def notify_error_once(cfg: dict, key: str, title: str, message: str):
    hcfg = cfg.get("hidden_browser") or {}
    if not hcfg.get("notify_auth_error", True):
        return
    cooldown_hours = float(hcfg.get("auth_error_cooldown_hours", 12))
    state = core.load_json(ERROR_STATE_PATH, {})
    now = datetime.now(timezone.utc)
    last = state.get(key)
    if last:
        try:
            dt = datetime.fromisoformat(last)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if (now - dt).total_seconds() < cooldown_hours * 3600:
                return
        except Exception:
            pass
    core.send_ntfy(cfg, title, message, priority=4, tags=["warning"])
    state[key] = now.isoformat()
    core.save_json(ERROR_STATE_PATH, state)

def process_table():
    if os.name != "nt":
        return {}
    k32 = ctypes.windll.kernel32
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == ctypes.c_void_p(-1).value:
        return {}
    pe = PROCESSENTRY32()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
    table = {}
    try:
        ok = k32.Process32FirstW(snap, ctypes.byref(pe))
        while ok:
            table[int(pe.th32ProcessID)] = int(pe.th32ParentProcessID)
            ok = k32.Process32NextW(snap, ctypes.byref(pe))
    finally:
        k32.CloseHandle(snap)
    return table

def descendant_pids(root_pid: int):
    table = process_table()
    out = {int(root_pid)}
    changed = True
    while changed:
        changed = False
        for pid, ppid in table.items():
            if ppid in out and pid not in out:
                out.add(pid)
                changed = True
    return out

def hide_windows_for_pids(pids):
    if os.name != "nt" or not pids:
        return 0
    user32 = ctypes.windll.user32
    targets = set(int(p) for p in pids)
    hidden = 0
    PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @PROC
    def cb(hwnd, lparam):
        nonlocal hidden
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if int(pid.value) in targets and user32.IsWindowVisible(hwnd):
            user32.ShowWindow(hwnd, SW_HIDE)
            hidden += 1
        return True

    user32.EnumWindows(cb, 0)
    return hidden

class WindowHider(threading.Thread):
    def __init__(self, root_pid: int, poll_ms: int):
        super().__init__(daemon=True)
        self.root_pid = root_pid
        self.delay = max(20, poll_ms) / 1000.0
        self.stop_event = threading.Event()
        self.hidden_count = 0

    def run(self):
        while not self.stop_event.is_set():
            try:
                self.hidden_count += hide_windows_for_pids(descendant_pids(self.root_pid))
            except Exception:
                pass
            self.stop_event.wait(self.delay)

    def stop(self):
        self.stop_event.set()

def looks_like_usage(text: str) -> bool:
    s = (text or "").lower()
    return "%" in s and (
        any(x in s for x in ("5-hour", "5 hour", "5h", "5 horas")) or
        any(x in s for x in ("weekly", "week", "semanal", "7-day", "7 day"))
    )

def auth_hint(text: str, title: str):
    s = ((title or "") + "\n" + (text or "")).lower()
    if any(x in s for x in ("log in", "sign in", "iniciar sesión", "inicia sesión", "create account", "crear cuenta")):
        return "El perfil dedicado de Codex Watcher necesita volver a iniciar sesión."
    return None

def challenge_hint(text: str, title: str):
    s = ((title or "") + "\n" + (text or "")).lower()
    if any(x in s for x in ("un momento", "just a moment", "verify you are human", "verifica que eres humano", "checking your browser", "cloudflare")):
        return "La página está mostrando una verificación temporal antes de Codex Usage."
    return None

def wait_devtools_port(profile: Path, proc: subprocess.Popen, timeout=15):
    marker = profile / "DevToolsActivePort"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if marker.exists():
            try:
                line = marker.read_text(encoding="utf-8", errors="ignore").splitlines()[0].strip()
                if line.isdigit():
                    return int(line)
            except Exception:
                pass
        if proc.poll() is not None:
            raise RuntimeError(f"Brave terminó antes de abrir DevTools (exit={proc.returncode}).")
        time.sleep(0.2)
    raise TimeoutError("Brave no creó DevToolsActivePort a tiempo.")

def get_json(url: str):
    with urllib.request.urlopen(url, timeout=3) as r:
        return json.loads(r.read().decode("utf-8"))

def wait_page_target(port: int, proc: subprocess.Popen, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Brave terminó durante la búsqueda de pestaña (exit={proc.returncode}).")
        try:
            targets = get_json(f"http://127.0.0.1:{port}/json/list")
            pages = [t for t in targets if t.get("type") == "page"]
            for t in pages:
                if "chatgpt.com/codex/settings/usage" in (t.get("url") or ""):
                    return t
            if pages:
                return pages[0]
        except Exception:
            pass
        time.sleep(0.3)
    raise TimeoutError("No encontré una pestaña CDP.")

class CDP:
    def __init__(self, ws_url: str):
        if websocket is None:
            raise RuntimeError("Falta websocket-client. Ejecuta setup_windows.bat.")
        self.ws = websocket.create_connection(ws_url, timeout=8, origin="http://127.0.0.1")
        self.next_id = 1

    def call(self, method: str, params=None):
        cid = self.next_id
        self.next_id += 1
        payload = {"id": cid, "method": method}
        if params is not None:
            payload["params"] = params
        self.ws.send(json.dumps(payload))
        deadline = time.time() + 10
        while time.time() < deadline:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == cid:
                if "error" in msg:
                    raise RuntimeError(f"CDP {method}: {msg['error']}")
                return msg.get("result") or {}
        raise TimeoutError(f"CDP timeout: {method}")

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass

def extract_page(cdp: CDP):
    expr = """(() => ({
      text: document.body ? document.body.innerText : "",
      title: document.title || "",
      href: location.href || "",
      readyState: document.readyState || ""
    }))()"""
    r = cdp.call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
    return ((r.get("result") or {}).get("value")) or {}

def terminate_tree(proc):
    if not proc or proc.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
                timeout=8,
            )
            return
        except Exception:
            pass
    try:
        proc.terminate()
    except Exception:
        pass

def process_capture(text: str, url: str, cfg: dict):
    data = core.parse_page_text(text, cfg)
    data["source"] = "codex_usage_browser_hidden"
    data["browser_url"] = url
    data["hidden_captured_at"] = datetime.now().astimezone().isoformat()
    core.save_json(core.output_path(cfg), data)
    (APP_DIR / "last_page_text.txt").write_text(text, encoding="utf-8")
    core.maybe_alert(data, cfg)
    return data

def main():
    started = time.time()
    cfg = core.load_config()
    browser = find_browser(cfg)
    if not browser:
        save_status({"ok": False, "stage": "startup", "error": "No encontré Brave, Google Chrome ni Microsoft Edge seleccionados"})
        return 2
    profile = profile_dir_for_browser(cfg, browser["key"])
    if websocket is None:
        save_status({"ok": False, "stage": "startup", "error": "websocket-client no instalado"})
        return 3

    profile.mkdir(parents=True, exist_ok=True)
    hc = cfg.get("hidden_browser") or {}
    timeout = float(hc.get("capture_timeout_seconds", 60))
    poll = float(hc.get("poll_interval_seconds", 1.0))
    grace = float(hc.get("challenge_grace_seconds", 45))
    hide_poll_ms = int(hc.get("hide_window_poll_ms", 80))
    x = int(hc.get("offscreen_x", -32000))
    y = int(hc.get("offscreen_y", -32000))
    w = int(hc.get("window_width", 900))
    h = int(hc.get("window_height", 700))

    marker = profile / "DevToolsActivePort"
    try:
        if marker.exists():
            marker.unlink()
    except Exception:
        pass

    args = [
        str(browser["exe"]),
        f"--user-data-dir={profile}",
        "--remote-debugging-port=0",
        "--remote-debugging-address=127.0.0.1",
        "--remote-allow-origins=http://127.0.0.1",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-default-apps",
        "--disable-sync",
        "--mute-audio",
        f"--window-position={x},{y}",
        f"--window-size={w},{h}",
        "--new-window",
        URL,
    ]

    proc = cdp = hider = None
    last_page = {}
    challenge_first = None

    try:
        si = None
        if os.name == "nt":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = SW_HIDE

        proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
            startupinfo=si,
        )

        hider = WindowHider(proc.pid, hide_poll_ms)
        hider.start()

        port = wait_devtools_port(profile, proc)
        target = wait_page_target(port, proc)
        ws_url = target.get("webSocketDebuggerUrl")
        if not ws_url:
            raise RuntimeError("La pestaña no entregó webSocketDebuggerUrl.")

        cdp = CDP(ws_url)
        cdp.call("Runtime.enable")
        cdp.call("Page.enable")

        deadline = time.time() + timeout
        while time.time() < deadline:
            last_page = extract_page(cdp)
            text = last_page.get("text") or ""
            title = last_page.get("title") or ""

            if looks_like_usage(text):
                data = process_capture(text, last_page.get("href") or URL, cfg)
                if not data.get("parse_ok"):
                    raise RuntimeError("Usage cargó, pero el parser no pudo leer los porcentajes.")
                save_status({
                    "ok": True,
                    "stage": "complete",
                    "mode": "headed_hidden",
                    "browser": browser["key"],
                    "browser_name": browser["display_name"],
                    "duration_seconds": round(time.time() - started, 2),
                    "five_hour_remaining": (data.get("five_hour") or {}).get("remaining_percent"),
                    "weekly_remaining": (data.get("weekly") or {}).get("remaining_percent"),
                    "reset_5h": (data.get("five_hour") or {}).get("reset_at"),
                    "reset_weekly": (data.get("weekly") or {}).get("reset_date"),
                    "page_title": title,
                    "profile_dir": str(profile),
                    "windows_hidden": hider.hidden_count if hider else 0,
                })
                print(f"PASS [{browser['display_name']}]:",
                      f"5h={(data.get('five_hour') or {}).get('remaining_percent')}%",
                      f"weekly={(data.get('weekly') or {}).get('remaining_percent')}%",
                      f"{round(time.time()-started,1)}s")
                return 0

            login = auth_hint(text, title)
            if login:
                save_status({"ok": False, "stage": "authentication", "mode": "headed_hidden",
                             "error": login, "page_title": title, "page_url": last_page.get("href"),
                             "text_preview": text[:1000], "profile_dir": str(profile)})
                notify_error_once(cfg, "hidden_auth", "⚠️ Codex Watcher necesita atención",
                                  login + " Ejecuta INSTALL_WINDOWS.bat para volver a autenticar el perfil dedicado.")
                print(f"AUTH [{browser['display_name']}]:", login)
                return 10

            challenge = challenge_hint(text, title)
            if challenge:
                if challenge_first is None:
                    challenge_first = time.time()
                if time.time() - challenge_first >= grace:
                    save_status({"ok": False, "stage": "challenge", "mode": "headed_hidden",
                                 "error": challenge + f" Persistió {int(grace)} s.",
                                 "page_title": title, "page_url": last_page.get("href"),
                                 "text_preview": text[:1000], "profile_dir": str(profile)})
                    notify_error_once(cfg, "hidden_challenge", "⚠️ Codex Watcher bloqueado",
                                      "La verificación de ChatGPT no avanzó automáticamente. Abre una vez el perfil dedicado.")
                    print(f"CHALLENGE [{browser['display_name']}]:", challenge)
                    return 11
            else:
                challenge_first = None

            time.sleep(poll)

        title = last_page.get("title") or ""
        text = last_page.get("text") or ""
        err = challenge_hint(text, title) or f"Codex Usage no apareció tras {int(timeout)} segundos."
        save_status({"ok": False, "stage": "capture_timeout", "mode": "headed_hidden",
                     "error": err, "page_title": title, "page_url": last_page.get("href"),
                     "text_preview": text[:1200], "profile_dir": str(profile)})
        print("FAIL:", err)
        return 12

    except Exception as exc:
        save_status({"ok": False, "stage": "exception", "mode": "headed_hidden",
                     "error": str(exc), "page_title": last_page.get("title"),
                     "page_url": last_page.get("href"),
                     "text_preview": (last_page.get("text") or "")[:1200],
                     "profile_dir": str(profile)})
        print("FAIL:", str(exc))
        return 13

    finally:
        if hider:
            hider.stop()
            hider.join(timeout=1)
        if cdp:
            cdp.close()
        terminate_tree(proc)

if __name__ == "__main__":
    raise SystemExit(main())
