# Tasks

Small, independent improvements to the link shortener. You only need to complete
**one** for this assignment (via your subagents), but pick whichever you like.

1. **Custom alias** — allow `POST /shorten` to accept an optional `alias`; use it as the
   code if it's free, else return 409.
2. **Click counter** — track how many times each code has been visited; expose
   `GET /stats/{code}` returning `{ "url": ..., "clicks": N }`.
3. **Expiry** — accept an optional `expires_in_days`; return 410 for expired links.
