#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -c 'import sys;assert sys.version_info>=(3,10),"Need Python 3.10+"'
python3 -m venv .venv
.venv/bin/python -m pip install -q -r requirements.txt
mkdir -p data logs output/packages
./jr history-import data/history_seed.csv
printf '\nInstalled. No periodic tasks created.\n./jr doctor\n./jr run\n'
