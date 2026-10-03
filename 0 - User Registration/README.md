# Step 0 — User Registration

| | |
|---|---|
| **Owner** | Herman |
| **Branch** | `step-0-user-registration` (work here, not on `main`) |
| **Status** | ✅ Done for the demo (mocked login, clearly labelled) |
| **Gets input from** | — |
| **Hands output to** | Step 1 |

## Goal
Let a researcher join under a **pseudonym**, give clear consent to have their imported chats processed, and get a user ID that every later step uses. In the shared brief this is the first half of "Account + context import" (Step 1 there).

## Input
Nothing (this is the entry point). The user either picks a synthetic demo researcher or fills in the sign-up form.

## Output
A **user record**:
```json
{
  "user_id": "user_a",
  "pseudonym": "researcher_014",
  "connection_intent": "research collaboration",
  "is_demo_account": true,
  "private": {"name": null, "email": null, "affiliation": null},
  "consent": {"process_imported_chats": true, "timestamp": "2026-10-03T20:00:00Z"}
}
```
- `user_id`: stable ID used by every later step. Demo users are `user_a` and `user_b`; new sign-ups get `user_` + 8 random hex characters.
- `pseudonym`: the **only** name other users ever see (3–30 lowercase letters, numbers or underscores; can't contain the person's real name).
- `private`: optional, never shown to other users. Use `public_view(user)` in `registration.py` whenever anything about a user goes to someone else.
- `consent`: covers **processing** only. Sharing happens later, idea by idea, in Step 4 ("AI can nominate. Only the user can publish.").

Where it lives: demo users in `samples/users.json` (committed, synthetic); real sign-ups in `data/users.json` at the repo root (git-ignored).

> If you change this output format, update the README of the next step too and log it in `docs/DECISIONS.md` (see `CLAUDE.md`, Rule 4).

## How to run
From the repo root (first time only: `python3 -m venv .venv` then `.venv/bin/pip install -r "0 - User Registration/requirements.txt"`):
```
.venv/bin/streamlit run "0 - User Registration/app.py" --server.address localhost --browser.gatherUsageStats false
```
Checks: `.venv/bin/python -m unittest discover -s "0 - User Registration"`

## Files
| File | What it is |
|---|---|
| `registration.py` | Creates, validates and loads user records; consent text |
| `app.py` | Sign-up screen (Streamlit) |
| `samples/users.json` | The two synthetic demo researchers from the shared brief |
| `test_registration.py` | Automatic checks |

## To do
- [x] Choose sign-up method: simple form, no real login for the demo
- [x] Write the consent text in plain language
- [x] Decide which preferences to ask for (none: everyone's intent is research collaboration)
- [x] Create the demo users (`user_a` / `researcher_014`, `user_b` / `cellbio_027`)
- [ ] Join into the shared Streamlit app once the team decides where it lives

## Open questions
- Where does the shared Streamlit app (the "shell" from D-004) live? Until then, each step has its own `app.py`.

---

## Decisions log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — decision — why.`_

- **2026-10-03 16:45** — Herman (with Claude) — Run the app on this laptop only (`--server.address localhost`) with Streamlit's usage statistics off. — Sign-ups hold private details; nobody else on the venue Wi-Fi should reach them.
- **2026-10-03 16:45** — Herman (with Claude) — Sign-up consent covers processing only; no "show my ideas" checkbox. — The brief says sharing is approved idea by idea in Step 4, so a blanket yes at sign-up would contradict it.
- **2026-10-03 16:45** — Herman (with Claude) — Pseudonyms instead of names; name/email/affiliation optional and private. — Shared brief: ideas before identity; identity only revealed through a later mutual step.
- **2026-10-03 16:45** — Herman (with Claude) — No real login for the demo; a "Demo: no real login" label on screen. — Fastest; the brief allows mocked auth if clearly labelled.
- **2026-10-03 16:45** — Herman (with Claude) — Researchers only, one connection intent ("research collaboration"); dropped the collaborator/co-founder/mentor and similar/complementary questions. — Scientist-first MVP per the shared brief.

## Progress log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — what was done / what's next.`_

- **2026-10-03 16:45** — Herman (with Claude) — Built registration logic, sign-up screen and the two demo users; 7 automatic checks pass; clicked through demo sign-in, missing-consent error and new account in the browser. Next: join with Step 1 in the shared app.
- **2026-10-03** — setup — Step folder and spec created.

## Code fixes log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — **Problem:** … **Cause:** … **Fix:** … (files: …)`_

- _No fixes yet._
