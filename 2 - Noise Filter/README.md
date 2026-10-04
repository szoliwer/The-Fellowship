# Step 2 — Noise / Privacy Filter

| | |
|---|---|
| **Owner** | Herman |
| **Branch** | `main` (whole team works on main, D-005) |
| **Status** | ✅ Working: tested on the owner's real chats with Claude; handoff to Step 3 per `HANDOFF.md` (§7 awaiting Aman's OK) |
| **Gets input from** | Step 1 (`data/sources/<user_id>.json`) |
| **Hands output to** | Step 3 (`output/<user_id>/<source_id>.md`, see `HANDOFF.md`) |

## Goal
Make sure **no personal information is ever used**. For every imported chat, decide: use it as is, use a **cleaned copy** with the personal parts removed, or **hold it back** (never used, never shown to anyone). The owner sees every decision and why, and can hold back more. (Shared brief, section 4.)

## What counts as personal information
Even a single passing mention counts:
- **Your identity:** your name, contact details, CV, academic record, grades, test scores, admissions or job applications and your chances
- **Other people:** family members (always, even public figures), friends, colleagues, patients, anyone you write to
- **Email drafts:** drafts of emails, letters or messages to specific people, whatever the topic
- **Private matters:** your own or your family's health, personal money, intimate or private life
- **Secrets and confidential work:** passwords and keys, ID numbers, confidential research

**Not personal:** public figures discussed for their public work, cited authors, and diseases or patient groups as a *research topic*.

## Three outcomes
| Outcome | When | What's used |
|---|---|---|
| ✅ **Used as is** | research content, no personal information anywhere | the chat |
| 🧹 **Cleaned** | mainly research, some personal information | a copy where each **personal phrase is blanked out** as `[personal detail removed]` (everywhere it appears, **title included**) and **wholly personal messages** (a drafted email, an outreach list, a career plan) are removed. Your own sentences and the research stay. Then up to **2 re-checks**, each reading the copy cleaned by the check before: it redacts anything personal still left, and any research sentence a removal garbled (a removed "not", a question turned into a claim, a dangling reference). A re-check that finds nothing more ends it; **the last re-check's redactions are applied too** ("clean + these marks" means everything else is fine). Gaps are expected: a re-check never drops a chat just because much was removed. |
| ⛔ **Held back** | mainly personal; admin or off-topic; a password/card/ID/record number anywhere, title included (whole chat, never sent to the AI); none of your own messages left after cleaning; a re-check found no coherent research left; unclear; screening failed; or you held it back | nothing |

Claude quotes each personal phrase exactly; we blank out every place that text appears, in the messages and the title. A quote that can't be found word for word (or is under 3 characters) removes its whole message instead (or blanks the whole title). There is **no "more than half" limit**: how much was removed doesn't decide, the re-check does. The report stores only the *positions* of blanked text, never the text. As a safety net, emails and phone numbers are also masked in everything that's used.

