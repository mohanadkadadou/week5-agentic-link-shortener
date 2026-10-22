---
name: implement-feature
description: Implement one small feature or task in the link shortener test-first (read guidance, inspect code and tests, state behaviour, failing test, smallest change, run the gate, summarize risks). Use when asked to implement a task from docs/TASKS.md or add an endpoint.
---

# Implement a feature (link shortener)

Follow these steps in order. Do not skip the failing test.

1. **Read** the selected task in `docs/TASKS.md`, then `AGENTS.md`, `intent.md` and `tests/AGENTS.md`.
2. **Inspect** the code the task touches: `main.py` (routes, `init_db()`, SQL) and `tests/test_main.py`.
3. **State** the expected behaviour in a few lines: request, response, status codes, DB change (with a migration that keeps an
   existing `links.db` working) and the files you will change. Check it against the invariants in `intent.md`.
4. **Add a failing behavioural test** in `tests/test_main.py`, following `tests/AGENTS.md` (success + failure/edge case,
   independent, public API only). Run `pytest -q` and confirm it fails for the right reason.
5. **Implement the smallest change** in `main.py` that satisfies the task. Parameterised SQL only; no new dependencies.
6. **Run `scripts/check.sh`** (ruff, format check, `pytest`). Fix until it passes. Never use `--no-verify`.
7. **Summarize** in at most 10 lines: what changed, tests added, gate result, and any remaining risks or assumptions.
   Do not commit unless asked.
