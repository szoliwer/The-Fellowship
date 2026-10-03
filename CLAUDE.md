# CLAUDE.md — Project Harness for The Fellowship

This file is the **base harness** for any AI assistant (Claude, Claude Code, Cowork, Cursor, Copilot, etc.) working in this repository. Read it in full before doing anything. It gives you the context and the rules. If a request conflicts with these rules, stop and ask the user.

---

## 1. Context

### What we are building
**The Fellowship** is an AI-native discovery network that matches people on what they are actually thinking about, not on static profiles. Users import their LLM chat histories. We distill their ideas and interests and match them with other users whose ideas are **similar** or **complementary**, using a ranking model. A user decides whether to accept a match, both sides get a **warm intro** explaining why they matched, and they start a productive conversation.

### Who you are working with
- A team of **4 people, mostly non-technical**, building live at a **hackathon**. Time is short.
- **Explain everything in plain language.** Avoid jargon. When you must use a technical term, define it in one line.
- Prefer the **simplest thing that works for a demo** over the "proper" production solution. Say so when you take a shortcut.
- Everyone uses **GitHub Desktop**, not the command line. Give instructions in terms of GitHub Desktop buttons.

### Repository
- GitHub: `https://github.com/szoliwer/The-Fellowship`. `main` is the stable version, with one working branch per step (see Rule 0).
- Each step of the pipeline lives in its own folder (`0 - User Registration` … `6 - Matching Interface`).
- Project-wide docs live in `docs/`.

### The 7-step pipeline
| # | Step | Input → Output |
|---|------|----------------|
| 0 | User Registration | Sign-up form → user record (id, name, email, consent, match preferences) |
| 1 | Data Collection | Uploaded chat exports → conversations in one common format |
| 2 | Noise Filter | All conversations → only the meaningful ones, with personal details removed |
| 3 | Idea Generation | Filtered conversations → list of ideas/interests/skills/needs per user |
| 4 | Idea Ranking | Ideas → ideas with a score for how central and current each one is |
| 5 | Match Generation | Everyone's ranked ideas → ranked list of suggested pairs + reason for each |
| 6 | Matching Interface | Suggested pairs → UI where users accept/pass and see the warm intro |

Details, inputs/outputs and open questions for each step are in that step's `README.md`.

---

## 2. Rules

### Rule 0 — Work on your step's branch, never directly on `main`
- Each step has its own branch. **`main` is the "known good" version** and only changes through a reviewed pull request.

  | Step | Branch |
  |------|--------|
  | 0 User Registration | `step-0-user-registration` |
  | 1 Data Collection | `step-1-data-collection` |
  | 2 Noise Filter | `step-2-noise-filter` |
  | 3 Idea Generation | `step-3-idea-generation` |
  | 4 Idea Ranking | `step-4-idea-ranking` |
  | 5 Match Generation | `step-5-match-generation` |
  | 6 Matching Interface | `step-6-matching-interface` |

- **Before changing anything, check which branch is checked out** (GitHub Desktop shows it at the top, under *Current branch*). If it's `main`, or it doesn't match the step being worked on, stop and ask the user to switch.
- On a step branch, only change files inside **that step's folder**. Shared files (`README.md`, `CLAUDE.md`, `docs/*`) are updated on `main` when a step is merged, so seven branches don't conflict over them.
- Getting work into `main`: open a **pull request** on GitHub from the step branch into `main`. A teammate reviews it before merging. Never merge without the user's go-ahead.
- To pick up teammates' merged work, merge `main` into the step branch (GitHub Desktop: *Branch → Update from main*).

### Rule 1 — Never commit or push without asking
- **Do not `git commit`, `git push`, merge, or create a pull request until the user has said yes** in the current conversation.
- Before asking, show: (a) a plain-language list of the files you changed and why, and (b) the commit message you plan to use.
- An earlier "yes" covers only the commit it was given for. Ask again for each new commit.
- Never force-push, rewrite history, or delete branches.

### Rule 2 — Document as you go
Every meaningful change gets logged **in the same session it was made**, in the right place:

| What happened | Where to log it |
|---------------|-----------------|
| A decision about one step (e.g. "we use cosine similarity") | That step's `README.md` → **Decisions log** |
| Work finished or started on a step | That step's `README.md` → **Progress log** |
| A bug found and fixed | That step's `README.md` → **Code fixes log** |
| A decision affecting several steps or the whole project (stack, data format, privacy) | `docs/DECISIONS.md` |
| Overall status change (step started, blocked, done) | `docs/PROGRESS.md` (updated on `main` when the step is merged; see Rule 0) |

Log entries use this format, newest at the top:
```
- **YYYY-MM-DD HH:MM** — [who] — what was done/decided, and *why* (one or two lines).
```
For a code fix, also include: what broke, the cause, and the fix.

### Rule 3 — Stay in your lane
- Only change files in the step folder you've been asked to work on, plus the docs you're logging to.
- If a change requires touching another step (for example, changing the shared data format), **stop, explain why, and ask first**, then log it in `docs/DECISIONS.md`.
- Never delete or overwrite a teammate's work. If something looks wrong, flag it.

### Rule 4 — Respect the handoffs between steps
- Each step's output format is written down in its `README.md` under **Output**. Keep to it.
- If you need to change an output format, update the README of **both** steps affected (the one producing it and the one consuming it) and log the decision.

### Rule 5 — Privacy and secrets
- **Never commit real chat logs or personal data.** Real exports go in a `data/` folder, which is git-ignored. Use synthetic/sample data in `samples/` folders for testing.
- **Never commit API keys or passwords.** Keep them in a `.env` file (git-ignored). If you see a key in a file that's about to be committed, stop and warn the user.
- Other users must never see raw chat text, only extracted ideas and the warm intro.

### Rule 6 — Keep it demo-able
- Something working end to end beats something perfect in one step. If a step isn't ready, use a simple placeholder (fake data or a hard-coded result) so the steps after it can keep going, and mark it clearly as a placeholder in the Progress log.
- Prefer well-known, free/simple tools. Ask before adding a paid service or a new dependency.

### Rule 7 — Communicate clearly
- Before larger changes, give a short plan (3–5 bullets) and wait for a go-ahead.
- After changes, summarise in 1–3 sentences what changed and what to do next.
- If you're unsure what the user wants, ask one clear question rather than guessing.

---

## 3. Session checklist (for the AI assistant)

At the **start** of a session:
1. Read this file, `docs/PROGRESS.md`, and the `README.md` of the step you're working on.
2. Confirm the right step branch is checked out (Rule 0).
3. Ask the user to **Pull** in GitHub Desktop if they haven't recently, so you're working on the latest version.

At the **end** of a session or after a chunk of work:
1. Update the step's Decisions / Progress / Code fixes logs.
2. Update `docs/PROGRESS.md` if the status changed.
3. Show the list of changed files and the proposed commit message, and **ask before committing** (Rule 1).
