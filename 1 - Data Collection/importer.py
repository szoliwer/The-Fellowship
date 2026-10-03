"""Step 1 — Data Collection (context import).

Turns what a researcher uploads into "Private Source Context": one record per
conversation, owned by one user, with message roles, order, timestamps and provenance.

Accepted uploads:
  • ChatGPT export: the .zip, or the conversations.json inside it
  • Claude export: the .zip, or the conversations.json inside it
  • A .zip of .md / .txt files: each file is one conversation
  • A single .md or .txt file
  • Pasted text

Everything is stored privately under data/ at the repo root (git-ignored):
  data/uploads/<user_id>/files/…        the original files, exactly as uploaded
  data/uploads/<user_id>/uploads.json   upload history (what, when, result)
  data/sources/<user_id>.json           parsed conversations: what Step 2 reads

Importing never publishes anything. Imported chats are untrusted data: we copy their
text, we never act on it. Errors never include chat text.
"""

import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

STEP_DIR = Path(__file__).resolve().parent
REPO_ROOT = STEP_DIR.parent
DATA_DIR = REPO_ROOT / "data"
# Synthetic demo histories, one per demo researcher (shared brief, section 11).
DEMO_FIXTURES = {
    "user_a": STEP_DIR / "samples" / "demo_chatgpt_user_a.json",
    "user_b": STEP_DIR / "samples" / "demo_chatgpt_user_b.json",
}
DEMO_FIXTURE = DEMO_FIXTURES["user_a"]

# Images and files in chats are never imported; they are marked with these (HANDOFF.md, section 3).
CHATGPT_DIALOGUE_TYPES = {"text", "multimodal_text"}
IMAGE_PLACEHOLDER = "[image omitted]"
FILE_PLACEHOLDER = "[file omitted]"
_MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")

SCHEMA_VERSION = "1.0"
ROLE_LABELS = {"user": "User", "assistant": "Assistant"}

ACCEPTED_EXTENSIONS = ["zip", "json", "md", "markdown", "txt"]
TEXT_EXTENSIONS = {".md", ".markdown", ".txt"}
MAX_UPLOAD_BYTES = 200 * 1024 * 1024        # matches Streamlit's default upload limit
MAX_EXPORT_JSON_BYTES = 500 * 1024 * 1024   # conversations.json inside a zip, uncompressed
MAX_TEXT_FILE_BYTES = 5 * 1024 * 1024
MAX_TEXT_FILES_IN_ZIP = 500
MAX_TEXT_BYTES_IN_ZIP = 100 * 1024 * 1024


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


def _iso_from_epoch(epoch):
    if epoch is None:
        return None
    return datetime.fromtimestamp(float(epoch), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_from_string(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _source_id(user_id, source_type, original_id):
    # The demo history keeps the shared fixture IDs (a_s01 …) so every step can refer to them.
    if source_type == "demo":
        return original_id
    digest = hashlib.sha1(f"{user_id}|{source_type}|{original_id}".encode("utf-8")).hexdigest()
    return "src_" + digest[:12]


def build_raw_text(messages):
    """Role-labelled text, in order, e.g. 'User: …\n\nAssistant: …'."""
    return "\n\n".join(f"{ROLE_LABELS[m['role']]}: {m['text']}" for m in messages)


def _make_source(user_id, source_type, original_id, title, created_at, messages, imported_at, upload_id=None):
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
            "upload_id": upload_id,
        },
    }


def _require_user(user_id):
    if not user_id:
        raise ImportFailed("missing_user", "Log in before importing chats.")


# ---------- ChatGPT export ----------

def _selected_branch(mapping, current_node):
    """Walk from the selected leaf up to the root: the branch the user last saw.

    Edited questions and regenerated answers leave other branches in the tree; we skip them.
    """
    if current_node not in mapping:
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


