# Step 0 — User Registration

| | |
|---|---|
| **Owner** | _TBD_ |
| **Status** | ⬜ Not started |
| **Gets input from** | — |
| **Hands output to** | Step 1 |

## Goal
Let a person sign up, give clear consent to have their chats analysed, and say what kind of connections they want.

## Input
Nothing (this is the entry point). The user fills in a sign-up form.

## Output
A **user record**:
```json
{
  "user_id": "u_001",
  "name": "Ada Lovelace",
  "email": "ada@example.com",
  "affiliation": "MIT",
  "consent": {"analyse_chats": true, "show_ideas_to_matches": true, "timestamp": "2026-10-03T14:00:00"},
  "looking_for": ["collaborator", "co-founder", "mentor", "peer"],
  "match_types": ["similar", "complementary"]
}
```

> If you change this output format, update the README of the next step too and log it in `docs/DECISIONS.md` (see `CLAUDE.md`, Rule 4).

## To do
- [ ] Choose sign-up method: simple form (fastest) vs. Google/university login
- [ ] Write the consent text in plain language
- [ ] Decide which preferences to ask for (keep it to 2–3 questions)
- [ ] Create 3–5 fake users for the demo

## Open questions
- Do we need real login for the demo, or is a name + email form enough?
- Is it researchers only (e.g. verified university email), or anyone?

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
