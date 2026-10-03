"""Turn the 10 synthetic test users (chats/<user_id>.json) into Step 2-format Markdown files.

Writes step2_output/<user_id>/uNN_cMM.md in the Step 2 -> 3 handoff format. Chat dates are
spread over Jul-Sep 2026 (about one every 9 days) so recency and first/last-seen are testable.

Run from the repo root:  python3 "3 - Idea Generation/samples/test_users/build_test_users.py"
All content is synthetic.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from build_step2_standin import to_markdown  # noqa: E402  (same file format as the user_a stand-in)

CHATS_DIR = HERE / "chats"
OUT_DIR = HERE / "step2_output"
START = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)


def main():
    for path in sorted(CHATS_DIR.glob("user_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        user_id = data["user_id"]
        n = int(user_id.split("_")[1])
        folder = OUT_DIR / user_id
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob("*.md"):
            old.unlink()
        for k, chat in enumerate(data["chats"]):
            source_id = f"u{n:02d}_{chat['chat']}"
            created = START + timedelta(days=9 * k + (n - 1) % 5)
            src = {
                "user_id": user_id,
                "source_id": source_id,
                "source_type": "demo",
                "messages": chat["messages"],
                "provenance": {
                    "title": chat["title"],
                    "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "original_conversation_id": source_id,
                    "derived_from_source_id": None,
                },
            }
            (folder / f"{source_id}.md").write_text(to_markdown(src), encoding="utf-8")
        print(f"{user_id}: {len(data['chats'])} chats")


if __name__ == "__main__":
    main()
