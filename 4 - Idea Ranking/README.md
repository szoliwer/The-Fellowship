# Step 4 — Idea Ranking

| | |
|---|---|
| **Owner** | _TBD_ |
| **Branch** | `main` (whole team works on main) |
| **Status** | ⬜ Not started |
| **Gets input from** | Step 3 |
| **Hands output to** | Step 5 |

## Goal
Give each idea a score for how important and current it is to that user, so matching focuses on what they care about **now**.

## Input
Ideas per user (from Step 3).

## Output
Ideas with a **score** (0–1) and the parts that make it up:
```json
{ "...": "same fields as Step 3", "score": 0.82,
  "score_parts": {"frequency": 0.7, "recency": 0.9, "depth": 0.85} }
```

> If you change this output format, update the README of the next step too and log it in `docs/DECISIONS.md` (see `CLAUDE.md`, Rule 4).

## To do
- [ ] Pick the signals: frequency (how often), recency (how recently), depth (how long/serious the conversations were)
- [ ] Pick simple weights to start (e.g. 0.4 recency, 0.3 frequency, 0.3 depth) and log them
- [ ] Check the top 3 ideas for each sample user make sense by eye

## Open questions
- Should the user be able to pin or boost their own top ideas?

---

## Decisions log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — decision — why.`_

- _No decisions yet._

## Progress log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — what was done / what's next.`_

- **2026-10-03** — setup — Step folder and spec created.

## Code fixes log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — **Problem:** … **Cause:** … **Fix:** … (files: …)`_

- _No fixes yet._
