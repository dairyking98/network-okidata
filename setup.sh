#!/usr/bin/env bash
# Set up a venv and install dependencies (Linux/macOS).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo
echo "Setup complete. Run the app with:"
echo "  .venv/bin/python main.py"
