#!/usr/bin/env bash
# The one quality gate: lint, format check, tests. Used by the git hook, CI and by agents.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
fi
echo "==> ruff check";           "$PY" -m ruff check .
echo "==> ruff format --check";  "$PY" -m ruff format --check .
echo "==> pytest";               "$PY" -m pytest -q
echo "ALL CHECKS PASSED"
