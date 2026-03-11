#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SCOPE="${1:-changed}"
shift || true

# Use uv run to handle dependencies automatically via PEP 723
uv run "$SCRIPT_DIR/lint_skill.py" \
	--project-root "$ROOT" \
	--scope "$SCOPE" \
	"$@"
