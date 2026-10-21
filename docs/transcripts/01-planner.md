# Subagent 1: PLANNER (read-only) — task 2, "Click counter"

Role definition: `.claude/agents/planner.md`. Spawned as a read-only `Plan` subagent (cannot edit files).
Prompt given: read AGENTS.md, intent.md, main.py, test_main.py, docs/TASKS.md and planner.md; plan task 2; be concrete about route order,
status codes, a safe migration for an existing links.db, atomic increment, failing tests first (order-independent, incl. a migration test), risks vs intent.md; <60 lines.

## Planner's report (verbatim)

PLAN: Task 2, Click counter (planner format: files, API, schema/migration, failing tests, risks)

ASSUMPTIONS
- A "click" is a successful GET /{code} redirect (307). A 404 on /{code} is not a click. GET /stats/{code} never counts.
- Clicks are counted when the redirect is issued. Whether the client follows it is not tracked.
- Pre-existing rows start at 0 clicks.
- Codes contain only base62 characters, so no real code collides with the literal path "stats".
- AGENTS.md says to wait for approval on a schema change. This plan changes the schema (one added column), so approval is needed before implementing.

(1) FILES TO CHANGE
- main.py: schema, migration in init_db(), the redirect handler, and a new stats route.
- test_main.py: new tests (list in section 4).
- Optional: update the AGENTS.md "Where things live" row for main.py. Nothing else changes (no new dependencies, no .githooks change).

(2) API, ROUTES AND STATUS CODES
Route ordering:
- FastAPI matches routes in registration order. `GET /{code}` takes a single path segment (no slashes), so `/stats/abc` has two segments and does not match it. The two routes cannot collide in the normal case.
- The only real collision is a one-segment path like `/stats`. It hits `/{code}` and returns 404 "unknown code". That is acceptable.
- Still, register `@app.get("/stats/{code}")` BEFORE `@app.get("/{code}")`. This is cheap insurance, and a comment should say it must stay above the catch-all.
- Do not use `{code:path}`, because it would swallow `/stats/x`.

GET /stats/{code}:
- 200 returns `{"url": <str>, "clicks": <int>}`.
- 404 with `detail="unknown code"` when the code is not found. This matches the existing wording.
- Implementation is one parameterised `SELECT url, clicks FROM links WHERE code = ?`. It is read-only, so it cannot increment.

GET /{code}:
- Behaviour is unchanged: 307 with a Location header, or 404.
- For clicks, run a single atomic statement: `UPDATE links SET clicks = clicks + 1 WHERE code = ?`. Do it on the same connection, then `conn.commit()`.
- Then `SELECT url FROM links WHERE code = ?`. Do the UPDATE first and use `cur.rowcount == 0` to detect an unknown code. If it is 0, raise 404 without a select.
- The UPDATE changes `clicks`, never `url`, so invariant 2 holds.
- Better: SQLite 3.35+ supports `UPDATE ... SET clicks = clicks + 1 WHERE code = ? RETURNING url`, which gives one statement for count and lookup. Confirm that `sqlite3.sqlite_version >= 3.35` in the venv. If it is not, fall back to UPDATE then SELECT in one connection and one transaction.
- Parameterised `?` placeholders only, and use `with closing(get_db())`.

(3) SCHEMA AND MIGRATION (inside init_db(), no data loss)
- New-database DDL: add `clicks INTEGER NOT NULL DEFAULT 0` to CREATE TABLE IF NOT EXISTS.
- Old-database migration, run after the CREATE in init_db():
  1. `cols = {r["name"] for r in conn.execute("PRAGMA table_info(links)")}`.
  2. If `"clicks" not in cols`, run `ALTER TABLE links ADD COLUMN clicks INTEGER NOT NULL DEFAULT 0`.
  3. Commit.
- ALTER TABLE ADD COLUMN with a constant default is allowed on NOT NULL columns. It backfills existing rows to 0 and drops nothing.
- It is idempotent: the PRAGMA check means a second import or run does nothing. Optionally also catch `sqlite3.OperationalError` for "duplicate column name" to cover two processes racing at startup.
- The PRAGMA is static SQL with no user input, so invariant 3 holds.
- `code` stays `UNIQUE`, so the redirect lookup is still one indexed lookup (invariant 5).
- Make the migration testable: DB_PATH is a module constant used by get_db(). Either (a) let `init_db()` and `get_db()` take an optional path argument (default DB_PATH), or (b) have the test `monkeypatch.setattr(main, "DB_PATH", tmp_path / "old.db")` and call `main.init_db()`. Option (b) needs no signature change, because get_db() reads the module global at call time. Prefer (b), and monkeypatch restores the path after the test.

