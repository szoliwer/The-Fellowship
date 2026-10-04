"""Fills an empty app with the showcase in pipeline/showcase/, so the hosted demo (for the judges)
works straight away. Free hosting forgets every file when the app restarts, so this runs again
after each restart. On a laptop that already has data it does nothing, and it never overwrites a file.

What the showcase holds (see pipeline/showcase/README.md; rebuilt by build_showcase.py):
  • the two synthetic demo researchers, imported, screened and with approved ideas (all made up);
  • our team's profiles: username and approved ideas only. No chats, emails or names;
  • matches between everyone, one connected demo pair and a short synthetic conversation.
"""

import json
import shutil
from datetime import datetime, timezone

import registration as reg  # Step 0
from pipeline import matches as mt

BUNDLE = mt.ROOT / "pipeline" / "showcase"
DATA = mt.ROOT / "data"
STEP5_CACHE = (BUNDLE / "step5_cache.json", mt.ROOT / "5 - Match Generation" / "data" / "llm_cache.json")


def load_if_empty(bundle=BUNDLE, root=mt.ROOT, db_file=reg.DB_FILE):
    """Copy the showcase into an app that has no data yet. Returns True if it did."""
    data = root / "data"
    marker = data / ".showcase_loaded"
    if marker.exists() or (data / "ideas.json").exists() or not (bundle / "people.json").exists():
        return False
    places = {bundle / "app_data": data, bundle / "handoff": root / "2 - Noise Filter" / "output"}
    pairs = [(src, dest / src.relative_to(folder)) for folder, dest in places.items()
             for src in folder.rglob("*") if src.is_file()]
    pairs.append((bundle / "step5_cache.json", root / "5 - Match Generation" / "data" / "llm_cache.json"))
    for src, dest in pairs:
        if src.exists() and not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
    reg.add_showcase_users(json.loads((bundle / "people.json").read_text(encoding="utf-8")), db_file)
    marker.write_text(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + "\n", encoding="utf-8")
    return True
