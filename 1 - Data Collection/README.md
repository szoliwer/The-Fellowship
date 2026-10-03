# Step 1 — Data Collection

| | |
|---|---|
| **Owner** | _TBD_ |
| **Branch** | `step-1-data-collection` (work here, not on `main`) |
| **Status** | ⬜ Not started |
| **Gets input from** | Step 0 |
| **Hands output to** | Step 2 |

## Goal
Let users upload chat exports from the LLM tools they choose, and convert them all into **one common format** the rest of the pipeline can read.

## Input
Export files uploaded by the user, e.g. ChatGPT export (`conversations.json` inside a .zip), Claude export (.json), Gemini via Google Takeout, or a pasted transcript.

## Output
A list of **conversations** in the common format:
```json
{
  "user_id": "u_001",
  "source": "chatgpt",
  "conversation_id": "c_123",
  "title": "Protein folding with diffusion models",
  "created_at": "2026-09-14T10:22:00",
  "messages": [
    {"role": "user", "text": "...", "timestamp": "..."},
    {"role": "assistant", "text": "...", "timestamp": "..."}
  ]
}
```

> If you change this output format, update the README of the next step too and log it in `docs/DECISIONS.md` (see `CLAUDE.md`, Rule 4).

## To do
- [ ] Get a real sample export from ChatGPT and from Claude (from a teammate, never committed)
- [ ] Write a reader for each source that outputs the common format
- [ ] Create synthetic sample chats in `samples/` for 3–5 demo users
- [ ] Decide on a size limit (e.g. only the last N conversations)

## Open questions
- Which sources do we support for the demo? (Suggest ChatGPT + Claude + paste-in text.)
- Do we keep the assistant's replies, or only the user's own messages? (The user's messages say the most about them.)

---

## Decisions log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — decision — why.`_

- _No decisions yet._

## Progress log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — what was done / what's next.`_

- **2026-10-03** — setup — Step folder and spec created.

## Code fixes log
_Newest at the top. Format: `- **YYYY-MM-DD HH:MM** — [who] — **Problem:** … **Cause:** … **Fix:** … (files: …)`_

- _No fixes yet._
