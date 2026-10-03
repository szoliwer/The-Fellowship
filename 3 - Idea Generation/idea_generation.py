"""Step 3 — Idea Generation.

Reads one user's filtered chats from Step 2 (one Markdown file per chat, see
the Step 2 -> 3 handoff, HANDOFF.md), asks Claude to extract their ideas with the prompt in
prompt.md, then checks and cleans the answer in code:

  * drops anything not traced to a real chat, and enforces the size limits
  * works out every count and date itself (the model is never trusted with numbers)
  * marks each sub-theme primary/secondary
  * writes data/ideas/<user_id>.json, with NO raw chat text in it

The output holds two views of the same ideas:
  * "themes" / "adjacent_ideas": the full structure from the prompt, plus computed stats
  * "ideas": one row per sub-theme in the agreed Step 3 -> 4 format (see README)

Chat text is untrusted data: it goes to the model inside <conversation> tags and is
never acted on, logged or written out.

Run from the repo root:
  python3 "3 - Idea Generation/idea_generation.py" --user user_a
  python3 "3 - Idea Generation/idea_generation.py" --all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

STEP_DIR = Path(__file__).resolve().parent
REPO_ROOT = STEP_DIR.parent
PROMPT_FILE = STEP_DIR / "prompt.md"
DEFAULT_INPUT_DIR = REPO_ROOT / "2 - Noise Filter" / "output"   # Step 2's real output (git-ignored)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "ideas"               # git-ignored
CACHE_FILE = REPO_ROOT / "data" / "step3_llm_cache.json"         # git-ignored

# --- Settings (all in one place) -------------------------------------------------------
MODEL = "claude-opus-5-5"   # current default Claude model
EFFORT = "high"             # how hard the model thinks: low | medium | high | xhigh | max
MAX_TOKENS = 64000          # room for thinking + the JSON answer (streaming avoids timeouts)
# If the model declines a request, the API re-runs it on a fallback model automatically.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

# Limits from prompt.md ("RULES THE CODE MUST ENFORCE", rule 3)
MAX_SUB_THEMES_PER_THEME = 5
MAX_INSIGHTS_PER_SUB_THEME = 5
MAX_SUB_THEMES_TOTAL = 15
MAX_ADJACENT_IDEAS = 4

SCHEMA_VERSION = "1.0"
MODES = {"working_on", "curious_about"}
DIRECTIONS = {"can_offer", "looking_for", "none"}
EMPTY_RESULT = {"themes": [], "adjacent_ideas": []}


def log(msg=""):
    print(msg, flush=True)


# ======================================================================================
# 1. Reading Step 2's output
# ======================================================================================
_MESSAGE_START = re.compile(r"^\*\*(User|Assistant):\*\*[ \t]?", re.MULTILINE)


def _header_value(raw):
    raw = raw.strip()
    if raw in ("null", "~", ""):
        return None
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1].replace('\\"', '"')
    return raw


def parse_chat_file(path: Path) -> dict:
    """One Step 2 Markdown file -> {header..., messages: [(role, text), ...]}."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("missing header")
    try:
        _, header_block, body = text.split("---", 2)
    except ValueError:
        raise ValueError("header not closed")
    header = {}
    for line in header_block.strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            header[key.strip()] = _header_value(value)

    messages = []
    starts = list(_MESSAGE_START.finditer(body))
    for n, m in enumerate(starts):
        end = starts[n + 1].start() if n + 1 < len(starts) else len(body)
        messages.append((m.group(1), body[m.end():end].strip()))
    header["messages"] = messages
    return header


