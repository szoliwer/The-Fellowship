# Progress Board

The single place to see where the project stands. Update it when a step changes status.

**Status key:** ⬜ Not started · 🟨 In progress · 🟦 Placeholder (fake data, so later steps can keep going) · ✅ Done · 🟥 Blocked

| # | Step | Owner | Status | Next action |
|---|------|-------|--------|-------------|
| 0 | User Registration | _TBD_ | ⬜ | Decide sign-up method (simple form vs. login provider) |
| 1 | Data Collection | _TBD_ | ⬜ | Get sample exports from ChatGPT and Claude, define common format |
| 2 | Noise Filter | _TBD_ | ⬜ | Define what counts as "noise" |
| 3 | Idea Generation | Aman | 🟨 | Code + prompt done, tested on stand-in data with a fake model answer. Next: real run with an API key; switch to Step 2's samples when pushed |
| 4 | Idea Ranking | _TBD_ | ⬜ | Choose ranking signals (frequency, recency, depth) |
| 5 | Match Generation | _TBD_ | ⬜ | Choose how to score similarity + complementarity |
| 6 | Matching Interface | Oliver | 🟨 | UX mockup done (`6 - Matching Interface/mockup/`). Next: build it in Streamlit (D-004) |

_Everyone works on `main`. Update your own row when your step's status changes._

## Demo checklist
- [ ] 3–5 synthetic user profiles with sample chats in `samples/`
- [ ] Pipeline runs end to end on sample users (even with placeholders)
- [ ] One match shown in the interface with a warm intro
- [ ] Pitch / demo script

## Timeline
- **2026-10-03** — Step 3 first version: extraction code + prompt, tested offline (D-006).
- **2026-10-03** — Switched back to everyone working on `main` (D-005).
- **2026-10-03** — Step 6 clickable UX mockup (v2) added.
- **2026-10-03** — Switched to one branch per step. `main` only changes via pull request.
- **2026-10-03** — Repo structure, harness (`CLAUDE.md`) and docs set up.
