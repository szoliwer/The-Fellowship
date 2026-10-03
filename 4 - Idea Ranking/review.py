"""Step 4 — the "Your ideas" review page: all the logic, no Streamlit.

The AI nominates ideas; only the user decides what is used for matching.
This module reads a user's ranked ideas, keeps track of what they include,
exclude or remove, and saves only the approved parts for Step 5.

Rules the page follows (agreed with the team, see README Decisions log):
- Everything starts included. Ideas are shown most central first.
- Each idea has a main title and sub-ideas ("details").
- Unchecking a main idea excludes it and all its details.
- The main checkbox mirrors its details: all checked = checked,
  some = partly checked, none = unchecked. Unchecking the last detail
  unchecks the main idea; removing the last detail removes it. Checking a detail of an unchecked idea
  brings that idea back with just that detail, so no click ever "fails".
- Re-checking a main idea restores the details the user had picked before.
- Main ideas and details can also be removed (trash icon). The latest
  removal can be undone until the user's next change.

Files (all under data/, which is git-ignored):
- input:  data/ranked_ideas/<user_id>.json   ranked ideas for one user
          (until Steps 3-4 write this, the synthetic samples/ file is used)
- output: data/approved_ideas/<user_id>.json what this user approved
          data/ideas.json                    everyone's approved ideas, for Step 5

The output rows keep the input's own format (per-chat packages with
main_idea/insights, or spec rows with summary/keywords). Excluded and removed
parts are dropped, and nothing the user didn't see is copied (raw_text included).
Saving with nothing checked is allowed: it withdraws the user's ideas from matching.
"""

import copy
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

STEP_DIR = Path(__file__).resolve().parent
REPO_ROOT = STEP_DIR.parent
RANKED_DIR = REPO_ROOT / "data" / "ranked_ideas"
APPROVED_DIR = REPO_ROOT / "data" / "approved_ideas"
MATCHING_FILE = REPO_ROOT / "data" / "ideas.json"
SAMPLE_FILE = STEP_DIR / "samples" / "sample_ranked_ideas.json"

SCHEMA_VERSION = "1.0"
TITLE_FIELDS = ("main_idea", "summary", "idea", "title")
DETAIL_FIELDS = ("insights", "subtopics", "specific_insights", "keywords")
SCORE_FIELDS = ("rank_score", "score", "rank")
# Besides the title and details the user saw, only these plain bookkeeping fields are copied
# to Step 5. Anything else (raw_text, offers/needs lists, extra text fields) is left behind,
# because the user never saw it on the page. Add a field here only if it holds no idea text.
METADATA_FIELDS = ("user_id", "idea_id", "type", "rank_score", "score", "rank", "score_parts",
                   "evidence", "first_seen", "last_seen", "mentions")


