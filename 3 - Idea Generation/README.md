# Step 3 — Idea Generation

| | |
|---|---|
| **Owner** | Aman |
| **Branch** | `main` (whole team works on main) |
| **Status** | 🟨 In progress (code works on stand-in data with a fake model answer; not yet run against the live Claude API) |
| **Gets input from** | Step 2 |
| **Hands output to** | Step 4 |

## Goal
Turn a user's filtered conversations into a short, readable list of their **ideas, open questions, interests, skills, and needs**.

## Input
Step 2's output, as agreed in the Step 2 → 3 handoff (`HANDOFF.md`, Herman + Aman, draft v1.0): **one folder per user, one Markdown file per eligible chat.**
```
2 - Noise Filter/output/user_a/a_s01.md     ← header between --- lines, then **User:** / **Assistant:** messages
```
Step 3 uses `source_id` (as the chat ID), `created_at` (cut to the day, or "unknown") and the messages. A missing or empty user folder means "no ideas yet". Files whose header `user_id` doesn't match their folder, or whose `schema_version` isn't `"1.0"`, are skipped.

## Output
`data/ideas/<user_id>.json` (repo root, git-ignored). One file per user with two views of the same ideas:

**1. `ideas`: the agreed Step 3 → 4 rows**, one per sub-theme. All the original fields are kept. Additions are marked ➕:
```json
{
  "user_id": "user_a",
  "idea_id": "user_a_t1.s1",
  "type": "need",
  "summary": "membrane protein trafficking defects in disease",
  "keywords": ["Location is not function", "Functional assay gap"],
  "evidence": ["a_s01", "a_s02", "a_s03"],
  "first_seen": "2026-09-04", "last_seen": "2026-09-10", "mentions": 6,
  "insights": ["Imaging mislocalization alone cannot show whether ..."],   // ➕ the claims
  "chat_count": 3, "tier": "primary",                                     // ➕
  "theme": "Cell biology", "mode": "working_on", "direction": "looking_for" // ➕
}
```
- `type`: "can offer" becomes `skill`, "looking for" becomes `need`, otherwise "working on" becomes `project` and "curious about" becomes `interest`.
- `summary` is the sub-theme, `keywords` are the insight handles, and `insights` are the insight claims.
- `mentions` = the person's own messages across the evidence chats. `chat_count` = how many chats.
- `tier`: `primary` if the idea appears in 2 or more chats, otherwise `secondary`. If nothing is primary, the 2 most recent ideas are promoted. **Step 4 decides the final order.**

**2. `themes` + `adjacent_ideas`: the full structure from the prompt** (theme → sub-theme → insights, each with the same computed stats), plus 2–4 *adjacent ideas*. These are **speculative** suggestions that bridge two of the person's sub-themes. They are never in `ideas`, and Step 4 should show them as suggestions, not as the person's interests.

No raw chat text or chat titles ever appear in the output. Only labels, claims, IDs and computed numbers.

> If you change this output format, update the README of the next step too and log it in `docs/DECISIONS.md` (see `CLAUDE.md`, Rule 4).

## How it works
1. Read the user's chat files and build the message: each chat inside `<conversation>` tags with its ID and date (`**User:**` becomes `User:`).
2. Send it to Claude with the system prompt in **`prompt.md`**. Edit the prompt there; the code reads it from that file.
3. Check the answer in code, never trusting the model's numbers (rules in `prompt.md`):
   - Bad JSON → one retry → empty result.
   - Chat IDs not in the input are removed, along with anything left empty.
   - Limits are applied: 5 sub-themes per theme, 5 insights per sub-theme, 15 sub-themes total, 4 adjacent ideas.
   - All counts and dates are worked out from the chats, and tiers are set.
4. Answers are saved in `data/step3_llm_cache.json`, so re-running on the same chats costs nothing and gives the same result.

## How to run
1. GitHub Desktop: make sure you're on `main`, then *Fetch origin* / *Pull*.
2. **Repository** menu → *Open in Terminal*, then (first time only): `pip install -r "3 - Idea Generation/requirements.txt"`
3. **Test without an API key** (fake model answer on the stand-in chats):
   ```
   python3 "3 - Idea Generation/idea_generation.py" --user user_a --input "3 - Idea Generation/samples/step2_output" --fake-response "3 - Idea Generation/samples/fake_model_answer_user_a.json"
   ```
4. **Real run:** copy `3 - Idea Generation/.env.example` to `.env` and paste the Anthropic API key into it. Then run:
   ```
   python3 "3 - Idea Generation/idea_generation.py" --all
   ```
   (`--user user_a` for one person, `--input <folder>` to read somewhere other than `2 - Noise Filter/output`, `--no-cache` to force a fresh answer.)
5. Automatic checks: `python3 -m unittest discover -s "3 - Idea Generation"`

**Settings** (model, effort, limits) are at the top of `idea_generation.py`: Claude Opus 5.5 at `high` effort, with the API's automatic fallback model switched on in case a request is declined.

