# Step 5 — Match Generation

| | |
|---|---|
| **Owner** | _TBD_ |
| **Branch** | `main` (the whole team works on `main`) |
| **Status** | 🟨 In progress (works end to end on sample data; offline mode is a placeholder; not yet run against the live Claude API) |
| **Gets input from** | Step 4 (ranked ideas) + Step 0 (user records) |
| **Hands output to** | Step 6 |

## Goal
Compare every user's ranked ideas and produce a ranked list of suggested matches, each with the reason two people should meet. A pair is suggested when the two are **similar** (same problem or method), **complementary** (one has something specific the other needs), or **both**. Pairs that are different *and* not complementary are never suggested.

## Input
**Ranked ideas from Step 4**: the Step 3 idea fields plus `score`, one idea per row. This is the format in the Step 3 and Step 4 READMEs:
```json
{ "user_id": "u_001", "idea_id": "i_007", "type": "need",
  "summary": "How to use diffusion models to predict protein–ligand binding",
  "keywords": ["diffusion models", "drug discovery"], "score": 0.82, "...": "other Step 3/4 fields are ignored" }
```
Rows can be a plain list or wrapped as `{"ideas": [...]}`. Rows of `type` **skill** count as things a person can *offer*, and rows of `type` **need** as things they *need*. Their keywords count too.

**Also accepted:** per-chat packages (`main_idea`, `insights`, `rank_score`, `raw_text`). `raw_text` is **never read** by this step.

