# Subagent 2: IMPLEMENTER — task 2, "Click counter"

Role definition: `.claude/agents/implementer.md` (spawned as a `general-purpose` subagent with full edit rights but told: only main.py/test_main.py, no git writes).
Prompt: implement the approved plan (docs/transcripts/01-planner.md incl. the human-gate decisions) test-first; show the failing run; implement; run scripts/check.sh; report.

## Implementer's report (verbatim)

The click counter is implemented as planned, test-first, and `scripts/check.sh` passes: ruff check and format are clean, and 12 tests pass (3 existing, 9 new). Nothing was committed or staged. `git status` shows only `main.py` and `test_main.py` modified.

**Tests added** (9, all with type hints and one-line docstrings; the three existing tests are untouched):
- `test_stats_new_link_has_zero_clicks`
- `test_redirect_increments_clicks`
- `test_stats_does_not_count_as_click`
- `test_stats_unknown_code_404`
- `test_unknown_redirect_does_not_create_or_count`
- `test_stats_reports_correct_url_per_code`
- `test_stats_route_not_shadowed_by_redirect`
- `test_concurrent_clicks_are_atomic`, which uses 20 requests through a `ThreadPoolExecutor` with 8 workers, all via the shared `TestClient`
- `test_migration_adds_clicks_column_to_old_db`

The migration test builds an old-schema DB in `tmp_path` and patches `main.DB_PATH` with `monkeypatch`. It calls `main.init_db()` twice and checks that the rows survive with clicks 0. It then redirects `/a` and checks that `/stats/a` shows 1 click.

**Step 1, failing run before implementing** (8 failed, 4 passed). `main` imported fine, so none of the failures is an import error:
- `test_stats_new_link_has_zero_clicks`: got 404 where 200 was expected, because the `/stats` route doesn't exist yet.
- `test_stats_route_not_shadowed_by_redirect`: same 404 from the missing route.
- `test_stats_unknown_code_404`: the detail is FastAPI's default "Not Found", not "unknown code".
- `test_redirect_increments_clicks`, `test_stats_does_not_count_as_click` and `test_concurrent_clicks_are_atomic`: `KeyError: 'clicks'`, because the catch-all `/{code}` treated `stats` as a code.
- `test_stats_reports_correct_url_per_code`: wrong body for the same reason.
- `test_migration_adds_clicks_column_to_old_db`: `sqlite3.OperationalError: no such column: clicks`, because no migration exists yet.

The 4 that passed were the 3 existing tests plus `test_unknown_redirect_does_not_create_or_count` (a guard expected to pass already).

**Step 2, implemented in `main.py`:** DDL has `clicks INTEGER NOT NULL DEFAULT 0`; `init_db()` migrates idempotently with `PRAGMA table_info(links)` + `ALTER TABLE ... ADD COLUMN`; `GET /stats/{code}` registered above `GET /{code}`; the redirect runs `UPDATE links SET clicks = clicks + 1 WHERE code = ? RETURNING url`, commits, and returns 404 "unknown code" when no row comes back.

**Step 4:** The migration test passes against a real old-schema DB (temp copy in `tmp_path`). `links.db` was never deleted or modified by me.

**Deviations from the plan:**
- The concurrency test uses the real `ThreadPoolExecutor` with a shared `TestClient` instead of one client per thread. It passed (20 clicks counted), so I kept it.
- I used `UPDATE ... RETURNING` rather than the planned fallback, as the human gate allows. I did not re-check the SQLite version myself and relied on the 3.53 stated. The test run confirms `RETURNING` works.
- I did not catch the "duplicate column name" race on startup, which the plan listed as optional. A write error such as "database is locked" propagates, as the human gate decided.

## Orchestrator verification (not taken on trust)
`git diff main.py` was read and matched the report; `scripts/check.sh` re-run: ruff clean, 12 passed.
