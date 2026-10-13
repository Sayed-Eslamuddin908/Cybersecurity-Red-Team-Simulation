# abilities.py
# MITRE ATT&CK mapped abilities for lab use only

ABILITIES = {
    "T1033": {
        "name": "System Owner/User Discovery",
        "cmd": "whoami",
        "tactic": "Discovery"
    },
    "T1087": {
        "name": "Account Discovery",
        "cmd": "net user",
        "tactic": "Discovery"
    },
    "T1016": {
        "name": "System Network Configuration Discovery",
        "cmd": "ipconfig /all" if __import__("os").name == "nt" else "ifconfig -a",
        "tactic": "Discovery"
    },
    "T1057": {
        "name": "Process Discovery",
        "cmd": "tasklist" if __import__("os").name == "nt" else "ps aux",
        "tactic": "Discovery"
    },
    "T1082": {
        "name": "System Information Discovery",
        "cmd": "systeminfo" if __import__("os").name == "nt" else "uname -a",
        "tactic": "Discovery"
    },
    "T1049": {
        "name": "System Network Connections Discovery",
        "cmd": "netstat -an",
        "tactic": "Discovery"
    },
    "T1135": {
        "name": "Network Share Discovery",
        "cmd": "net view",
        "tactic": "Discovery"
    },
    "T1018": {
        "name": "Remote System Discovery",
        "cmd": "arp -a",
        "tactic": "Discovery"
    },
    "T1083": {
        "name": "File and Directory Discovery",
        "cmd": "dir C:\\Users" if __import__("os").name == "nt" else "ls -la /home",
        "tactic": "Discovery"
    },
    "T1059": {
        "name": "Command and Scripting Interpreter",
        "cmd": "echo 'test' && whoami",
        "tactic": "Execution"
    },
}
