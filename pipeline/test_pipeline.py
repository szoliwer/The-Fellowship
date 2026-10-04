"""Checks for the glue between steps. Free and offline (no API calls). Run from the repo root:

    .venv/bin/python -m unittest discover -s pipeline -t .
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for folder in ["3 - Idea Generation", "4 - Idea Ranking", "5 - Match Generation"]:
    sys.path.insert(0, str(ROOT / folder))

import review as rv  # noqa: E402  (Step 4)
from pipeline import matches as mt  # noqa: E402
from pipeline import messages as msg  # noqa: E402
from pipeline import ranking  # noqa: E402

STEP3_SAMPLE = ROOT / "3 - Idea Generation" / "samples" / "output" / "user_a.json"


class RankingTests(unittest.TestCase):
    def test_scores_put_primary_frequent_recent_ideas_first(self):
        rows = [
            {"idea_id": "old_once", "summary": "x", "tier": "secondary", "chat_count": 1, "mentions": 1,
             "last_seen": "2026-01-01"},
            {"idea_id": "main", "summary": "y", "tier": "primary", "chat_count": 3, "mentions": 6,
             "last_seen": "2026-09-10"},
            {"idea_id": "undated", "summary": "z", "tier": "secondary", "chat_count": 1, "mentions": 1,
             "last_seen": "unknown"},
        ]
        ranked = ranking.score_rows(rows)
        self.assertEqual([r["idea_id"] for r in ranked], ["main", "old_once", "undated"])
        self.assertEqual(ranked[0]["rank_score"], 1.0)
        self.assertEqual(set(ranked[0]["score_parts"]), {"primary", "chats", "mentions", "recency"})

    def test_step3_output_becomes_step4_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            step3, ranked_dir = Path(tmp) / "ideas", Path(tmp) / "ranked"
            step3.mkdir()
            (step3 / "user_a.json").write_text(STEP3_SAMPLE.read_text())
            ranking.rank_user("user_a", step3, ranked_dir)
            rows, is_sample = rv.load_ranked_rows("user_a", ranked_dir=ranked_dir, sample_file=None)
            cards = rv.build_cards(rows)
        source = json.loads(STEP3_SAMPLE.read_text())
        self.assertFalse(is_sample)
        self.assertEqual(len(cards), len(source["ideas"]))
        self.assertTrue(all(c["title"] and c["subs"] for c in cards))       # title = summary, details = insights
        self.assertEqual([c["score"] for c in cards], sorted((c["score"] for c in cards), reverse=True))
        adjacent = {a["claim"] for a in source["adjacent_ideas"]}
        self.assertFalse(adjacent & {c["title"] for c in cards})            # speculative ideas never copied


class TwoPersonMatch(unittest.TestCase):
    """One synthetic match between user_a and user_b, in temporary files (no checks of its own)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.matches, self.ideas, self.status = d / "matches.json", d / "ideas.json", d / "status.json"
        self.matches.write_text(json.dumps({
            "people": {"user_a": {"name": "researcher_014", "summary": "s_a"},
                       "user_b": {"name": "cellbio_027", "summary": "s_b"}},
            "matches": [{"match_id": "m_1", "user_a": "user_a", "user_b": "user_b", "match_type": "complementary",
                         "shared_or_linked_ideas": [["ia", "ib"]], "reason": "R",
                         "a_can_offer_b": "A offers", "b_can_offer_a": "B offers",
                         "intro_for_a": "intro for A", "intro_for_b": "intro for B"}],
        }))
        self.ideas.write_text(json.dumps({"ideas": [{"user_id": "user_a", "idea_id": "ia", "summary": "Idea A"},
                                                    {"user_id": "user_b", "idea_id": "ib", "summary": "Idea B"}]}))

    def tearDown(self):
        self.tmp.cleanup()

    def view(self, uid):
        [m] = mt.my_matches(uid, self.matches, self.ideas, self.status)
        return m


class MatchViewTests(TwoPersonMatch):
    def test_each_person_sees_their_own_side(self):
        a, b = self.view("user_a"), self.view("user_b")
        self.assertEqual((a["other_name"], a["they_can_offer"], a["linked"]), ("cellbio_027", "B offers", [("Idea A", "Idea B")]))
        self.assertEqual((b["other_name"], b["they_can_offer"], b["linked"]), ("researcher_014", "A offers", [("Idea B", "Idea A")]))
        self.assertEqual(mt.my_matches("user_z", self.matches, self.ideas, self.status), [])

    def test_intro_only_after_both_say_yes(self):
        self.assertEqual((self.view("user_a")["state"], self.view("user_a")["intro"]), ("new", None))
        mt.decide("user_a", "user_b", "connect", self.status)
        self.assertEqual((self.view("user_a")["state"], self.view("user_a")["intro"]), ("waiting", None))
        self.assertEqual(self.view("user_b")["state"], "new")  # B isn't told A said yes
        mt.decide("user_b", "user_a", "connect", self.status)
        self.assertEqual((self.view("user_a")["state"], self.view("user_a")["intro"]), ("connected", "intro for A"))
        self.assertEqual(self.view("user_b")["intro"], "intro for B")

    def test_a_pass_is_never_revealed(self):
        mt.decide("user_a", "user_b", "connect", self.status)
        mt.decide("user_b", "user_a", "pass", self.status)
        self.assertEqual(self.view("user_a")["state"], "waiting")   # A just keeps waiting
        self.assertEqual(self.view("user_b")["state"], "passed")
        self.assertIsNone(self.view("user_a")["intro"])
        with self.assertRaises(ValueError):
            mt.decide("user_a", "user_b", "maybe", self.status)


