# Link Shortener, made agent-native (Week 5)

FastAPI + SQLite URL shortener with `AGENTS.md`, `intent.md`, a pre-commit quality gate, a saved command and
planner/implementer/reviewer subagents. See [`writeup.md`](writeup.md) for the artifacts, evidence and reflection.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
git config core.hooksPath .githooks   # enable the pre-commit gate
scripts/check.sh                      # ruff + format check + pytest (12 tests)
uvicorn main:app --reload             # POST /shorten, GET /{code}, GET /stats/{code}
```
