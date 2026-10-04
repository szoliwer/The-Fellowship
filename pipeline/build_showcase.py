"""Builds pipeline/showcase/ (the hosted demo's data) from this laptop. Run from the repo root:

    .venv/bin/python -m pipeline.build_showcase

It screens the two synthetic demo researchers' chats and finds their ideas (Steps 2, 3), approves
Step 4's sample ideas for them, and matches everyone (Step 5). Claude costs well under $1, and a
rebuild reuses the last bundle's answers.

What goes into the bundle (the repo is public, so this is all anyone can see):
  • demo researchers (user_a, user_b): their synthetic chats and every step's results;
  • real accounts: username and approved ideas only (each row checked against an allow-list),
    plus the matches. Never their chats, email, name, password or data/users.json.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for folder in ["0 - User Registration", "1 - Data Collection", "2 - Noise Filter", "3 - Idea Generation",
               "4 - Idea Ranking", "5 - Match Generation"]:
    sys.path.insert(0, str(ROOT / folder))
sys.path.insert(0, str(ROOT))

import idea_generation as ig  # noqa: E402  (Step 3)
import importer as im  # noqa: E402  (Step 1)
import match_generation as mg  # noqa: E402  (Step 5)
import review as rv  # noqa: E402  (Step 4)
import screening as sc  # noqa: E402  (Step 2)
from pipeline import matches as mt  # noqa: E402
from pipeline import messages as msg  # noqa: E402
from pipeline import showcase  # noqa: E402

DEMO = {"user_a": "researcher_014", "user_b": "cellbio_027"}
# Fields an approved idea may have (Step 4's own list plus the idea text the owner approved).
ALLOWED_FIELDS = set(rv.METADATA_FIELDS) | {"main_idea", "summary", "idea", "title",
                                            "insights", "subtopics", "specific_insights", "keywords"}
CONVERSATION = [  # synthetic, between the two demo researchers
    ("user_a", "Hi! Your live-cell recycling assays look like exactly what I need to test the trafficking "
               "hypothesis for Disease A. Would you be up for comparing notes?"),
    ("user_b", "Happy to! I could run two or three of your patient-derived lines through the assay. "
               "Which markers are you most sure about?"),
    ("user_a", "The transferrin receptor first: that's where the mislocalisation is clearest. "
               "I'll send you the construct list."),
]


def _copy(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)


def demo_researchers(app_data, handoff, tmp):
    """The synthetic researchers arrive imported and screened (Steps 1–2), with Step 4's sample ideas
    approved: the sample was written so the two complement each other, while their two-idea Step 3
    result is too thin for Step 5 to shortlist them (see the Step 5 note in the README). Their Step 3
    answer goes in the cache, so "Find my ideas" on the hosted app is instant and free."""
    ig.CACHE_FILE = tmp / "step3_cache.json"  # so the bundle gets only these researchers' answers
    for user_id in DEMO:
        if not sc.load_sources(user_id):
            im.import_demo(user_id)
        sc.screen_user(user_id)
        ig.run_user(user_id)  # fills the cache only; its output isn't put in the bundle
        rows, is_sample = rv.load_ranked_rows(user_id, ranked_dir=tmp / "none")
        assert is_sample, "expected Step 4's sample ideas for the demo researchers"
        cards = rv.build_cards(rows)
        state = rv.start_state(user_id, cards, approved_dir=tmp / "none")  # everything checked
        rv.save_approved(user_id, state, cards, approved_dir=app_data / "approved_ideas",
                         matching_file=tmp / "ideas.json")
        for sub in ("sources", "filter"):
            _copy(showcase.DATA / sub / f"{user_id}.json", app_data / sub / f"{user_id}.json")
        for md in (sc.OUTPUT_DIR / user_id).glob("*.md"):
            _copy(md, handoff / user_id / md.name)
    _copy(ig.CACHE_FILE, app_data / "step3_llm_cache.json")


def team(app_data):
    """Username + approved ideas of every real account that approved at least one idea."""
    users = {u["user_id"]: u for u in json.loads((showcase.DATA / "users.json").read_text(encoding="utf-8"))}
    people = []
    for path in sorted((showcase.DATA / "approved_ideas").glob("*.json")):
        user_id = path.stem
        record = users.get(user_id)
        if user_id in DEMO or not record or record.get("is_demo_account"):
            continue
        if not record["consent"].get("process_imported_chats"):
            continue
        approved = json.loads(path.read_text(encoding="utf-8"))
        if not approved.get("ideas"):
            continue
        for row in approved["ideas"]:
            extra = set(row) - ALLOWED_FIELDS
            if extra:
                raise SystemExit(f"Stopped: an approved idea of {record['pseudonym']} has unexpected fields {extra}")
        (app_data / "approved_ideas" / path.name).write_text(json.dumps(approved, indent=2, ensure_ascii=False))
        people.append({"user_id": user_id, "pseudonym": record["pseudonym"]})
    return people


def match_everyone(app_data, people, tmp):
    ideas_file, matches_file = app_data / "ideas.json", app_data / "matches.json"
    rv.rebuild_matching_file(approved_dir=app_data / "approved_ideas", matching_file=ideas_file)
    users = [{"user_id": u, "pseudonym": p, "name": p, "consent": {"analyse_chats": True}}
             for u, p in list(DEMO.items()) + [(x["user_id"], x["pseudonym"]) for x in people]]
    users_file = tmp / "users.json"
    users_file.write_text(json.dumps(users))
    cache = tmp / "step5_cache.json"  # judgements of today's approved ideas (and the last bundle's)
    mg.run(str(ideas_file), str(matches_file), mg.Settings(cache_file=str(cache)), users_path=str(users_file))
    if cache.exists():
        _copy(cache, showcase.STEP5_CACHE[0])
    status, messages = app_data / "match_status.json", app_data / "messages.json"
    mt.decide("user_a", "user_b", "connect", status)
    mt.decide("user_b", "user_a", "connect", status)
    for sender, text in CONVERSATION:
        other = "user_b" if sender == "user_a" else "user_a"
        msg.send(sender, other, text, status_file=status, messages_file=messages)


def write_readme(people, matches_file):
    data = json.loads(matches_file.read_text(encoding="utf-8"))
    names = {**DEMO, **{p["user_id"]: p["pseudonym"] for p in people}}
    lines = [f"- {names.get(m['user_a'], m['user_a'])} ↔ {names.get(m['user_b'], m['user_b'])} ({m['match_type']})"
             for m in data["matches"]]
    (showcase.BUNDLE / "README.md").write_text(f"""# Showcase data for the hosted demo

