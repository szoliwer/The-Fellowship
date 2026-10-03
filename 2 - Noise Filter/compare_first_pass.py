"""Compare first-pass effort settings on your own imported chats, to decide FIRST_PASS_EFFORT.

Screens the user's chats twice, once with each first-pass effort (re-checks stay at RECHECK_EFFORT),
and prints, per chat, the outcome and how many checks it needed, plus what each run really cost
(from the API's own token counts).

Spends real money (asks before starting). Works on temporary copies: your real screening report
and Step 3 files are not touched. Prints only chat IDs and numbers, never chat text or titles.

Run from the repo root:
    .venv/bin/python "2 - Noise Filter/compare_first_pass.py" <user_id> [effort_a] [effort_b]
    e.g. .venv/bin/python "2 - Noise Filter/compare_first_pass.py" user_1a2b3c4d low medium
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

import screening as sc


def run(user_id, effort, data_dir):
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / "sources").mkdir()
        shutil.copy(sc._user_file("sources", user_id, data_dir), work / "sources" / f"{user_id}.json")
        classifier = sc.ClaudeClassifier(first_pass_effort=effort)
        report = sc.screen_user(user_id, classify=classifier, data_dir=work, output_dir=work / "output")
    return report, classifier


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    user_id = sys.argv[1]
    efforts = sys.argv[2:4] or ["low", "medium"]
    sources = sc.load_sources(user_id)
    if not sources:
        sys.exit(f"No imported chats for {user_id}.")
    est = sc.estimate_cost(sources)
    print(f"{len(sources)} chat(s); {est['chats_to_send']} go to the AI. Two runs ({' vs '.join(efforts)}).")
    print(f"Rough cost: about ${2 * est['dollars']:.2f}, up to ~4x that if chats need cleaning.")
    if input("Type yes to spend that and run the comparison: ").strip().lower() != "yes":
        sys.exit("Cancelled; nothing was sent.")

    results = {}
    for effort in efforts:
        print(f"\nRunning first pass at effort '{effort}'…")
        results[effort] = run(user_id, effort, sc.DATA_DIR)

    print(f"\n{'chat':<22}" + "".join(f"{e:>28}" for e in efforts))
    for s in sources:
        row = f"{s['source_id']:<22}"
        for effort in efforts:
            e = results[effort][0].get(s["source_id"])
            checks = 1 + len(e["recheck"]) if e and e["model"] else 0
            outcome = e["decision"] if e else "?"
            removed = f", -{len(e['removed_message_ids'])} msgs" if e and e["removed_message_ids"] else ""
            row += f"{f'{outcome}, {checks} check(s){removed}':>28}"
        print(row)
    print()
    for effort in efforts:
        c = results[effort][1]
        print(f"effort '{effort}': {c.usage['calls']} API calls, ${c.cost_dollars():.3f} "
              f"(tokens: {json.dumps(c.usage)})")
    print("\nIf the stronger setting is cheaper overall, or catches more on the first pass, set "
          "FIRST_PASS_EFFORT in screening.py to it.")


if __name__ == "__main__":
    main()