class ReviewError(Exception):
    """A clear, user-safe error. Never includes idea or chat text."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def _now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _check_user_id(user_id):
    if not re.match(r"^[A-Za-z0-9_]+$", user_id or ""):
        raise ReviewError("invalid_user", "Unknown user.")


def _first(row, keys):
    for k in keys:
        if row.get(k) not in (None, "", []):
            return k, row[k]
    return None, None


def _rows_in(data):
    """Rows can be a plain list or wrapped as {"ideas": [...]} (same as Step 5 accepts)."""
    rows = data.get("ideas", []) if isinstance(data, dict) else data
    return [r for r in (rows or []) if isinstance(r, dict)]


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise ReviewError("malformed_json", f"{Path(path).name} is not valid JSON.")


# ---------- Reading ranked ideas ----------

def load_ranked_rows(user_id, ranked_dir=RANKED_DIR, sample_file=SAMPLE_FILE):
    """Return (rows, is_sample) for one user. Uses the user's real ranked file when it
    exists, otherwise the synthetic sample (a placeholder until Steps 3-4 write real files).
    Rows that belong to a different user are never returned."""
    _check_user_id(user_id)
    path = Path(ranked_dir) / f"{user_id}.json"
    if path.exists():
        rows = _rows_in(_read_json(path))
        return [r for r in rows if str(r.get("user_id", user_id)) == user_id], False
    if sample_file and Path(sample_file).exists():
        rows = _rows_in(_read_json(sample_file))
        return [r for r in rows if str(r.get("user_id")) == user_id], True
    return [], False


def available_users(ranked_dir=RANKED_DIR, sample_file=SAMPLE_FILE):
    """User IDs that have ranked ideas (real files first, then sample users). For the demo picker."""
    users = []
    if Path(ranked_dir).exists():
        users += sorted(p.stem for p in Path(ranked_dir).glob("*.json") if re.match(r"^[A-Za-z0-9_]+$", p.stem))
    if sample_file and Path(sample_file).exists():
        for r in _rows_in(_read_json(sample_file)):
            uid = str(r.get("user_id", ""))
            if uid and uid not in users:
                users.append(uid)
    return users


def build_cards(rows):
    """Turn ranked rows (either format) into display cards, most central first.

    card = {"idea_id", "title", "title_field", "score", "detail_field", "subs": [{"sub_id", "text", "index"}], "row"}
    """
    cards, seen = [], set()
    for row in rows:
        title_field, title = _first(row, TITLE_FIELDS)
        title = str(title or "").strip() if isinstance(title, (str, int, float)) else ""
        if not title:
            continue  # nothing to show
        # No ID? Derive one from the title, so it stays the same if the file is reordered.
        idea_id = str(row.get("idea_id") or row.get("id") or "idea_" + hashlib.sha1(title.encode("utf-8")).hexdigest()[:8])
        while idea_id in seen:
            idea_id += "_dup"
        seen.add(idea_id)

        detail_field, details = _first(row, DETAIL_FIELDS)
        if isinstance(details, str):
            details = [details]
        subs, sub_ids = [], set()
        for i, item in enumerate(details or []):
            text = str(item).strip() if isinstance(item, (str, int, float)) else ""
            if not text:
                continue
            sub_id = f"{idea_id}::{hashlib.sha1(text.encode('utf-8')).hexdigest()[:8]}"
            while sub_id in sub_ids:
                sub_id += "-2"
            sub_ids.add(sub_id)
            subs.append({"sub_id": sub_id, "text": text, "index": i})

        _, score = _first(row, SCORE_FIELDS)
        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 0.0
        cards.append({"idea_id": idea_id, "title": title, "title_field": title_field, "score": score,
                      "detail_field": detail_field if subs else None, "subs": subs, "row": row})
    cards.sort(key=lambda c: c["score"], reverse=True)  # stable: equal scores keep file order
    return cards


# ---------- Review state ----------
# A plain dict so it can live in Streamlit's session_state:
# {"ideas": {idea_id: {"on", "removed"}}, "subs": {sub_id: {"on", "removed"}}, "undo": None | {...}}

def new_state(cards):
    return {
        "ideas": {c["idea_id"]: {"on": True, "removed": False} for c in cards},
        "subs": {s["sub_id"]: {"on": True, "removed": False} for c in cards for s in c["subs"]},
        "undo": None,
    }


def live_subs(state, card):
    """The card's details that haven't been removed."""
    return [s for s in card["subs"] if not state["subs"][s["sub_id"]]["removed"]]


def idea_status(state, card):
    """'all', 'some' or 'none': what the main checkbox shows (checked / partly / unchecked)."""
    if not state["ideas"][card["idea_id"]]["on"]:
        return "none"
    live = live_subs(state, card)
    on = sum(state["subs"][s["sub_id"]]["on"] for s in live)
    if not live or on == len(live):
        return "all"
    return "some" if on else "none"


def sub_is_on(state, card, sub_id):
    """Whether a detail is actually included (its main idea must be included too)."""
    return state["ideas"][card["idea_id"]]["on"] and state["subs"][sub_id]["on"]


def _settle(state, card):
    """Mirror rules: an idea whose details have all been removed is removed too, and an
    included idea whose remaining details are all unchecked becomes unchecked."""
    idea = state["ideas"][card["idea_id"]]
    live = live_subs(state, card)
    if card["subs"] and not live:
        idea["removed"] = True
    elif idea["on"] and live and not any(state["subs"][s["sub_id"]]["on"] for s in live):
        idea["on"] = False


def toggle_idea(state, card):
    state["undo"] = None
    idea = state["ideas"][card["idea_id"]]
    if idea["on"]:
        idea["on"] = False  # the details keep their own ticks, so re-checking restores them
        return
    idea["on"] = True
    live = live_subs(state, card)
    if live and not any(state["subs"][s["sub_id"]]["on"] for s in live):
        for s in live:
            state["subs"][s["sub_id"]]["on"] = True


def toggle_sub(state, card, sub_id):
    state["undo"] = None
    idea = state["ideas"][card["idea_id"]]
    if not idea["on"]:
        # Checking a detail of an unchecked idea brings the idea back with just this detail.
        idea["on"] = True
        for s in live_subs(state, card):
            state["subs"][s["sub_id"]]["on"] = s["sub_id"] == sub_id
        return
    sub = state["subs"][sub_id]
    sub["on"] = not sub["on"]
    _settle(state, card)


def _snapshot(state):
    return {"ideas": copy.deepcopy(state["ideas"]), "subs": copy.deepcopy(state["subs"])}


def remove_idea(state, card):
    snap = _snapshot(state)
    state["ideas"][card["idea_id"]]["removed"] = True
    state["undo"] = {"kind": "idea", "id": card["idea_id"], "label": card["title"], "snapshot": snap}


def remove_sub(state, card, sub_id):
    snap = _snapshot(state)
    state["subs"][sub_id]["removed"] = True
    _settle(state, card)
    if state["ideas"][card["idea_id"]]["removed"]:
        # That was its last detail, so the whole idea goes. Undo brings back both.
        state["undo"] = {"kind": "idea", "id": card["idea_id"], "label": card["title"], "snapshot": snap}
        return
    text = next(s["text"] for s in card["subs"] if s["sub_id"] == sub_id)
    state["undo"] = {"kind": "sub", "id": sub_id, "idea_id": card["idea_id"], "label": text, "snapshot": snap}


def undo(state):
    """Put back the latest removal exactly as it was."""
    if state.get("undo"):
        state["ideas"] = state["undo"]["snapshot"]["ideas"]
        state["subs"] = state["undo"]["snapshot"]["subs"]
    state["undo"] = None


def restore_all(state, cards):
    """Bring back every removed idea (offered when nothing is left on the page).
    Details removed on purpose stay removed, unless the idea went because all of its
    details were removed: then its details come back with it."""
    for c in cards:
        state["ideas"][c["idea_id"]]["removed"] = False
        if c["subs"] and not live_subs(state, c):
            for s in c["subs"]:
                state["subs"][s["sub_id"]]["removed"] = False
        _settle(state, c)
    state["undo"] = None


def visible_cards(state, cards):
    """Cards to draw: not removed, or removed just now (shown as 'Removed · Undo')."""
    pending = (state.get("undo") or {}).get("id")
    return [c for c in cards if not state["ideas"][c["idea_id"]]["removed"] or c["idea_id"] == pending]


def counts(state, cards):
    """(ideas included, details included)."""
    ideas = details = 0
    for c in cards:
        flags = state["ideas"][c["idea_id"]]
        if flags["removed"] or not flags["on"]:
            continue
        ideas += 1
        details += sum(state["subs"][s["sub_id"]]["on"] for s in live_subs(state, c))
    return ideas, details


def removed_count(state, cards):
    return sum(state["ideas"][c["idea_id"]]["removed"] for c in cards)


# ---------- Output ----------

def approved_rows(state, cards):
    """The rows Step 5 will read: included ideas only, in rank order, in the input's own format.
    Each row holds the title and only the details the user kept, plus bookkeeping fields
    (METADATA_FIELDS). Nothing the user didn't see on the page is copied, raw_text included."""
    rows = []
    for c in cards:
        flags = state["ideas"][c["idea_id"]]
        if flags["removed"] or not flags["on"]:
            continue
        row = {k: copy.deepcopy(v) for k, v in c["row"].items() if k in METADATA_FIELDS}
        row["idea_id"] = c["idea_id"]
        row[c["title_field"]] = c["row"][c["title_field"]]
        if c["detail_field"]:
            keep = {s["index"] for s in live_subs(state, c) if state["subs"][s["sub_id"]]["on"]}
            original = c["row"][c["detail_field"]]
            original = [original] if isinstance(original, str) else original
            row[c["detail_field"]] = [x for i, x in enumerate(original) if i in keep]
        rows.append(row)
    return rows