def _chatgpt_messages(conv):
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
        # Only real dialogue: plain text, or text with images. Hidden reasoning ("thoughts",
        # "reasoning_recap"), code/tool calls and custom-instruction records are never imported.
        if (msg.get("content") or {}).get("content_type") not in CHATGPT_DIALOGUE_TYPES:
            continue
        parts = (msg.get("content") or {}).get("parts") or []
        pieces = []
        for p in parts:
            if isinstance(p, str):
                if p.strip():
                    pieces.append(p.strip())
            elif isinstance(p, dict):  # an uploaded image or file: we never import its contents
                kind = str(p.get("content_type", ""))
                pieces.append(IMAGE_PLACEHOLDER if "image" in kind else FILE_PLACEHOLDER)
        for a in (msg.get("metadata") or {}).get("attachments") or []:
            if isinstance(a, dict) and not str(a.get("mime_type", "")).startswith("image/"):
                pieces.append(FILE_PLACEHOLDER)
        text = "\n".join(pieces)
        if not text:
            continue
        messages.append({
            "message_id": msg.get("id") or node.get("id"),
            "role": role,
            "text": text,
            "created_at": _iso_from_epoch(msg.get("create_time")),
        })
    return messages


def _chatgpt_conversation_info(conv):
    return (conv.get("conversation_id") or conv.get("id"),
            (conv.get("title") or "").strip(),
            _iso_from_epoch(conv.get("create_time")))


# ---------- Claude export ----------

_CLAUDE_ROLES = {"human": "user", "assistant": "assistant"}


def _claude_messages(conv):
    raw = conv.get("chat_messages")
    if not isinstance(raw, list):
        return None
    messages = []
    for i, msg in enumerate(raw):
        if not isinstance(msg, dict):
            continue
        role = _CLAUDE_ROLES.get(msg.get("sender"))
        if not role:
            continue
        text = (msg.get("text") or "").strip()
        if not text:
            blocks = msg.get("content") or []
            text = "\n".join(b["text"].strip() for b in blocks
                             if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str)
                             and b["text"].strip())
        # Attached files and images: we never import their contents, only mark that they were there.
        placeholders = [FILE_PLACEHOLDER for a in msg.get("attachments") or [] if isinstance(a, dict)]
        placeholders += [IMAGE_PLACEHOLDER if f.get("file_kind") == "image" else FILE_PLACEHOLDER
                         for f in msg.get("files") or [] if isinstance(f, dict)]
        text = "\n".join([t for t in [text] if t] + placeholders)
        if not text:
            continue
        messages.append({
            "message_id": msg.get("uuid") or f"{conv.get('uuid', 'claude')}-m{i:03d}",
            "role": role,
            "text": text,
            "created_at": _iso_from_string(msg.get("created_at")),
        })
    return messages


def _claude_conversation_info(conv):
    return conv.get("uuid"), (conv.get("name") or "").strip(), _iso_from_string(conv.get("created_at"))


# ---------- Export files (ChatGPT or Claude conversations.json) ----------