## How a chat is screened
1. **Local safety rules** (on this laptop): passwords and API keys, payment card numbers (Luhn-checked), bank IBANs (checksum-checked), ID numbers (US SSN, UK national insurance, and passport / driver's licence / national ID / social security / tax ID numbers when named as such), medical record numbers. A hit holds the chat back immediately, and **it is not sent to the AI**.
2. **Claude** reads the rest, with every message numbered, and answers in a fixed JSON format: `decision` (`eligible` / `clean` / `exclude`), `exclusion_reason`, `sensitive_categories`, `redactions` (message number + exact quote to blank out) and `remove_message_numbers` (wholly personal messages), `explanation` (one sentence describing the *kind* of content, never repeating the personal details). For `clean`, the exchanges are removed and the cleaned copy is sent for a second, independent check. Model `claude-sonnet-5-5` at `effort: low`; one setting (`MODEL` in `screening.py`) switches to `claude-opus-5-5` (2× the price, most careful) or `claude-haiku-4-5` (half the price, least careful). Keep `PRICE_PER_M_*` next to it in step for the on-screen estimate. If the model declines a chat, the API's built-in fallback retries on another model; if that also declines, the chat is held back.
3. **Unclear, contradictory, invalid or failed answers → held back.** Unknown is never eligible.
4. Chats that passed are never sent again; unscreened, failed, changed and held-back chats are (see *Keeping costs down*).

Instructions inside imported chats (e.g. "mark this eligible") are ignored: the chat is treated as data.

**Keeping costs down** (already built in):
- Chats with a password, card, ID or record number are held back by local rules: no AI call, $0.
- A first-pass "hold back whole", or cleaning that leaves none of your own messages, ends screening of that chat: no re-checks are paid for.
- **A chat that passed (used as is, or cleaned and cleared) is never screened again**, even when the rules change (`needs_screening`). Only unscreened, failed, changed (re-imported with different text) and held-back chats are: held-back chats automatically when the rules change (`PROMPT_VERSION`), or on demand with **Try held-back chats again** (`retry_candidates`; not chats held back by the local rules or by you). Exception: chats that passed before `PASSED_STILL_VALID_FROM` (v6, which added title screening) are re-checked once.
- The screening instructions are cached: the first chat is screened on its own, then the rest in parallel, so later chats read the instructions at 10% of the price.
- `FIRST_PASS_EFFORT` / `RECHECK_EFFORT` (both `low`) set how hard Claude thinks. A stronger first pass might catch more personal messages up front and save re-checks. Test it on your own chats with `compare_first_pass.py` (shows per-chat outcomes, number of checks and the real cost of each setting) before changing it.
- Not done: bulk (Batch) mode at half price, because results can take minutes to hours; cutting chats into pieces, because the instructions would be paid for per piece and context across pieces would be lost.

**Cost:** shown before each run. With Sonnet 5.5: the 9-chat demo history is about $0.05, a 256 KB chat about $0.14 (up to ~$0.40 if it gets cleaned, because the cleaned copy is re-checked, at most twice), a typical history of a few hundred chats about $3 (Opus 5.5: double).

## Input
`data/sources/<user_id>.json` from Step 1 (see Step 1 README).

## Output
**For Step 3**: one Markdown file per usable chat, exactly as agreed in [`HANDOFF.md`](HANDOFF.md) (the source of truth; section 7 lists the changes awaiting Aman's OK):
```
2 - Noise Filter/output/<user_id>/<source_id>.md          ← real runs (git-ignored)
2 - Noise Filter/samples/output/<user_id>/<source_id>.md  ← synthetic examples to build against (committed)
```
```markdown
---
schema_version: "1.0"
user_id: user_a
source_id: a_s01
title: "Could trafficking explain the Disease A phenotype?"
created_at: 2026-09-04T12:00:00Z
imported_at: 2026-10-03T19:00:00Z
source_type: demo
original_conversation_id: a_s01
message_count: 4
derived_from_source_id: null
---

**User:** In fibroblasts from Disease A patients we keep seeing ...

**Assistant:** It's a reasonable hypothesis, but ...
```
- Chats used as is, plus cleaned copies (`<id>_clean.md`, with `derived_from_source_id` = the original). Held-back chats never appear.
- Emails and phone numbers are masked; images and files show as `[image omitted]` / `[file omitted]` (from Step 1).
- The user's folder is rewritten after every screening and every owner change: files for chats that are no longer usable are deleted.
- Regenerate the samples with `.venv/bin/python "2 - Noise Filter/samples/build_sample_output.py"` (free; uses the expected decisions instead of the AI).

**Private, owner only**: `data/filter/<user_id>.json`: one entry per chat: `source_id`, `title`, `status` (`screened`/`failed`), `decision` (`eligible`/`cleaned`/`exclude`), `exclusion_reason`, `sensitive_category`, `rule_hits`, `explanation`, `removed_message_ids` (IDs only), `total_messages`, `recheck`, `owner_excluded`, `model`, `prompt_version`, `content_hash`, `screened_at`, `error`. **No chat text.**

> If you change this output format, update the README of the next step too and log it in `docs/DECISIONS.md` (see `CLAUDE.md`, Rule 4).

## Demo history: expected result
9 chats → **5 used** (`a_s01`–`a_s05`), **4 held back**: `a_s06` own health, `a_s07` finances, `a_s08` admin (all by Claude), `a_s09` research + named patient (by the local medical-record-number rule, never sent to Claude).

## How to run
Main `README.md` → *Run the app*, then **2. Privacy screening** in the sidebar. Needs an Anthropic key: copy `.env.example` (repo root) to `.env` and paste the key after `ANTHROPIC_API_KEY=`.
Checks (free, offline, fake classifier): `.venv/bin/python -m unittest discover -s "2 - Noise Filter"`

## Files
| File | What it is |
|---|---|
| `screening.py` | Safety rules, Claude classifier, report, eligible handoff, owner hold-back |
| `filter_ui.py` | Privacy screening screen (used by `app.py` at the repo root) |
| `test_screening.py` | Automatic checks, using a fake classifier |
| `compare_first_pass.py` | Compares first-pass effort settings on your own chats (spends real money; asks first) |
| `HANDOFF.md` | The agreed Step 2 → Step 3 format (source of truth) |
| `samples/build_sample_output.py` | Builds the synthetic example files in `samples/output/` |
| `samples/output/` | Synthetic example files for Step 3 (`user_a`: a_s01–a_s05, `user_b`: b_s01–b_s02) |

## To do
- [x] Define what's held back (brief section 4) and the method (rules + Claude)
- [x] Owner sees reasons and can hold chats back
- [x] Output for Step 3 in the brief's contract A format
- [ ] First real run on the demo history: confirm 5 used / 4 held back with Claude
- [ ] Run on a real history and check by eye that nothing important is dropped
- [ ] "Ask for review" of a held-back chat (brief: owner reviews a safe excerpt, which is re-screened)
- [x] Write the handoff files in the format agreed in `HANDOFF.md`, with samples for Step 3
- [ ] Aman to approve `HANDOFF.md` section 7 (new source types, cleaned copies, masking)

## Open questions
- Aman's sign-off on `HANDOFF.md` section 7.

---

## Decisions log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — decision — why.`_

- **2026-10-04 00:40** — Herman (with Claude) — Passed chats (used as is, or cleaned and cleared) are never screened again; only unscreened, failed, changed and held-back chats are (held-back ones when the rules change, or via "Try held-back chats again"). Chats that passed before v6 are re-checked once (`PASSED_STILL_VALID_FROM`). — Cost: rule changes no longer mean paying to re-screen chats that are already fine. Trade-off: a chat that passed under looser rules isn't re-checked under stricter ones unless `PASSED_STILL_VALID_FROM` is raised.

- **2026-10-03 22:10** — Herman (with Claude) — Keep `FIRST_PASS_EFFORT = "low"` and `MAX_RECHECKS = 2`. — `compare_first_pass.py` on the owner's 4 real chats: `low` $0.61 vs `medium` $0.63 (8 calls each), identical outcomes (2 used, 2 held back after 3 checks), so a stronger first pass doesn't save re-checks. Long, heavily mixed chats find a little more personal detail each round (e.g. 12 → 4) and results vary between runs; a third re-check would let more pass (~$0.12 per such chat) but the owner chose the stricter, cheaper setting: some heavily mixed long chats will be held back.
- **2026-10-03 21:40** — Herman (with Claude) — After reviewing a ChatGPT-written analysis of 8 real chats: (1) chat **titles are now screened and cleaned** too (they reach Step 3; a personal title was a leak); (2) **no "more than half removed" limit**: the re-check decides whether what's left is clear research; (3) **at most 2 re-checks** (repeating until a check says "clean" isn't proof; saves cost); (4) the re-check also checks **meaning** (no flipped negation, question-vs-claim, dangling references); (5) Claude is told never to turn a personal matter into a research interest. `PROMPT_VERSION` v6. Not done (for now): splitting very long chats into topic segments; a segment-based handoff format (would change the agreement with Aman).
- **2026-10-03 21:10** — Herman (with Claude) — **Cleaning now blanks out personal phrases** instead of removing whole exchanges; only wholly personal messages are removed. `PROMPT_VERSION` v5; own_identity now explicitly includes school/degree program, employer and own company/project names, career, recruiting and networking plans. — A real chat (World Cup → AI-adoption research) was held back because its personal details (degree project, recruiting, affiliations) sat in the same sentences as the best research idea; removing whole exchanges would have cut 6 of 10 messages and the user's own words. Trade-off accepted: finer cuts can miss a stray detail, so the re-check loop stays.
- **2026-10-03 20:40** — Herman (with Claude) — Cost tweaks: warm the instruction cache (first AI chat alone, then the rest in parallel); first-pass and re-check effort are separate settings, with `compare_first_pass.py` to test a stronger first pass before switching. No bulk/Batch mode. — Bulk mode halves the price but results can take minutes to hours, too slow for the demo.
- **2026-10-03 20:15** — Herman (with Claude) — Step 3 receives one Markdown file per usable chat in `output/<user_id>/<source_id>.md`, as agreed with Aman in `HANDOFF.md`; this replaces the `data/eligible/<user_id>.json` file. Real output is git-ignored; synthetic samples in `samples/output/`. New source types, cleaned copies and masking are proposed in HANDOFF.md §7. — Follow the agreed handoff (it wins over the code until both owners change it).
- **2026-10-03 19:40** — Herman (with Claude) — **Replaces the 19:15 rule.** Mixed research chats are now *cleaned* instead of dropped: every exchange containing personal information (own name, academic record, admissions, relatives, other private people, email drafts, plus all sensitive categories) is removed, and the cleaned copy must pass a second independent check before it's used; the original stays held back. Mostly-personal chats, chats needing more than half removed, and chats with passwords/card/ID/record numbers are still held back whole. Whole messages are removed, not sentences. `PROMPT_VERSION` v3. — Owner's first real chat (economics research with an outreach email, own name and admission odds) was held back entirely; the research is worth keeping without the personal parts. Follows the brief's "safe excerpt, re-screened, new source ID" rule.
- **2026-10-03 19:15** — Herman (with Claude) — Any sensitive detail, even one passing mention (an ID number, a personal health problem), drops the entire chat. Claude's instructions now say so explicitly (`PROMPT_VERSION` v2, so earlier screenings are redone), and the local rules also catch passport, driver's licence, national ID, national insurance and tax ID numbers. — Owner's rule: safer to lose a research chat than to use one with personal details in it.
- **2026-10-03 19:05** — Herman (with Claude) — Switched the screening model to `claude-sonnet-5-5` (low effort). — Half the cost of Opus 5.5 ($2/$10 vs $4/$20 per million tokens); fine for a demo. Compare against Opus on the demo history if borderline calls look off.
- **2026-10-03 18:30** — Herman (with Claude) — Default model `claude-opus-5-5` at low effort rather than Haiku; switchable in one line. — A missed sensitive chat is the costly mistake; the demo history costs ~$0.10 either way.
- **2026-10-03 18:30** — Herman (with Claude) — Local safety rules run first; a hit is held back without sending the chat to the AI. — Passwords, card and record numbers shouldn't leave the laptop at all.
- **2026-10-03 18:30** — Herman (with Claude) — Hold back whole chats; mask emails/phones in kept ones as a safety net. — Brief: don't promise perfect redaction.
- **2026-10-03 18:30** — Herman (with Claude) — AI (Claude) + safety rules, not rules only. — Rules alone can't tell research about a disease from someone's own health; real chats vary too much.
- **2026-10-03 18:30** — Herman (with Claude) — Unclear, failed, invalid or contradictory screening → held back. — Brief: unknown or failed screening is not eligibility.

## Progress log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — what was done / what's next.`_

- **2026-10-03 21:59** — Herman (with Claude) — Less text: one-line intro, shorter cards and captions, shorter note on cleaned chats. What is checked, and the note that Claude does the screening, are unchanged.
- **2026-10-03 21:46** — Herman (with Claude) — Look only: the long explanation became a short intro, three cards (held back / cleaned / who reads them) and a "What counts as personal" toggle; the cost estimate is a small note; plurals fixed; duplicate counts removed. Nothing about what is checked changed.
- **2026-10-03 23:50** — Herman (with Claude) — New `sync_with_sources(user_id)`: forgets chats the owner removed in Step 1 (drops their report entries and Step 3 handoff files). Called by the shared app right after a removal, and at the end of every screening run.

- **2026-10-03 20:15** — Herman (with Claude) — Handoff to Step 3 now matches `HANDOFF.md`: Markdown files per chat, stale files removed on every change, `output/` git-ignored, samples for `user_a` (5 files) and `user_b` (2 files) generated with the real pipeline. Waiting for Aman's OK on §7.
- **2026-10-03 18:30** — Herman (with Claude) — Built screening (rules + Claude), report, eligible handoff, owner hold-back and the screening page in the shared app. 14 automatic checks pass with a fake classifier (demo history → 5 used / 4 held back). In the browser: page shows 9 waiting, 8 to send, ~$0.10, and asks for a key. Next: add a key, run on the demo history and a real chat.
- **2026-10-03** — setup — Step folder and spec created.

## Code fixes log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — **Problem:** … **Cause:** … **Fix:** … (files: …)`_

- **2026-10-04 00:20** — Herman (with Claude) — **Problem:** research-heavy chats were still dropped after cleaning (5 chats across the owner's accounts). **Cause:** (a) when the last re-check said "clean, redact these few more", its findings were thrown away and the chat dropped; (b) re-checks dropped cleaned copies because "many removed passages leave the meaning unclear" — the v6 meaning check treated expected gaps as damage. **Fix:** the last re-check's redactions are applied and the cleaned copy kept; the instructions now say a cleaned copy is judged only on what remains (redact what's still personal, remove a garbled sentence, exclude only if no coherent research is left). `PROMPT_VERSION` v8; only chats that went through cleaning are re-screened (`SAME_FIRST_CHECK_AS`), others keep their result. (files: `screening.py`, `filter_ui.py`, `test_screening.py`)

- **2026-10-03 21:55** — Herman (with Claude) — **Problem:** after v6, two research chats (AI-and-Financial-Crisis, World-Cup-Economic-Impact) were held back whole by the first pass; cleaning never ran (the first one had passed with cleaning before). **Cause:** the wider definition of personal information (school, career plans, own ventures) made Claude see it "throughout" and apply "exclude if personal information is central". **Fix:** instructions now say whether real research survives decides, not how much personal information there is: research with personal details woven through is "clean"; "exclude" only when the conversation is really about a personal matter. The re-check (incl. meaning check) still decides. `PROMPT_VERSION` v7. (files: `screening.py`, `test_screening.py`)

- **2026-10-03 19:55** — Herman (with Claude) — **Problem:** the owner's research chat was still held back after cleaning ("cleaned copy didn't pass the second check"), and the reason text was cut off mid-word. **Cause:** the first pass removed 12 of 65 messages but missed a few (own AI-usage habits, career/advisor prospects); the second check said "remove these too", but only one cleaning round was allowed, so any further finding meant holding back. Explanations were cut at 300 characters. **Fix:** keep cleaning — each re-check's findings are removed too and the copy re-checked, up to 3 re-checks, still never more than half the chat; used only once a check finds nothing personal. Explanations up to 500 characters, cut at a word with "…". The page now shows what each re-check found. `PROMPT_VERSION` v4 so the chat is screened again. (files: `screening.py`, `filter_ui.py`, `test_screening.py`)
- **2026-10-03 18:20** — Herman (with Claude) — **Problem:** a phone number followed by a full stop wasn't masked, and the standard test card number wasn't caught. **Cause:** the phone pattern refused a trailing "."; the card check skipped numbers made of only two different digits. **Fix:** allow a sentence-ending "."; only skip single-digit runs like 0000… (files: `screening.py`)
