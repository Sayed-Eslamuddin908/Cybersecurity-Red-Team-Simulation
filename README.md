# 🔴 Cybersecurity Red Team Simulation

A lightweight **Red Team Simulation and Adversary Emulation Tool** built with Python and Flask for authorized cybersecurity labs, security research, and controlled testing environments.

The project provides a web-based interface for managing Red Team simulations, agents, reconnaissance, MITRE ATT&CK techniques, and security-testing activities.

> ⚠️ **For authorized and educational use only. Run this project only against systems you own or have explicit permission to test.**

---

## 🧰 Requirements

Before starting, make sure you have:

- Linux / Kali Linux
- Python 3
- Git
- Internet connection
- `pip`
- Required Python packages from `requirements.txt`

Recommended environment:

```text
Kali Linux
Python 3.x
```

---

# 🚀 Installation & Execution

Follow the steps **in order**.

---

## 1. Check Python 3

First verify that Python 3 is installed:

```bash
python3 --version
```

Example:

```text
Python 3.13.x
```

If Python 3 is not installed:

```bash
sudo apt install python3 python3-pip -y
```

Verify again:

```bash
python3 --version
```

---

# 2. Update Kali Linux

Update the package lists:

```bash
sudo apt update
```

You can optionally upgrade installed packages:

```bash
sudo apt upgrade -y
```

### Why?

Updating the package list ensures that your system uses the latest available package information before installing dependencies.

---

# 3. Clone the Repository

Clone the project:

```bash
git clone https://github.com/Sayed-Eslamuddin908/Cybersecurity-Red-Team-Simulation.git
```

Move into the project directory:

```bash
cd Cybersecurity-Red-Team-Simulation
```

Verify that you are inside the correct directory:

```bash
pwd
```

You should see something similar to:

```text
/home/kali/Cybersecurity-Red-Team-Simulation
```

Check the project files:

```bash
ls
```

You should see files such as:

```text
server.py
requirements.txt
README.md
```

---

# 4. Give Execution Permission

Make the main server executable:

```bash
chmod +x server.py
```

Verify the permission:

```bash
ls -l server.py
```

You should see executable permissions similar to:

```text
-rwxr-xr-x
```

The `x` indicates that the file has execute permission.

---

# 5. Install Python Requirements

The project contains its Python dependencies inside:

```text
requirements.txt
```

Install them with:

```bash
pip3 install -r requirements.txt
```

If your Kali system requires the Python package manager through Python 3:

```bash
python3 -m pip install -r requirements.txt
```

### What does `-r` mean?

The `-r` option tells pip:

> Read the package names from the specified requirements file and install them.

Therefore:

```bash
pip3 install -r requirements.txt
```

means:

```text
requirements.txt
       ↓
Read dependencies
       ↓
Download packages
       ↓
Install packages
       ↓
Project ready
```

---

# 6. Start the Tool

Start the Red Team Simulation server:

```bash
python3 server.py
```

The server will start the Flask application.

You should see output indicating that the application is running.

The default web interface is available on:

```text
http://127.0.0.1:8888
```

If your server is configured to listen on your network interface, you can access it using the Kali machine's IP address:

```text
http://YOUR-KALI-IP:8888
```

Example:

```text
http://192.168.163.135:8888
```

---

# 🔄 Complete Installation in One Flow

For a fresh Kali installation:

```bash
sudo apt update

git clone https://github.com/Sayed-Eslamuddin908/Cybersecurity-Red-Team-Simulation.git

cd Cybersecurity-Red-Team-Simulation

chmod +x server.py

python3 -m pip install -r requirements.txt

python3 server.py
```

Then open:

```text
http://127.0.0.1:8888
```

---

# 🛑 Stop the Tool

To stop the server:

```text
CTRL + C
```

This stops the running Flask process.

---

# 🔁 Start the Tool Again

After the installation has already been completed, you only need:

```bash
cd Cybersecurity-Red-Team-Simulation
```

Then:

```bash
python3 server.py
```

---

# 📁 Project Structure

```text
Cybersecurity-Red-Team-Simulation/
│
├── server.py
├── redteam_api.py
├── deployer.py
├── payload_builder.py
├── agent.py
├── payload.ps1
├── abilities.py
├── abilities.json
├── requirements.txt
├── README.md
│
├── static/
│
└── templates/
```

### `server.py`

Main Flask server responsible for starting the web application and handling the primary application workflow.

### `redteam_api.py`

Contains API functionality used by the Red Team simulation interface.

### `deployer.py`

Handles controlled laboratory deployment functionality.

### `payload_builder.py`

Provides payload-generation functionality used within the authorized testing environment.

### `agent.py`

Python-based laboratory agent component.

### `payload.ps1`

PowerShell-based Windows laboratory agent.

### `abilities.py`

Handles the project's Red Team abilities and techniques.

### `abilities.json`

Contains the defined simulation abilities and associated information.

### `requirements.txt`

Contains the Python packages required by the project.

---

# 🖥️ How the Tool Works

The basic architecture is:

