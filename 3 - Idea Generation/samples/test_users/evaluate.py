"""Score Step 3's output for the 10 synthetic test users against answer_key.json.

An expected idea counts as FOUND when one sub-theme
  * cites at least half of the idea's chats (or `min_chats`), and
  * mentions one of the idea's keywords (in the sub-theme, a handle or a claim).
Also checked: trap words that must never appear, ideas that must stay in separate
sub-themes, expected primary tier, and sub-themes built only from no-idea task chats.
Keyword matching is a first pass: read the misses by eye before concluding anything.

Run from the repo root:
  python3 "3 - Idea Generation/samples/test_users/evaluate.py" [--outputs DIR]
"""

import argparse
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEY = json.loads((HERE / "answer_key.json").read_text(encoding="utf-8"))["users"]


def sub_text(s):
    parts = [s["sub_theme"]] + [i["handle"] + " " + i["claim"] for i in s["insights"]]
    return " ".join(parts).lower()


def full_id(user_id, chat):
    return f"u{int(user_id.split('_')[1]):02d}_{chat}"


def evaluate_user(user_id, spec, result):
    subs = [s for t in result["themes"] for s in t["sub_themes"]]
    rows = {r["idea_id"].split("_")[-1]: r for r in result["ideas"]}   # "t1.s1" -> Step 4 row
    report = {"user_id": user_id, "pattern": spec["pattern"], "ideas": [], "problems": [],
              "sub_theme_count": len(subs)}
    matched = {}
    for eid, idea in spec["ideas"].items():
        chats = {full_id(user_id, c) for c in idea["chats"]}
        need = idea.get("min_chats", max(1, math.ceil(len(chats) / 2)))
        best = None
        for s in subs:
            overlap = len(chats & set(s["source_chat_ids"]))
            if overlap >= need and any(k in sub_text(s) for k in idea["keywords"]):
                if best is None or overlap > best[0]:
                    best = (overlap, s)
        entry = {"id": eid, "label": idea["label"], "key": idea.get("key", True), "found": bool(best)}
        if not best:   # diagnose: was the idea split over several sub-themes?
            parts = [s["id"] for s in subs if chats & set(s["source_chat_ids"])
                     and any(k in sub_text(s) for k in idea["keywords"])]
            covered = len(chats & {c for s in subs if s["id"] in parts for c in s["source_chat_ids"]})
            if len(parts) > 1 and covered >= need:
                entry["note"] = f"SPLIT over {len(parts)} sub-themes {parts} (together cite {covered}/{len(chats)} chats)"
        if best:
            s = best[1]
            matched[eid] = s["id"]
            row = rows.get(s["id"], {})
            entry.update(sub_theme=s["sub_theme"], sub_id=s["id"], tier=s["tier"], type=row.get("type"),
                         chats_cited=f"{best[0]}/{len(chats)}")
            if idea.get("type") and row.get("type") != idea["type"]:
                entry["note"] = f"type {row.get('type')} (expected {idea['type']})"
            if idea.get("primary") and s["tier"] != "primary":
                report["problems"].append(f"{eid} should be primary, is {s['tier']}")
        report["ideas"].append(entry)

    for a, b in spec.get("separate", []):
        if a in matched and matched[a] == matched.get(b):
            report["problems"].append(f"{a} and {b} wrongly merged into {matched[a]}")
    if spec.get("distinct"):
        seen = {}
        for eid, sid in matched.items():
            if sid in seen:
                report["problems"].append(f"{seen[sid]} and {eid} wrongly merged into {sid}")
            seen[sid] = eid
    text = json.dumps(result, ensure_ascii=False).lower()
    for word in spec.get("must_not", []):
        if word in text:
            report["problems"].append(f"trap leaked: '{word}' appears in the output")
    noise = {full_id(user_id, c) for c in spec.get("noise_chats", [])}
    for s in subs:
        if noise and set(s["source_chat_ids"]) <= noise:
            report["problems"].append(f"{s['id']} '{s['sub_theme']}' is built only from task chats")
    key_ideas = [e for e in report["ideas"] if e["key"]]
    report["score"] = f"{sum(e['found'] for e in key_ideas)}/{len(key_ideas)}"
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--outputs", default=str(HERE / "outputs"))
    args = p.parse_args()
    reports, found, total = [], 0, 0
    for user_id, spec in KEY.items():
        path = Path(args.outputs) / f"{user_id}.json"
        if not path.exists():
            print(f"{user_id}: no output file")
            continue
        r = evaluate_user(user_id, spec, json.loads(path.read_text(encoding="utf-8")))
        reports.append(r)
        k = [e for e in r["ideas"] if e["key"]]
        found += sum(e["found"] for e in k)
        total += len(k)
        print(f"\n{user_id} [{r['pattern']}]  key ideas found {r['score']}, {r['sub_theme_count']} sub-themes")
        for e in r["ideas"]:
            mark = "OK  " if e["found"] else ("MISS" if e["key"] else "miss")
            extra = (f"-> {e['sub_id']} '{e['sub_theme']}' ({e['tier']}, {e['type']}, {e['chats_cited']} chats)"
                     if e["found"] else "")
            if not e["found"] and e.get("note", "").startswith("SPLIT"):
                mark = "SPLT"
            print(f"  {mark} {e['id']:4} {e['label']}  {extra}" + (f"  [{e['note']}]" if e.get("note") else ""))
        for prob in r["problems"]:
            print(f"  !! {prob}")
    print(f"\nTOTAL key ideas found: {found}/{total}; "
          f"problems: {sum(len(r['problems']) for r in reports)}")
    (Path(args.outputs) / "evaluation.json").write_text(json.dumps(reports, indent=2, ensure_ascii=False),
                                                       encoding="utf-8")


if __name__ == "__main__":
    main()
