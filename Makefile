# ─────────────────────────────
# Quoridor — AUTO SETUP (Windows)
# ─────────────────────────────

PY = py -3.11
VENV_DIR = venv

.PHONY: install run setup clean

setup:
	# Try to create venv with py -3.11, fallback to python3 or python
	$(PY) -m venv $(VENV_DIR) || python3 -m venv $(VENV_DIR) || python -m venv $(VENV_DIR)
	# Use the venv's python to upgrade pip and install requirements
	@if [ -x $(VENV_DIR)/bin/python ]; then \
		$(VENV_DIR)/bin/python -m pip install --upgrade pip && \
		$(VENV_DIR)/bin/python -m pip install -r requirements.txt; \
	elif [ -x $(VENV_DIR)/Scripts/python.exe ]; then \
		$(VENV_DIR)/Scripts/python.exe -m pip install --upgrade pip && \
		$(VENV_DIR)/Scripts/python.exe -m pip install -r requirements.txt; \
	else \
		echo "Could not find venv python interpreter. Did venv creation fail?"; exit 1; \
	fi

run:
	# Prefer using the venv python directly (no need to 'activate')
	@if [ -x $(VENV_DIR)/bin/python ]; then \
		$(VENV_DIR)/bin/python main.py; \
	elif [ -x $(VENV_DIR)/Scripts/python.exe ]; then \
		$(VENV_DIR)/Scripts/python.exe main.py; \
	else \
		echo "No virtualenv found. Run 'make setup' first or ensure python is installed."; exit 1; \
	fi

install:
	$(PY) -m pip install -r requirements.txt

clean:
	rm -rf __pycache__ || true