#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
mkdir -p "$ROOT/vendor"
fetch() {
  local name="$1" url="$2" sha="$3"
  if [ ! -d "$ROOT/vendor/$name/.git" ]; then git clone --filter=blob:none --no-checkout "$url" "$ROOT/vendor/$name"; fi
  git -C "$ROOT/vendor/$name" fetch origin "$sha"
  git -C "$ROOT/vendor/$name" checkout --detach "$sha"
  test "$(git -C "$ROOT/vendor/$name" rev-parse HEAD)" = "$sha"
}
fetch FlowEvo https://github.com/DEFENSE-SEU/FlowEvo.git 36e81efd4d1fdbabca7366200b15808ebef157fa
fetch ScienceWorld https://github.com/allenai/ScienceWorld.git e8216d6044e8e39be9fcb185e3b2dfb602584b52
# Historical repository is provenance-only; no historical dataset is needed to run.
# Optional audit checkout: fde8da720f09ae823cd36c4582a9413e764ab74a from
# https://github.com/zaoshuiban/FlowEvo-failure-driven-experiments.git
