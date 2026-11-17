#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
bash "$ROOT/output/scripts/fetch_upstreams.sh" "$ROOT"
python3 -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/python" -m pip install -r "$ROOT/output/requirements.lock.txt"
"$ROOT/.venv/bin/python" -m pip install --no-deps --no-build-isolation -e "$ROOT/vendor/FlowEvo" "$ROOT/vendor/ScienceWorld" -e "$ROOT/output"
"$ROOT/.venv/bin/python" -m pytest "$ROOT/output/tests" -q
