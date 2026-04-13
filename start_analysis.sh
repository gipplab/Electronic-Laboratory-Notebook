#!/bin/bash

# 1. Venv aktivieren
source venv/bin/activate

# 2. Pfad für das Autostart-Skript
export IPYTHONDIR=$(pwd)/jupyter_config

# 3. Jupyter Lab starten
echo "Starte Jupyter Lab auf Port 8888 (offen für alle IPs)..."

# --ip='0.0.0.0' ist der entscheidende Fix!
jupyter lab --ServerApp.port=8888 --ServerApp.port_retries=0 --ServerApp.token='' --ServerApp.password='' --ServerApp.ip='0.0.0.0' --ServerApp.allow_origin='*' -y