Loaded by `pipeline/showcase.py` when the app starts with an empty `data/` folder (the hosted demo,
after every restart). Never loaded over existing data. Rebuild with `.venv/bin/python -m pipeline.build_showcase`.

**This folder is public.** It holds only:
- the two **synthetic** demo researchers ({", ".join(DEMO.values())}): made-up chats, their privacy-check
  results, and Step 4's sample ideas approved (labelled as sample data on the Review page). Their own Step 3
  result has only two short ideas each, which Step 5 doesn't shortlist (below its 0.20 pre-score), so the
  sample ideas are used to show a real match. "Find my ideas" still works and is instant (cached);
- for our team's accounts: **username and approved ideas** ({", ".join(p["pseudonym"] for p in people)}),
  the ideas each person chose to share with matches. No chats, emails, names or passwords;
- the matches between everyone, one connected demo pair and a short synthetic conversation.

Matches in this bundle ({len(lines)}):
{chr(10).join(lines) or "- none"}
""", encoding="utf-8")


def main():
    sc.load_env_file()
    if not sc.api_key_available():
        raise SystemExit("Needs the Anthropic API key in .env (Steps 2, 3 and 5 call Claude).")
    app_data, handoff = showcase.BUNDLE / "app_data", showcase.BUNDLE / "handoff"
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        # Reuse the last bundle's Claude answers (all about today's approved ideas or the synthetic
        # researchers), so a rebuild only pays for what changed.
        for old, new in ((app_data / "step3_llm_cache.json", tmp / "step3_cache.json"),
                         (showcase.STEP5_CACHE[0], tmp / "step5_cache.json")):
            if old.exists():
                _copy(old, new)
        for old in (app_data, handoff):
            shutil.rmtree(old, ignore_errors=True)
        demo_researchers(app_data, handoff, tmp)
        people = team(app_data)
        match_everyone(app_data, people, tmp)
    (showcase.BUNDLE / "people.json").write_text(json.dumps(people, indent=2) + "\n")
    write_readme(people, app_data / "matches.json")
    print(f"Showcase built: {len(DEMO)} demo researchers, {len(people)} team profiles.")


if __name__ == "__main__":
    main()
