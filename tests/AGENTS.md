# tests/AGENTS.md: rules for test files only

Loaded when you work on files under `tests/` (the nearest `AGENTS.md` to the file being edited applies).
Repository-wide rules are in the root `AGENTS.md`.

- **Test the public API.** Call endpoints through the FastAPI `TestClient`. Do not call `get_db()`, `encode()` or other
  helpers directly, except in a dedicated migration test that patches `main.DB_PATH` with `tmp_path`.
- **Cover success and failure.** Every new behaviour needs at least one happy-path test and one failure or edge case
  (unknown code -> 404, invalid input -> 4xx).
- **Independent tests.** All tests share one `links.db`. Create your own link inside each test, use only the code returned
  by `POST /shorten`, and never assert an absolute code like `"b"` or rely on execution order.
- **Assert behaviour, not implementation.** Check status codes, response bodies and redirects, not SQL, column names or
  private functions.
- **Failing first.** Run the new test and confirm it fails for the right reason before implementing the feature.
- Give each test a descriptive name and a one-line docstring; keep type hints (`-> None`).
- Never delete or weaken an existing test to make the suite pass.
