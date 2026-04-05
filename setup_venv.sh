#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
PYTHON_CMD="${PYTHON_CMD:-python3}"

if ! command -v "$PYTHON_CMD" >/dev/null 2>&1; then
    echo "Error: Python not found: $PYTHON_CMD" >&2
    echo "Set PYTHON_CMD=<python_executable> or install Python 3." >&2
    exit 1
fi

echo "Creating/updating virtual environment at: $VENV_DIR"
"$PYTHON_CMD" -m venv "$VENV_DIR"

PIP="$VENV_DIR/bin/pip"
PYTHON="$VENV_DIR/bin/python"

echo "Upgrading pip..."
"$PYTHON" -m pip install --upgrade pip

echo "Installing Python dependencies..."
"$PIP" install \
    browser-cookie3==0.20.1 \
    Markdown==3.10.1 \
    lz4==4.4.5 \
    pycryptodomex==3.23.0 \
    requests==2.32.5

echo
echo "Done."
echo "Next steps:"
echo "  1) source \"$VENV_DIR/bin/activate\""
echo "  2) run ./modded_tools"