def review_record(state, cards):
    """IDs only (no text) of what the user changed and what they approved. Lets the page
    restore their choices next time and tell whether the current choices are saved."""
    rec = {"ideas_off": [], "ideas_removed": [], "details_off": [], "details_removed": [], "approved": {}}
    for c in cards:
        flags = state["ideas"][c["idea_id"]]
        if flags["removed"]:
            rec["ideas_removed"].append(c["idea_id"])
        elif not flags["on"]:
            rec["ideas_off"].append(c["idea_id"])
        else:
            rec["approved"][c["idea_id"]] = [s["sub_id"] for s in live_subs(state, c) if state["subs"][s["sub_id"]]["on"]]
        for s in c["subs"]:
            if state["subs"][s["sub_id"]]["removed"]:
                rec["details_removed"].append(s["sub_id"])
            elif not state["subs"][s["sub_id"]]["on"]:
                rec["details_off"].append(s["sub_id"])
    return rec


def apply_record(state, record, cards):
    """Restore earlier choices onto a fresh state. Ideas that are new since then stay included."""
    for idea_id in record.get("ideas_off", []):
        if idea_id in state["ideas"]:
            state["ideas"][idea_id]["on"] = False
    for idea_id in record.get("ideas_removed", []):
        if idea_id in state["ideas"]:
            state["ideas"][idea_id]["removed"] = True
    for sub_id in record.get("details_off", []):
        if sub_id in state["subs"]:
            state["subs"][sub_id]["on"] = False
    for sub_id in record.get("details_removed", []):
        if sub_id in state["subs"]:
            state["subs"][sub_id]["removed"] = True
    for c in cards:
        _settle(state, c)
    state["undo"] = None
    return state


