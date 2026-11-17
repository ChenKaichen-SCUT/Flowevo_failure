#!/usr/bin/env bash
# Run on Ubuntu 22.04 x86_64 as root. No network except local JVM loopback.
set -euo pipefail
RESTORED="$(realpath "${1:?Pass the directory created by server_snapshot.py restore}")"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
test -f "$RESTORED/RESTORE_VERIFICATION.json"
export RESTORED SCRIPTS
unshare -n -- bash <<'OFFLINE'
set -euo pipefail
ip link set lo up
export FLOWEVO_OFFLINE_ONLY=1
unset DEEPSEEK_API_KEY OPENAI_API_KEY
PROJECT="$RESTORED/root/flowevo-scienceworld"
OUTPUT="$RESTORED/root/flowevo-success-trace/output"
export JAVA_HOME="$RESTORED/usr/lib/jvm/java-11-openjdk-amd64"
export PATH="$JAVA_HOME/bin:$PATH"
export PYTHONPATH="$OUTPUT/src:$PROJECT/vendor/FlowEvo/src:$PROJECT/vendor/ScienceWorld"
PYTHON="$PROJECT/.venv/bin/python"
"$PYTHON" -c 'import sys; assert sys.version_info[:2]==(3,10), "Use Ubuntu 22.04 Python 3.10 or rebuild the venv"'
"$PYTHON" -m pytest "$OUTPUT/tests" -q > "$RESTORED/RESTORED_TESTS.txt"
"$PYTHON" "$SCRIPTS/backup_offline_smoke.py" --restored "$RESTORED" --output "$RESTORED/RESTORED_SMOKE.json"
cat "$RESTORED/RESTORED_TESTS.txt"
OFFLINE
