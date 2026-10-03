# Step 3 — Idea Generation

| | |
|---|---|
| **Owner** | _TBD_ |
| **Branch** | `main` (whole team works on main) |
| **Status** | ⬜ Not started |
| **Gets input from** | Step 2 |
| **Hands output to** | Step 4 |

## Goal
Turn a user's filtered conversations into a short, readable list of their **ideas, open questions, interests, skills, and needs**.

## Input
Filtered conversations for one user (from Step 2).

## Output
A list of **ideas** per user:
```json
{
  "user_id": "u_001",
  "idea_id": "i_007",
  "type": "open_question",
  "summary": "How to use diffusion models to predict protein–ligand binding",
  "keywords": ["diffusion models", "protein folding", "drug discovery"],
  "evidence": ["c_123", "c_140"],
  "first_seen": "2026-08-01", "last_seen": "2026-09-14", "mentions": 6
}
```
Idea types: `interest`, `open_question`, `project`, `skill` (what they can offer), `need` (what they're looking for). Skills and needs are what make complementary matches possible.

> If you change this output format, update the README of the next step too and log it in `docs/DECISIONS.md` (see `CLAUDE.md`, Rule 4).

## To do
- [ ] Write and test the extraction prompt on sample chats
- [ ] Merge duplicate ideas that come up across many conversations
- [ ] Make sure summaries are written so the user would be happy to have a match see them

## Open questions
- How many ideas per user? (Suggest 5–15.)
- Can users edit or hide an idea before it's used for matching?

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
