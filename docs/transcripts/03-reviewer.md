# Subagent 3: REVIEWER (read-only) — task 2, "Click counter"

Role definition: `.claude/agents/reviewer.md`. Spawned as `general-purpose` but instructed to be read-only (no edits, no git writes).
Prompt: review the uncommitted diff against the plan, intent.md invariants, AGENTS.md rules, SQL injection, migration safety, status codes, test quality; findings by severity + verdict.

## Reviewer's report (verbatim)

REVIEW of uncommitted diff (main.py, test_main.py). scripts/check.sh: ALL CHECKS PASSED (ruff, format, 12 tests). Venv SQLite is 3.53.1, so RETURNING is valid here. Nothing was edited.

Plan and invariants: the change matches the plan and the recorded approval.
- Invariants 1-5 hold. All SQL is `?`-parameterised or static (PRAGMA/ALTER). `url` is never written. `code` stays UNIQUE.
- The migration is additive: ALTER ADD COLUMN with a constant default, guarded by PRAGMA, so it is idempotent and non-destructive.
- AGENTS.md rules hold: `with closing(get_db())` is used everywhere, `detail` strings are short and lowercase, no new dependencies, ruff passes.
- Status codes are correct: 307 or 404 on redirect, 200 or 404 on stats. The three existing tests are untouched, and the diff only adds tests.
- Connections: no leaks.
- `RETURNING` + `commit()` inside `closing`: correct here. Unknown code: the UPDATE matches nothing, the commit is harmless, and the result is 404.
- HEAD: HEAD requests get 405 on `/{code}`, as before this change, and are not counted. Not a regression.
- Code "stats": a bare `/stats` goes to the redirect handler and returns 404.
- Special characters in `code`: bound as parameters, clean 404.

BLOCKER: none.

SHOULD-FIX
1. main.py:96-99 – `UPDATE ... RETURNING` needs SQLite >= 3.35, but AGENTS.md promises Python 3.10+, where many systems (e.g. Ubuntu 20.04, SQLite 3.31) bundle an older SQLite. There, every redirect would fail with a 500 `OperationalError`. Fix: add a fallback, or document the requirement in AGENTS.md and fail fast at import, e.g. `assert sqlite3.sqlite_version_info >= (3, 35)`.
2. main.py:97-100 – the RETURNING cursor is never exhausted or closed before `commit()`. Fine on 3.12 and this SQLite, but fragile across versions. Fix: `cur = conn.execute(...); row = cur.fetchone(); cur.close()`, then commit.

NIT
3. test_main.py:~96 (`test_stats_route_not_shadowed_by_redirect`) is vacuous. `/stats/x` has two segments and can never match `/{code}`, so the test passes whichever way routes are ordered. The main.py:83 comment overstates the risk. Drop the test or soften the comment; a more useful test would be `/stats` (single segment) returning 404 "unknown code".
4. The concurrency test is not flaky in practice, but it would also pass with a non-atomic UPDATE+SELECT, so it guards correctness without proving atomicity.
5. The migration test is sound (genuinely old schema, migrates twice, data and clicks == 0, end to end on the migrated DB, DB_PATH restored). Gaps: both `init_db()` calls run before any assertion; it doesn't check that a fresh row after migration gets clicks 0.
6. The migration is not race-safe if two processes start at once ("duplicate column name"). Optional: catch `sqlite3.OperationalError` around the ALTER.
7. DDL alignment cosmetic; AGENTS.md "Where things live" row for main.py and docs/TASKS.md are stale.
8. Prefetchers and bots will inflate counts. Accepted in the plan; note in the writeup.

VERDICT: APPROVE (items 1-2 are recommended hardening, not blocking in this environment, where SQLite is 3.53.1)

## Human decision on the findings (made before accepting the diff)
| # | Decision |
|---|---|
| 1 | **Fixed:** fail-fast `RuntimeError` at import if SQLite < 3.35; requirement documented in AGENTS.md "Known gotchas" |
| 2 | **Fixed:** `cur.fetchone(); cur.close()` before `commit()` |
| 3 | **Fixed:** vacuous test replaced by `test_bare_stats_path_is_just_an_unknown_code`; comment softened to "cheap insurance" |
| 4 | Accepted as is (documented limitation of the test) |
| 5 | Accepted (gaps are minor) |
| 6 | Accepted (optional, single-process teaching service) |
| 7 | **Fixed:** AGENTS.md row and docs/TASKS.md updated |
| 8 | Noted in AGENTS.md and writeup |

The gate also caught two over-long comment lines I introduced while applying these fixes (ruff E501): fixed before the commit succeeded.
