"""Step 1 — Data Collection (context import).

Turns a ChatGPT export (or pasted text, or the synthetic demo history) into
"Private Source Context": one record per conversation, owned by one user, with
message roles, order, timestamps and provenance kept.

Importing never publishes anything. Records are saved to data/sources/<user_id>.json
at the repo root, which is git-ignored. Step 2 (Noise Filter) reads them from there.

Imported chats are untrusted data: we copy their text, we never act on it.
"""

import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

STEP_DIR = Path(__file__).resolve().parent
REPO_ROOT = STEP_DIR.parent
SOURCES_DIR = REPO_ROOT / "data" / "sources"
DEMO_FIXTURE = STEP_DIR / "samples" / "demo_chatgpt_user_a.json"
DEMO_FIXTURE_OWNER = "user_a"

SCHEMA_VERSION = "1.0"
ROLE_LABELS = {"user": "User", "assistant": "Assistant"}


class ImportFailed(Exception):
    """A clear, user-safe import error. Never includes private chat text."""

    def __init__(self, code, message, retryable=False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable

    def as_dict(self):
        return {"code": self.code, "message": self.message, "retryable": self.retryable}


def _now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso(epoch):
    if epoch is None:
        return None
    return datetime.fromtimestamp(float(epoch), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _source_id(user_id, source_type, original_id):
    # The demo history keeps the shared fixture IDs (a_s01 …) so every step can refer to them.
    if source_type == "demo":
        return original_id
    digest = hashlib.sha1(f"{user_id}|{source_type}|{original_id}".encode("utf-8")).hexdigest()
    return "src_" + digest[:12]


def build_raw_text(messages):
    """Role-labelled text, in order, e.g. 'User: …\n\nAssistant: …'."""
    return "\n\n".join(f"{ROLE_LABELS[m['role']]}: {m['text']}" for m in messages)


def _make_source(user_id, source_type, original_id, title, created_at, messages, imported_at):
    return {
        "user_id": user_id,
        "source_id": _source_id(user_id, source_type, original_id or title),
        "source_type": source_type,
        "messages": messages,
        "raw_text": build_raw_text(messages),
        "provenance": {
            "original_conversation_id": original_id,
            "title": title,
            "created_at": created_at,
            "imported_at": imported_at,
            "message_ids": [m["message_id"] for m in messages],
            "derived_from_source_id": None,
        },
    }


# ---------- ChatGPT export ----------

def _load_export_json(file_bytes, filename):
    name = (filename or "").lower()
    if name.endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                candidates = [n for n in zf.namelist() if n.split("/")[-1] == "conversations.json"]
                if not candidates:
                    raise ImportFailed(
                        "missing_conversations_json",
                        "This zip has no conversations.json. Upload the zip ChatGPT emailed you, "
                        "or the conversations.json file inside it.",
                    )
                file_bytes = zf.read(candidates[0])
        except zipfile.BadZipFile:
            raise ImportFailed("bad_zip", "This file isn't a readable zip archive.")
    elif not name.endswith(".json"):
        raise ImportFailed(
            "unsupported_file_type",
            "Unsupported file. Upload a ChatGPT export (.zip) or its conversations.json.",
        )
    try:
        return json.loads(file_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ImportFailed("malformed_json", "This file isn't valid JSON, so it can't be a ChatGPT export.")


def _selected_branch(mapping, current_node):
    """Walk from the selected leaf up to the root: the branch the user last saw.

    Edited questions and regenerated answers leave other branches in the tree; we skip them.
    """
    if current_node not in mapping:
        # Fallback: the most recent leaf.
        leaves = [n for n in mapping.values() if not n.get("children")]
        if not leaves:
            return []
        current_node = max(leaves, key=lambda n: ((n.get("message") or {}).get("create_time") or 0))["id"]
    path, node_id, seen = [], current_node, set()
    while node_id and node_id in mapping and node_id not in seen:
        seen.add(node_id)
        path.append(mapping[node_id])
        node_id = mapping[node_id].get("parent")
    return list(reversed(path))


def _message_text(message):
    parts = (message.get("content") or {}).get("parts") or []
    return "\n".join(p.strip() for p in parts if isinstance(p, str) and p.strip())


def _parse_chatgpt_conversation(conv):
    mapping = conv.get("mapping")
    if not isinstance(mapping, dict):
        return None
    messages = []
    for node in _selected_branch(mapping, conv.get("current_node")):
        msg = node.get("message")
        if not msg:
            continue
        role = (msg.get("author") or {}).get("role")
        if role not in ROLE_LABELS:  # skip system and tool messages
            continue
        if (msg.get("metadata") or {}).get("is_visually_hidden_from_conversation"):
            continue
        text = _message_text(msg)
        if not text:
            continue
        messages.append({
            "message_id": msg.get("id") or node.get("id"),
            "role": role,
            "text": text,
            "created_at": _iso(msg.get("create_time")),
        })
    return messages


def import_chatgpt_export(file_bytes, filename, user_id, source_type="chatgpt_json", imported_at=None):
    """Parse a ChatGPT export. Returns (sources, skipped) where skipped lists
    {title, reason} for conversations with nothing usable."""
    if not user_id:
        raise ImportFailed("missing_user", "Sign in before importing chats.")
    data = _load_export_json(file_bytes, filename)
    if isinstance(data, dict) and "mapping" in data:
        data = [data]  # a single conversation
    if not isinstance(data, list) or not all(isinstance(c, dict) for c in data):
        raise ImportFailed("not_a_chatgpt_export", "This JSON doesn't look like a ChatGPT conversations export.")
    if not data:
        raise ImportFailed("empty_export", "This export contains no conversations.")

    imported_at = imported_at or _now_utc()
    sources, skipped, seen_ids = [], [], set()
    for conv in data:
        title = (conv.get("title") or "Untitled conversation").strip()
        messages = _parse_chatgpt_conversation(conv)
        if messages is None:
            skipped.append({"title": title, "reason": "not in ChatGPT conversation format"})
            continue
        if not messages:
            skipped.append({"title": title, "reason": "no user or assistant messages"})
            continue
        original_id = conv.get("conversation_id") or conv.get("id")
        source = _make_source(user_id, source_type, original_id, title,
                              _iso(conv.get("create_time")), messages, imported_at)
        if source["source_id"] in seen_ids:
            skipped.append({"title": title, "reason": "duplicate conversation in this export"})
            continue
        seen_ids.add(source["source_id"])
        sources.append(source)

    if not sources:
        raise ImportFailed("nothing_importable", "No conversations in this export had any messages to import.")
    return sources, skipped


def import_demo_history(user_id, imported_at=None):
    """Load the synthetic demo history. Only the demo researcher it was written for may use it."""
    if user_id != DEMO_FIXTURE_OWNER:
        raise ImportFailed("demo_not_available", f"The demo history belongs to the demo account {DEMO_FIXTURE_OWNER}.")
    return import_chatgpt_export(DEMO_FIXTURE.read_bytes(), DEMO_FIXTURE.name, user_id,
                                 source_type="demo", imported_at=imported_at)


# ---------- Pasted text ----------

_SPEAKER = re.compile(r"^\s*(user|you|me|human|assistant|chatgpt|gpt|claude|ai|gemini)\s*:\s?(.*)$", re.IGNORECASE)
_USER_WORDS = {"user", "you", "me", "human"}


def import_pasted_text(text, user_id, title=None, imported_at=None):
    """One pasted conversation. Lines starting 'User:' / 'Assistant:' (or ChatGPT:, Claude:, …)
    start a new turn; if there are no labels, the whole text counts as one user message."""
    if not user_id:
        raise ImportFailed("missing_user", "Sign in before importing chats.")
    text = (text or "").strip()
    if not text:
        raise ImportFailed("empty_paste", "Paste a conversation first.")

    turns = []
    for line in text.splitlines():
        match = _SPEAKER.match(line)
        if match:
            role = "user" if match.group(1).lower() in _USER_WORDS else "assistant"
            turns.append([role, [match.group(2)]])
        elif turns:
            turns[-1][1].append(line)
        else:
            turns.append(["user", [line]])

    imported_at = imported_at or _now_utc()
    original_id = "paste_" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    messages = []
    for i, (role, lines) in enumerate(turns):
        body = "\n".join(lines).strip()
        if body:
            messages.append({"message_id": f"{original_id}-m{i:02d}", "role": role, "text": body, "created_at": None})
    if not messages:
        raise ImportFailed("empty_paste", "The pasted text has no message content.")

    title = (title or "").strip() or messages[0]["text"][:60]
    return [_make_source(user_id, "pasted_text", original_id, title, None, messages, imported_at)], []


# ---------- Private storage ----------

def _sources_file(user_id, sources_dir):
    if not re.match(r"^[A-Za-z0-9_]+$", user_id or ""):
        raise ImportFailed("invalid_user", "Unknown user.")
    return Path(sources_dir) / f"{user_id}.json"


def load_sources(user_id, sources_dir=SOURCES_DIR):
    path = _sources_file(user_id, sources_dir)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)["sources"]


def save_sources(user_id, new_sources, sources_dir=SOURCES_DIR):
    """Add sources to the owner's private store. Re-importing the same conversation
    replaces the earlier copy instead of duplicating it. Returns all of the owner's sources."""
    for s in new_sources:
        if s["user_id"] != user_id:
            raise ImportFailed("wrong_owner", "These chats belong to a different user.")
    by_id = {s["source_id"]: s for s in load_sources(user_id, sources_dir)}
    for s in new_sources:
        by_id[s["source_id"]] = s
    sources = sorted(by_id.values(), key=lambda s: s["source_id"])

    path = _sources_file(user_id, sources_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"schema_version": SCHEMA_VERSION, "user_id": user_id, "sources": sources},
                  f, indent=2, ensure_ascii=False)
    tmp.replace(path)
    return sources
