"""Builds 2 - Noise Filter/samples/output/: the synthetic example files Step 3 builds against
(see HANDOFF.md, section 6).

It runs the real Step 1 import and the real Step 2 screening and file writer on the synthetic
demo histories. The only stand-in is the AI: decisions come from EXPECTED below (the brief's
expected results), so the samples are free, reproducible and don't depend on a live model.
The local safety rules still run for real (they hold back a_s09).

ALL CONTENT IS SYNTHETIC. Run from the repo root to regenerate:
    .venv/bin/python "2 - Noise Filter/samples/build_sample_output.py"
"""

import shutil
import sys
import tempfile
from pathlib import Path

STEP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STEP_DIR))
sys.path.insert(0, str(STEP_DIR.parent / "1 - Data Collection"))

import importer as im  # noqa: E402
import screening as sc  # noqa: E402

IMPORTED_AT = "2026-10-03T19:00:00Z"  # fixed, so regenerating doesn't change the files

# First words of each chat → the decision a correct screen makes (shared brief, section 11).
EXPECTED = {
    "In fibroblasts": "eligible",
    "Our immunofluorescence": "eligible",
    "I'm honestly uncertain": "eligible",
    "We're using an LLM": "eligible",
    "Following up on extraction": "eligible",
    "I've had headaches": ("sensitive", ["personal_health"]),
    "Help me plan repayments": ("sensitive", ["financial"]),
    "I land at 14:20": ("administrative", []),
    "In Disease B cells": "eligible",
    "For the synchronized-release pilot": "eligible",
}


class ExpectedDecisions:
    model = "expected-decisions (sample build, no AI)"

    def __call__(self, text, stage="first"):
        first_message = text.split("[message 0 · User]\n", 1)[1].split("\n", 1)[0]
        for start, outcome in EXPECTED.items():
            if first_message.startswith(start):
                if outcome == "eligible":
                    return {"decision": "eligible", "exclusion_reason": "none", "sensitive_categories": [],
                            "redactions": [], "remove_message_numbers": [], "explanation": "Research content only."}
                reason, cats = outcome
                return {"decision": "exclude", "exclusion_reason": reason, "sensitive_categories": cats,
                        "redactions": [], "remove_message_numbers": [], "explanation": "Held back (sample build)."}
        raise ValueError(f"No expected decision for a chat starting: {first_message[:40]!r}")


def main():
    out = sc.SAMPLES_OUTPUT_DIR
    if out.exists():
        shutil.rmtree(out)
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp)
        for user_id in im.DEMO_FIXTURES:
            sources, _ = im.parse_demo_history(user_id, imported_at=IMPORTED_AT)
            im.save_sources(user_id, sources, data)
            sc.screen_user(user_id, ExpectedDecisions(), data, max_workers=1, output_dir=out)
    for folder in sorted(out.iterdir()):
        print(f"{folder.name}: {', '.join(sorted(p.stem for p in folder.glob('*.md')))}")


if __name__ == "__main__":
    main()
