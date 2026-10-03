# Step 5 — Match Generation

| | |
|---|---|
| **Owner** | _TBD_ |
| **Branch** | `step-5-match-generation` (work here, not on `main`) |
| **Status** | ⬜ Not started |
| **Gets input from** | Step 4 |
| **Hands output to** | Step 6 |

## Goal
Compare every user's ranked ideas and produce a ranked list of suggested matches, each with the reason two people should meet.

## Input
Ranked ideas for all users (from Step 4) and match preferences (from Step 0).

## Output
A ranked list of **suggested matches**:
```json
{
  "match_id": "m_042",
  "user_a": "u_001", "user_b": "u_007",
  "match_type": "complementary",
  "score": 0.88,
  "shared_or_linked_ideas": [["i_007", "i_093"]],
  "reason": "Ada is exploring diffusion models for binding prediction; Ben has built wet-lab assays to validate exactly those predictions.",
  "status": "suggested"
}
```

> If you change this output format, update the README of the next step too and log it in `docs/DECISIONS.md` (see `CLAUDE.md`, Rule 4).

## To do
- [ ] Similarity: compare idea text using embeddings (a numeric 'meaning fingerprint' for each idea) and cosine similarity
- [ ] Complementarity: match one user's `need` with another's `skill`, or ask an LLM to judge pairs
- [ ] Combine into one score, weighted by each idea's rank from Step 4
- [ ] Generate the plain-language `reason` (used for the warm intro in Step 6)
- [ ] Don't suggest the same pair twice, and respect `looking_for` preferences

## Open questions
- How many suggestions per user per day/session? (Suggest 3–5.)
- Do we show why the match is similar vs. complementary in the UI?

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
