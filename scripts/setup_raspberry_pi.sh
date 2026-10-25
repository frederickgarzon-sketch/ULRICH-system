#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install Raspberry Pi OS Bookworm 64-bit first."
  exit 1
fi

sudo apt-get update
sudo apt-get install -y python3-venv python3-pip libgl1 libglib2.0-0 v4l-utils
python3 -m venv .venv-rpi
.venv-rpi/bin/python -m pip install --upgrade pip
.venv-rpi/bin/python -m pip install -r requirements-rpi.txt

if [[ ! -f .env.rpi ]]; then
  cp .env.rpi.example .env.rpi
fi

echo "Setup complete. List cameras with: v4l2-ctl --list-devices"
echo "Test node with: RPI_MOCK_MODE=true .venv-rpi/bin/python run_rpi_node.py"
echo "For USB cameras: .venv-rpi/bin/python run_rpi_node.py"

