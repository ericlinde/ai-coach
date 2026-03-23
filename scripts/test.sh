#!/usr/bin/env bash
set -euo pipefail

pip3 install -e ".[dev]" --quiet --break-system-packages
python3 -m pytest "$@"