def _parse_export_json(file_bytes, user_id, imported_at, upload_id, demo=False):
    try:
        data = json.loads(file_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ImportFailed("malformed_json", "This file isn't valid JSON, so it can't be a chat export.")
    if isinstance(data, dict) and ("mapping" in data or "chat_messages" in data):
        data = [data]  # a single conversation
    if not isinstance(data, list) or not all(isinstance(c, dict) for c in data):
        raise ImportFailed("not_a_chat_export", "This JSON doesn't look like a ChatGPT or Claude conversations export.")
    if not data:
        raise ImportFailed("empty_export", "This export contains no conversations.")

    if any("mapping" in c for c in data):
        source_type, get_messages, get_info = "chatgpt_json", _chatgpt_messages, _chatgpt_conversation_info
    elif any("chat_messages" in c for c in data):
        source_type, get_messages, get_info = "claude_json", _claude_messages, _claude_conversation_info
    else:
        raise ImportFailed("not_a_chat_export", "This JSON doesn't look like a ChatGPT or Claude conversations export.")
    if demo:
        source_type = "demo"

    sources, skipped, seen_ids = [], [], set()
    for conv in data:
        original_id, title, created_at = get_info(conv)
        title = title or "Untitled conversation"
        messages = get_messages(conv)
        if messages is None:
            skipped.append({"title": title, "reason": "not in the expected conversation format"})
            continue
        if not messages:
            skipped.append({"title": title, "reason": "no user or assistant messages"})
            continue
        source = _make_source(user_id, source_type, original_id, title, created_at, messages, imported_at, upload_id)
        if source["source_id"] in seen_ids:
            skipped.append({"title": title, "reason": "duplicate conversation in this export"})
            continue
        seen_ids.add(source["source_id"])
        sources.append(source)
    return sources, skipped


# ---------- Markdown / plain text ----------

_USER_LABELS = r"user|you|me|human"
_ASSISTANT_LABELS = r"assistant|chatgpt|gpt(?:-[\w.]+)?|claude|ai|gemini|copilot"
_SUFFIX = r"(?:\s+(?:said|asked|response|replied|wrote|answered))?"  # "You said", "you asked", "ChatGPT response"
_LABEL = rf"(?P<label>{_USER_LABELS}|{_ASSISTANT_LABELS}){_SUFFIX}"
# Only accepted as a heading or a bold line on its own, never mid-sentence ("Response: …" is often prose).
_LABEL_STANDALONE = rf"(?P<label>{_USER_LABELS}|{_ASSISTANT_LABELS}|prompt|response){_SUFFIX}"
_B = r"(?:\*\*|__)?"  # optional bold markers
# "## User", "### **ChatGPT**", "#### You said:", "# you asked", "# chatgpt response", "## Prompt:"
_HEADING_LABEL = re.compile(rf"^\s*#{{1,6}}\s*{_B}\s*{_LABEL_STANDALONE}\s*:?\s*{_B}\s*:?\s*$", re.IGNORECASE)
# "User: hi", "**You:** hi", "**Claude**: hi", "> **User:** hi", "You said:"
_INLINE_LABEL = re.compile(rf"^\s*(?:>\s*)?{_B}\s*{_LABEL}\s*{_B}\s*:\s*{_B}\s*(?P<rest>.*)$", re.IGNORECASE)
# "**ChatGPT**" or "**Response:**" alone on a line
_BOLD_LABEL = re.compile(rf"^\s*(?:\*\*|__)\s*{_LABEL_STANDALONE}\s*:?\s*(?:\*\*|__)\s*:?\s*$", re.IGNORECASE)
_TITLE_HEADING = re.compile(r"^\s*#\s+(?P<title>.+?)\s*$")
# Export-tool metadata: "message time: 2026-03-31 11:23:00" under a speaker label,
# and a "> From: https://chatgpt.com/…" source line at the top.
_MESSAGE_TIME = re.compile(r"^\s*(?:\*\*|_)?message time:?(?:\*\*|_)?\s*:?\s*(?P<time>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?)\s*$",
                           re.IGNORECASE)
_SOURCE_LINE = re.compile(r"^\s*>\s*(?:From|Source):\s*https?://\S+\s*$", re.IGNORECASE)


def _speaker(line):
    for pattern in (_HEADING_LABEL, _BOLD_LABEL, _INLINE_LABEL):
        m = pattern.match(line)
        if m:
            label = m.group("label").lower()
            role = "user" if re.fullmatch(_USER_LABELS, label) or label == "prompt" else "assistant"
            rest = m.groupdict().get("rest") or ""
            return role, rest
    return None


def _decode_text(file_bytes):
    if b"\x00" in file_bytes[:4096]:
        raise ImportFailed("not_text", "This doesn't look like a text or Markdown file.")
    try:
        return file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")


def parse_text_conversation(text, fallback_title):
    """Split text into turns using speaker labels. Returns (title, [(role, text, created_at), …]).
    Text without any labels counts as one user message (the person's own notes)."""
    text = _MARKDOWN_IMAGE.sub(IMAGE_PLACEHOLDER, text)  # ![alt](link) → [image omitted]
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    # Skip Markdown front matter (--- … ---) that some export tools add.
    if lines and lines[0].strip() == "---":
        for i in range(1, min(len(lines), 60)):
            if lines[i].strip() == "---":
                lines = lines[i + 1:]
                break

    title = None
    turns = []  # [role, body_lines, created_at]
    for line in lines:
        speaker = _speaker(line)
        if speaker:
            role, rest = speaker
            turns.append([role, [rest] if rest else [], None])
        elif turns:
            turn = turns[-1]
            time = _MESSAGE_TIME.match(line)
            if time and turn[2] is None and not any(l.strip() for l in turn[1]):
                turn[2] = _iso_from_string(time.group("time"))  # time of day as written (zone unknown)
            else:
                turn[1].append(line)
        elif not line.strip() or _SOURCE_LINE.match(line):
            continue  # blank lines or an export tool's source link before any content
        elif title is None and _TITLE_HEADING.match(line):
            title = _TITLE_HEADING.match(line).group("title").strip("*_ ")
        else:
            turns.append(["user", [line], None])  # text before any label counts as the user's own

    messages = []
    for role, body_lines, created_at in turns:
        body = "\n".join(body_lines).strip()
        body = re.sub(r"\n\s*(?:---|\*\*\*|___)\s*$", "", body).strip()  # trailing separator lines
        if body and not re.fullmatch(r"[-*_\s]+", body):
            messages.append((role, body, created_at))
    return (title or fallback_title), messages


def _text_source(file_bytes, original_id, fallback_title, user_id, source_type, imported_at, upload_id):
    text = _decode_text(file_bytes)
    title, turns = parse_text_conversation(text, fallback_title)
    if not turns:
        return None
    base = "t_" + hashlib.sha1(f"{original_id}".encode("utf-8")).hexdigest()[:10]
    messages = [{"message_id": f"{base}-m{i:03d}", "role": role, "text": body, "created_at": created_at}
                for i, (role, body, created_at) in enumerate(turns)]
    return _make_source(user_id, source_type, original_id, title, messages[0]["created_at"],
                        messages, imported_at, upload_id)


# ---------- Uploads ----------

def _is_hidden_or_system(path):
    parts = PurePosixPath(path).parts
    return any(p.startswith(".") or p == "__MACOSX" for p in parts)


def _parse_zip(file_bytes, user_id, imported_at, upload_id):
    try:
        zf = zipfile.ZipFile(io.BytesIO(file_bytes))
    except zipfile.BadZipFile:
        raise ImportFailed("bad_zip", "This file isn't a readable zip archive.")
    with zf:
        members = [m for m in zf.infolist() if not m.is_dir() and not _is_hidden_or_system(m.filename)]

        exports = [m for m in members if PurePosixPath(m.filename).name == "conversations.json"]
        if exports:
            member = exports[0]
            if member.file_size > MAX_EXPORT_JSON_BYTES:
                raise ImportFailed("too_large", "The conversations.json in this zip is too large to import.")
            return _parse_export_json(zf.read(member), user_id, imported_at, upload_id)

        sources, skipped, total = [], [], 0
        text_members = [m for m in members if PurePosixPath(m.filename).suffix.lower() in TEXT_EXTENSIONS]
        for m in members:
            if m not in text_members:
                skipped.append({"title": m.filename, "reason": "not a .md or .txt file"})
        if len(text_members) > MAX_TEXT_FILES_IN_ZIP:
            for m in text_members[MAX_TEXT_FILES_IN_ZIP:]:
                skipped.append({"title": m.filename, "reason": f"over the {MAX_TEXT_FILES_IN_ZIP}-file limit"})
            text_members = text_members[:MAX_TEXT_FILES_IN_ZIP]
        for m in text_members:
            if m.file_size > MAX_TEXT_FILE_BYTES:
                skipped.append({"title": m.filename, "reason": "file too large (over 5 MB)"})
                continue
            total += m.file_size
            if total > MAX_TEXT_BYTES_IN_ZIP:
                skipped.append({"title": m.filename, "reason": "zip's total text limit reached"})
                continue
            try:
                source = _text_source(zf.read(m), m.filename, PurePosixPath(m.filename).stem,
                                      user_id, "text_file", imported_at, upload_id)
            except ImportFailed as e:
                skipped.append({"title": m.filename, "reason": e.message})
                continue
            if source is None:
                skipped.append({"title": m.filename, "reason": "empty file"})
            else:
                sources.append(source)
        if not sources and not skipped:
            raise ImportFailed("empty_zip", "This zip has no files in it.")
        return sources, skipped


def parse_upload(file_bytes, filename, user_id, imported_at=None, upload_id=None):
    """Turn one uploaded file into sources. Returns (sources, skipped)."""
    _require_user(user_id)
    imported_at = imported_at or _now_utc()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ImportFailed("too_large", "This file is over the 200 MB upload limit.")
    if not file_bytes:
        raise ImportFailed("empty_file", "This file is empty.")
    suffix = PurePosixPath(filename or "").suffix.lower()

    if suffix == ".zip":
        sources, skipped = _parse_zip(file_bytes, user_id, imported_at, upload_id)
    elif suffix == ".json":
        sources, skipped = _parse_export_json(file_bytes, user_id, imported_at, upload_id)
    elif suffix in TEXT_EXTENSIONS:
        source = _text_source(file_bytes, filename, PurePosixPath(filename).stem,
                              user_id, "text_file", imported_at, upload_id)
        if source is None:
            raise ImportFailed("empty_file", "This file has no text in it.")
        sources, skipped = [source], []
    else:
        raise ImportFailed(
            "unsupported_file_type",
            "Unsupported file. Upload a ChatGPT or Claude export (.zip or conversations.json), "
            "or a .md / .txt file, or a .zip of those.",
        )
    if not sources:
        raise ImportFailed("nothing_importable", "Nothing in this upload had any messages to import.")
    return sources, skipped


def parse_pasted_text(text, user_id, title=None, imported_at=None):
    """One pasted conversation. Same speaker labels as .md/.txt files."""
    _require_user(user_id)
    text = (text or "").strip()
    if not text:
        raise ImportFailed("empty_paste", "Paste a conversation first.")
    imported_at = imported_at or _now_utc()
    original_id = "paste_" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    parsed_title, turns = parse_text_conversation(text, None)
    if not turns:
        raise ImportFailed("empty_paste", "The pasted text has no message content.")
    title = (title or "").strip() or parsed_title or turns[0][1][:60]
    messages = [{"message_id": f"{original_id}-m{i:03d}", "role": role, "text": body, "created_at": created_at}
                for i, (role, body, created_at) in enumerate(turns)]
    return [_make_source(user_id, "pasted_text", original_id, title, messages[0]["created_at"],
                         messages, imported_at)], []


def parse_demo_history(user_id, imported_at=None):
    """A synthetic demo history. Only the demo researcher it was written for may load it."""
    _require_user(user_id)
    if user_id not in DEMO_FIXTURES:
        raise ImportFailed("demo_not_available", "Demo histories are only available to the demo researchers.")
    return _parse_export_json(DEMO_FIXTURES[user_id].read_bytes(), user_id, imported_at or _now_utc(),
                              None, demo=True)


# ---------- Private storage ----------

def _user_dir(kind, user_id, data_dir):
    if not re.fullmatch(r"[A-Za-z0-9_]+", user_id or ""):
        raise ImportFailed("invalid_user", "Unknown user.")
    return Path(data_dir) / kind / user_id


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def load_sources(user_id, data_dir=DATA_DIR):
    path = _user_dir("sources", user_id, data_dir).with_suffix(".json")
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)["sources"]