(4) FAILING TESTS TO WRITE FIRST
Each test creates its own link via POST /shorten and works only with that returned code. No test asserts an absolute code, and none assumes clicks values that another test could change. Order does not matter because each code is unique to its test.
Run `pytest -q` before implementing and confirm each fails for the right reason (404/KeyError on /stats, or a missing column), not for an import error.
- test_stats_new_link_has_zero_clicks: shorten, GET /stats/{code}. Assert 200, json == {"url": "https://example.com/zero", "clicks": 0}.
- test_redirect_increments_clicks: shorten, GET /{code} three times with follow_redirects=False. Assert each is 307, then /stats clicks == 3.
- test_stats_does_not_count_as_click: shorten, call GET /stats/{code} three times. Assert clicks == 0 each time and still 0 at the end. Then GET /{code} once and assert clicks == 1, so the call is shown to be non-incrementing, not just broken.
- test_stats_unknown_code_404: GET /stats/does-not-exist-xyz. Assert 404 and detail == "unknown code".
- test_unknown_redirect_does_not_create_or_count: GET /nope-xyz returns 404, and /stats/nope-xyz is still 404. Checks that nothing was created as a side effect.
- test_stats_reports_correct_url: shorten two different URLs, bump one by redirecting it twice. Assert each /stats shows its own url and clicks (2 and 0). This proves counts are per code.
- test_stats_route_not_shadowed_by_redirect: shorten, then GET /stats/{code} with follow_redirects=False. Assert status is 200, not 307, and the body contains "clicks". Guards against a future reordering.
- test_redirect_still_returns_307_and_location: the existing test_shorten_and_redirect already covers this. It must stay unmodified and green.
- test_concurrent_clicks_are_atomic: shorten once, then run e.g. 20 GETs on that code through ThreadPoolExecutor with a separate TestClient per thread or plain sequential calls. Assert clicks == 20. Each thread opens its own sqlite connection via get_db(), so it exercises the single-UPDATE path. If the TestClient is not thread-safe in this environment, use a single-threaded loop of 20 calls and call the code atomic by construction.
- test_migration_adds_clicks_column_to_old_db(tmp_path, monkeypatch): build an old-schema DB in a temp file:
  - Create a connection to `tmp_path / "old.db"` with `CREATE TABLE links (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, url TEXT NOT NULL)` and insert two rows with codes "a", "b" and urls. Commit and close.
  - `monkeypatch.setattr(main, "DB_PATH", tmp_path / "old.db")`, then `main.init_db()`.
  - Assert PRAGMA table_info(links) now contains "clicks".
  - Assert both rows are still present with the same code and url, and clicks == 0 for both.
  - Call `main.init_db()` again and assert it does not raise (idempotent) and the row count is unchanged.
  - Use a direct connection to the temp db; do not touch the shared links.db.
  - Optionally, with DB_PATH still patched, use TestClient to GET /a (307) and /stats/a (clicks == 1) to prove the migrated DB works end to end.

(5) RISKS AND INVARIANTS (intent.md)
- Invariant 4 (data survives upgrades): the main risk. Mitigated by ALTER ADD COLUMN, never a drop or recreate. Never delete links.db (forbidden in AGENTS.md). Covered by the migration test.
- Invariant 2 (code always redirects to the same URL): the redirect handler now writes. Mitigate by touching only `clicks`. A write failure such as "database is locked" must not break the redirect. Decide: let it 500 (simple, loud) or catch sqlite3.OperationalError and still redirect. Smallest behaviour is to let it propagate. State this assumption and flag it to the reviewer.
- Invariant 5 (one indexed lookup): kept. The UPDATE ... WHERE code = ? uses the UNIQUE index. Using RETURNING keeps it to a single statement. The redirect is now a write, so it takes SQLite's write lock; acceptable for a teaching service.
- Invariant 3 (parameterised SQL): all new statements use `?` or static text (PRAGMA, ALTER). No f-strings.
- Invariant 1 (http/https only): untouched.
- Non-goal tension: "analytics dashboards" are a non-goal, but task 2 is an explicit task and this is only a counter plus one endpoint. Do not add timestamps, referrers, or per-click rows.
- Unauthenticated stats: anyone can read clicks and the original URL for a code. No auth is a stated non-goal, so just note it.
- Link prefetchers and bots will inflate counts; accepted, since the spec says count visits.
- Shared links.db across tests: only per-test unique codes are used. The migration test must use the temp DB with monkeypatch so it cannot corrupt the shared file or leak DB_PATH to other tests.
- The ruff/format gate: 100 columns, double quotes, type hints on every function.

ORDER OF WORK
1. Get approval for the schema change.
2. Write the tests and run pytest -q to confirm they fail for the right reasons.
3. Edit main.py: DDL, migration, stats route above the catch-all, UPDATE in the redirect.
4. Run scripts/check.sh.
5. Review the diff with the reviewer agent.

## Human gate (AGENTS.md: "schema change => ask first")
Decision recorded before step 2: **APPROVED** with two clarifications: (a) if the click increment fails (e.g. database locked) let the error propagate (loud, simple); (b) use `UPDATE ... RETURNING url` only if SQLite >= 3.35 (checked: see writeup), otherwise UPDATE + SELECT in one transaction.
(The approval was given by the session driver (Claude Code acting for the student, who delegated the whole assignment); the student can override it.)