def load_user_chats(user_id: str, input_dir: Path) -> list:
    """All eligible chats for one user. A missing or empty folder means 'no ideas yet'."""
    folder = input_dir / user_id
    if not folder.is_dir():
        return []
    chats = []
    for path in sorted(folder.glob("*.md")):
        try:
            chat = parse_chat_file(path)
        except (ValueError, UnicodeDecodeError) as e:
            log(f"  ! skipped {path.name}: unreadable ({e})")
            continue
        if chat.get("schema_version") != SCHEMA_VERSION:
            log(f"  ! skipped {path.name}: schema_version {chat.get('schema_version')!r}, expected {SCHEMA_VERSION!r}")
            continue
        if chat.get("user_id") != user_id:   # privacy: never mix another user's chat in
            log(f"  ! skipped {path.name}: belongs to a different user than its folder")
            continue
        if not chat.get("source_id"):
            log(f"  ! skipped {path.name}: no source_id")
            continue
        created = chat.get("created_at")
        chat["date"] = created[:10] if created and re.match(r"\d{4}-\d{2}-\d{2}", created) else None
        chat["user_message_count"] = sum(1 for role, _ in chat["messages"] if role == "User")
        chats.append(chat)
    # Fixed order (by date, then id) so the same chats always make the same prompt.
    chats.sort(key=lambda c: (c["date"] or "9999", c["source_id"]))
    return chats


# ======================================================================================
# 2. Building the prompt
# ======================================================================================
def load_system_prompt(path: Path = PROMPT_FILE) -> str:
    """The SYSTEM PROMPT is the first ``` block after '## SYSTEM PROMPT' in prompt.md."""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^## SYSTEM PROMPT\s*$.*?^```[^\n]*\n(.*?)^```", text, re.MULTILINE | re.DOTALL)
    if not m:
        raise RuntimeError(f"Could not find the SYSTEM PROMPT block in {path.name}")
    return m.group(1).strip()


def _defuse_tags(text: str) -> str:
    # A chat can't close its own <conversation> block and pose as part of the prompt.
    return re.sub(r"<(/?)(conversation)", r"<\1 \2", text, flags=re.IGNORECASE)


def build_user_message(chats: list) -> str:
    blocks = ["Here are the conversations. Return the JSON object only."]
    for c in chats:
        body = "\n\n".join(f"{role}: {_defuse_tags(text)}" for role, text in c["messages"])
        blocks.append(
            "<conversation>\n"
            f"[chat_id: {c['source_id']} | date: {c['date'] or 'unknown'}]\n"
            f"{body}\n"
            "</conversation>"
        )
    return "\n\n".join(blocks)


# ======================================================================================
# 3. Calling Claude (with a cache, and one retry on bad JSON)
# ======================================================================================
def load_env():
    """Read ANTHROPIC_API_KEY from a .env file in this folder or the repo root."""
    for p in (STEP_DIR / ".env", REPO_ROOT / ".env"):
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


class ModelDeclined(Exception):
    """The model (and its fallback) refused the request."""


def ask_claude(system: str, user_message: str, model: str = MODEL) -> str:
    import anthropic   # imported here so tests and fake runs don't need it

    client = anthropic.Anthropic()
    with client.messages.stream(
        model=model,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user_message}],
        # Passed as raw fields so this works on any recent version of the anthropic package.
        extra_headers={"anthropic-beta": FALLBACK_BETA},
        extra_body={"output_config": {"effort": EFFORT}, "fallbacks": "default"},
    ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        raise ModelDeclined("the model declined this request")
    if msg.stop_reason == "max_tokens":
        log("  ! answer was cut off (max_tokens); it will probably fail to parse")
    return "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text")


def parse_json(text: str):
    """Strip markdown fences and parse the outer JSON object. None if it isn't valid."""
    text = re.sub(r"```(?:json)?", "", text or "")
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _read_cache() -> dict:
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_cache(cache: dict):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8")


def get_model_answer(user_id, system, user_message, ask=ask_claude, model=MODEL, use_cache=True):
    """Returns (parsed answer, came_from_cache). Never logs chat text."""
    key = hashlib.sha256(f"{user_id}\n{model}\n{system}\n{user_message}".encode("utf-8")).hexdigest()
    cache = _read_cache() if use_cache else {}
    if key in cache:
        return cache[key], True

    for attempt in (1, 2):   # rule 1: retry once on invalid JSON
        text = ask(system, user_message)
        data = parse_json(text)
        if data is not None:
            if use_cache:
                cache = _read_cache()
                cache[key] = data
                _write_cache(cache)
            return data, False
        log(f"  ! attempt {attempt}: the model's answer was not valid JSON ({len(text or '')} characters)")
    log("  ! giving up: writing an empty result for this user")
    return dict(EMPTY_RESULT), False


