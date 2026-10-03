# How We Work (GitHub Desktop)

A short guide for saving and sharing work without stepping on each other.

## The big idea: one branch per step
A **branch** is your own copy of the project to work in. Changes there don't affect anyone else until you choose to merge them.

- **`main`** is the version that works. Nobody edits it directly.
- Each step has its own branch:

| Step | Branch |
|------|--------|
| 0 User Registration | `step-0-user-registration` |
| 1 Data Collection | `step-1-data-collection` |
| 2 Noise Filter | `step-2-noise-filter` |
| 3 Idea Generation | `step-3-idea-generation` |
| 4 Idea Ranking | `step-4-idea-ranking` |
| 5 Match Generation | `step-5-match-generation` |
| 6 Matching Interface | `step-6-matching-interface` |

## Every time you sit down
1. Open **GitHub Desktop**. Check that the current repository is **The-Fellowship**.
2. Click **Current branch** (top middle) and pick **your step's branch**. ⚠️ Check this every time. It's the most common mistake.
3. Click **Fetch origin**, then **Pull origin** if it appears.
4. Optional but helpful: **Branch → Update from main** to pull in steps your teammates have finished.

## While you work
- Only change files **inside your step's folder**. Leave `README.md`, `CLAUDE.md` and `docs/` alone on your branch. Those get updated on `main` when your step is merged.
- Log what you did in your step's `README.md` (Decisions / Progress / Code fixes).
- Never put real chat exports or API keys in the repo. Real data goes in `data/`, keys go in `.env`, and both are ignored by Git automatically.

## Saving your work (commit + push to your branch)
1. Look at the **Changes** list on the left. Every file there should be one you meant to change, inside your step folder.
2. In the **Summary** box, write what you did, e.g. `Step 3: first version of idea-extraction prompt`.
3. Click **Commit to step-3-…** (the button shows your branch name. If it says **main**, stop and switch branches.)
4. Click **Push origin**.

> If an AI assistant is helping you, it has to **ask you before committing** and show you the file list and message first. That's a rule in `CLAUDE.md`.

## Getting your step into `main` (pull request)
Do this when your step works, or has a useful working placeholder.
1. In GitHub Desktop: **Branch → Create Pull Request**. This opens GitHub in your browser.
2. Make sure it says **base: main ← compare: your-branch**. Write 2–3 lines on what the step does now.
3. Ask a teammate to look at it. When you're both happy, click **Merge pull request**.
4. Then, on `main`, update your row in `docs/PROGRESS.md` (or ask Claude to).

## If GitHub Desktop says there's a conflict
This means two people edited the same lines of the same file. Don't panic and don't discard anything. Tell the team and open the file. GitHub Desktop marks both versions, so keep the right one (or both) and then commit. Sticking to your own step folder makes this rare.

## Commit message convention
`Step N: what changed` for step work, `Docs: what changed` for documentation, `Fix (Step N): what was fixed` for bug fixes.