def save_sources(user_id, new_sources, data_dir=DATA_DIR):
    """Add sources to the owner's private store. Re-importing the same conversation
    replaces the earlier copy instead of duplicating it. Returns all of the owner's sources."""
    for s in new_sources:
        if s["user_id"] != user_id:
            raise ImportFailed("wrong_owner", "These chats belong to a different user.")
    by_id = {s["source_id"]: s for s in load_sources(user_id, data_dir)}
    for s in new_sources:
        by_id[s["source_id"]] = s
    sources = sorted(by_id.values(), key=lambda s: (s["provenance"]["created_at"] or "", s["source_id"]))
    path = _user_dir("sources", user_id, data_dir).with_suffix(".json")
    _write_json(path, {"schema_version": SCHEMA_VERSION, "user_id": user_id, "sources": sources})
    return sources


def load_upload_log(user_id, data_dir=DATA_DIR):
    path = _user_dir("uploads", user_id, data_dir) / "uploads.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _append_upload_log(user_id, entry, data_dir):
    log = load_upload_log(user_id, data_dir)
    log.append(entry)
    _write_json(_user_dir("uploads", user_id, data_dir) / "uploads.json", log)


def _safe_filename(name):
    name = PurePosixPath((name or "upload").replace("\\", "/")).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:80] or "upload"