# ======================================================================================
# 4. Checking and cleaning the answer (rules 2-5 from prompt.md)
# ======================================================================================
def _str(x) -> str:
    return x.strip() if isinstance(x, str) else ""


def _list(x) -> list:
    return x if isinstance(x, list) else []


def _keep_top(items, n, key):
    """Keep the n items with the highest key, but leave them in their original order."""
    if len(items) <= n:
        return items
    ranked = sorted(range(len(items)), key=lambda i: -key(items[i]))[:n]   # stable: ties keep order
    return [items[i] for i in sorted(ranked)]


def compute_stats(chat_ids, chats_by_id) -> dict:
    """Rule 4: every number comes from the chats themselves, never from the model."""
    ids = sorted(set(chat_ids))
    dates = [chats_by_id[c]["date"] for c in ids if chats_by_id[c]["date"]]
    return {
        "chat_count": len(ids),
        "user_message_count": sum(chats_by_id[c]["user_message_count"] for c in ids),
        "first_seen": min(dates) if dates else None,
        "last_seen": max(dates) if dates else None,
    }


def clean_answer(answer: dict, chats: list) -> dict:
    chats_by_id = {c["source_id"]: c for c in chats}

    # --- Rule 2: keep only what traces back to a real chat ---------------------------
    themes, old_to_new = [], {}
    for t in _list(answer.get("themes")):
        if not isinstance(t, dict) or not _str(t.get("theme")):
            continue
        subs = []
        for s in _list(t.get("sub_themes")):
            if not isinstance(s, dict) or not _str(s.get("sub_theme")):
                continue
            insights = []
            for ins in _list(s.get("insights")):
                if not isinstance(ins, dict) or not _str(ins.get("handle")) or not _str(ins.get("claim")):
                    continue
                ids = []
                for c in _list(ins.get("source_chat_ids")):
                    if isinstance(c, str) and c in chats_by_id and c not in ids:
                        ids.append(c)
                if ids:
                    insights.append({"handle": _str(ins["handle"]), "claim": _str(ins["claim"]),
                                     "source_chat_ids": sorted(ids)})
            if insights:
                mode = s.get("mode") if s.get("mode") in MODES else "curious_about"
                direction = s.get("direction") if s.get("direction") in DIRECTIONS else "none"
                subs.append({"model_id": _str(s.get("id")), "sub_theme": _str(s["sub_theme"]),
                             "mode": mode, "direction": direction, "insights": insights})
        if subs:
            themes.append({"theme": _str(t["theme"]), "sub_themes": subs})

    # --- Rule 3: limits (trim by number of distinct source chats, most first) --------
    def sub_chats(s):
        return len({c for ins in s["insights"] for c in ins["source_chat_ids"]})

    for t in themes:
        for s in t["sub_themes"]:
            s["insights"] = _keep_top(s["insights"], MAX_INSIGHTS_PER_SUB_THEME,
                                      key=lambda ins: len(ins["source_chat_ids"]))
        t["sub_themes"] = _keep_top(t["sub_themes"], MAX_SUB_THEMES_PER_THEME, key=sub_chats)
    all_subs = [s for t in themes for s in t["sub_themes"]]
    if len(all_subs) > MAX_SUB_THEMES_TOTAL:
        keep = {id(s) for s in _keep_top(all_subs, MAX_SUB_THEMES_TOTAL, key=sub_chats)}
        for t in themes:
            t["sub_themes"] = [s for s in t["sub_themes"] if id(s) in keep]
        themes = [t for t in themes if t["sub_themes"]]

    # --- Fresh IDs (t1, t1.s1, t1.s1.i1) and Rule 4 stats ----------------------------
    for ti, t in enumerate(themes, 1):
        t["id"] = f"t{ti}"
        for si, s in enumerate(t["sub_themes"], 1):
            s["id"] = f"t{ti}.s{si}"
            if s["model_id"] and s["model_id"] not in old_to_new:
                old_to_new[s["model_id"]] = s["id"]
            for ii, ins in enumerate(s["insights"], 1):
                ins["id"] = f"{s['id']}.i{ii}"
                ins.update(compute_stats(ins["source_chat_ids"], chats_by_id))
            s["source_chat_ids"] = sorted({c for ins in s["insights"] for c in ins["source_chat_ids"]})
            s.update(compute_stats(s["source_chat_ids"], chats_by_id))

    # --- Rule 5: tiers -----------------------------------------------------------------
    all_subs = [s for t in themes for s in t["sub_themes"]]
    for s in all_subs:
        s["tier"] = "primary" if s["chat_count"] >= 2 else "secondary"
    if all_subs and not any(s["tier"] == "primary" for s in all_subs):
        newest = sorted(all_subs, key=lambda s: s["last_seen"] or "", reverse=True)[:2]
        for s in newest:
            s["tier"] = "primary"

    # --- Adjacent ideas: bridges must point at surviving sub-themes --------------------
    adjacent = []
    for a in _list(answer.get("adjacent_ideas")):
        if not isinstance(a, dict) or not _str(a.get("handle")) or not _str(a.get("claim")):
            continue
        bridges = []
        for b in _list(a.get("bridges")):
            new = old_to_new.get(b) if isinstance(b, str) else None
            if new and new not in bridges:
                bridges.append(new)
        if bridges:
            adjacent.append({"handle": _str(a["handle"]), "claim": _str(a["claim"]), "bridges": bridges})
    adjacent = adjacent[:MAX_ADJACENT_IDEAS]
    for ai, a in enumerate(adjacent, 1):
        a["id"] = f"a{ai}"

    # --- Rule 6: output only labels, claims, IDs and stats (fixed field order) ---------
    out_themes = [{
        "id": t["id"],
        "theme": t["theme"],
        "sub_themes": [{
            "id": s["id"], "sub_theme": s["sub_theme"], "mode": s["mode"], "direction": s["direction"],
            "tier": s["tier"], "source_chat_ids": s["source_chat_ids"], "chat_count": s["chat_count"],
            "user_message_count": s["user_message_count"], "first_seen": s["first_seen"],
            "last_seen": s["last_seen"],
            "insights": [{k: ins[k] for k in ("id", "handle", "claim", "source_chat_ids", "chat_count",
                                              "user_message_count", "first_seen", "last_seen")}
                         for ins in s["insights"]],
        } for s in t["sub_themes"]],
    } for t in themes]
    out_adjacent = [{k: a[k] for k in ("id", "handle", "claim", "bridges")} for a in adjacent]
    return {"themes": out_themes, "adjacent_ideas": out_adjacent}


