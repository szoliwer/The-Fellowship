# Step 6 — Matching Interface

| | |
|---|---|
| **Owner** | _TBD_ |
| **Branch** | `main` (whole team works on main) |
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
- [x] Choose the build tool → Python + Streamlit (team decision D-004)
- [ ] Rebuild the four mockup screens in Streamlit, reading Step 5's `sample_matches.json`
- [ ] Write the warm-intro prompt / template
- [ ] Wire up the demo with 3–5 sample users

## AI nudge rules (draft, for the build)
| Nudge | When it fires | What it says / offers |
|---|---|---|
| **Gone quiet** | Both people have sent at least one message, then nothing for **3 days**. At most once a week per chat. | Names both people, recalls the last open thread or question, and asks one easy follow-up. |
| **Take it further** | About **10+ messages over 2+ days**, or someone mentions meeting, calling or emailing. At most once per chat (can be re-offered after 2 weeks). | Three buttons: **Share email**, **Meet in person** (same city) / **Plan a video call** (different cities), **Connect on LinkedIn**. |
| **Mutual reveal** | Both people pick the same option. | Posts both email addresses or profile links in the chat. If only one person opts in, the other sees nothing about it. |

The nudge text should be written by the LLM from the conversation and the match reason (from Step 5), using first names only.

## Open questions
- Should people be able to turn nudges off per chat?
- ~~What happens after the intro?~~ → In-app chat (see Decisions log).
- Can a user un-match or report someone? (Not in the mockup yet.)
- Do we need a 'profile' page showing a user their own ideas? (Good for trust, and for the demo.)

---

## Decisions log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — decision — why.`_

- **2026-10-03** — Oliver — **Sounds on pass and connect.** Passing plays a short, flat, slightly clashing "bonk-bonk" that drops in pitch. Connecting plays a bright rising chime (C–E–G–C). Both last under half a second, are generated in code (no audio files) and can be muted with the speaker button on Discover. *Why:* a small sting makes people think twice before passing, and a happy chime rewards connecting.
- **2026-10-03** — Oliver — **Privacy: first names and usernames only.** No last names anywhere in the app (cards, matches list, chat). Avatars show a single initial. *Why:* the app is privacy-first; people can share more themselves once they're talking.
- **2026-10-03** — Oliver — **Two clearly different colours for the two sides of the match card.** Pink for them (left), green for you (right), running from top to bottom. The type labels (shared interest / complementary) sit on the middle line between them. *Why:* makes the "them vs. you" comparison obvious at a glance.
- **2026-10-03** — Oliver — **The AI's opening message is the same for both people.** It's addressed to both by first name, explains why each of them is here and how their work connects, and ends with one open-ended question that either person can answer. This replaces the tappable conversation starters. *Why:* both people start from the same context, and an open question invites a real answer, not a canned one.
- **2026-10-03** — Oliver — **The AI can nudge inside a chat.** (1) "Gone quiet": after a few days without messages it reminds both people where they left off. (2) "Take it further": when a conversation is going well it offers to swap emails, meet in person (or set up a video call if they live in different areas), or connect on LinkedIn. Contact details are only revealed when **both** people opt in. *Why:* turns matches into real collaborations without giving up privacy.
- **2026-10-03** — Oliver — **The app speaks in a third colour (blue) in chat**, so its messages never look like they came from either person.
- **2026-10-03** — Oliver — **Swipe-based flow, mobile first.** Discover (swipe card) → "both said yes" match screen → Matches list → Chat. *Why:* everyone already knows the pattern from dating apps, so there's nothing to learn.
- **2026-10-03** — Oliver — **Match card puts them on the left and you on the right.** Each "bridge" row links their idea to yours: **=** shared interest (blue), **⇄** complementary (amber). Shows both usernames and locations. *Why:* the reason for the match is visible at a glance.
- **2026-10-03** — Oliver — **Accept or pass always moves to the next person.** A match only happens when both accept. Accepting someone who hasn't accepted yet shows a "request sent" note.
- **2026-10-03** — Oliver — **After a match, people talk in an in-app chat** with text, voice notes, and sharing one specific past LLM chat (read-only, chosen by the sender). The warm intro and a suggested first question stay pinned at the top of every chat.

## Progress log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — what was done / what's next.`_

- **2026-10-03** — Oliver + Claude — Mockup v4: pass/connect sounds with a mute button; "Hear pass / Hear connect" buttons in the side panel for demos. **For the Streamlit build:** browsers only play sound after a tap or click, and Streamlit needs a small HTML/JS component for this. The sound code in `mockup/matching-mockup.html` (search for `const Sound`) can be reused as is.
- **2026-10-03** — Oliver + Claude — Mockup v3: one shared AI welcome message addressed to both people, ending in an open question (replaces the conversation starters). AI nudges added ("gone quiet" and "take it further", with mutual opt-in for swapping emails or LinkedIn). New screenshots: `mockup/5-nudge-quiet.png`, `mockup/6-nudge-connect.png`.
- **2026-10-03** — Oliver + Claude — Step 6 now works on `main` with the rest of the team (D-005). **Next:** build the screens in Streamlit (D-004).
- **2026-10-03** — Oliver + Claude — Mockup v2: first names only, pink/green split card, blue app note with 3 conversation starters in chat. Screenshots refreshed.
- **2026-10-03** — Oliver + Claude — Clickable UX mockup added: `mockup/matching-mockup.html` (open in any browser), plus screenshots `mockup/1-discover.png` … `4-chat.png`. Uses invented sample users.
- **2026-10-03** — setup — Step folder and spec created.

## Code fixes log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — **Problem:** … **Cause:** … **Fix:** … (files: …)`_

- _No fixes yet._