def _run_import(user_id, kind, label, parse, data_dir, file_bytes=None, fingerprint=None):
    """Parse, then store sources, the original file (uploads only) and a history entry.
    The same content uploaded twice gets the same upload_id."""
    content = file_bytes if file_bytes is not None else (fingerprint or label.encode("utf-8"))
    sha = hashlib.sha256(content).hexdigest()
    upload_id = "up_" + hashlib.sha256(f"{user_id}|{sha}".encode("utf-8")).hexdigest()[:12]
    entry = {
        "upload_id": upload_id,
        "kind": kind,
        "filename": label,
        "size_bytes": len(file_bytes) if file_bytes is not None else None,
        "sha256": sha,
        "uploaded_at": _now_utc(),
        "stored_file": None,
        "status": None,
        "imported_count": 0,
        "skipped": [],
        "error": None,
    }
    try:
        sources, skipped = parse(upload_id)
        if file_bytes is not None:
            # Keep the original only once it parsed: a wrong file (say, a PDF) is never stored.
            stored = _user_dir("uploads", user_id, data_dir) / "files" / f"{upload_id}__{_safe_filename(label)}"
            stored.parent.mkdir(parents=True, exist_ok=True)
            stored.write_bytes(file_bytes)
            entry["stored_file"] = str(stored.relative_to(Path(data_dir)))
        all_sources = save_sources(user_id, sources, data_dir)
    except ImportFailed as e:
        entry.update(status="failed", error=e.as_dict())
        _append_upload_log(user_id, entry, data_dir)
        raise
    entry.update(status="imported", imported_count=len(sources), skipped=skipped)
    _append_upload_log(user_id, entry, data_dir)
    return {"upload": entry, "sources": sources, "skipped": skipped, "total_sources": len(all_sources)}


def import_file(user_id, file_bytes, filename, data_dir=DATA_DIR):
    """Upload flow for one file. Raises ImportFailed (and logs the failure) if nothing usable."""
    _require_user(user_id)
    return _run_import(user_id, "file", filename or "upload",
                       lambda upload_id: parse_upload(file_bytes, filename, user_id, upload_id=upload_id),
                       data_dir, file_bytes=file_bytes)


def import_paste(user_id, text, title=None, data_dir=DATA_DIR):
    _require_user(user_id)
    if not (text or "").strip():
        raise ImportFailed("empty_paste", "Paste a conversation first.")

    def parse(upload_id):
        sources, skipped = parse_pasted_text(text, user_id, title=title)
        for s in sources:
            s["provenance"]["upload_id"] = upload_id
        return sources, skipped

    return _run_import(user_id, "paste", (title or "").strip() or "Pasted text", parse, data_dir,
                       fingerprint=text.encode("utf-8"))


def import_demo(user_id, data_dir=DATA_DIR):
    _require_user(user_id)
    return _run_import(user_id, "demo", "Synthetic demo history",
                       lambda upload_id: parse_demo_history(user_id), data_dir)
