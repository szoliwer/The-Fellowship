# Step 4 — Idea Ranking

| | |
|---|---|
| **Owner** | _TBD_ |
| **Branch** | `main` (whole team works on main) |
| **Status** | 🟨 In progress (review page done; ranking itself is a placeholder: synthetic sample ideas) |
| **Gets input from** | Step 3 |
| **Hands output to** | Step 5 |

## Goal
1. Give each idea a score for how important and current it is to that user, so matching focuses on what they care about **now**.
2. Show the user their ranked ideas and let them decide what is used for matching ("AI can nominate. Only the user can publish."). Nothing reaches Step 5 until the user presses the button on the review page.

## Input
Ideas per user (from Step 3), saved as `data/ranked_ideas/<user_id>.json` (repo root, git-ignored). Either format works, as a plain list or wrapped as `{"ideas": [...]}`:
- **Per-chat packages** (one distilled chat per row): `main_idea` = the title, `insights` = the details, `rank_score`.
- **Spec rows** (Step 3 README): `summary` = the title, `keywords` = the details, `score`.

Until Steps 3–4 write real files, the page uses **`samples/sample_ranked_ideas.json`** (synthetic, placeholder). It has `user_a` (the Step 1 demo history, chats `a_s01`–`a_s05`) and `user_b`.

## Output
Ideas with a **score** (0–1) and the parts that make it up (still to build):
```json
{ "...": "same fields as Step 3", "score": 0.82,
  "score_parts": {"frequency": 0.7, "recency": 0.9, "depth": 0.85} }
```
After the user's review, only what they kept is saved:
- `data/approved_ideas/<user_id>.json`: that user's approved rows, plus a `review` record of their choices (IDs only, never text) so the page remembers them next time.
- `data/ideas.json`: **everyone's approved rows in one file. This is what Step 5 reads**, so Step 5's documented command works unchanged.

The rows keep the input's own format. Left-out ideas, left-out details and removed items are dropped. Only the title and details the user saw are copied, plus bookkeeping fields (IDs, type, scores, dates, `evidence`). `raw_text` and anything else the page didn't show are left behind (list in `METADATA_FIELDS` in `review.py`).
```json
{ "user_id": "user_a", "idea_id": "user_a_c01", "evidence": ["a_s01"], "rank_score": 0.92,
  "main_idea": "Altered membrane-protein trafficking as the cause of the Disease A phenotype",
  "insights": ["…only the details the user kept…"] }
```

> If you change this output format, update the README of the next step too and log it in `docs/DECISIONS.md` (see `CLAUDE.md`, Rule 4).

## The review page ("Your ideas")
One screen, nothing to type. **Designed for the web first**, inside the same desktop layout as Step 6's `desktop-mockup.html` (sidebar with Discover / Matches / You). This page is the **You** tab, so people can come back and change their choices. The list sits in a reading column with the button pinned under it, always in view. Below 760px wide the same page becomes the phone layout from Step 6's phone mockup (title, list, button, tab bar), which is the starting point for the mobile app. See `mockup/review-mockup.html` (open it in any browser; the "Prototype controls" box jumps between example states and switches between "Desktop" and "Phone width") and the screenshots `mockup/1-review.png` … `5-phone.png`.
- Ideas in rank order, **all checked** by default. Only the titles show, each with "4 details ⌄". Click a title to see its details.
- **Uncheck a main idea** → it and all its details are left out.
- **Uncheck a detail** → the main box shows a dash (partly shared) and the line reads "3 of 4 details".
- **Uncheck every detail** → the main idea unchecks too. **Check a detail of an unchecked idea** → the idea comes back with just that detail, so no click is ever refused.
- **Re-check a main idea** → the details picked before come back.
- **Bin icon** on every idea and every detail removes it. **Removing every detail of an idea removes the idea too**; one Undo brings both back. "Removed · Undo" stays in its place until the next change. If every idea is removed, a "Restore removed ideas" button appears (details removed on purpose stay removed).
- **One button**: "Use 4 ideas for matching". With nothing checked it reads "Check at least one idea to continue" and is greyed out, so the reason is visible before anyone clicks. If the user had saved ideas before, it reads "Stop using my ideas for matching" instead, so they can withdraw in one click.

**Streamlit version (`app.py`) vs. the mockup.** Same rules, two differences Streamlit forces: tapping a title ticks its box (details open with the "4 details" button next to it), and a partly-shared idea shows a full tick with "3 of 4 details" beside it, because Streamlit checkboxes have no dash. On a narrow phone screen Streamlit stacks the columns; the demo runs on a laptop, so this was left as is.

