"""Link Shortener — starter app for Week 5.

A deliberately tiny FastAPI service you will make *agent-native*. Run it, read it,
then use your coding agent (Antigravity by default) plus the tasks in docs/TASKS.md.

Run:
    pip install -r requirements.txt
    uvicorn main:app --reload
Test:
    pytest
"""

import sqlite3
import string
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

DB_PATH = Path(__file__).parent / "links.db"
ALPHABET = string.ascii_letters + string.digits

# UPDATE ... RETURNING (atomic click + lookup) needs SQLite 3.35+; fail fast, not with 500s.
if sqlite3.sqlite_version_info < (3, 35):
    raise RuntimeError(f"SQLite >= 3.35 required, found {sqlite3.sqlite_version}")

app = FastAPI(title="Link Shortener")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(get_db()) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS links (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                url  TEXT NOT NULL,
                clicks INTEGER NOT NULL DEFAULT 0
            )"""
        )
        # Migration: databases created before click counting lack the column (never drop/recreate).
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(links)")}
        if "clicks" not in cols:
            conn.execute("ALTER TABLE links ADD COLUMN clicks INTEGER NOT NULL DEFAULT 0")
        conn.commit()


init_db()


def encode(n: int) -> str:
    """Base62-encode a row id into a short code."""
    base = len(ALPHABET)
    if n == 0:
        return ALPHABET[0]
    chars = []
    while n > 0:
        n, r = divmod(n, base)
        chars.append(ALPHABET[r])
    return "".join(reversed(chars))


class ShortenRequest(BaseModel):
    url: str


@app.post("/shorten")
def shorten(req: ShortenRequest):
    if not req.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="url must start with http:// or https://")
    with closing(get_db()) as conn:
        cur = conn.execute("INSERT INTO links (url) VALUES (?)", (req.url,))
        row_id = cur.lastrowid
        code = encode(row_id)
        conn.execute("UPDATE links SET code = ? WHERE id = ?", (code, row_id))
        conn.commit()
    return {"code": code, "short_url": f"/{code}"}


# NOTE: keep /stats/{code} registered above the catch-all /{code} (cheap insurance).
@app.get("/stats/{code}")
def stats(code: str):
    with closing(get_db()) as conn:
        row = conn.execute("SELECT url, clicks FROM links WHERE code = ?", (code,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown code")
    return {"url": row["url"], "clicks": row["clicks"]}


@app.get("/{code}")
def redirect(code: str):
    with closing(get_db()) as conn:
        # Atomic increment + lookup in one statement (SQLite >= 3.35 for RETURNING).
        cur = conn.execute(
            "UPDATE links SET clicks = clicks + 1 WHERE code = ? RETURNING url", (code,)
        )
        row = cur.fetchone()
        cur.close()
        conn.commit()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown code")
    return RedirectResponse(url=row["url"], status_code=307)
