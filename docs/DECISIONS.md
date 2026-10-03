# Project-wide Decisions

Decisions that affect more than one step, or the project as a whole. Decisions about a single step go in that step's `README.md`.

**Format** (newest at the top):
```
### D-### — Short title
- **Date / who:** YYYY-MM-DD — name
- **Decision:** what we chose
- **Why:** the reason, and what we considered instead
- **Affects:** which steps
```

---

### D-006 — Step 2 → 3 → 4 handoff formats
- **Date / who:** 2026-10-03 — Aman (with Claude)
- **Decision:** Step 3 reads Step 2's output as one Markdown file per eligible chat, one folder per user (`HANDOFF.md`, agreed by Herman and Aman). Step 3 writes `data/ideas/<user_id>.json`: an `ideas` list in the existing one-row-per-idea format (one row per sub-theme, with extra fields added), plus a `themes` / `adjacent_ideas` structure for display. Adjacent ideas are speculative and are never in `ideas`.
- **Why:** Steps 4 and 5 keep working unchanged (Step 5's loader already reads the rows). The richer structure lets Step 4 show ideas grouped by theme.
- **Affects:** Steps 2, 3, 4 (and 5, which reads the same rows)

### D-005 — Everyone works on `main` (replaces D-003)
- **Date / who:** 2026-10-03 — team (recorded by Oliver)
- **Decision:** The whole team commits directly to `main`. The per-step branches are retired and nobody should keep working on them.
- **Why:** Everyone wants to see all committed work immediately, whatever branch it was on. Pull requests and branch-switching were slowing the hackathon down.
- **How we stay safe:** pull before every change, stay in your own step folder, commit small and often. See `docs/HOW_WE_WORK.md`.
- **Affects:** all steps

### D-004 — Stack Choice; `main` changes only via pull request
- **Date / who:** 2026-10-03 — Herman
- **Decision:** Stack for the MVP: Python + Streamlit. Each step is plain Python code in its own folder that reads input files and writes output files; one Streamlit app is the shell that runs the steps and shows the screens. Steps pass data as files (e.g. the Noise Filter → Idea Generation handoff). 
- **Why:** one language for a mostly non-technical team, fast to build at a hackathon, and keeping steps separate from the screens means the UI could be replaced later without touching the pipeline. Demo runs locally on one laptop; the Claude API key lives in a git-ignored .env file.
- **Affects:** all steps

### D-003 — One branch per step; `main` changes only via pull request
- **Date / who:** 2026-10-03 — Oliver
- **Decision:** Seven working branches (`step-0-user-registration` … `step-6-matching-interface`). Each branch only changes its own step folder. Work reaches `main` through a pull request reviewed by a teammate. Shared docs (`README.md`, `CLAUDE.md`, `docs/*`) are edited on `main`.
- **Why:** Keeps `main` demo-able at all times, and keeps four people's work-in-progress from breaking each other. Limiting each branch to its own folder avoids merge conflicts.
- **Affects:** all steps

### D-002 — Privacy baseline
- **Date / who:** 2026-10-03 — team
- **Decision:** Uploads are opt-in. Raw chat text never leaves the pipeline. Other users see only extracted ideas and the warm intro. Contact details are shared only on a mutual accept. No real user data or API keys in GitHub (`data/` and `.env` are git-ignored).
- **Why:** Chat histories are very personal. Trust is the product.
- **Affects:** all steps

### D-001 — Repo structure and working rules
- **Date / who:** 2026-10-03 — team
- **Decision:** One folder per pipeline step (0–6), each with a `README.md` holding its spec and its decisions/progress/fixes logs. `CLAUDE.md` is the shared rulebook for AI assistants. Nothing is committed without a teammate saying yes.
- **Why:** Four people working in parallel at a hackathon need clear ownership and a shared record of what changed.
- **Affects:** all steps

---

## Open questions (to decide as a team)
- **Tech stack:** What do we build the app in? (e.g. a no-code tool, Streamlit/Python, or a simple web app.) Pick whatever the team can demo fastest.
- **Which LLM** do we use for idea extraction and warm intros, and who holds the API key?
- **Common conversation format** shared between Steps 1 → 2 → 3 (draft in `1 - Data Collection/README.md`).
- **Similar vs. complementary:** do we show both kinds of match in one list, or as two separate lists?
