# tunnel.py
# Lab-only Cloudflare Quick Tunnel manager.

import re
import shutil
import subprocess
import threading
import time

from flask import Blueprint, request, jsonify

tunnel_bp = Blueprint('tunnel_bp', __name__)

_tunnel_proc = None
_tunnel_url = None
_tunnel_log = []
_tunnel_lock = threading.Lock()
_tunnel_started_at = None

URL_RE = re.compile(r'https://[a-z0-9-]+\.trycloudflare\.com')


def cloudflared_available():
    return shutil.which("cloudflared") is not None


def _reader(proc):
    global _tunnel_url, _tunnel_log
    for raw in iter(proc.stdout.readline, b''):
        line = raw.decode(errors="replace").rstrip()
        with _tunnel_lock:
            _tunnel_log.append(line)
            if len(_tunnel_log) > 500:
                _tunnel_log = _tunnel_log[-500:]
        m = URL_RE.search(line)
        if m:
            with _tunnel_lock:
                _tunnel_url = m.group(0)
            print(f"[TUNNEL] Public URL: {_tunnel_url}")


def start_tunnel(local_url="http://localhost:8888"):
    global _tunnel_proc, _tunnel_url, _tunnel_log, _tunnel_started_at

    if not cloudflared_available():
        return None, "cloudflared not installed."

    with _tunnel_lock:
        if _tunnel_proc and _tunnel_proc.poll() is None:
            return _tunnel_url, None
        _tunnel_url = None
        _tunnel_log = []

    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", local_url, "--no-autoupdate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )

    with _tunnel_lock:
        _tunnel_proc = proc
        _tunnel_started_at = time.time()

    threading.Thread(target=_reader, args=(proc,), daemon=True).start()

    deadline = time.time() + 30
    while time.time() < deadline:
        with _tunnel_lock:
            if _tunnel_url:
                return _tunnel_url, None
        time.sleep(0.3)

    return None, "Timed out waiting for tunnel URL."


def stop_tunnel():
    global _tunnel_proc, _tunnel_url
    with _tunnel_lock:
        if _tunnel_proc and _tunnel_proc.poll() is None:
            try:
                _tunnel_proc.terminate()
            except Exception:
                pass
        _tunnel_proc = None
        _tunnel_url = None
    print("[TUNNEL] Stopped")


def current_url():
    with _tunnel_lock:
        return _tunnel_url


def is_running():
    with _tunnel_lock:
        return bool(_tunnel_proc and _tunnel_proc.poll() is None)


@tunnel_bp.route('/api/tunnel/status')
def tunnel_status():
    return jsonify({
        "available": cloudflared_available(),
        "running": is_running(),
        "url": current_url(),
        "started_at": _tunnel_started_at,
    })


@tunnel_bp.route('/api/tunnel/start', methods=['POST'])
def tunnel_start():
    data = request.json or {}
    if not data.get("consent"):
        return jsonify({"error": "Consent required."}), 400

    if not cloudflared_available():
        return jsonify({
            "error": "cloudflared not installed. Run: "
                     "wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 "
                     "-O cloudflared && chmod +x cloudflared && sudo mv cloudflared /usr/local/bin/"
        }), 500

    url, err = start_tunnel()
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"status": "ok", "url": url})


@tunnel_bp.route('/api/tunnel/stop', methods=['POST'])
def tunnel_stop():
    stop_tunnel()
    return jsonify({"status": "stopped"})


@tunnel_bp.route('/api/tunnel/log')
def tunnel_log():
    with _tunnel_lock:
        return jsonify({"lines": _tunnel_log[-100:]})
