"""Step 3 → Step 4 bridge. PLACEHOLDER ranking until Step 4's real ranking is built.

Step 3 writes data/ideas/<user_id>.json; Step 4's review page reads data/ranked_ideas/<user_id>.json.
This copies Step 3's idea rows across with a simple score, so Step 4 shows the most central
ideas first. Adjacent ideas (Step 3's speculative suggestions) are never copied.

rank_score (0-1) = 0.40 × primary (in 2+ chats)
                 + 0.25 × chats it appears in   (relative to the user's most-discussed idea)
                 + 0.15 × the user's own messages about it (relative)
                 + 0.20 × how recent it is      (relative to the user's oldest and newest idea)
"""

import json
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STEP3_DIR = ROOT / "data" / "ideas"
RANKED_DIR = ROOT / "data" / "ranked_ideas"
WEIGHTS = {"primary": 0.40, "chats": 0.25, "mentions": 0.15, "recency": 0.20}
RANKED_BY = "placeholder ranking (pipeline/ranking.py): chats, own messages, recency"


def _day(value):
    try:
        return date.fromisoformat(str(value)[:10]).toordinal()
    except ValueError:
        return None


def _relative(value, low, high):
    if value is None or high is None or high == low:
        return 1.0 if value is not None else 0.0
    return (value - low) / (high - low)


def score_rows(rows):
    """Copies of the rows with rank_score and score_parts added, highest score first."""
    chats = [r.get("chat_count") or len(r.get("evidence") or []) for r in rows]
    mentions = [r.get("mentions") or 0 for r in rows]
    days = [_day(r.get("last_seen")) for r in rows]
    known_days = [d for d in days if d is not None]
    lo, hi = (min(known_days), max(known_days)) if known_days else (None, None)
    out = []
    for r, c, m, d in zip(rows, chats, mentions, days):
        parts = {
            "primary": 1.0 if r.get("tier") == "primary" else 0.0,
            "chats": c / max(chats) if max(chats) else 0.0,
            "mentions": m / max(mentions) if max(mentions) else 0.0,
            "recency": _relative(d, lo, hi),
        }
        score = sum(WEIGHTS[k] * v for k, v in parts.items())
        out.append({**r, "rank_score": round(score, 3), "score_parts": {k: round(v, 3) for k, v in parts.items()}})
    return sorted(out, key=lambda r: r["rank_score"], reverse=True)


def rank_user(user_id, step3_dir=STEP3_DIR, ranked_dir=RANKED_DIR):
    """Read Step 3's file for this user and write Step 4's input. Returns the ranked rows."""
    data = json.loads((Path(step3_dir) / f"{user_id}.json").read_text(encoding="utf-8"))
    rows = [r for r in data.get("ideas", []) if r.get("user_id") == user_id]
    ranked = score_rows(rows)
    out = Path(ranked_dir) / f"{user_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps({
        "schema_version": "1.0",
        "user_id": user_id,
        "ranked_by": RANKED_BY,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ideas": ranked,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(out)
    return ranked
