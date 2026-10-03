# Step 6 — Matching Interface

| | |
|---|---|
| **Owner** | _TBD_ |
| **Status** | ⬜ Not started |
| **Gets input from** | Step 5 |
| **Hands output to** | — (end of pipeline) |

## Goal
Show users their suggested matches, let them accept or pass, and on a mutual accept show both people a **warm intro** so they can start talking.

## Input
Suggested matches (from Step 5) and user records (from Step 0).

## Output
The screens the user sees, plus updated match status:
- **Match card:** the other person's name/affiliation, 2–3 linked ideas, and the reason, with **Accept** / **Pass** buttons.
- **Warm intro (after both accept):** a short note to both people: who they are, why they matched, and a suggested first question to discuss. Then contact details or a chat link.
- Match `status` updates: `suggested` → `accepted_by_a` / `accepted_by_b` → `connected` (or `passed`).

> If you change this output format, update the README of the next step too and log it in `docs/DECISIONS.md` (see `CLAUDE.md`, Rule 4).

## To do
- [ ] Sketch the match card and warm-intro screens (paper or Figma is fine)
- [ ] Choose the build tool (whatever the team can demo fastest)
- [ ] Write the warm-intro prompt / template
- [ ] Wire up the demo with 3–5 sample users

## Open questions
- What happens after the intro: email both people, in-app chat, or just show contact details?
- Do we need a 'profile' page showing a user their own ideas? (Good for trust, and for the demo.)

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