def _approved_file(user_id, approved_dir):
    _check_user_id(user_id)
    return Path(approved_dir) / f"{user_id}.json"


def load_saved_record(user_id, approved_dir=APPROVED_DIR):
    """The review record from the user's last save, or None."""
    path = _approved_file(user_id, approved_dir)
    if not path.exists():
        return None
    data = _read_json(path)
    return data.get("review") if isinstance(data, dict) and data.get("user_id") == user_id else None


def start_state(user_id, cards, approved_dir=APPROVED_DIR):
    """A fresh state, with the user's earlier choices applied if they saved before."""
    state = new_state(cards)
    record = load_saved_record(user_id, approved_dir)
    return apply_record(state, record, cards) if record else state


def _write_json(path, data):
    """Write the whole file or nothing (a half-written file is never left behind)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def rebuild_matching_file(approved_dir=APPROVED_DIR, matching_file=MATCHING_FILE):
    """Combine every user's approved ideas into the one file Step 5 reads.
    A damaged file from one user is skipped, so it can't block everyone else's save."""
    rows = []
    for path in sorted(Path(approved_dir).glob("*.json")):
        try:
            data = _read_json(path)
        except (ReviewError, OSError):
            continue
        if not isinstance(data, dict) or not data.get("user_id"):
            continue
        uid = data["user_id"]
        rows += [r for r in _rows_in(data) if str(r.get("user_id", uid)) == uid]
    _write_json(Path(matching_file), {
        "_note": "Written by Step 4 (review page). Only ideas users approved. Step 5 reads this file.",
        "ideas": rows,
    })
    return len(rows)


def save_approved(user_id, state, cards, approved_dir=APPROVED_DIR, matching_file=MATCHING_FILE, now=None):
    """Save what the user approved, then refresh the combined file for Step 5.
    Returns {"ideas": n, "details": n, "path": Path}."""
    path = _approved_file(user_id, approved_dir)
    for c in cards:
        if str(c["row"].get("user_id", user_id)) != user_id:
            raise ReviewError("wrong_owner", "These ideas belong to a different user.")
    rows = [dict(r, user_id=user_id) for r in approved_rows(state, cards)]
    try:
        _write_json(path, {
            "schema_version": SCHEMA_VERSION,
            "user_id": user_id,
            "approved_at": now or _now_utc(),
            "ideas": rows,
            "review": review_record(state, cards),
        })
        rebuild_matching_file(approved_dir, matching_file)
    except OSError:
        raise ReviewError("save_failed", "Couldn't save your choices. Please try again.")
    ideas, details = counts(state, cards)
    return {"ideas": ideas, "details": details, "path": path}
