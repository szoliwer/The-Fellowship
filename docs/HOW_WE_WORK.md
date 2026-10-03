# How We Work (GitHub Desktop)

A short guide for saving and sharing work without stepping on each other.

## The big idea: everyone works on `main`
We all work on the **`main`** branch, so every committed change is visible to the whole team straight away. (We tried one branch per step first, and switched on 2026-10-03. See `docs/DECISIONS.md`, D-005.)

The trade-off is that nothing protects `main` from a mistake, so the habits below matter.

## Every time you sit down
1. Open **GitHub Desktop**. Check that the current repository is **The-Fellowship** and **Current branch** says **main**.
2. Click **Fetch origin**, then **Pull origin** if it appears. Do this **before** you change anything.

## While you work
- Work **inside your step's folder** (see `docs/PROGRESS.md` for who owns what).
- Shared files (`README.md`, `CLAUDE.md`, `docs/`) are fine to edit, but pull right before you do and keep the edit small. These are where clashes happen.
- Log what you did in your step's `README.md` (Decisions / Progress / Code fixes).
- Never put real chat exports or API keys in the repo. Real data goes in `data/`, keys go in `.env`, and both are ignored by Git automatically.

## Saving your work (commit + push)
1. **Pull first** (Fetch origin → Pull origin), so you have your teammates' latest work.
2. Look at the **Changes** list on the left. Make sure every file there is one you meant to change.
3. In the **Summary** box, write what you did, e.g. `Step 3: first version of idea-extraction prompt`.
4. Click **Commit to main**, then **Push origin**.
5. Commit **small and often**. Small commits rarely clash.

> If an AI assistant is helping you, it has to **ask you before committing** and show you the file list and message first. That's a rule in `CLAUDE.md`.

## If GitHub Desktop says there's a conflict
Two people edited the same lines of the same file. Don't panic and don't discard anything. Tell the team and open the file. GitHub Desktop marks both versions, so keep the right one (or both) and then commit. Sticking to your own step folder makes this rare.

## If Push is rejected
Someone pushed before you. Click **Pull origin**, then **Push origin** again.

## Commit message convention
`Step N: what changed` for step work, `Docs: what changed` for documentation, `Fix (Step N): what was fixed` for bug fixes.
