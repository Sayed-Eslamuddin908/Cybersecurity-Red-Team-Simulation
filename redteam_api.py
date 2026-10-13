# redteam_api.py
# Lab-only Red Team backend: real msfvenom, msfconsole (PTY), nmap.

import os
import shutil
import subprocess
import threading
import queue
import uuid
import ipaddress
import socket
import pty
import select
import re
import time

from flask import Blueprint, request, jsonify, Response

redteam_bp = Blueprint('redteam_bp', __name__)

# ---------------- Tool availability ----------------

def tool_available(name):
    return shutil.which(name) is not None

def tools_status():
    return {
        "msfvenom":   tool_available("msfvenom"),
        "msfconsole": tool_available("msfconsole"),
        "nmap":       tool_available("nmap"),
        "whois":      tool_available("whois"),
        "dig":        tool_available("dig"),
    }

@redteam_bp.route('/api/tools-status')
def api_tools_status():
    return jsonify(tools_status())

# ---------------- ANSI stripping ----------------

ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(text):
    return ANSI_RE.sub('', text)

# ---------------- msfvenom ----------------

@redteam_bp.route('/api/run-msfvenom', methods=['POST'])
def run_msfvenom():
    data = request.json or {}
    if not data.get("consent"):
        return jsonify({"error": "Consent required."}), 400

    command = (data.get("command") or "").strip()
    if not command:
        return jsonify({"error": "No command provided"}), 400

    if not command.startswith("msfvenom "):
        return jsonify({"error": "Only msfvenom commands allowed here."}), 400

    for bad in [";", "&&", "||", "|", "`", "$(", "\n", "\r"]:
        if bad in command:
            return jsonify({"error": f"Illegal character: {bad}"}), 400

    if not tool_available("msfvenom"):
        return jsonify({"error": "msfvenom not installed"}), 500

    os.makedirs("generated_payloads", exist_ok=True)

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "msfvenom timed out"}), 500

    output_file = None
    parts = command.split()
    if "-o" in parts:
        try:
            output_file = os.path.basename(parts[parts.index("-o") + 1])
        except Exception:
            pass

    exists = False
    if output_file:
        exists = os.path.exists(os.path.join("generated_payloads", output_file)) or os.path.exists(output_file)

    print(f"[msfvenom] rc={result.returncode} file={output_file}")
    return jsonify({
        "status":       "ok" if result.returncode == 0 else "error",
        "returncode":   result.returncode,
        "stdout":       result.stdout[-6000:],
        "stderr":       result.stderr[-2000:],
        "output_file":  output_file,
        "download_url": f"/download/{output_file}" if output_file and exists else None,
        "file_exists":  exists,
    })

# ---------------- nmap ----------------

@redteam_bp.route('/api/run-nmap', methods=['POST'])
def run_nmap():
    data = request.json or {}
    if not data.get("consent"):
        return jsonify({"error": "Consent required."}), 400

    target = (data.get("target") or "").strip()
    args   = (data.get("args") or "-sV -T4 --top-ports 100").strip()

    if not target:
        return jsonify({"error": "No target provided"}), 400

    allowed = False
    try:
        allowed = ipaddress.ip_address(target).is_private
    except ValueError:
        try:
            allowed = ipaddress.ip_address(socket.gethostbyname(target)).is_private
        except Exception:
            allowed = False

    if not allowed:
        return jsonify({"error": "Only private (RFC1918) lab targets allowed."}), 400

    for bad in ["--script", "-oN", "-oX", "-oS", "|", ";", "&&", "||", "`", "$("]:
        if bad in args:
            return jsonify({"error": f"Illegal argument: {bad}"}), 400

    if not tool_available("nmap"):
        return jsonify({"error": "nmap not installed"}), 500

    cmd = f"nmap {args} {target}"
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "nmap timed out"}), 500

    print(f"[nmap] {cmd} rc={result.returncode}")
    return jsonify({
        "status":     "ok" if result.returncode == 0 else "error",
        "command":    cmd,
        "returncode": result.returncode,
        "stdout":     result.stdout[-8000:],
        "stderr":     result.stderr[-2000:],
    })

# ---------------- msfconsole via PTY ----------------
#
# Using pty.openpty() gives msfconsole a real TTY, which stops it from
# emitting the "stty: Inappropriate ioctl for device" spam.
#
# A separate writer thread handles stdin so we don't block the Flask worker.

_msf_sessions = {}
_msf_lock = threading.Lock()


def _pty_reader(session_id, master_fd, out_queue, stop_flag):
    """Read from PTY master, push to queue."""
    while not stop_flag.is_set():
        try:
            r, _, _ = select.select([master_fd], [], [], 0.3)
            if master_fd in r:
                try:
                    data = os.read(master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                try:
                    out_queue.put_nowait(data)
                except queue.Full:
                    pass
        except Exception:
            break
    try:
        out_queue.put_nowait(b"\n[msfconsole session ended]\n")
    except Exception:
        pass


@redteam_bp.route('/api/msf/start', methods=['POST'])
def msf_start():
    data = request.json or {}
    if not data.get("consent"):
        return jsonify({"error": "Consent required."}), 400
    if not tool_available("msfconsole"):
        return jsonify({"error": "msfconsole not installed"}), 500

    session_id = str(uuid.uuid4())[:8]

    master_fd, slave_fd = pty.openpty()

    # Environment for msfconsole: quiet, no color-pager weirdness, TERM=xterm
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLUMNS"] = "160"
    env["LINES"] = "40"

    proc = subprocess.Popen(
        ["msfconsole", "-q"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        env=env,
        preexec_fn=os.setsid,
        close_fds=True,
    )
    os.close(slave_fd)

    out_q = queue.Queue(maxsize=20000)
    stop_flag = threading.Event()
    t = threading.Thread(target=_pty_reader, args=(session_id, master_fd, out_q, stop_flag), daemon=True)
    t.start()

    with _msf_lock:
        _msf_sessions[session_id] = {
            "proc":      proc,
            "master_fd": master_fd,
            "queue":     out_q,
            "thread":    t,
            "stop":      stop_flag,
        }

    print(f"[msfconsole] started session {session_id} pid={proc.pid}")
    return jsonify({"status": "ok", "session_id": session_id})


@redteam_bp.route('/api/msf/write/<session_id>', methods=['POST'])
def msf_write(session_id):
    with _msf_lock:
        s = _msf_sessions.get(session_id)
    if not s:
        return jsonify({"error": "session not found"}), 404

    data = request.json or {}
    text = data.get("text", "")
    try:
        os.write(s["master_fd"], text.encode())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"status": "ok"})


@redteam_bp.route('/api/msf/read/<session_id>')
def msf_read(session_id):
    with _msf_lock:
        s = _msf_sessions.get(session_id)
    if not s:
        return jsonify({"error": "session not found"}), 404

    buf = b""
    try:
        while True:
            chunk = s["queue"].get_nowait()
            buf += chunk
            if len(buf) > 65536:
                break
    except queue.Empty:
        pass

    raw = buf.decode(errors="replace")
    clean = strip_ansi(raw)
    return Response(clean, mimetype="text/plain")


@redteam_bp.route('/api/msf/stop/<session_id>', methods=['POST'])
def msf_stop(session_id):
    with _msf_lock:
        s = _msf_sessions.pop(session_id, None)
    if not s:
        return jsonify({"error": "session not found"}), 404

    s["stop"].set()
    try:
        s["proc"].terminate()
    except Exception:
        pass
    try:
        os.close(s["master_fd"])
    except Exception:
        pass

    print(f"[msfconsole] stopped session {session_id}")
    return jsonify({"status": "stopped"})
