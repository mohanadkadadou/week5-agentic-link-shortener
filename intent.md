# intent.md: why this exists

## Purpose
Give users a short, stable code for a long URL, and redirect them to it fast. It is a teaching service
used to practise agent-native engineering: the code is small on purpose so an agent can hold all of it in context.

## Users and success
- A caller `POST`s a URL and gets a code; anyone visiting `/<code>` is redirected to the original URL.
- Success = round trip works, bad input gets a clear 4xx, an unknown code gets 404, and nothing crashes on odd input.

## Invariants (must stay true after every change)
1. Only `http://` and `https://` URLs are accepted (blocks `javascript:`, `file:`, `ftp:` redirects).
2. A code, once issued, always redirects to the same URL until it is deliberately removed or expired.
3. All SQL is parameterised; no user input is ever concatenated into a query.
4. Existing `links.db` data survives upgrades (migrate, never drop).
5. The redirect path stays one indexed lookup (`code` is `UNIQUE`).

## Non-goals
Accounts/auth, a UI, analytics dashboards, multi-host deployment, rate limiting. Do not add them without an explicit task.

## Decision rules for agents
- When the spec is ambiguous, choose the smallest behaviour that satisfies it and write the assumption in the PR/writeup.
- Prefer a clear 4xx over a silent fix-up of bad input.
- If a change would violate an invariant, stop and ask instead of working around it.
