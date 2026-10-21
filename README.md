# Starter — Link Shortener

A tiny FastAPI + SQLite service you'll make *agent-native*. You don't build the app —
you add `AGENTS.md`, a hook, a reusable workflow, and use subagents on one task.

## Setup
```bash
pip install -r requirements.txt
pytest                      # 3 tests should pass
uvicorn main:app --reload   # http://localhost:8000  (docs at /docs)
```

## Try it
```bash
curl -X POST localhost:8000/shorten -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}'
# -> {"code":"b","short_url":"/b"}  then GET localhost:8000/<code> redirects
```

## Files
- `main.py` — the app (`POST /shorten`, `GET /{code}`)
- `test_main.py` — pytest suite
- `docs/TASKS.md` — pick one task for the subagent exercise
