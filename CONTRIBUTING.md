# Contributing

Thank you for contributing to Cybersecurity Red Team Simulation.

## Before Contributing

Please make sure changes are intended for:

- Authorized security testing
- Cybersecurity education
- Isolated laboratory environments
- Adversary simulation
- Defensive validation

Do not submit features designed to facilitate unauthorized access, credential theft, privacy invasion, or evasion of platform security controls.

## Development

Clone the repository:

```bash
git clone https://github.com/Sayed-Eslamuddin908/Cybersecurity-Red-Team-Simulation.git
cd Cybersecurity-Red-Team-Simulation
```

Create an environment:

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Before Opening a Pull Request

Run:

```bash
python3 -m py_compile server.py redteam_api.py deployer.py payload_builder.py agent.py
```

If tests are available:

```bash
python3 -m pytest
```

Also verify that:

- No secrets are committed.
- No generated payloads are committed.
- Documentation matches the implementation.
- Changes are tested inside an isolated lab.
- New dependencies are documented in `requirements.txt`.

## Pull Request

Describe:

1. What changed
2. Why it changed
3. How it was tested
4. Any security implications
5. Any documentation changes
