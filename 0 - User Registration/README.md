# Step 0 — User Registration

| | |
|---|---|
| **Owner** | Herman |
| **Status** | ✅ Done for the demo: real accounts with passwords, stored on this laptop |
| **Gets input from** | — |
| **Hands output to** | Step 1 (and Step 5/6 via `data/users.json`) |

## Goal
Let a researcher create an account under a **pseudonym**, give clear consent to have their imported chats processed, and **come back later** by logging in with email + password. In the shared brief this is the first half of "Account + context import".

## Input
The sign-up form (pseudonym, email, password, optional name/affiliation, consent) or the log-in form (email, password). Or "Try a demo account" for the two synthetic researchers.

## Output
A **user record** (never contains password data):
```json
{
  "user_id": "user_3f9a1c2e",
  "pseudonym": "neuro_lab_17",
  "connection_intent": "research collaboration",
  "is_demo_account": false,
  "private": {"name": null, "email": "ada@example.com", "affiliation": null},
  "consent": {"process_imported_chats": true, "timestamp": "2026-10-03T20:00:00Z"}
}
```
- `user_id`: stable ID used by every later step. Demo users are `user_a` (`researcher_014`) and `user_b` (`cellbio_027`); new accounts get `user_` + 8 random hex characters.
- `pseudonym`: the **only** name other users ever see (3–30 lowercase letters, numbers or underscores; can't contain the person's real name). Use `public_view(user)` whenever anything about a user goes to someone else.
- `private.email`: required for real accounts (it's the log-in), never shown to others. `null` for demo accounts.
- `consent`: covers **processing** only. Sharing happens later, idea by idea, in Step 4.

**Where it lives**
- `data/fellowship.db` (repo root, git-ignored): SQLite database with two tables: `users` and `credentials` (password hash, failed attempts, lock time).
- `data/users.json`: all user records, rewritten after every sign-up and at every app start, for steps that read files (D-004). No password data. Each record also carries the fields Step 5 (Match Generation) reads, so Step 5 works unchanged (D-011):
  - `name` = the **pseudonym** (warm intros never show a real name; the real name stays under `private.name`)
  - `consent.analyse_chats` = `consent.process_imported_chats` (anyone who said no is left out of matching)
  - `match_types` = `["similar", "complementary"]`, `looking_for` = `["collaborator"]` (scientist-first MVP defaults)
- `samples/users.json`: the two synthetic demo researchers (committed); loaded into the database automatically.

> If you change this output format, update the README of the next step too and log it in `docs/DECISIONS.md` (see `CLAUDE.md`, Rule 4).

## How passwords are handled
- Stored only as a **salted scrypt hash** (`scrypt$n$r$p$salt$hash`), never the password itself, never logged.
- At least 10 characters; can't be the email or pseudonym.
- 5 wrong passwords in a row lock the account for 15 minutes.
- "Wrong password" and "no such email" give the same message (and take the same time), so nobody can probe which emails have accounts.
- **Demo limits:** refreshing the page logs you out (Streamlit keeps logins in memory). There's no password reset or email verification. Fine on one laptop; going online would need HTTPS and a proper login provider.

## How to run
From the repo root, see the main `README.md` → *Run the app*. Checks:
`.venv/bin/python -m unittest discover -s "0 - User Registration"`

## Files
| File | What it is |
|---|---|
| `registration.py` | Accounts, passwords, log-in, user records, consent text |
| `signup_ui.py` | Log in / create account / demo account screens (used by `app.py` at the repo root) |
| `samples/users.json` | The two synthetic demo researchers from the shared brief |
| `test_registration.py` | Automatic checks (12) |

## To do
- [x] Sign-up with pseudonym + consent
- [x] Accounts with passwords so users can return
- [x] Demo users (`user_a` / `researcher_014`, `user_b` / `cellbio_027`)
- [ ] Stay logged in across page refreshes (needs a cookie add-on; ask the team first)
- [ ] Delete my account and data (for the brief's "withdraw" principle)
- [x] Make `data/users.json` work with Step 5 (pseudonym as `name`, consent passed on, default match types)

## Open questions

---

## Decisions log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — decision — why.`_

- **2026-10-03 22:40** — Herman (with Claude) — `data/users.json` now also carries Step 5's fields: `name` = pseudonym, `consent.analyse_chats` = the processing consent, default `match_types` / `looking_for`; refreshed at every app start. — Step 5 read `consent.analyse_chats` (missing → users who declined weren't excluded) and put `name` in intros (real names would break pseudonymity). Fixed on Step 0's side so Step 5 needs no change; checked with Step 5's own loader.
- **2026-10-03 18:30** — Herman (with Claude) — Consent text now says imported chats are sent to Anthropic's Claude for screening (except ones caught by local safety rules). — Step 2 uses Claude to screen (D-008); the old text implied nothing left the laptop before screening. Accounts created earlier agreed to the old wording.
- **2026-10-03 17:40** — Herman (with Claude) — Real accounts: email + password log-in, salted scrypt hashes, 15-minute lock after 5 wrong tries, stored in SQLite (`data/fellowship.db`). — Users must be able to come back; SQLite and scrypt are built into Python, so no new installs.
- **2026-10-03 17:40** — Herman (with Claude) — Log in with email, not pseudonym. — Pseudonyms are public, so using them as the log-in name would make guessing easier.
- **2026-10-03 17:40** — Herman (with Claude) — Keep writing `data/users.json` after each sign-up. — Later steps read files (D-004); keeps the handoff unchanged.
- **2026-10-03 16:45** — Herman (with Claude) — Run the app on this laptop only (`localhost`) with Streamlit's usage statistics off. — Sign-ups hold private details; nobody else on the venue Wi-Fi should reach them.
- **2026-10-03 16:45** — Herman (with Claude) — Sign-up consent covers processing only; no "show my ideas" checkbox. — The brief says sharing is approved idea by idea in Step 4.
- **2026-10-03 16:45** — Herman (with Claude) — Pseudonyms instead of names; name/affiliation optional and private. — Shared brief: ideas before identity.
- **2026-10-03 16:45** — Herman (with Claude) — Researchers only, one connection intent ("research collaboration"). — Scientist-first MVP per the shared brief.

## Progress log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — what was done / what's next.`_

- **2026-10-03 22:43** — Herman (with Claude) — New `add_showcase_users(people)`: profiles for the hosted demo with a username only (no email, name or password, so nobody can log in as them; not offered as demo accounts). Consent text no longer says "on this laptop" (it also runs hosted). D-018.
- **2026-10-03 21:59** — Herman (with Claude) — Less text: removed the "Username, email and password" line under the landing buttons and the extra line in the sign-up pop-up (the form labels already say what's public).
- **2026-10-03 21:46** — Herman (with Claude) — Look only: the account page shows username and email side by side, with the privacy details; the landing page has a header with Log in / Create account (D-016). No logic changed.
- **2026-10-03 17:40** — Herman (with Claude) — Replaced the no-password sign-up with real accounts (SQLite + hashed passwords + lockout); screens now part of the shared `app.py`. 12 automatic checks pass; in the browser: created an account, wrong password rejected, logged back in and saw the earlier upload. Next: agree the user format with Step 5.
- **2026-10-03 16:45** — Herman (with Claude) — Built registration logic, sign-up screen and the two demo users.
- **2026-10-03** — setup — Step folder and spec created.

## Code fixes log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — **Problem:** … **Cause:** … **Fix:** … (files: …)`_

- _No fixes yet._