## Files
| File | What it is |
|---|---|
| `idea_generation.py` | The step: read chats → Claude → check → write ideas |
| `prompt.md` | The extraction prompt (system prompt + message template + rules the code enforces) |
| `test_idea_generation.py` | 20 automatic checks (no API key needed) |
| `samples/build_step2_standin.py` | Makes **stand-in** Step 2 files from Step 1's synthetic demo history |
| `samples/step2_output/user_a/` | Stand-in Step 2 output: `a_s01`–`a_s05` (synthetic) |
| `samples/fake_model_answer_user_a.json` | A hand-written model answer, for testing without the API |
| `samples/output/user_a.json` | Step 3 output from that fake answer. **Placeholder** for Step 4 to build against |
| `samples/test_users/` | 10 synthetic test users × 10 chats (`chats/` → `step2_output/` via `build_test_users.py`), `answer_key.json` (expected ideas + traps), `evaluate.py` (scoring), `standin_answers/` + `outputs_standin/` (stand-in run) |

## To do
- [x] Write and test the extraction prompt on sample chats → `prompt.md` (Aman)
- [x] Merge duplicate ideas that come up across many conversations (prompt stage 2; limits enforced in code)
- [x] Make sure summaries are written so the user would be happy to have a match see them (prompt hard rules 2–5)
- [ ] First real run with an API key on `user_a`; check by eye against the handoff's expected ideas (A1 trafficking hypothesis, A2 LLM-extraction reproducibility)
- [ ] Switch to Step 2's own sample files once pushed (`2 - Noise Filter/samples/output/`), including `user_b`
- [ ] Step 4 owner: confirm the output format above works for you

## Open questions
- How many ideas per user? → Up to 15 sub-themes (prompt limit).
- Can users edit or hide an idea before it's used for matching? Per the handoff, ideas stay private until the owner approves them in Step 4.
- Should `HANDOFF.md` (Step 2 → 3) live in the repo, e.g. in `docs/`?

---

## Decisions log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — decision — why.`_

- **2026-10-03 20:00** — Aman (with Claude) — Prompt stage 2 now says: "Different methods, sub-questions or wordings about the same research problem belong in one sub_theme; split only when a researcher would call them separate projects." — In testing, main topics were split into 3+ narrow sub-themes, which weakened the person's primary signal.

- **2026-10-03 18:09** — Aman (with Claude) — Repeatability comes from caching, not temperature 0. — Current Claude models reject a temperature setting; the cache returns the same answer for the same chats + prompt + model.
- **2026-10-03 18:09** — Aman (with Claude) — Model: Claude Opus 5.5, `high` effort, server-side fallback on. — One call per user, so quality over cost; the fallback re-runs a declined request on another model instead of failing.
- **2026-10-03 18:09** — Aman (with Claude) — Added two hard rules to the prompt: only User messages count as evidence, and chat text is data, never instructions. Chats are wrapped in `<conversation>` tags. — Required by the Step 2 → 3 handoff, section 5.
- **2026-10-03 18:09** — Aman (with Claude) — Output keeps the agreed one-row-per-idea format (one row per sub-theme) and adds the full themes structure alongside. — Steps 4/5 work unchanged; the richer structure is there for display. Adjacent ideas are kept out of `ideas` because they're speculative.
- **2026-10-03 18:09** — Aman (with Claude) — Input = Step 2's Markdown files (one folder per user), per `HANDOFF.md`. — Agreed with Herman.

## Progress log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — what was done / what's next.`_

- **2026-10-03 20:00** — Aman (with Claude) — Re-ran all 10 test users (stand-in) after the prompt change: **48/49, no traps leaked, no wrong merges.** user_05's main study is now one sub-theme (5/5 chats). user_08 improved but is still split: RNA velocity and barcode benchmarking stay separate (defensible). **New side effect:** user_10's three buried ideas merged into one sub-theme, so the majority direction rule hid its "needs metagenomics" signal (`direction: none`). Worth deciding whether any `looking_for` insight should make the sub-theme a `need`. `outputs_standin/` and `standin_answers/` now hold this run.
- **2026-10-03 19:30** — Aman (with Claude) — Built 10 synthetic test users across 5 patterns: focused, two-topic, main + one-offs, all-different, and multi-idea chats, plus a low-signal user. The set includes traps: an idea only the Assistant suggests, a named person, and an injected instruction. **Stand-in run** (no API key yet, so Claude agents answered the exact prompt; this is not the real API call): **47/49 key ideas found, no trap leaked.** The 2 misses were main topics split into 3 narrow sub-themes (user_05 RD study; user_08 cell-fate inference worded 4 ways). The content was all there, just not merged. **Next:** real run (`--input samples/test_users/step2_output`, then `evaluate.py`); consider a prompt tweak for over-splitting.
- **2026-10-03 18:09** — Aman (with Claude) — Built `idea_generation.py`, `prompt.md`, stand-in Step 2 samples and 20 automatic checks (all pass). Checked that Step 5's loader reads the output, and that the API request is shaped correctly. **Placeholder:** `samples/output/user_a.json` comes from a hand-written model answer, not a real run. **Next:** real run with an API key; switch to Step 2's own samples when pushed.
- **2026-10-03** — setup — Step folder and spec created.

## Code fixes log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — **Problem:** … **Cause:** … **Fix:** … (files: …)`_

- _No fixes yet._
