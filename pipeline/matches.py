"""Matches as one user sees them, and their Accept/Pass decisions. Used by the Step 6 placeholder.

Reads Step 5's data/matches.json and Step 4's data/ideas.json (approved ideas only).
Decisions are stored in data/match_status.json, keyed by the pair of users (not Step 5's
match_id), so they survive re-running Step 5.

Shared brief rules followed here:
  • Each person sees their own side of a match (what the other person can add for *them*).
  • Before both say yes, nobody learns the other's decision (a "pass" looks like "waiting").
  • The warm introduction appears only after both said yes.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MATCHES_FILE = ROOT / "data" / "matches.json"
IDEAS_FILE = ROOT / "data" / "ideas.json"
STATUS_FILE = ROOT / "data" / "match_status.json"
DECISIONS = ("connect", "pass")
TITLE_FIELDS = ("summary", "main_idea", "idea", "title")


def _read(path, default):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def pair_key(a, b):
    return "|".join(sorted([a, b]))


def _idea_titles(ideas_file):
    data = _read(ideas_file, {})
    rows = data.get("ideas", []) if isinstance(data, dict) else data
    titles = {}
    for r in rows:
        title = next((r[f] for f in TITLE_FIELDS if r.get(f)), None)
        if r.get("idea_id") and title:
            titles[r["idea_id"]] = str(title)
    return titles


def load_status(status_file=STATUS_FILE):
    return _read(status_file, {})


def decide(user_id, other_id, decision, status_file=STATUS_FILE):
    """Record this user's Accept ("connect") or Pass for the match with other_id."""
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}")
    status = load_status(status_file)
    entry = status.setdefault(pair_key(user_id, other_id), {"decisions": {}})
    entry["decisions"][user_id] = decision
    entry["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = Path(status_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def my_matches(user_id, matches_file=MATCHES_FILE, ideas_file=IDEAS_FILE, status_file=STATUS_FILE):
    """This user's matches, from their side only. Each item:
    {other_id, other_name, other_summary, match_type, reason, they_can_offer, you_can_offer,
     shared_topics, linked [(your idea, their idea)], my_decision, state, intro}
    state: "new" (you haven't decided), "waiting" (you said yes, they haven't, or passed),
           "passed" (you passed), "connected" (both said yes; only then is intro set)."""
    data = _read(matches_file, {})
    people = data.get("people", {})
    titles = _idea_titles(ideas_file)
    status = load_status(status_file)
    out = []
    for m in data.get("matches", []):
        if user_id not in (m.get("user_a"), m.get("user_b")):
            continue
        side = "a" if m["user_a"] == user_id else "b"
        other = m["user_b"] if side == "a" else m["user_a"]
        decisions = status.get(pair_key(user_id, other), {}).get("decisions", {})
        mine, theirs = decisions.get(user_id), decisions.get(other)
        if mine == "pass":
            state = "passed"
        elif mine == "connect" and theirs == "connect":
            state = "connected"
        elif mine == "connect":
            state = "waiting"
        else:
            state = "new"
        linked = []
        for pair in m.get("shared_or_linked_ideas") or []:
            mine_id, theirs_id = (pair[0], pair[1]) if side == "a" else (pair[1], pair[0])
            if mine_id in titles and theirs_id in titles:
                linked.append((titles[mine_id], titles[theirs_id]))
        out.append({
            "other_id": other,
            "other_name": (people.get(other) or {}).get("name") or "A researcher",
            "other_summary": (people.get(other) or {}).get("summary") or "",
            "match_type": m.get("match_type"),
            "reason": m.get("reason") or "",
            "they_can_offer": m.get("b_can_offer_a" if side == "a" else "a_can_offer_b") or "",
            "you_can_offer": m.get("a_can_offer_b" if side == "a" else "b_can_offer_a") or "",
            "shared_topics": m.get("shared_topics") or [],
            "linked": linked[:3],
            "my_decision": mine,
            "state": state,
            "intro": m.get(f"intro_for_{side}") if state == "connected" else None,
        })
    return out