## How to run
From the repo root (first time only: `python3 -m venv .venv` then `.venv/bin/pip install -r "4 - Idea Ranking/requirements.txt"`):
```
.venv/bin/streamlit run "4 - Idea Ranking/app.py" --server.address localhost --browser.gatherUsageStats false
```
The demo user is picked in the sidebar (arrow at the top left) until the steps are joined.

Checks: `.venv/bin/python -m unittest discover -s "4 - Idea Ranking"`

## Files
| File | What it is |
|---|---|
| `review.py` | All the rules: reading ranked ideas, include/exclude/remove/undo, saving what's approved |
| `app.py` | The review screen (Streamlit). Only draws; the rules are in `review.py` |
| `test_review.py` | Automatic checks (30) |
| `samples/sample_ranked_ideas.json` | Synthetic ranked ideas for `user_a` and `user_b` (placeholder) |
| `mockup/` | Clickable web-page mockup in Step 6's desktop layout (with a phone-width preview), plus screenshots |

## To do
- [ ] Pick the signals: frequency (how often), recency (how recently), depth (how long/serious the conversations were)
- [ ] Pick simple weights to start (e.g. 0.4 recency, 0.3 frequency, 0.3 depth) and log them
- [ ] Check the top 3 ideas for each sample user make sense by eye
- [ ] Write ranked ideas to `data/ranked_ideas/<user_id>.json` (then the review page uses them instead of the sample)
- [x] Review page: include / exclude / remove ideas and details, save only what's approved for Step 5
- [ ] Run `app.py` once on a laptop with Streamlit installed (it could not be run where it was built)
- [ ] Join into the shared Streamlit app once the team decides where it lives

## Open questions
- Should the user be able to pin or boost their own top ideas?
- Step 6's README asks whether there should be a page where users see their own ideas. This page could be it (the "You" tab). Step 6 owner to confirm.
- Should the Streamlit pages share one colour theme (a `.streamlit/config.toml` at the repo root) so they match the Step 6 look? That touches every step, so it's a team call.

---

## Decisions log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — decision — why.`_

- **2026-10-03 18:46** — Cog (with Claude) — **Web page first, mobile app later.** Same sidebar shell as Step 6's desktop mockup, with this page as the "You" tab; the list in a reading column (about 770px) with the button pinned under it. Below 760px it becomes Step 6's phone layout (tab bar, full-width button). — The first version people use is a website, matching Step 6 keeps the app consistent, and a layout that narrows cleanly keeps the mobile app a small step.
- **2026-10-03 18:46** — Cog (with Claude) — **Removing every detail removes the main idea too**, and one Undo brings back both. (Unchecking every detail still only unchecks it.) — An idea with nothing left under it isn't worth keeping on the list.
- **2026-10-03 18:40** — Cog (with Claude) — Only fields the user saw (title, kept details) plus bookkeeping fields go to Step 5; saving with nothing checked is allowed when ideas were saved before ("Stop using my ideas for matching"). — Nothing unseen should be published, and withdrawing must be as easy as sharing.
- **2026-10-03 18:11** — Cog (with Claude) — Step 4 writes `data/ideas.json` with **only approved** ideas for Step 5; `raw_text` is dropped. Logged as D-006. — Excluded content must never reach matching, and Step 5's documented command then works unchanged.
- **2026-10-03 18:11** — Cog (with Claude) — The page keeps the input's format (per-chat `main_idea`/`insights` or spec `summary`/`keywords`). — Step 5 already reads both, and the team hasn't settled on one yet.
- **2026-10-03 18:11** — Cog (with Claude) — Nothing is saved until the user presses the button; choices are not auto-saved. — Everything starts checked, so auto-saving would share ideas the user never confirmed.
- **2026-10-03 18:11** — Cog (with Claude) — Bin icon on every idea **and** every detail, with an inline "Removed · Undo" in place of what was removed (no confirm pop-up). — One click to remove, one click to recover from a slip.
- **2026-10-03 18:11** — Cog (with Claude) — The main checkbox mirrors its details (checked / dash / unchecked); unchecking the last detail unchecks the idea; checking a detail of an unchecked idea re-includes it with just that detail; re-checking an idea restores earlier picks. — Standard checklist behaviour people already know, and no click is ever refused or loses earlier work.
- **2026-10-03 18:11** — Cog (with Claude) — Design rules for this page: fewest clicks, little clutter, clear within 3 seconds, never let a click fail after the user has committed to it, match the rest of the app. — The user's brief for the review page.

