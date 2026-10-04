"""Messages between two people who both said yes to their match. Used by the Messages page
(a placeholder for Step 6's own chat, see the mockups in 6 - Matching Interface/).

Rules:
  • Only a connected pair (both chose "connect" in data/match_status.json) can message each
    other. If either later passes, the conversation is closed and hidden.
  • Conversations are keyed by the pair of users (like match decisions), so they survive
    re-running Step 5.
  • Messages are stored on this laptop only, in data/messages.json (git-ignored).

File format:
  {"<user_a>|<user_b>": {"messages": [{"from": user_id, "text": str, "at": "...Z"}],
                         "read": {user_id: number of messages seen}}}
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from pipeline import matches as mt

MESSAGES_FILE = mt.ROOT / "data" / "messages.json"
USERS_FILE = mt.ROOT / "data" / "users.json"
MAX_LENGTH = 2000  # characters per message

_lock = threading.Lock()  # one app serves every browser window; write one message at a time


class MessageError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _load(messages_file):
    return mt._read(messages_file, {})


def _save(data, messages_file):
    path = Path(messages_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def is_connected(user_id, other_id, status_file=mt.STATUS_FILE):
    decisions = mt.load_status(status_file).get(mt.pair_key(user_id, other_id), {}).get("decisions", {})
    return decisions.get(user_id) == "connect" and decisions.get(other_id) == "connect"


def _names(users_file):
    users = mt._read(users_file, [])
    return {u["user_id"]: u.get("pseudonym") or "A researcher" for u in users if u.get("user_id")}


def conversations(user_id, status_file=mt.STATUS_FILE, messages_file=MESSAGES_FILE, users_file=USERS_FILE,
                  matches_file=mt.MATCHES_FILE, ideas_file=mt.IDEAS_FILE):
    """Everyone this user is connected with, most recent conversation first. Each item:
    {other_id, other_name, match_type, intro, messages, unread, last_at}."""
    names = _names(users_file)
    current = {m["other_id"]: m for m in mt.my_matches(user_id, matches_file, ideas_file, status_file)}
    data = _load(messages_file)
    out = []
    for key, entry in mt.load_status(status_file).items():
        people = key.split("|")
        if user_id not in people or len(people) != 2:
            continue
        other = people[1] if people[0] == user_id else people[0]
        if not is_connected(user_id, other, status_file):
            continue
        match = current.get(other, {})
        convo = data.get(key, {})
        msgs = convo.get("messages", [])
        seen = convo.get("read", {}).get(user_id, 0)
        out.append({
            "other_id": other,
            "other_name": match.get("other_name") or names.get(other, "A researcher"),
            "match_type": match.get("match_type"),
            "intro": match.get("intro"),
            "messages": msgs,
            "unread": sum(1 for m in msgs[seen:] if m["from"] != user_id),
            "last_at": msgs[-1]["at"] if msgs else entry.get("updated_at", ""),
        })
    return sorted(out, key=lambda c: c["last_at"], reverse=True)


def send(user_id, other_id, text, status_file=mt.STATUS_FILE, messages_file=MESSAGES_FILE):
    """Add a message from user_id to other_id. Only allowed when both said yes."""
    text = (text or "").strip()
    if not text:
        raise MessageError("Write something first.")
    if len(text) > MAX_LENGTH:
        raise MessageError(f"Messages can be at most {MAX_LENGTH} characters.")
    if not is_connected(user_id, other_id, status_file):
        raise MessageError("You can message someone only after you have both said yes.")
    with _lock:
        data = _load(messages_file)
        convo = data.setdefault(mt.pair_key(user_id, other_id), {"messages": [], "read": {}})
        convo["messages"].append({"from": user_id, "text": text,
                                  "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
        convo["read"][user_id] = len(convo["messages"])  # you have seen your own message
        _save(data, messages_file)


def mark_read(user_id, other_id, messages_file=MESSAGES_FILE):
    """Remember that user_id has seen every message in this conversation so far."""
    with _lock:
        data = _load(messages_file)
        convo = data.get(mt.pair_key(user_id, other_id))
        if not convo or convo.get("read", {}).get(user_id) == len(convo["messages"]):
            return
        convo.setdefault("read", {})[user_id] = len(convo["messages"])
        _save(data, messages_file)


def unread_total(user_id, **files):
    return sum(c["unread"] for c in conversations(user_id, **files))
