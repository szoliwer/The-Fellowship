# Step 2 — Noise Filter

| | |
|---|---|
| **Owner** | _TBD_ |
| **Branch** | `step-2-noise-filter` (work here, not on `main`) |
| **Status** | ⬜ Not started |
| **Gets input from** | Step 1 |
| **Hands output to** | Step 3 |

## Goal
Keep only the conversations that say something about what a person is thinking about, and strip out personal or sensitive details.

## Input
Conversations in the common format (from Step 1).

## Output
The same format, but **fewer conversations**, each tagged with why it was kept, with personal details masked:
```json
{ "...": "same fields as Step 1", "kept_reason": "research question", "pii_removed": true }
```

> If you change this output format, update the README of the next step too and log it in `docs/DECISIONS.md` (see `CLAUDE.md`, Rule 4).

## To do
- [ ] Write down what counts as noise (e.g. one-off tasks, coding typos, emails, recipes, travel)
- [ ] Choose the method: simple rules, an LLM yes/no check, or both
- [ ] Mask names, emails, phone numbers, addresses
- [ ] Test on the sample chats and check by eye that nothing important is dropped

## Open questions
- Should a user be able to review and remove conversations before they're analysed?
- Which topics are always excluded (health, relationships, finances)?

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
