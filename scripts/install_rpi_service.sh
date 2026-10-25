#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_FILE="/etc/systemd/system/behavioral-camera-node.service"
USER_NAME="$(id -un)"

sudo tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=Behavioral Monitoring Dual Camera Node
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=-$PROJECT_DIR/.env.rpi
ExecStart=$PROJECT_DIR/.venv-rpi/bin/python $PROJECT_DIR/run_rpi_node.py
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now behavioral-camera-node.service
sudo systemctl status behavioral-camera-node.service --no-pager

