# Step 1 — Data Collection

| | |
|---|---|
| **Owner** | Herman |
| **Branch** | `step-1-data-collection` (work here, not on `main`) |
| **Status** | ✅ Done for the demo (user picker is a placeholder until the steps are joined) |
| **Gets input from** | Step 0 (`user_id` of the signed-in user, e.g. `user_a`) |
| **Hands output to** | Step 2 |

## Goal
Let a researcher import their LLM chats and turn them into **private source records**: one per conversation, owned by one user, with who-said-what, order, timestamps and where it came from. Importing never shares anything. In the shared brief this is the second half of "Account + context import".

## Input
One of:
- **ChatGPT export**: the `.zip` ChatGPT emails you, or the `conversations.json` inside it.
- **Pasted chat**: text with lines starting `User:` / `Assistant:` (also `ChatGPT:`, `Claude:`, `You:` …). No labels → one user message.
- **Demo history**: the synthetic history for `user_a` in `samples/demo_chatgpt_user_a.json`.

## Output
`data/sources/<user_id>.json` (repo root, git-ignored):
```json
{
  "schema_version": "1.0",
  "user_id": "user_a",
  "sources": [
    {
      "user_id": "user_a",
      "source_id": "a_s01",
      "source_type": "demo",
      "messages": [
        {"message_id": "a_s01-m00", "role": "user", "text": "...", "created_at": "2026-09-04T12:10:00Z"},
        {"message_id": "a_s01-m01", "role": "assistant", "text": "...", "created_at": "2026-09-04T12:11:00Z"}
      ],
      "raw_text": "User: ...\n\nAssistant: ...",
      "provenance": {
        "original_conversation_id": "a_s01",
        "title": "Could trafficking explain the Disease A phenotype?",
        "created_at": "2026-09-04T12:00:00Z",
        "imported_at": "2026-10-03T20:00:00Z",
        "message_ids": ["a_s01-m00", "a_s01-m01"],
        "derived_from_source_id": null
      }
    }
  ]
}
```
- Field names follow the shared brief's handoff contract A (`SourceContextV1`). **Step 2 adds** `sensitive_flag`, `sensitive_category` and `eligible_for_idea_extraction`, and passes on only eligible records.
- `source_type`: `chatgpt_json`, `pasted_text` or `demo`.
- `source_id`: the demo history keeps the shared fixture IDs `a_s01` … `a_s09`. Everything else gets `src_` + 12 characters derived from the owner and conversation, so re-importing the same chat replaces it instead of duplicating it.
- Both user and assistant messages are kept, labelled by role, so later steps can tell the user's own thinking from the AI's suggestions.
- Errors are `{code, message, retryable}` and never include chat text (e.g. `malformed_json`, `empty_export`, `unsupported_file_type`).

> If you change this output format, update the README of the next step too and log it in `docs/DECISIONS.md` (see `CLAUDE.md`, Rule 4).

## How ChatGPT exports are read
- A conversation is a tree: editing a question or regenerating an answer leaves side branches. We import only the **branch the user last viewed** (`current_node`), not every alternative.
- System, tool and hidden messages are skipped; images are skipped but text next to them is kept.
- Conversations with no messages are skipped and listed on screen with a reason.

## Demo history (synthetic)
`samples/build_demo_fixture.py` writes `samples/demo_chatgpt_user_a.json`: nine fictional conversations for `user_a`, matching section 11 of the shared brief. Expected after Step 2: `a_s01`–`a_s05` eligible (two ideas: trafficking hypothesis `a_s01`–`a_s03`, LLM-extraction reproducibility `a_s04`–`a_s05`); `a_s06` health, `a_s07` finances, `a_s08` admin, `a_s09` research mixed with patient details: all held back. All people, patients, accounts and results in it are invented.

## How to run
From the repo root (first time only: `python3 -m venv .venv` then `.venv/bin/pip install -r "1 - Data Collection/requirements.txt"`):
```
.venv/bin/streamlit run "1 - Data Collection/app.py" --server.address localhost --browser.gatherUsageStats false
```
Checks: `.venv/bin/python -m unittest discover -s "1 - Data Collection"`

## Files
| File | What it is |
|---|---|
| `importer.py` | Reads ChatGPT exports / pasted text / demo history; saves private source records |
| `app.py` | Import screen (Streamlit) |
| `samples/build_demo_fixture.py` | Generates the synthetic demo history |
| `samples/demo_chatgpt_user_a.json` | The synthetic demo history (generated) |
| `test_importer.py` | Automatic checks |

## To do
- [x] Read ChatGPT exports (zip or conversations.json), including branched conversations
- [x] Paste-in text fallback
- [x] Synthetic demo history for `user_a` with the shared fixture IDs
- [ ] Try one real ChatGPT export from a teammate (on a laptop, never committed) to confirm the format still matches
- [ ] Replace the "Signed-in user ID" box with the real signed-in user once the steps are joined

## Open questions
- Claude/Gemini exports: out of scope for the demo (brief: support one format well). Revisit after the golden path works.
- Size limit: none yet. Streamlit's default upload limit is 200 MB; add a cap if big exports are slow.

---

## Decisions log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — decision — why.`_

- **2026-10-03 16:45** — Herman (with Claude) — Output follows the brief's `SourceContextV1` names, plus a `messages` list; Step 2 adds the filter fields. — One record shape from import to extraction, so Step 2 only adds fields.
- **2026-10-03 16:45** — Herman (with Claude) — Keep both user and assistant messages, labelled. — The brief asks to preserve roles; extraction must not mistake an AI suggestion for the user's own belief.
- **2026-10-03 16:45** — Herman (with Claude) — Import only the selected branch of each ChatGPT conversation. — Brief's proposed default; avoids counting edited/regenerated text twice.
- **2026-10-03 16:45** — Herman (with Claude) — Support ChatGPT JSON + pasted text only; dropped Claude/Gemini for now. — Brief: one real format done well before adding connectors.

## Progress log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — what was done / what's next.`_

- **2026-10-03 16:45** — Herman (with Claude) — Built importer, import screen and synthetic demo history (9 conversations); 18 automatic checks pass; loaded the demo history in the browser and saw all 9. **Placeholder:** the user is picked by typing a user ID until joined with Step 0. Next: Step 2 noise filter reads `data/sources/<user_id>.json`.
- **2026-10-03** — setup — Step folder and spec created.

## Code fixes log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — **Problem:** … **Cause:** … **Fix:** … (files: …)`_

- _No fixes yet._