class MessageTests(TwoPersonMatch):
    """Messages between a connected pair."""

    def setUp(self):
        super().setUp()
        d = Path(self.tmp.name)
        self.messages, self.users = d / "messages.json", d / "users.json"
        self.users.write_text(json.dumps([{"user_id": "user_a", "pseudonym": "researcher_014"},
                                          {"user_id": "user_b", "pseudonym": "cellbio_027"}]))

    def files(self):
        return dict(status_file=self.status, messages_file=self.messages, users_file=self.users,
                    matches_file=self.matches, ideas_file=self.ideas)

    def send(self, frm, to, text):
        msg.send(frm, to, text, status_file=self.status, messages_file=self.messages)

    def connect_both(self):
        mt.decide("user_a", "user_b", "connect", self.status)
        mt.decide("user_b", "user_a", "connect", self.status)

    def test_no_messages_until_both_say_yes(self):
        mt.decide("user_a", "user_b", "connect", self.status)
        with self.assertRaises(msg.MessageError):
            self.send("user_a", "user_b", "hello")
        self.assertEqual(msg.conversations("user_a", **self.files()), [])
        self.assertFalse(self.messages.exists())

    def test_connected_pair_can_talk_and_unread_is_counted(self):
        self.connect_both()
        self.send("user_a", "user_b", "Hi! Want to compare assays?")
        self.send("user_a", "user_b", "Line one\nline two")
        [a] = msg.conversations("user_a", **self.files())
        [b] = msg.conversations("user_b", **self.files())
        self.assertEqual((a["other_name"], a["unread"], a["intro"]), ("cellbio_027", 0, "intro for A"))
        self.assertEqual((b["other_name"], b["unread"], b["intro"]), ("researcher_014", 2, "intro for B"))
        self.assertEqual([m["from"] for m in b["messages"]], ["user_a", "user_a"])
        msg.mark_read("user_b", "user_a", messages_file=self.messages)
        self.assertEqual(msg.unread_total("user_b", **self.files()), 0)

    def test_empty_or_too_long_messages_are_refused(self):
        self.connect_both()
        for text in ("", "   ", "x" * (msg.MAX_LENGTH + 1)):
            with self.assertRaises(msg.MessageError):
                self.send("user_a", "user_b", text)

    def test_a_later_pass_closes_the_conversation(self):
        self.connect_both()
        self.send("user_b", "user_a", "Hello")
        mt.decide("user_b", "user_a", "pass", self.status)
        self.assertEqual(msg.conversations("user_a", **self.files()), [])
        with self.assertRaises(msg.MessageError):
            self.send("user_a", "user_b", "Are you there?")


class OfflineFlowTests(unittest.TestCase):
    """Step 4 approval → Step 5 (offline mode) → Step 6 view, on Step 4's synthetic sample users."""

    def test_approved_sample_ideas_flow_to_a_match_and_intro(self):
        import match_generation as mg  # Step 5

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            approved, ideas_file = d / "approved", d / "ideas.json"
            for uid in ("user_a", "user_b"):
                rows, _ = rv.load_ranked_rows(uid, ranked_dir=d / "none")
                cards = rv.build_cards(rows)
                state = rv.start_state(uid, cards, approved_dir=approved)
                rv.save_approved(uid, state, cards, approved_dir=approved, matching_file=ideas_file)
            users = d / "users.json"
            users.write_text(json.dumps([
                {"user_id": "user_a", "name": "researcher_014", "consent": {"analyse_chats": True}},
                {"user_id": "user_b", "name": "cellbio_027", "consent": {"analyse_chats": True}}]))
            matches_file, status = d / "matches.json", d / "status.json"
            mg.run(str(ideas_file), str(matches_file), mg.Settings(offline=True), users_path=str(users))
            a = mt.my_matches("user_a", matches_file, ideas_file, status)
            self.assertTrue(a, "the complementary sample researchers should match")
            mt.decide("user_a", "user_b", "connect", status)
            mt.decide("user_b", "user_a", "connect", status)
            [a] = [m for m in mt.my_matches("user_a", matches_file, ideas_file, status) if m["other_id"] == "user_b"]
            self.assertEqual(a["state"], "connected")
            self.assertTrue(a["intro"])
            self.assertNotIn("Maya", json.dumps(a))  # pseudonyms only


if __name__ == "__main__":
    unittest.main()
