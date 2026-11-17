#!/usr/bin/env bash
set -euo pipefail
KEY_FILE="${1:?Pass the private API key file path for the scan}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/output"
test "$(git branch --show-current)" = feat/scienceworld-failure-invariants
"$ROOT/.venv/bin/python" scripts/scan_publication.py --repo . --api-key-file "$KEY_FILE"
git add src scripts tests configs reports artifacts results data README.md REPRODUCE.md UPSTREAM_LICENSES.md requirements.lock.txt pyproject.toml .gitignore .gitattributes
"$ROOT/.venv/bin/python" scripts/scan_publication.py --repo . --api-key-file "$KEY_FILE"
if ! git diff --cached --quiet; then git commit -m 'Publish real ScienceWorld experiments and audited Chinese report'; fi
"$ROOT/.venv/bin/python" scripts/scan_publication.py --repo . --api-key-file "$KEY_FILE"
git push origin HEAD:refs/heads/feat/scienceworld-failure-invariants
test "$(git rev-parse HEAD)" = "$(git ls-remote origin refs/heads/feat/scienceworld-failure-invariants | cut -f1)"
