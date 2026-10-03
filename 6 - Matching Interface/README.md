# Step 6 — Matching Interface

| | |
|---|---|
| **Owner** | _TBD_ |
| **Branch** | `step-6-matching-interface` (work here, not on `main`) |
| **Status** | 🟨 In progress (UX mockup done) |
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
- [x] Sketch the match card and warm-intro screens → `mockup/matching-mockup.html`
- [ ] Choose the build tool (whatever the team can demo fastest)
- [ ] Write the warm-intro prompt / template
- [ ] Wire up the demo with 3–5 sample users

## Open questions
- ~~What happens after the intro?~~ → In-app chat (see Decisions log).
- Can a user un-match or report someone? (Not in the mockup yet.)
- Do we need a 'profile' page showing a user their own ideas? (Good for trust, and for the demo.)

---

## Decisions log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — decision — why.`_

- **2026-10-03** — Oliver — **Swipe-based flow, mobile first.** Discover (swipe card) → "both said yes" match screen → Matches list → Chat. *Why:* everyone already knows the pattern from dating apps, so there's nothing to learn.
- **2026-10-03** — Oliver — **Match card puts them on the left and you on the right.** Each "bridge" row links their idea to yours: **=** shared interest (blue), **⇄** complementary (amber). Shows both usernames and locations. *Why:* the reason for the match is visible at a glance.
- **2026-10-03** — Oliver — **Accept or pass always moves to the next person.** A match only happens when both accept. Accepting someone who hasn't accepted yet shows a "request sent" note.
- **2026-10-03** — Oliver — **After a match, people talk in an in-app chat** with text, voice notes, and sharing one specific past LLM chat (read-only, chosen by the sender). The warm intro and a suggested first question stay pinned at the top of every chat.

## Progress log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — what was done / what's next.`_

- **2026-10-03** — Oliver + Claude — Clickable UX mockup added: `mockup/matching-mockup.html` (open in any browser), plus screenshots `mockup/1-discover.png` … `4-chat.png`. Uses invented sample users. **Next:** team feedback, then pick the build tool.
- **2026-10-03** — setup — Step folder and spec created.

## Code fixes log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — **Problem:** … **Cause:** … **Fix:** … (files: …)`_

- _No fixes yet._
