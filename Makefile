# ─────────────────────────────
# Quoridor — AUTO SETUP (Windows & Linux)
# ─────────────────────────────

VENV_DIR = venv

# Detect OS
ifeq ($(OS),Windows_NT)
	PYTHON = $(VENV_DIR)\Scripts\python.exe
	VENV_CREATE = py -3.11 -m venv $(VENV_DIR) || python -m venv $(VENV_DIR)
	RM_CMD = if exist __pycache__ rmdir /s /q __pycache__
else
	PYTHON = $(VENV_DIR)/bin/python
	VENV_CREATE = python3 -m venv $(VENV_DIR) || python -m venv $(VENV_DIR)
	RM_CMD = rm -rf __pycache__
endif

.PHONY: install run setup clean

setup:
	$(VENV_CREATE)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) main.py

install:
	$(PYTHON) -m pip install -r requirements.txt

clean:
	$(RM_CMD)