# ======================================================================================
# 5. Flat rows for Step 4 (the agreed Step 3 -> 4 format, one row per sub-theme)
# ======================================================================================
def idea_type(mode: str, direction: str) -> str:
    if direction == "can_offer":
        return "skill"
    if direction == "looking_for":
        return "need"
    return "project" if mode == "working_on" else "interest"


def to_idea_rows(user_id: str, themes: list) -> list:
    rows = []
    for t in themes:
        for s in t["sub_themes"]:
            rows.append({
                "user_id": user_id,
                "idea_id": f"{user_id}_{s['id']}",
                "type": idea_type(s["mode"], s["direction"]),
                "summary": s["sub_theme"],
                "insights": [ins["claim"] for ins in s["insights"]],
                "keywords": [ins["handle"] for ins in s["insights"]],
                "evidence": s["source_chat_ids"],
                "first_seen": s["first_seen"],
                "last_seen": s["last_seen"],
                "mentions": s["user_message_count"],
                # Extra fields (Step 4/5 ignore what they don't use):
                "chat_count": s["chat_count"],
                "tier": s["tier"],
                "theme": t["theme"],
                "mode": s["mode"],
                "direction": s["direction"],
            })
    return rows


# ======================================================================================
# 6. Running one user end to end
# ======================================================================================
def run_user(user_id, input_dir=DEFAULT_INPUT_DIR, output_dir=DEFAULT_OUTPUT_DIR,
             ask=ask_claude, model=MODEL, use_cache=True) -> dict:
    chats = load_user_chats(user_id, Path(input_dir))
    system = load_system_prompt()
    user_message = build_user_message(chats)
    input_hash = hashlib.sha256(user_message.encode("utf-8")).hexdigest()[:16]
    log(f"{user_id}: {len(chats)} eligible chat(s)")

    from_cache = False
    if chats:
        answer, from_cache = get_model_answer(user_id, system, user_message, ask=ask, model=model,
                                              use_cache=use_cache)
    else:
        answer = dict(EMPTY_RESULT)   # no eligible chats = "no ideas yet", not an error
    cleaned = clean_answer(answer, chats)

    result = {
        "schema_version": SCHEMA_VERSION,
        "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": model,
        "from_cache": from_cache,
        "input_hash": input_hash,
        "chats_read": [c["source_id"] for c in chats],
        "themes": cleaned["themes"],
        "adjacent_ideas": cleaned["adjacent_ideas"],
        "ideas": to_idea_rows(user_id, cleaned["themes"]),
    }
    out = Path(output_dir) / f"{user_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    n_subs = len(result["ideas"])
    n_primary = sum(1 for r in result["ideas"] if r["tier"] == "primary")
    log(f"  -> {n_subs} idea(s) ({n_primary} primary), {len(result['adjacent_ideas'])} adjacent idea(s)"
        f"{' [from cache]' if from_cache else ''} -> {out}")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description="Step 3: extract each user's ideas from their filtered chats.")
    who = p.add_mutually_exclusive_group(required=True)
    who.add_argument("--user", help="one user_id (a folder name in the input folder)")
    who.add_argument("--all", action="store_true", help="every user folder in the input folder")
    p.add_argument("--input", default=str(DEFAULT_INPUT_DIR), help="Step 2 output folder")
    p.add_argument("--output", default=str(DEFAULT_OUTPUT_DIR), help="where to write <user_id>.json")
    p.add_argument("--model", default=MODEL)
    p.add_argument("--no-cache", action="store_true", help="always call the model, even for a saved answer")
    p.add_argument("--fake-response", help="use this JSON file as the model's answer (no API call, for testing)")
    args = p.parse_args(argv)

    input_dir = Path(args.input)
    if not input_dir.is_dir():
        sys.exit(f"Input folder not found: {input_dir}")
    users = [args.user] if args.user else sorted(d.name for d in input_dir.iterdir() if d.is_dir())

    if args.fake_response:
        fake_text = Path(args.fake_response).read_text(encoding="utf-8")
        ask = lambda system, msg: fake_text   # noqa: E731
        use_cache = False
        args.model = "fake-response"   # so the output file says it didn't come from a real model
    else:
        load_env()
        ask = lambda system, msg: ask_claude(system, msg, model=args.model)   # noqa: E731
        use_cache = not args.no_cache

    for user_id in users:
        try:
            run_user(user_id, input_dir, args.output, ask=ask, model=args.model, use_cache=use_cache)
        except ModelDeclined as e:
            log(f"  ! {user_id}: {e}; no output written")
        except Exception as e:   # API/network problems: say what kind, never print chat text
            log(f"  ! {user_id}: model call failed ({type(e).__name__}); no output written")
            if not os.environ.get("ANTHROPIC_API_KEY") or type(e).__name__ == "AuthenticationError":
                log("    Check ANTHROPIC_API_KEY in your .env file (copy .env.example to .env).")
            raise SystemExit(1)


if __name__ == "__main__":
    main()
