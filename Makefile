# ─────────────────────────────
# Quoridor — AUTO SETUP (Windows)
# ─────────────────────────────

PY = py -3.11

.PHONY: install run setup clean

setup:
	$(PY) -m venv venv
	venv\Scripts\activate && python -m pip install --upgrade pip
	venv\Scripts\activate && python -m pip install -r requirements.txt

run:
	venv\Scripts\activate && python main.py

install:
	$(PY) -m pip install -r requirements.txt

clean:
	rmdir /s /q __pycache__ 2>nul || true