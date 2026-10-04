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

### D-013 — One app runs Steps 0–6; glue and placeholders live in `pipeline/`
- **Date / who:** 2026-10-03 — Herman (integration)
- **Decision:** `app.py` shows one sidebar page per step (Streamlit navigation), always for the logged-in user. Steps 0–2 and Step 4 use their own screens (Step 4's `app.py` runs as a page as is). New glue in `pipeline/`: page 3 runs Step 3's `run_user`; a **placeholder ranking** copies Step 3's `data/ideas/<user>.json` to Step 4's `data/ranked_ideas/<user>.json` with a simple score (chats, own messages, recency); page 5 runs Step 5's `run` on `data/ideas.json` + `data/users.json` → `data/matches.json`; page 6 is a **placeholder Discover** screen until Step 6's own page exists. Accept/Pass decisions go to `data/match_status.json`, keyed by the pair of users so they survive re-running Step 5. Step 4's demo user picker is hidden when you came through the shared login (a 7-line change in Step 4's `app.py`).
- **Why:** the team asked for one flow to test end to end; keeping glue out of the step folders leaves each owner's code as is. A user picker next to a real login would let anyone open anyone's ideas.
- **Affects:** all steps. Step 4: replace the placeholder ranking when real ranking exists. Step 6: provide `render(user)` to replace the Discover placeholder (match view helpers in `pipeline/matches.py`).

### D-012 — Step 3 → 4 output format
- **Date / who:** 2026-10-03 — Aman (with Claude)
- **Decision:** Step 3 reads Step 2's Markdown files (format: D-010 / `HANDOFF.md`). It writes `data/ideas/<user_id>.json`: an `ideas` list in the existing one-row-per-idea format (one row per sub-theme, with extra fields added), plus a `themes` / `adjacent_ideas` structure for display. Adjacent ideas are speculative and are never in `ideas`.
- **Why:** Steps 4 and 5 keep working unchanged (Step 5's loader already reads the rows). The richer structure lets Step 4 show ideas grouped by theme.
- **Affects:** Steps 3, 4 (and 5, which reads the same rows)

### D-011 — Step 0's user file also speaks Step 5's format (pseudonyms, consent)
- **Date / who:** 2026-10-03 — Herman
- **Decision:** Every record in `data/users.json` also carries the fields Step 5 reads: `name` = the user's **pseudonym**, `consent.analyse_chats` = Step 0's `consent.process_imported_chats`, `match_types` = `["similar", "complementary"]`, `looking_for` = `["collaborator"]`. Real names stay under `private.name`, which Step 5 doesn't read.
- **Why:** Step 5 checked a consent field Step 0 didn't write (users who declined weren't excluded) and used `name` in warm intros (the brief requires pseudonymous intros). Adding the fields on Step 0's side fixes both without changing Step 5.
- **Affects:** Step 0, Step 5 (Oliver + Colin: no code change needed; your README's Step 0 example still shows the old format).

### D-010 — Step 2 → Step 3 handoff: one Markdown file per chat (HANDOFF.md)
- **Date / who:** 2026-10-03 — Herman and Aman (format); Herman (implementation)
- **Decision:** Step 3 reads `2 - Noise Filter/output/<user_id>/<source_id>.md`: a header between `---` lines and `**User:**` / `**Assistant:**` turns, as specified in `2 - Noise Filter/HANDOFF.md` (the source of truth). This replaces `data/eligible/<user_id>.json` from D-008. `output/` is git-ignored; synthetic examples live in `2 - Noise Filter/samples/output/`. HANDOFF.md §7 proposes extra source types, cleaned copies and masking, pending Aman's OK.
- **Why:** agreed between the two step owners; readable by people and LLM prompts alike.
- **Affects:** Step 2, Step 3.

### D-009 — Personal information is removed from research chats, not just whole chats dropped
- **Date / who:** 2026-10-03 — Herman
- **Decision:** Step 2 cleans mixed chats: each personal phrase (own name, school/program, academic record, applications, career plans, relatives and other private people, health, money, private life) is blanked out as `[personal detail removed]`, wholly personal messages (e.g. email drafts) are removed, and the cleaned copy is re-screened until a check finds nothing personal. It reaches Step 3 as a new source (`<id>_clean`, `derived_from_source_id` = original). Mostly-personal chats and chats with hard secrets are still held back whole.
- **Why:** dropping whole chats lost too much research; cleaning + an independent second check is the brief's own "safe excerpt" rule. Blanking phrases (rather than removing whole exchanges) keeps the user's own words, which Step 3 needs to tell their ideas from the AI's; the repeated re-checks guard against missed details. (Updated 21:10: first version removed whole exchanges.)
- **Affects:** Step 2, Step 3 (some inputs are cleaned copies with fewer messages; `source_id`s ending `_clean`).

### D-008 — Privacy screening uses Claude; consent text says so
- **Date / who:** 2026-10-03 — Herman
- **Decision:** Step 2 screens imported chats with local safety rules first, then Claude (`claude-sonnet-5-5`, low effort; switchable to Opus 5.5 or Haiku in one setting) for everything the rules didn't hold back. So imported chats, including ones that end up held back, are sent to Anthropic for screening; the sign-up consent text now says this. Only eligible chats reach Step 3 (file format: see D-010). One Anthropic key for the team in a repo-root `.env` (template: `.env.example`), the same file Step 5 already reads.
- **Why:** rules alone can't tell research about a disease from someone's own health. The consent text previously implied screening happened before anything left the laptop, which would no longer be true. Considered: rules only (no data leaves the laptop, but too many mistakes on real chats).
- **Affects:** Step 0 (consent text), Step 2, Step 3 (input file and format), Step 5 (shared `.env`). Open: the brief says the track prize requires OpenAI models.

### D-007 — Shared app, accounts and where private data is stored
- **Date / who:** 2026-10-03 — Herman
- **Decision:** The shared Streamlit app is `app.py` at the repo root (run: `.venv/bin/streamlit run app.py`); each step keeps its logic and screens in its own folder and `app.py` only shows them. `.streamlit/config.toml` keeps the app on this laptop only and turns off Streamlit's usage statistics. Accounts (email + password, salted scrypt hashes) live in SQLite at `data/fellowship.db`; user records are also written to `data/users.json`. Each user's imports live in `data/sources/<user_id>.json`, with original files and upload history in `data/uploads/<user_id>/`. Step 1 adds `source_type`s `claude_json` and `text_file` and `provenance.upload_id` to the brief's `SourceContextV1`.
- **Why:** users need to come back to their data; SQLite and scrypt are built into Python (no new installs); keeping files per user makes ownership obvious and matches D-004's "steps pass data as files". Considered: a hosted login service (too slow to set up for the hackathon).
- **Affects:** all steps (shared app, data locations); Step 2 reads the new `source_type`s.

### D-006 — Only user-approved ideas reach matching
- **Date / who:** 2026-10-03 — Cog (with Claude)
- **Decision:** Step 4's review page writes `data/ideas.json`, which holds only the ideas and details each user kept (same row format as its input, `raw_text` removed). Step 5 reads that file. Nothing is written until the user presses the button.
- **Why:** "AI can nominate. Only the user can publish." Everything starts checked, so the user's press is the consent. Using the path in Step 5's README means Step 5 needs no change.
- **Affects:** Steps 4 and 5

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
