# pipeline/ — glue between the steps

The shared app (`app.py` at the repo root) shows one page per step for the logged-in user. Each step keeps its own code in its own folder; this folder holds only what sits **between** steps, plus clearly labelled **placeholders** for parts that aren't built yet (D-013).

## How data flows (all under `data/` at the repo root, git-ignored)

| Step | Page | Reads | Writes |
|---|---|---|---|
| 0 | sign in | — | `data/fellowship.db`, `data/users.json` |
| 1 | 1. Import chats | uploads | `data/sources/<user>.json` |
| 2 | 2. Privacy screening | `data/sources/<user>.json` | `2 - Noise Filter/output/<user>/*.md` |
| 3 | 3. Find my ideas (`ideas_page.py`) | Step 2's `.md` files | `data/ideas/<user>.json` |
| 3→4 | (`ranking.py`, **placeholder**) | `data/ideas/<user>.json` | `data/ranked_ideas/<user>.json` |
| 4 | 4. Review ideas (Step 4's own `app.py`) | `data/ranked_ideas/<user>.json` | `data/approved_ideas/<user>.json`, `data/ideas.json` |
| 5 | 5. Find matches (`matching_page.py`) | `data/ideas.json`, `data/users.json` | `data/matches.json` |
| 6 | 6. Discover (`discover_page.py`, **placeholder**) | `data/matches.json`, `data/ideas.json` | `data/match_status.json` |

## Placeholders to replace
- **`ranking.py`** (Step 4 owner): orders ideas by a simple score (in 2+ chats, number of chats, own messages, recency). Replace with real ranking that writes `data/ranked_ideas/<user>.json` in the same shape.
- **`discover_page.py`** (Step 6, Oliver + Colin): a plain match screen. Provide a `render(user)` in your step folder and point page 6 in `app.py` at it. `matches.py` already gives each user their own side of every match, hides a "pass" until both decide, and only shows the warm intro after both said yes. Reuse it or replace it.

## Checks
Free and offline (no API calls): `.venv/bin/python -m unittest discover -s pipeline -t .`. They include a Step 4 → 5 → 6 run on the synthetic sample users.
