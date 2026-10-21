---
description: Run the quality gate and summarize failures (reusable workflow)
allowed-tools: Bash(scripts/check.sh:*), Bash(.venv/bin/python -m pytest:*), Read, Grep
---
Run `scripts/check.sh` (ruff check, ruff format --check, pytest) from the repo root.

Then report, in at most 12 lines:
1. **Verdict**: PASS or FAIL, and which stage failed first (lint / format / tests).
2. For every failing test: `test name`, the assertion or exception in one line, and the most likely cause
   (point to the `main.py` function or the test line; do not guess beyond the evidence).
3. **Suggested next command** (for example `ruff format .` or re-run one test with `pytest -q -k <name>`).

Rules: do NOT edit any file and do NOT run any other command. If everything passes, say so in one line and
include the test count.
