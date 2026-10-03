# Progress Board

The single place to see where the project stands. Update it when a step changes status.

**Status key:** ⬜ Not started · 🟨 In progress · 🟦 Placeholder (fake data, so later steps can keep going) · ✅ Done · 🟥 Blocked

| # | Step | Branch | Owner | Status | Next action |
|---|------|--------|-------|--------|-------------|
| 0 | User Registration | `step-0-user-registration` | _TBD_ | ⬜ | Decide sign-up method (simple form vs. login provider) |
| 1 | Data Collection | `step-1-data-collection` | _TBD_ | ⬜ | Get sample exports from ChatGPT and Claude, define common format |
| 2 | Noise Filter | `step-2-noise-filter` | _TBD_ | ⬜ | Define what counts as "noise" |
| 3 | Idea Generation | `step-3-idea-generation` | _TBD_ | ⬜ | Write the prompt that extracts ideas |
| 4 | Idea Ranking | `step-4-idea-ranking` | _TBD_ | ⬜ | Choose ranking signals (frequency, recency, depth) |
| 5 | Match Generation | `step-5-match-generation` | _TBD_ | ⬜ | Choose how to score similarity + complementarity |
| 6 | Matching Interface | `step-6-matching-interface` | _TBD_ | ⬜ | Sketch the match card + warm intro screen |

_This board lives on `main` and is updated when a step's pull request is merged._

## Demo checklist
- [ ] 3–5 synthetic user profiles with sample chats in `samples/`
- [ ] Pipeline runs end to end on sample users (even with placeholders)
- [ ] One match shown in the interface with a warm intro
- [ ] Pitch / demo script

## Timeline
- **2026-10-03** — Switched to one branch per step. `main` only changes via pull request.
- **2026-10-03** — Repo structure, harness (`CLAUDE.md`) and docs set up.
