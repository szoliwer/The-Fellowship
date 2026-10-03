"""Build STAND-IN Step 2 output for testing Step 3, until Step 2's own samples land.

Takes Step 1's synthetic demo history for user_a and writes the 5 chats Step 2 is expected
to keep (a_s01-a_s05) in the Step 2 -> 3 handoff format (one Markdown file per chat).
a_s06-a_s09 (health, finances, admin, patient details) are deliberately left out.

Run from the repo root:  python3 "3 - Idea Generation/samples/build_step2_standin.py"
All content is synthetic.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / "1 - Data Collection"))

import importer  # noqa: E402  (Step 1's importer, used read-only)

USER_ID = "user_a"
KEEP = ["a_s01", "a_s02", "a_s03", "a_s04", "a_s05"]
OUT_DIR = HERE / "step2_output" / USER_ID
IMPORTED_AT = "2026-10-03T19:00:00Z"  # fixed so the files don't change on every run


def _yaml_value(v):
    if v is None:
        return "null"
    if isinstance(v, int):
        return str(v)
    text = str(v)
    if any(c in text for c in ':#"\'') or text != text.strip():
        return '"' + text.replace('"', '\\"') + '"'
    return text


def to_markdown(src):
    prov = src["provenance"]
    header = {
        "schema_version": "1.0",
        "user_id": src["user_id"],
        "source_id": src["source_id"],
        "title": prov["title"],
        "created_at": prov["created_at"],
        "imported_at": IMPORTED_AT,
        "source_type": src["source_type"],
        "original_conversation_id": prov["original_conversation_id"],
        "message_count": len(src["messages"]),
        "derived_from_source_id": prov["derived_from_source_id"],
    }
    lines = ["---"]
    for k, v in header.items():
        lines.append(f"{k}: " + ('"1.0"' if k == "schema_version" else _yaml_value(v)))
    lines += ["---", ""]
    body = "\n\n".join(
        f"**{'User' if m['role'] == 'user' else 'Assistant'}:** {m['text']}" for m in src["messages"]
    )
    return "\n".join(lines) + "\n" + body + "\n"


def main():
    sources, _ = importer.import_demo_history(USER_ID, imported_at=IMPORTED_AT)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for src in sources:
        if src["source_id"] in KEEP:
            (OUT_DIR / f"{src['source_id']}.md").write_text(to_markdown(src), encoding="utf-8")
            print("wrote", src["source_id"])


if __name__ == "__main__":
    main()
