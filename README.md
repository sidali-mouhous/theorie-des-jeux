# 🎯 Quoridor — IA en Python

Projet de Master 1 — Université de Rouen Normandie (2025/2026)

---

## ⚠️ Prérequis

- Python **3.11 uniquement**
- Windows / Linux OK
- pygame (installed via the project's requirements)

---

## 🚀 Installation (ULTRA SIMPLE)

```bash
git clone <repo_url>
cd theorie-des-jeux
# Create a virtual environment and install dependencies
make setup
# On Linux/macOS you can also run the game directly with the venv python:
./venv/bin/python main.py
# On Windows (PowerShell/CMD):
venv\Scripts\python.exe main.py

# Or use the convenience target:
make run

Les fichiers du jeu sont maintenant directement à la racine du dépôt.
```

Note: The Makefile was updated to support both Windows and Unix virtualenv activation and to prefer invoking the virtualenv's python directly (no manual `activate` required). If you hit issues, run `make setup` again and check your Python version with `python --version` or `python3 --version`.