**User records from Step 0** (`--users users.json`). Used fields: `pseudonym` (the username; it's how people are named in every reason and intro. Older files that only have `name` still work, and the `private` block is never read), `match_types` (only suggest kinds of match the person asked for), `looking_for` (shapes the intro), and `consent.analyse_chats` (anyone with `false` is left out entirely).

## Output
A ranked list of **suggested matches**. The fields in the original spec are all kept. Additions are marked ➕:
```json
{
  "match_id": "m_0042",
  "user_a": "u_001", "user_b": "u_007",
  "match_type": "complementary",               // similar | complementary | ➕ both
  "score": 0.88,
  "shared_or_linked_ideas": [["i_007", "i_093"]], // [user_a's idea, user_b's idea]
  "reason": "Ada is exploring diffusion models for binding prediction; Ben has built wet-lab assays to validate exactly those predictions.",
  "status": "suggested",
  "similarity": 0.31, "complementarity": 0.86,  // ➕ the two scores behind `score`
  "shared_topics": ["…"],                        // ➕
  "a_can_offer_b": "…", "b_can_offer_a": "…",    // ➕
  "intro_for_a": "…", "intro_for_b": "…",        // ➕ ready-made warm intro for each side
  "judged_by": "claude | vectors-only",          // ➕
  "debug": { }                                   // ➕ internal; never show to users
}
```
The file also contains `people` (`name`, which holds the username, plus a one-line research summary per user) and `by_user` (each user's `match_id`s, best first).

The `a`/`b` in field names only say which side a field belongs to. The text inside (`reason`, intros, offers) always names people by their username, never "A" or "B".

> If you change this output format, update the README of the next step too and log it in `docs/DECISIONS.md` (see `CLAUDE.md`, Rule 4). **Pending:** Step 6 needs to know about `"both"` and the ➕ fields. See *Open questions*.

## How it works: a 4-stage funnel

**Why not just one method?** Vector math alone (embeddings) is fast and free. But it can't see complementarity, because complementary research is by definition about *different* things. An LLM on every pair can, but that's one call per pair: 100 users means 4,950 calls. So cheap math shortlists and Claude judges only the shortlist (the "retrieve, then rerank" pattern from search engines).

1. **Profile.** List what each person can **offer** and **needs**, phrased the same way (as capabilities) so the two lists can be compared directly. This comes straight from Step 3's `skill`/`need` rows when they exist. Otherwise it's one Claude call per person, or a keyword fallback offline.
2. **Score.** Every phrase becomes an *embedding* (a list of numbers where similar meanings sit close together). Each pair of people gets two scores from 0 to 1.
   * **Similarity** is the average closeness of their 3 closest research topics.
   * **Complementarity** measures how well one person's offers cover the other's needs, counted in both directions. The strongest direction counts 70% and the other 30%, so two-way exchanges score higher.
   * Ideas with a lower Step 4 `score` count up to 25% less.
3. **Judge.** Each person's 5 best partners by similarity plus 5 best by complementarity go to Claude. Claude scores both signals 0–10 on a strict rubric, answers `no_match` for vague or forced links, and writes the reason and intros, naming each person by their username.
4. **Assign.** The final score is 70% Claude and 30% vector math. It takes the stronger signal, plus a bonus when a pair is both. Matches of a type either person didn't ask for are dropped. Each person gets up to 5 matches, and if their top 5 are all one kind, the best match of the other kind is swapped in. A pair kept for either person is shown to both, so both can accept. Pairs from `--previous` are never suggested again.

## How to run
1. GitHub Desktop: check that *Current branch* is `main`, then *Fetch origin* / *Pull origin*.
2. Open a terminal there: **Repository** menu → *Open in Terminal* (Mac) or *Open in Command Prompt* (Windows). Then run:
   ```
   cd "5 - Match Generation"
   pip install -r requirements.txt
   ```
3. **Test without an API key** (runs in seconds):
   ```
   python match_generation.py samples/sample_ideas.json samples/sample_matches.json --users samples/sample_users.json --offline
   ```
4. **Full mode.** Copy `.env.example` to `.env` and paste the Anthropic API key into it. Put real inputs in `data/`, which is git-ignored. Then run:
   ```
   python match_generation.py data/ideas.json data/matches.json --users data/users.json
   ```
   On later runs, add `--previous data/matches_old.json` so nobody is shown the same pair twice. Other options are `--k 3` (matches per person) and `--min-score 0.6` (stricter). Every other knob is in `Settings` at the top of `match_generation.py`.

Claude's answers are cached in `data/llm_cache.json`, so re-running on the same data costs nothing.

**Files:** `match_generation.py` (the engine). In `samples/`: `sample_ideas.json` (Step 4 format), `sample_users.json` (Step 0 format), `sample_ideas_chat_packages.json` (per-chat format) and `sample_matches.json` (offline output). All sample data is synthetic.

## Tuning and limits
* The console prints the spread of both scores. If almost everything sits near 0 or 1, adjust `lo`/`hi` in the `Embedder` class. Too many weak matches → raise `min_match_score`. Obvious partners missing → lower `candidate_floor`.
* **Offline mode is a placeholder.** It matches on shared words, not meaning. On the sample data it finds every intended pair, but it also suggests Dev ↔ Omar: Dev needs audio *recordings*, Omar has neural *recordings*. Full mode adds real embeddings and Claude's judgement, which are built to reject exactly this.
* `lo`/`hi` calibration values for the real embedding model are first guesses. Tune them on real data.
* No cap yet on how often one popular person is suggested. Beyond ~1,000 users, move the vectors into a vector index (e.g. FAISS).

## To do
- [x] Similarity: compare idea text using embeddings and cosine similarity
- [x] Complementarity: match one user's `need` with another's `skill`, then ask an LLM to judge pairs
- [x] Combine into one score, weighted by each idea's rank from Step 4
- [x] Generate the plain-language `reason` (plus a warm intro for each side)
- [x] Don't suggest the same pair twice (`--previous`), and respect `match_types` / `looking_for` preferences
- [x] Name people by their username in reasons and intros (not "A"/"B")
- [ ] Run in full mode with a real API key and the free embedding model; tune `lo`/`hi`
- [ ] Run on real Step 4 output once available

## Open questions
- How many suggestions per user per day/session? (Suggest 3–5.) *Currently up to 5 (`--k`).*
- Do we show why the match is similar vs. complementary in the UI? *The data supports it: `match_type`, `shared_topics`, `a_can_offer_b`/`b_can_offer_a`.*
- **Step 6 owner:** OK with `match_type: "both"` and the ➕ fields? Will you use `intro_for_a`/`intro_for_b`, or write your own intro from `reason`?
- **Step 3/4 owners:** this step reads the repo spec (one idea per row). The per-chat package format also works, but the team should settle on one.
- `consent.show_ideas_to_matches: false`: should those users still be matched, with intros that reveal no ideas?
- **Team:** OK to use the paid Anthropic API and the dependencies in `requirements.txt` (CLAUDE.md Rule 6)?

---

## Decisions log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — decision — why.`_

- **2026-10-03 20:14** — Claude (for Step 5 owner) — Reasons and warm intros name people by their Step 0 username (`pseudonym`), never "A"/"B" and never by real name. The `a`/`b` field names stay as they are. — In the mockup, users couldn't tell who "A" and "B" were. Step 0 makes the username the only name other users see, and keeping the field names means Step 6 needs no change.
- **2026-10-03 16:13** — Claude (for Step 5 owner) — Read the repo's Step 3/4 spec as primary input: `skill` rows = offers, `need` rows = needs, keywords included; `need` rows don't count as research topics. — Matches the agreed handoff, and it skips the per-person Claude profile call whenever Step 3 already lists skills and needs.
- **2026-10-03 16:13** — Claude (for Step 5 owner) — Output keeps every spec field and adds `"both"` plus extras (scores, intros). — Step 6 gets ready-made intros; nothing in the spec was removed.
- **2026-10-03 16:13** — Claude (for Step 5 owner) — A match is suggested only if its type is acceptable to *both* people (`match_types`); users with `consent.analyse_chats: false` are excluded. — Both sides see every match, and consent comes first (D-002).
- **2026-10-03 15:40** — Claude (for Step 5 owner) — Hybrid funnel: embeddings shortlist, Claude judges only the shortlist. — Embeddings can't see complementarity; judging every pair with an LLM grows with the square of the user count.
- **2026-10-03 15:40** — Claude (for Step 5 owner) — Complementarity = needs vs. offers, both phrased as capabilities. — Turns an open-ended judgement into a fast closeness search.
- **2026-10-03 15:40** — Claude (for Step 5 owner) — Ignore `raw_text`. — Privacy (Rule 5) and cost.
- **2026-10-03 15:40** — Claude (for Step 5 owner) — A pair kept for either person is shown to both. — Step 6 needs a mutual accept.
- **2026-10-03 15:40** — Claude (for Step 5 owner) — Models: Claude Haiku 4.5 for profiles, Claude Sonnet 5.5 for judging, free local `all-MiniLM-L6-v2` embeddings. — Cost vs. quality; all swappable in `Settings`.

## Progress log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — what was done / what's next.`_

- **2026-10-03 20:14** — Claude (for Step 5 owner) — Warm intros and reasons now use usernames. Checked: the offline sample run gives the same 5 matches as before; a test with Step 0-style records and a stand-in Claude that deliberately wrote "Researcher A/B" came out with usernames only. Also updated this README's branch notes to `main`. **Next:** one full-mode run with a real API key to see the new intros.
- **2026-10-03 16:13** — Claude (for Step 5 owner) — Aligned with the repo spec: loader reads Step 3/4 rows and Step 0 user records; output adds `shared_or_linked_ideas` and `status`; added `match_types`/`looking_for`/consent handling and `--previous`. New samples in Step 4 and Step 0 formats. Tests pass offline and with a stand-in API. **Next:** one run with a real API key, then tune.
- **2026-10-03 15:40** — Claude (for Step 5 owner) — First version of `match_generation.py` (4-stage engine) with synthetic samples. Offline mode marked as a **placeholder**.
- **2026-10-03** — setup — Step folder and spec created.

## Code fixes log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — **Problem:** … **Cause:** … **Fix:** … (files: …)`_

- **2026-10-03 20:14** — Claude — **Problem:** warm intros and reasons called people "A" and "B", so users couldn't tell who was meant. **Cause:** the judge prompt labelled the two people "RESEARCHER A" / "RESEARCHER B" and its hints said "A needs … B offers", so Claude copied the letters. Also, names were read from `name`, which Step 0 records don't have (they use `pseudonym`), so people fell back to IDs like `user_a`. **Fix:** the prompt now shows usernames only, with a short key saying which username each `a`/`b` field belongs to and an instruction never to write the letters; names come from `pseudonym` (then `name`, then the ID); a safety net replaces any leftover "Researcher A/B" with the username. (files: `match_generation.py`)
- **2026-10-03 16:13** — Claude — **Problem:** on spec-format data the loader read almost nothing. **Cause:** it only knew `main_idea`/`insights`, not `summary`/`keywords`/`type`. **Fix:** accept the spec fields; map `skill`/`need` rows to offers/needs. (files: `match_generation.py`)
- **2026-10-03 16:13** — Claude — **Problem:** offline mode matched Dev ↔ Tomás ("contrastive" ≈ "contracts") and Priya ↔ Maya ("field trials" ≈ "field audio"). **Cause:** word stems cut to 6 letters; generic words counted. **Fix:** 7-letter stems; ignore generic research words such as "field" and "large". (files: `match_generation.py`)
- **2026-10-03 15:40** — Claude — **Problem:** offline mode missed offers phrased "Our …". **Cause:** missing cue word. **Fix:** added "our " to the offer cues. (files: `match_generation.py`)
- **2026-10-03 15:40** — Claude — **Problem:** offline reasons lowercased names; the "similar" intro quoted a need. **Cause:** `str.capitalize()`; used the raw matched phrase. **Fix:** capitalise the first letter only; quote the idea's main topic. (files: `match_generation.py`)
