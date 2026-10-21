# AGENTS.md: Link Shortener

Instructions for any coding agent (Claude Code, Antigravity/Gemini, Codex, Cursor...).
Read `intent.md` first for *why* this service exists and what it must never do.

## What this is
A tiny FastAPI + SQLite URL shortener. One module (`main.py`), one test file (`test_main.py`).

## Run, test, lint (copy-paste commands)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt     # fastapi, uvicorn, httpx, pytest, ruff
scripts/check.sh                        # THE quality gate: ruff check + ruff format --check + pytest
pytest -q                               # tests only
uvicorn main:app --reload               # dev server on :8000 (OpenAPI docs at /docs)
git config core.hooksPath .githooks     # enable the pre-commit gate (once per clone)
```

## Where things live
| Path | Purpose |
|---|---|
| `main.py` | the whole app: DB helpers + migration, `encode()` (base62), `POST /shorten`, `GET /stats/{code}`, `GET /{code}` (counts a click) |
| `test_main.py` | pytest suite using FastAPI `TestClient` |
| `docs/TASKS.md` | backlog of small tasks |
| `docs/PLAYBOOKS.md` | reusable prompts/workflows (test-and-summarize, new-endpoint) |
| `.githooks/pre-commit` | blocks commits when lint, format or tests fail |
| `.claude/commands/`, `.claude/agents/` | Claude Code saved command and the planner/implementer/reviewer subagents |
| `links.db` | SQLite file created next to `main.py` at import time. **Git-ignored. Never commit it.** |

## Conventions
- Python 3.10+, type hints on every function, 4-space indent, double quotes, 100-column lines (`ruff.toml`).
- Use parameterised SQL (`?` placeholders) only. **Never** build SQL with f-strings.
- DB access goes through `get_db()` inside `with closing(...)`. Do not leave connections open.
- Errors are `HTTPException` with the status code from the task spec; keep `detail` strings short and lowercase.
- Keep `main.py` as a single small module unless a task says otherwise. No new dependencies without asking.

## Workflow: new endpoint or behaviour (follow in order)
1. **Plan**: state the endpoint, request/response shape, status codes and DB changes. Wait for approval if the plan changes the schema.
2. **Failing test first**: add a test in `test_main.py`, run `pytest -q`, and confirm it fails *for the right reason*.
3. **Implement** the smallest change in `main.py`.
4. **Run the hook/gate**: `scripts/check.sh` must pass. This is also what `git commit` runs.
5. **Review** the diff (see `.claude/agents/reviewer.md`) before accepting.

## Safe vs. forbidden
**Safe (no need to ask):** reading any file; `pytest`, `ruff check`, `ruff format`, `scripts/check.sh`; editing `main.py`, `test_main.py`, `docs/*`; `git status|diff|log|add|commit` on a feature branch.

**Ask first:** adding a dependency; changing the DB schema (a migration must keep existing `links.db` files working); renaming/removing an endpoint; `git push`.

**Forbidden:**
- `rm -rf`, deleting `links.db` to "fix" a schema problem (write a migration instead), `git reset --hard`, `git push --force`.
- `git commit --no-verify` or editing `.githooks/` to weaken the gate.
- Weakening or deleting a test to make it pass. A failing test means the code is wrong or the spec changed: say which.
- Committing secrets, `.env` files or `links.db`. Calling external URLs from the service (it only *redirects*).

## Known gotchas
- Tests share the real `links.db` (no isolation fixture). Run order must not matter; never assert on absolute codes like `"b"`.
- `init_db()` runs at import time and only `CREATE TABLE IF NOT EXISTS`: an older `links.db` will **not** get new columns. Schema changes need an explicit migration in `init_db()`.
- `short_url` is relative (`/<code>`): it has no host.
- Needs SQLite >= 3.35 (`UPDATE ... RETURNING`); `main.py` fails fast at import otherwise.
- A click = one `GET /{code}` that returned 307. `/stats/{code}` and 404s never count; prefetchers/bots can inflate counts (accepted).
