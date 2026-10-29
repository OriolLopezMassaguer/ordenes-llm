#!/usr/bin/env bash
# Instalación en Linux / macOS:  ./instalar.sh
set -euo pipefail
cd "$(dirname "$0")"

if command -v uv >/dev/null; then
    echo "Instalando con uv..."
    uv sync --extra anthropic
    echo -e "\nListo. Ejecuta los scripts con:  uv run python scripts/experimento_fase1.py --help"
    echo "Tests:  uv run pytest"
    exit 0
fi

PY=$(command -v python3 || command -v python) || { echo "No encuentro Python 3.10+"; exit 1; }
echo "Instalando con venv + pip..."
"$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[anthropic,dev]"
echo -e "\nListo. Activa el entorno con:  source .venv/bin/activate"
echo "Luego:  python scripts/experimento_fase1.py --help   y   pytest"
