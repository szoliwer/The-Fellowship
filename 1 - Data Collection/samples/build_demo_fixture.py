"""Builds the canonical demo history for user_a (researcher_014) as a ChatGPT export.

ALL PEOPLE, DISEASES, PATIENTS, ACCOUNTS AND RESULTS HERE ARE SYNTHETIC.
They exist to test the pipeline (see the shared brief, section 11), not to state facts.

Source IDs a_s01 … a_s09 are used by every step, so don't renumber them.
Expected after Step 2: a_s01–a_s05 eligible; a_s06–a_s09 held back.

The output mimics ChatGPT's real `conversations.json` (a message tree in `mapping`,
`current_node` pointing at the selected branch), including a few awkward cases the
importer must handle: a hidden system message, an edited question that leaves an
abandoned branch (a_s02), and an image-plus-text message (a_s04).

Run from the repo root to regenerate:
    .venv/bin/python "1 - Data Collection/samples/build_demo_fixture.py"
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "demo_chatgpt_user_a.json"
DAY = 86400
T0 = 1788523200.0  # 2026-09-04 12:00 UTC

U, A = "user", "assistant"

CONVERSATIONS = [
    ("a_s01", "Could trafficking explain the Disease A phenotype?", T0, [
        (U, "In fibroblasts from Disease A patients we keep seeing a membrane protein piling up "
            "near the nucleus instead of reaching the cell surface. Could altered intracellular "
            "trafficking explain the phenotype, or am I over-reading one observation?"),
        (A, "It's a reasonable hypothesis, but the same picture could come from several causes: "
            "slower delivery from the Golgi, faster internalisation, failure to recycle from "
            "endosomes, or simply more of the protein being made. Each predicts something different "
            "about where and how fast the protein moves, so the next step is to separate them."),
        (U, "So I should treat 'trafficking defect' as a hypothesis to test, not a conclusion. "
            "What would most cleanly separate those explanations?"),
        (A, "Comparing total protein levels with the surface fraction rules expression in or out. "
            "Timing how quickly the protein reaches or leaves the surface separates delivery from "
            "recycling. Co-staining with compartment markers shows where it is stuck."),
    ]),
    ("a_s02", "Does mislocalization mean function changed?", T0 + 3 * DAY, [
        (U, "Our immunofluorescence shows mislocalization in about 60% of Disease A cells versus 15% "
            "of controls. Does that tell us anything about function, or only about location?"),
        (A, "On its own it tells you about location. A protein can be in an unusual place and "
            "still work, or look normal and be impaired. To link location to the phenotype you "
            "need a functional readout: for example, a cargo-uptake measurement, a pulse-chase "
            "to follow delivery over time, or surface labelling to quantify how much arrives."),
        (U, "We've only ever done imaging. I'm not sure which functional measurement fits our "
            "question, or how to tell a real effect from an artifact of the assay itself."),
        (A, "That's the key gap: picking a functional readout that matches the hypothesis, with "
            "controls that rule out artifacts. Someone who has designed trafficking assays before "
            "would help you choose."),
    ]),
    ("a_s03", "What assay or expertise could test the hypothesis?", T0 + 6 * DAY, [
        (U, "I'm honestly uncertain here. If the trafficking idea is right, what assay would test "
            "it, and what kind of expertise would I need? Nobody in our group has run functional "
            "trafficking assays."),
        (A, "You'd want a measurement of movement over time rather than a snapshot, plus controls: "
            "a condition known to block the pathway, a protein that should be unaffected, and a "
            "check that the labelling itself doesn't change trafficking. A cell biologist with "
            "assay-design experience could tell you which is feasible with your cells."),
        (U, "Good. Then the open question is really: which functional measurement, with which "
            "controls, and who could help design it."),
    ]),
    ("a_s04", "How reproducible is LLM-assisted literature extraction?", T0 + 9 * DAY, [
        (U, "We're using an LLM to pull variant-phenotype mentions out of papers for a literature "
            "review. Running the same paper twice gives slightly different lists. How worried "
            "should I be about reproducibility?"),
        (A, "Some variation is expected. It matters most if the differences change your "
            "conclusions. Measure it before deciding: run each paper several times and check "
            "how often the extracted items agree."),
        (U, [{"content_type": "image_asset_pointer", "asset_pointer": "file-service://synthetic-0001"},
             "Here's a screenshot of two runs on the same paper. The second run missed two variants."]),
        (A, "Missing items between runs suggests recall is the weak spot. Track agreement per "
            "item, not just per paper, so you can see which mentions are unstable."),
    ]),
    ("a_s05", "Checking disagreements between extraction runs", T0 + 11 * DAY, [
        (U, "Following up on extraction reproducibility: if I run each paper three times, how do "
            "I handle items that appear in only one or two runs?"),
        (A, "Treat agreement as a signal. Items found in all runs can be accepted with spot "
            "checks, while items that appear inconsistently go to a human reviewer. Record how "
            "often the reviewer overturns the model so you can report an error rate."),
        (U, "So the workflow is repeated extraction, then agreement scoring, then human checking "
            "of the disagreements, with the human decisions logged."),
    ]),
    ("a_s06", "Headaches and poor sleep", T0 + 13 * DAY, [
        (U, "I've had headaches most mornings for three weeks and I'm sleeping badly. I'm also "
            "taking a new medication. Should I be worried about my own health here?"),
        (A, "I can't diagnose you, but headaches that persist for weeks, especially after starting "
            "a new medication, are worth raising with your doctor soon."),
    ]),
    ("a_s07", "Budget and loan repayment", T0 + 15 * DAY, [
        (U, "Help me plan repayments. Take-home pay is 3,100 a month, rent is 1,400, and the loan "
            "on account TEST-0000-4471 has 8,200 left at 6.5%."),
        (A, "After rent you have 1,700 a month. Paying 400 a month toward the loan would clear "
            "it in roughly two years. Want a month-by-month table?"),
    ]),
    ("a_s08", "Conference travel and meeting logistics", T0 + 17 * DAY, [
        (U, "I land at 14:20 on the 12th and the hotel check-in is 15:00. Can you draft a schedule "
            "that fits three 30-minute meetings before the 18:00 reception?"),
        (A, "Here's one option: 15:30, 16:15 and 17:00, each with a 15-minute buffer."),
    ]),
    ("a_s09", "Clinic case notes and the trafficking phenotype", T0 + 19 * DAY, [
        (U, "One of our clinic patients, Jordan Ellery, 34, from Millbrook, record number "
            "MRN-0000123, has the strongest mislocalization we've seen. Her family history might "
            "explain why. Does her case support the trafficking hypothesis?"),
        (A, "A single case can motivate the hypothesis but can't confirm it. I'd avoid sharing "
            "identifying details; the useful part for your question is the phenotype pattern, "
            "which you could compare across de-identified samples."),
    ]),
]

ABANDONED_BRANCH = {  # an earlier version of a_s02's first question, later edited
    "conversation": "a_s02",
    "messages": [
        (U, "ABANDONED-BRANCH: is 60% mislocalization enough to publish?"),
        (A, "ABANDONED-BRANCH: probably not without a functional readout."),
    ],
}


def _node(node_id, role, parts, t, parent, hidden=False):
    content_type = "multimodal_text" if any(isinstance(p, dict) for p in parts) else "text"
    return {
        "id": node_id,
        "message": {
            "id": node_id,
            "author": {"role": role, "name": None, "metadata": {}},
            "create_time": t,
            "update_time": None,
            "content": {"content_type": content_type, "parts": parts},
            "status": "finished_successfully",
            "end_turn": True if role == A else None,
            "weight": 0.0 if hidden else 1.0,
            "metadata": {"is_visually_hidden_from_conversation": True} if hidden else {},
            "recipient": "all",
        },
        "parent": parent,
        "children": [],
    }


def _link(mapping, node):
    mapping[node["id"]] = node
    if node["parent"]:
        mapping[node["parent"]]["children"].append(node["id"])


def build_conversation(conv_id, title, t_start, messages):
    mapping = {"client-created-root": {"id": "client-created-root", "message": None, "parent": None, "children": []}}
    sys_id = f"{conv_id}-sys"
    _link(mapping, _node(sys_id, "system", [""], None, "client-created-root", hidden=True))

    branch_point = sys_id
    if ABANDONED_BRANCH["conversation"] == conv_id:
        parent = branch_point
        for i, (role, text) in enumerate(ABANDONED_BRANCH["messages"]):
            node_id = f"{conv_id}-old{i}"
            _link(mapping, _node(node_id, role, [text], t_start + i * 30, parent))
            parent = node_id

    parent = branch_point
    for i, (role, text) in enumerate(messages):
        node_id = f"{conv_id}-m{i:02d}"
        parts = text if isinstance(text, list) else [text]
        _link(mapping, _node(node_id, role, parts, t_start + 600 + i * 60, parent))
        parent = node_id

    return {
        "title": title,
        "create_time": t_start,
        "update_time": t_start + 600 + len(messages) * 60,
        "mapping": mapping,
        "moderation_results": [],
        "current_node": parent,
        "conversation_id": conv_id,
        "id": conv_id,
    }


def main():
    export = [build_conversation(*c) for c in CONVERSATIONS]
    OUT.write_text(json.dumps(export, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(export)} synthetic conversations to {OUT}")


if __name__ == "__main__":
    main()