```text
                 RED TEAM OPERATOR
                        │
                        ▼
                ┌───────────────┐
                │  Web Interface│
                └───────┬───────┘
                        │
                        ▼
                 ┌─────────────┐
                 │  server.py  │
                 └──────┬──────┘
                        │
             ┌──────────┼──────────┐
             │          │          │
             ▼          ▼          ▼
          API        Abilities   Simulation
             │          │          │
             └──────────┼──────────┘
                        │
                        ▼
                  Authorized Lab
```

The tool is designed around a controlled Red Team simulation workflow rather than unrestricted targeting.

---

# 🎯 Main Purpose

The project is designed to help security students and researchers understand:

- Red Team operations
- Adversary simulation
- MITRE ATT&CK
- Network reconnaissance
- Endpoint simulation
- Security testing
- Command execution workflows
- Detection validation
- Cybersecurity laboratory environments

---

# 🧪 Recommended Lab Environment

Use this project inside an isolated virtual environment.

Example:

```text
┌──────────────────────────────┐
│          HOST PC             │
│                              │
│  ┌────────────┐              │
│  │ Kali Linux │              │
│  │ Red Team   │              │
│  └──────┬─────┘              │
│         │                    │
│   Isolated Network           │
│         │                    │
│  ┌──────▼──────────┐         │
│  │ Windows Lab VM  │         │
│  │ Test Target     │         │
│  └─────────────────┘         │
│                              │
└──────────────────────────────┘
```

Recommended network types:

- VMware Host-Only
- VMware Custom isolated network
- VirtualBox Host-Only
- VirtualBox Internal Network

Do not expose the laboratory control server to the public Internet.

---

# 🔴 Red Team Simulation

The project can be used to simulate controlled adversary activity against laboratory systems.

Typical workflow:

```text
Target
   │
   ▼
Reconnaissance
   │
   ▼
Technique Selection
   │
   ▼
Simulation
   │
   ▼
Execution
   │
   ▼
Result
   │
   ▼
Analysis
```

---

# 🧩 MITRE ATT&CK

The project includes MITRE ATT&CK-related abilities for adversary simulation.

The purpose is to help researchers understand how individual techniques can be represented and simulated inside an isolated environment.

Example categories include:

```text
Discovery
Execution
Network Discovery
System Discovery
Process Discovery
File and Directory Discovery
User Discovery
```

---

# 🔵 Blue Team Integration

The Red Team Simulation tool can also be used as the offensive component of a Purple Team laboratory.

Example:

```text
🔴 RED TEAM
     │
     ▼
Simulation
     │
     ▼
Windows Lab
     │
     ▼
Logs / Events
     │
     ▼
🔵 BLUE TEAM
     │
     ▼
Detection
     │
     ▼
Investigation
```

Possible defensive technologies:

- Wazuh
- Sysmon
- Suricata
- Wireshark
- Windows Event Logs
- Sigma
- MITRE ATT&CK

This allows you to test whether defensive controls detect simulated adversary behavior.

---

# 🔐 Security Recommendations

This project should be operated only in a controlled environment.

Recommended:

### Use an isolated network

```text
Kali
   │
   └── Host-Only Network ── Windows Lab
```

### Do not expose the server publicly

Avoid:

```text
Internet
   ↓
Port 8888
   ↓
Red Team Server
```

Use:

```text
Private Lab Network
        ↓
Red Team Server
        ↓
Authorized Targets
```

### Never test unauthorized systems

Only use:

- Your own machines
- Your own virtual machines
- Authorized penetration-testing environments
- Approved educational laboratories

---

# 🛠️ Troubleshooting

## Python command not found

Try:

```bash
sudo apt install python3 python3-pip -y
```

Then:

```bash
python3 --version
```

---

## `requirements.txt` not found

Check your current directory:

```bash
pwd
```

Then:

```bash
ls
```

Make sure you are inside:

```text
Cybersecurity-Red-Team-Simulation
```

If necessary:

```bash
cd Cybersecurity-Red-Team-Simulation
```

---

## Permission denied for `server.py`

Run:

```bash
chmod +x server.py
```

Then:

```bash
python3 server.py
```

---

## Port 8888 already in use

Check:

```bash
sudo lsof -i :8888
```

Or:

```bash
sudo ss -lntp | grep 8888
```

Stop the process only if you know it belongs to your lab/application.

---

# 📜 License

See the repository license for the applicable terms.

---

# 👨‍💻 Author

**Sayed Eslamuddin**

Cybersecurity | Red Team | Digital Forensics

GitHub:

**Sayed-Eslamuddin908**

---

# ⚠️ Disclaimer

This project is developed for:

- Cybersecurity education
- Authorized security testing
- Red Team simulation
- Adversary emulation
- Security research
- Isolated laboratory environments

The author does not authorize the use of this project against systems without explicit permission.

**You are responsible for ensuring that your use of this project complies with applicable laws, regulations, policies, and authorization requirements.**

---

## ⭐ If You Find This Project Useful

Consider giving the repository a ⭐ on GitHub and sharing feedback or improvements through the project's contribution process.
