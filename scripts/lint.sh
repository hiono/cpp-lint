#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SCOPE="${1:-changed}"
shift || true

python3 "$SCRIPT_DIR/lint_skill.py" \
	--project-root "$ROOT" \
	--scope "$SCOPE" \
	"$@"
