# How We Work (GitHub Desktop)

A short guide for saving and sharing work without stepping on each other.

## Every time you sit down
1. Open **GitHub Desktop**. Check that the current repository is **The-Fellowship**.
2. Click **Fetch origin**, then **Pull origin** if it appears. You now have everyone's latest work.

## While you work
- Work only in **your step's folder** (see `docs/PROGRESS.md` for who owns what).
- Log what you did in your step's `README.md` (Decisions / Progress / Code fixes).
- Never put real chat exports or API keys in the repo. Real data goes in `data/`, keys go in `.env`, and both are ignored by Git automatically.

## Saving to GitHub (commit + push)
1. In GitHub Desktop, look at the **Changes** list on the left. Make sure every file there is one you meant to change.
2. In the **Summary** box (bottom-left), write a short message saying what you did, starting with the step number, e.g. `Step 3: first version of idea-extraction prompt`.
3. Click **Commit to main**.
4. Click **Push origin**.

> If an AI assistant is helping you, it has to **ask you before committing** and show you the file list and message first. That's a rule in `CLAUDE.md`.

## If GitHub Desktop says there's a conflict
This means two people edited the same lines of the same file. Don't panic and don't discard anything. Tell the team, and open the file. GitHub Desktop marks both versions, so keep the right one (or both) and then commit.

**Tip:** shared files like `docs/PROGRESS.md` get edited by everyone, so keep your edits to your own row, and pull right before you edit.

## Commit message convention
`Step N: what changed` for step work, `Docs: what changed` for documentation, `Fix (Step N): what was fixed` for bug fixes.
