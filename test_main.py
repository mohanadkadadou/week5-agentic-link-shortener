import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


def test_shorten_and_redirect():
    r = client.post("/shorten", json={"url": "https://example.com"})
    assert r.status_code == 200
    code = r.json()["code"]
    assert code
    r2 = client.get(f"/{code}", follow_redirects=False)
    assert r2.status_code == 307
    assert r2.headers["location"] == "https://example.com"


def test_rejects_bad_url():
    r = client.post("/shorten", json={"url": "ftp://nope"})
    assert r.status_code == 400


def test_unknown_code_404():
    r = client.get("/does-not-exist", follow_redirects=False)
    assert r.status_code == 404


def _shorten(url: str) -> str:
    """Create a link through the API and return its code."""
    r = client.post("/shorten", json={"url": url})
    assert r.status_code == 200
    return r.json()["code"]


def test_stats_new_link_has_zero_clicks() -> None:
    """A fresh link reports zero clicks and its original url."""
    code = _shorten("https://example.com/zero")
    r = client.get(f"/stats/{code}")
    assert r.status_code == 200
    assert r.json() == {"url": "https://example.com/zero", "clicks": 0}


def test_redirect_increments_clicks() -> None:
    """Each successful redirect adds one click."""
    code = _shorten("https://example.com/inc")
    for _ in range(3):
        assert client.get(f"/{code}", follow_redirects=False).status_code == 307
    assert client.get(f"/stats/{code}").json()["clicks"] == 3


def test_stats_does_not_count_as_click() -> None:
    """Reading stats never changes the counter."""
    code = _shorten("https://example.com/nocount")
    for _ in range(3):
        assert client.get(f"/stats/{code}").json()["clicks"] == 0
    client.get(f"/{code}", follow_redirects=False)
    assert client.get(f"/stats/{code}").json()["clicks"] == 1


def test_stats_unknown_code_404() -> None:
    """Stats for an unknown code is a 404 with the standard detail."""
    r = client.get("/stats/does-not-exist-xyz")
    assert r.status_code == 404
    assert r.json()["detail"] == "unknown code"


def test_unknown_redirect_does_not_create_or_count() -> None:
    """A 404 redirect creates nothing as a side effect."""
    assert client.get("/nope-xyz", follow_redirects=False).status_code == 404
    assert client.get("/stats/nope-xyz").status_code == 404


def test_stats_reports_correct_url_per_code() -> None:
    """Counts and urls are tracked per code."""
    a = _shorten("https://example.com/a-per")
    b = _shorten("https://example.com/b-per")
    for _ in range(2):
        client.get(f"/{a}", follow_redirects=False)
    assert client.get(f"/stats/{a}").json() == {"url": "https://example.com/a-per", "clicks": 2}
    assert client.get(f"/stats/{b}").json() == {"url": "https://example.com/b-per", "clicks": 0}


def test_bare_stats_path_is_just_an_unknown_code() -> None:
    """GET /stats (one segment) hits the catch-all and is a plain 404, not a crash or a redirect."""
    r = client.get("/stats", follow_redirects=False)
    assert r.status_code == 404
    assert r.json()["detail"] == "unknown code"


def test_concurrent_clicks_are_atomic() -> None:
    """Parallel redirects all get counted."""
    code = _shorten("https://example.com/concurrent")

    def hit(_: int) -> int:
        return client.get(f"/{code}", follow_redirects=False).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(hit, range(20)))
    assert statuses == [307] * 20
    assert client.get(f"/stats/{code}").json()["clicks"] == 20


def test_migration_adds_clicks_column_to_old_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An old-schema database gains clicks without losing rows, and migrating twice is safe."""
    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE links (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, "
        "url TEXT NOT NULL)"
    )
    conn.execute("INSERT INTO links (code, url) VALUES (?, ?)", ("a", "https://old.example/a"))
    conn.execute("INSERT INTO links (code, url) VALUES (?, ?)", ("b", "https://old.example/b"))
    conn.commit()
    conn.close()

    monkeypatch.setattr(main, "DB_PATH", db)
    main.init_db()
    main.init_db()

    conn = sqlite3.connect(db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(links)")}
    rows = conn.execute("SELECT code, url, clicks FROM links ORDER BY code").fetchall()
    conn.close()
    assert "clicks" in cols
    assert rows == [("a", "https://old.example/a", 0), ("b", "https://old.example/b", 0)]

    assert client.get("/a", follow_redirects=False).status_code == 307
    assert client.get("/stats/a").json() == {"url": "https://old.example/a", "clicks": 1}