## Progress log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — what was done / what's next.`_

- **2026-10-03 23:30** — Herman (integration, with Claude) — This page now runs inside the shared app (`app.py` at the repo root, page "4. Review ideas"). One change in `app.py`: the "Signed-in user" picker is hidden when the user came in through the shared login (`st.session_state["fellowship_logged_in_user"]`), so nobody can open someone else's ideas; run on its own, the picker works as before. Its input `data/ranked_ideas/<user_id>.json` is now written by a **placeholder ranking** (`pipeline/ranking.py`) from Step 3's output, until this step's real ranking exists (D-013).

- **2026-10-03 18:46** — Cog (with Claude) — Mockup redesigned as a web page in Step 6's desktop layout ("You" tab), with a "Phone width" preview; new rule: removing the last detail removes the idea. 30 automatic checks, 33 browser checks, 40 stand-in checks on `app.py`; the Step 5 end-to-end run still passes. `app.py` needed no change (it follows `review.py`).
- **2026-10-03 18:40** — Cog (with Claude) — Independent code review; fixed the 7 problems it found (see Code fixes log). Now 28 automatic checks, 35 browser checks on the mockup, 37 stand-in checks on `app.py`, and the end-to-end run with Step 5 still passes.
- **2026-10-03 18:11** — Cog (with Claude) — Built the review page: `review.py` (rules), `app.py` (Streamlit screen), 24 automatic checks passing, clickable mockup + 4 screenshots (32 browser checks). Tested end to end: saved approvals for `user_a`/`user_b`, ran Step 5 `--offline` on `data/ideas.json`, and confirmed nothing left out reached the matches file. **Placeholder:** the ideas are the synthetic sample until ranking is built. `app.py` was checked with a stand-in for Streamlit (36 checks) because Streamlit couldn't be installed where it was built; run it once for real. **Next:** ranking signals and weights.
- **2026-10-03** — setup — Step folder and spec created.

## Code fixes log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — **Problem:** … **Cause:** … **Fix:** … (files: …)`_

- **2026-10-03 18:40** — Cog (with Claude) — **Problem:** text the user never saw could reach Step 5 (e.g. `keywords` or `offers` next to `insights`, or details stored as objects). **Cause:** every field except `raw_text` was copied. **Fix:** copy only the shown title, the kept details and plain bookkeeping fields. (files: `review.py`)
- **2026-10-03 18:40** — Cog (with Claude) — **Problem:** after saving, unchecking everything couldn't be saved, so the old ideas stayed in matching. **Cause:** the button was disabled at zero. **Fix:** "Stop using my ideas for matching" appears when something was saved before. (files: `app.py`, `review.py`, mockup)
- **2026-10-03 18:40** — Cog (with Claude) — **Problem:** one damaged approved file blocked everyone's save; two saves at once could clash. **Cause:** the combine step stopped on the first bad file; all saves used the same temporary file name. **Fix:** skip damaged files, unique temporary files, a clear "Couldn't save" message. (files: `review.py`)
- **2026-10-03 18:40** — Cog (with Claude) — **Problem:** rows without `user_id` or `idea_id` lost their owner in Step 5, and their IDs changed if the file was reordered. **Cause:** IDs were built from the row position and the owner wasn't added. **Fix:** IDs come from the title; saved rows always carry the owner and the page's ID. (files: `review.py`)
- **2026-10-03 18:40** — Cog (with Claude) — **Problem:** "Restore removed ideas" also brought back details removed on purpose; Streamlit showed "1 details". **Cause:** restore reset everything; no plural check. **Fix:** restore ideas only; proper plurals. (files: `review.py`, `app.py`, mockup)
- **2026-10-03 18:11** — Cog (with Claude) — **Problem:** in the mockup, the custom checkbox drawing sat on top of the real checkbox, so tests couldn't click it directly. **Cause:** the drawn box was layered above the hidden input. **Fix:** the drawn box ignores clicks, so they go straight to the real checkbox. (files: `mockup/review-mockup.html`)
- **2026-10-03 18:11** — Cog (with Claude) — **Problem:** in the Streamlit page, after removing the very last idea the "Restore removed ideas" button never appeared. **Cause:** the "Removed · Undo" line still counted as a visible idea. **Fix:** the empty message now checks whether any idea is left, not what is drawn. (files: `app.py`)
