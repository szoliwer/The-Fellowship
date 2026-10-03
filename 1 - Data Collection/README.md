# Step 1 — Data Collection

| | |
|---|---|
| **Owner** | Herman |
| **Status** | ✅ Done for the demo: uploads, paste, demo history; everything stored per user |
| **Gets input from** | Step 0 (the logged-in user's `user_id`) |
| **Hands output to** | Step 2 |

## Goal
Let a logged-in researcher import their LLM chats and turn them into **private source records**: one per conversation, owned by one user, with who-said-what, order, timestamps and where it came from. Importing never shares anything. In the shared brief this is the second half of "Account + context import".

## Input
Uploaded files (several at once is fine) or pasted text:

| Upload | What happens |
|---|---|
| **ChatGPT export**: the `.zip`, or `conversations.json` | Every conversation becomes one source (`chatgpt_json`) |
| **Claude export**: the `.zip`, or `conversations.json` | Every conversation becomes one source (`claude_json`); detected automatically |
| **`.md` / `.txt` file** | The file is one source (`text_file`) |
| **`.zip` of `.md` / `.txt` files** | Each file is one source; other files are skipped and listed |
| **Pasted text** | One source (`pasted_text`) |
| **Demo history** (only for `researcher_014`) | The 9 synthetic conversations (`demo`) |

**Who said what** in text, Markdown and pasted chats: a new turn starts at lines like `User:`, `You:`, `Assistant:`, `ChatGPT:`, `Claude:`, `AI:`, `**You:**`, `> **User:**`, `## ChatGPT`, `### **Claude**`, or ChatGPT's copy-paste labels `You said:` / `ChatGPT said:`. Text with no labels counts as one message from the user (their own notes). A first-line `# Heading` becomes the title; front matter (`--- … ---`) is skipped.

**Limits:** 200 MB per upload; inside zips: `conversations.json` up to 500 MB, at most 500 text files of up to 5 MB each (100 MB total). Hidden files and `__MACOSX` are ignored.

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
        "derived_from_source_id": null,
        "upload_id": "up_1a2b3c4d5e6f"
      }
    }
  ]
}
```
- Field names follow the shared brief's handoff contract A (`SourceContextV1`), plus `messages` and `provenance.upload_id`. **Step 2 adds** `sensitive_flag`, `sensitive_category` and `eligible_for_idea_extraction`, and passes on only eligible records.
- `source_type`: `chatgpt_json`, `claude_json`, `text_file`, `pasted_text` or `demo`. (`claude_json` and `text_file` are additions to the brief's list; see D-005.)
- `source_id`: the demo history keeps the shared fixture IDs `a_s01` … `a_s09`. Everything else gets `src_` + 12 characters derived from the owner and conversation, so re-importing the same chat replaces it instead of duplicating it.
- `created_at` is `null` for text files and pastes (they carry no dates).
- Both user and assistant messages are kept, labelled by role, so later steps can tell the user's own thinking from the AI's suggestions.

**Also stored, privately per user:**
- `data/uploads/<user_id>/files/<upload_id>__<filename>`: the original file, exactly as uploaded. Only kept if it imported; a wrong file (e.g. a PDF) is never stored.
- `data/uploads/<user_id>/uploads.json`: upload history: what, when, size, SHA-256 fingerprint, result, skipped items, or the error.

Errors are `{code, message, retryable}` and never include chat text (e.g. `malformed_json`, `unsupported_file_type`, `bad_zip`, `not_text`, `too_large`).

> If you change this output format, update the README of the next step too and log it in `docs/DECISIONS.md` (see `CLAUDE.md`, Rule 4).

## How exports are read
- **ChatGPT:** a conversation is a tree (edits and regenerations leave side branches). We import only the **branch the user last viewed** (`current_node`). System, tool and hidden messages are skipped; images are skipped but text next to them is kept.
- **Claude:** `chat_messages` in order; `human` → `user`. Text comes from `text`, or from the `content` text blocks if that's empty.
- Conversations with no messages are skipped and listed on screen with a reason.

## Demo history (synthetic)
`samples/build_demo_fixture.py` writes `samples/demo_chatgpt_user_a.json`: nine fictional conversations for `user_a`, matching section 11 of the shared brief. Expected after Step 2: `a_s01`–`a_s05` eligible (two ideas: trafficking hypothesis `a_s01`–`a_s03`, LLM-extraction reproducibility `a_s04`–`a_s05`); `a_s06` health, `a_s07` finances, `a_s08` admin, `a_s09` research mixed with patient details: all held back. All people, patients, accounts and results in it are invented.

## How to run
From the repo root, see the main `README.md` → *Run the app*. Checks:
`.venv/bin/python -m unittest discover -s "1 - Data Collection"`

## Files
| File | What it is |
|---|---|
| `importer.py` | Reads every upload type; stores sources, original files and upload history |
| `import_ui.py` | Import screen (used by `app.py` at the repo root) |
| `samples/build_demo_fixture.py` | Generates the synthetic demo history |
| `samples/demo_chatgpt_user_a.json` | The synthetic demo history (generated) |
| `test_importer.py` | Automatic checks (24) |

## To do
- [x] ChatGPT and Claude exports (zip or conversations.json), .md/.txt files, zips of them, paste
- [x] Store original uploads + upload history per user
- [x] Tied to the logged-in user (no more typing a user ID)
- [ ] Try one real ChatGPT and one real Claude export from a teammate (on a laptop, never committed) to confirm the formats still match
- [ ] Let users delete an import (and its stored file)

## Open questions
- Claude exports occasionally change shape; if a real one fails, send the error code (never the file) and we'll adjust.

---

## Decisions log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — decision — why.`_

- **2026-10-03 17:40** — Herman (with Claude) — Keep the original uploaded file and an upload history per user under `data/uploads/`; only keep files that imported successfully. — Provenance (brief: "original imported chats/files"), and a wrong upload (e.g. an ID scan) shouldn't linger.
- **2026-10-03 17:40** — Herman (with Claude) — Accept ChatGPT + Claude exports, .md/.txt (alone or zipped) and paste; new `source_type`s `claude_json` and `text_file`. — Researchers use both assistants and often save chats as Markdown.
- **2026-10-03 16:45** — Herman (with Claude) — Output follows the brief's `SourceContextV1` names, plus a `messages` list; Step 2 adds the filter fields. — One record shape from import to extraction.
- **2026-10-03 16:45** — Herman (with Claude) — Keep both user and assistant messages, labelled. — Extraction must not mistake an AI suggestion for the user's own belief.
- **2026-10-03 16:45** — Herman (with Claude) — Import only the selected branch of each ChatGPT conversation. — Avoids counting edited/regenerated text twice.

## Progress log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — what was done / what's next.`_

- **2026-10-03 17:40** — Herman (with Claude) — Importer now takes ChatGPT/Claude zips and JSON, .md/.txt, zips of text files and paste; stores originals + history per user; screen moved into the shared `app.py` behind log-in. 24 automatic checks pass; in the browser: uploaded a .md file, logged out and back in, chat still there. Next: Step 2 noise filter reads `data/sources/<user_id>.json`.
- **2026-10-03 16:45** — Herman (with Claude) — Built importer, import screen and synthetic demo history (9 conversations).
- **2026-10-03** — setup — Step folder and spec created.

## Code fixes log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — **Problem:** … **Cause:** … **Fix:** … (files: …)`_

- _No fixes yet._
