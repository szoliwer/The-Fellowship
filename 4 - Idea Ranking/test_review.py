"""Checks for the Step 4 review page logic. Run from the repo root:

    .venv/bin/python -m unittest discover -s "4 - Idea Ranking"

All data here is synthetic.
"""

import json
import tempfile
import unittest
from pathlib import Path

import review as rv


def cards_for(user_id="user_a"):
    rows, _ = rv.load_ranked_rows(user_id, ranked_dir="/nonexistent")
    return rv.build_cards(rows)


def card(cards, idea_id):
    return next(c for c in cards if c["idea_id"] == idea_id)


class LoadingTests(unittest.TestCase):
    def test_sample_is_used_and_marked_until_real_files_exist(self):
        rows, is_sample = rv.load_ranked_rows("user_a", ranked_dir="/nonexistent")
        self.assertTrue(is_sample)
        self.assertEqual({r["user_id"] for r in rows}, {"user_a"})  # never another user's ideas

    def test_cards_are_most_central_first(self):
        cards = cards_for()
        scores = [c["score"] for c in cards]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(cards[0]["idea_id"], "user_a_c01")
        self.assertEqual(len(cards), 5)

    def test_real_ranked_file_wins_and_other_users_rows_are_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "user_a.json").write_text(json.dumps({"ideas": [
                {"user_id": "user_a", "idea_id": "x1", "main_idea": "Mine", "insights": ["a"], "rank_score": 0.5},
                {"user_id": "user_b", "idea_id": "y1", "main_idea": "Not mine", "insights": ["b"], "rank_score": 0.9},
            ]}))
            rows, is_sample = rv.load_ranked_rows("user_a", ranked_dir=d)
            self.assertFalse(is_sample)
            self.assertEqual([r["idea_id"] for r in rows], ["x1"])
            self.assertIn("user_a", rv.available_users(ranked_dir=d))

    def test_spec_format_rows_use_summary_and_keywords(self):
        cards = rv.build_cards([{"user_id": "u", "idea_id": "i_1", "type": "need", "summary": "Fish-call classifier",
                                 "keywords": ["audio", "few labels"], "score": 0.9}])
        self.assertEqual(cards[0]["title"], "Fish-call classifier")
        self.assertEqual([s["text"] for s in cards[0]["subs"]], ["audio", "few labels"])
        self.assertEqual(cards[0]["detail_field"], "keywords")

    def test_odd_rows_are_handled(self):
        cards = rv.build_cards([
            {"idea_id": "a", "main_idea": "Has duplicate details", "insights": ["same", "same", "", "  "]},
            {"idea_id": "b", "main_idea": "No details at all"},
            {"idea_id": "c", "main_idea": "   "},  # no title: skipped
        ])
        self.assertEqual([c["idea_id"] for c in cards], ["a", "b"])
        subs = cards[0]["subs"]
        self.assertEqual(len(subs), 2)
        self.assertNotEqual(subs[0]["sub_id"], subs[1]["sub_id"])
        self.assertEqual(cards[1]["subs"], [])
        state = rv.new_state(cards)
        rv.restore_all(state, cards)  # an idea with no details at all stays as it is
        self.assertEqual(rv.idea_status(state, cards[1]), "all")
        self.assertFalse(state["ideas"]["b"]["removed"])

    def test_bad_input_gives_clear_errors(self):
        with self.assertRaises(rv.ReviewError) as e:
            rv.load_ranked_rows("../etc")
        self.assertEqual(e.exception.code, "invalid_user")
        with tempfile.TemporaryDirectory() as d:
            Path(d, "user_a.json").write_text("{not json")
            with self.assertRaises(rv.ReviewError) as e:
                rv.load_ranked_rows("user_a", ranked_dir=d)
            self.assertEqual(e.exception.code, "malformed_json")


class CheckboxRuleTests(unittest.TestCase):
    def setUp(self):
        self.cards = cards_for()
        self.state = rv.new_state(self.cards)
        self.c = card(self.cards, "user_a_c01")  # 4 details
        self.subs = [s["sub_id"] for s in self.c["subs"]]

    def test_everything_starts_included(self):
        self.assertEqual(rv.counts(self.state, self.cards), (5, 19))
        self.assertTrue(all(rv.idea_status(self.state, c) == "all" for c in self.cards))

    def test_unchecking_a_main_idea_excludes_all_its_details(self):
        rv.toggle_idea(self.state, self.c)
        self.assertEqual(rv.idea_status(self.state, self.c), "none")
        self.assertFalse(any(rv.sub_is_on(self.state, self.c, s) for s in self.subs))
        self.assertEqual(rv.counts(self.state, self.cards), (4, 15))

    def test_unchecking_one_detail_makes_the_idea_partly_checked(self):
        rv.toggle_sub(self.state, self.c, self.subs[1])
        self.assertEqual(rv.idea_status(self.state, self.c), "some")
        self.assertEqual(rv.counts(self.state, self.cards), (5, 18))

    def test_unchecking_every_detail_unchecks_the_main_idea(self):
        for s in self.subs:
            rv.toggle_sub(self.state, self.c, s)
        self.assertEqual(rv.idea_status(self.state, self.c), "none")
        self.assertEqual(rv.counts(self.state, self.cards), (4, 15))
        rv.toggle_idea(self.state, self.c)  # checking it again brings every detail back
        self.assertEqual(rv.idea_status(self.state, self.c), "all")

    def test_rechecking_a_main_idea_restores_earlier_picks(self):
        rv.toggle_sub(self.state, self.c, self.subs[1])
        rv.toggle_idea(self.state, self.c)  # off
        rv.toggle_idea(self.state, self.c)  # on again
        self.assertEqual(rv.idea_status(self.state, self.c), "some")
        self.assertFalse(rv.sub_is_on(self.state, self.c, self.subs[1]))
        self.assertTrue(rv.sub_is_on(self.state, self.c, self.subs[0]))

    def test_checking_a_detail_of_an_unchecked_idea_brings_back_just_that_detail(self):
        rv.toggle_idea(self.state, self.c)
        rv.toggle_sub(self.state, self.c, self.subs[2])
        self.assertEqual(rv.idea_status(self.state, self.c), "some")
        self.assertEqual([rv.sub_is_on(self.state, self.c, s) for s in self.subs], [False, False, True, False])


class RemoveAndUndoTests(unittest.TestCase):
    def setUp(self):
        self.cards = cards_for()
        self.state = rv.new_state(self.cards)
        self.c = card(self.cards, "user_a_c01")
        self.subs = [s["sub_id"] for s in self.c["subs"]]

    def test_removing_an_idea_excludes_it_and_undo_puts_it_back(self):
        rv.remove_idea(self.state, self.c)
        self.assertEqual(rv.counts(self.state, self.cards), (4, 15))
        self.assertIn(self.c, rv.visible_cards(self.state, self.cards))  # still drawn, as "Removed · Undo"
        rv.undo(self.state)
        self.assertEqual(rv.counts(self.state, self.cards), (5, 19))
        self.assertIsNone(self.state["undo"])

    def test_removal_becomes_final_after_the_next_change(self):
        rv.remove_idea(self.state, self.c)
        rv.toggle_idea(self.state, card(self.cards, "user_a_c02"))
        self.assertIsNone(self.state["undo"])
        self.assertNotIn(self.c, rv.visible_cards(self.state, self.cards))
        self.assertEqual(rv.removed_count(self.state, self.cards), 1)

    def test_a_second_removal_replaces_the_first_undo(self):
        rv.remove_idea(self.state, self.c)
        other = card(self.cards, "user_a_c02")
        rv.remove_idea(self.state, other)
        rv.undo(self.state)
        self.assertFalse(self.state["ideas"][other["idea_id"]]["removed"])
        self.assertTrue(self.state["ideas"][self.c["idea_id"]]["removed"])

    def test_removing_a_detail_and_undo(self):
        rv.remove_sub(self.state, self.c, self.subs[0])
        self.assertEqual(rv.counts(self.state, self.cards), (5, 18))
        self.assertEqual(rv.idea_status(self.state, self.c), "all")  # the 3 remaining details are all checked
        self.assertEqual(self.state["undo"]["kind"], "sub")
        rv.undo(self.state)
        self.assertEqual(rv.counts(self.state, self.cards), (5, 19))

    def test_removing_the_last_checked_detail_unchecks_the_idea_and_undo_restores_it(self):
        for s in self.subs[1:]:
            rv.toggle_sub(self.state, self.c, s)
        rv.remove_sub(self.state, self.c, self.subs[0])
        self.assertEqual(rv.idea_status(self.state, self.c), "none")
        rv.undo(self.state)
        self.assertEqual(rv.idea_status(self.state, self.c), "some")

    def test_removing_every_detail_removes_the_idea_and_undo_brings_both_back(self):
        for s in self.subs[:-1]:
            rv.remove_sub(self.state, self.c, s)
        self.assertFalse(self.state["ideas"][self.c["idea_id"]]["removed"])  # one detail left: idea stays
        rv.remove_sub(self.state, self.c, self.subs[-1])
        self.assertTrue(self.state["ideas"][self.c["idea_id"]]["removed"])
        self.assertEqual(self.state["undo"]["kind"], "idea")                  # "Removed <idea title> · Undo"
        self.assertEqual(rv.counts(self.state, self.cards), (4, 15))
        self.assertEqual([r["idea_id"] for r in rv.approved_rows(self.state, self.cards)].count("user_a_c01"), 0)
        rv.undo(self.state)
        self.assertFalse(self.state["ideas"][self.c["idea_id"]]["removed"])
        self.assertEqual(len(rv.live_subs(self.state, self.c)), 1)

    def test_restore_all_brings_back_an_idea_with_its_details_if_they_were_all_removed(self):
        for s in self.subs:
            rv.remove_sub(self.state, self.c, s)
        for c in self.cards:
            if not self.state["ideas"][c["idea_id"]]["removed"]:
                rv.remove_idea(self.state, c)
        rv.restore_all(self.state, self.cards)
        self.assertEqual(rv.counts(self.state, self.cards), (5, 19))

    def test_old_saved_choices_with_every_detail_removed_load_as_removed(self):
        rec = {"details_removed": self.subs}
        state = rv.apply_record(rv.new_state(self.cards), rec, self.cards)
        self.assertTrue(state["ideas"][self.c["idea_id"]]["removed"])

    def test_restore_all_brings_back_ideas_but_not_details_removed_on_purpose(self):
        rv.remove_sub(self.state, self.c, self.subs[0])
        for c in self.cards:
            rv.remove_idea(self.state, c)
        self.assertEqual(rv.counts(self.state, self.cards), (0, 0))
        rv.restore_all(self.state, self.cards)
        self.assertEqual(rv.counts(self.state, self.cards), (5, 18))
        self.assertTrue(self.state["subs"][self.subs[0]]["removed"])


class OutputTests(unittest.TestCase):
    def setUp(self):
        self.cards = cards_for()
        self.state = rv.new_state(self.cards)
        self.tmp = tempfile.TemporaryDirectory()
        self.approved_dir = Path(self.tmp.name, "approved_ideas")
        self.matching_file = Path(self.tmp.name, "ideas.json")

    def tearDown(self):
        self.tmp.cleanup()

    def save(self, user_id="user_a", state=None, cards=None):
        return rv.save_approved(user_id, state or self.state, cards or self.cards,
                                approved_dir=self.approved_dir, matching_file=self.matching_file,
                                now="2026-10-03T21:00:00Z")

    def test_only_approved_parts_are_written_and_raw_text_never(self):
        c1, c2, c4 = (card(self.cards, i) for i in ("user_a_c01", "user_a_c02", "user_a_c04"))
        rv.toggle_sub(self.state, c1, c1["subs"][1]["sub_id"])
        rv.remove_sub(self.state, c1, c1["subs"][3]["sub_id"])
        rv.toggle_idea(self.state, c2)
        rv.remove_idea(self.state, c4)
        rows = rv.approved_rows(self.state, self.cards)
        self.assertEqual([r["idea_id"] for r in rows], ["user_a_c01", "user_a_c03", "user_a_c05"])
        self.assertEqual(rows[0]["insights"], [c1["row"]["insights"][0], c1["row"]["insights"][2]])
        self.assertEqual(rows[0]["evidence"], ["a_s01"])
        self.assertEqual(rows[0]["rank_score"], 0.92)
        self.assertTrue(all("raw_text" not in r for r in rows))
        self.assertIn("raw_text", c1["row"])  # the input itself is untouched

    def test_spec_format_keeps_its_own_fields(self):
        cards = rv.build_cards([{"user_id": "u", "idea_id": "i_1", "summary": "S", "keywords": ["k1", "k2"], "score": 0.9}])
        state = rv.new_state(cards)
        rv.toggle_sub(state, cards[0], cards[0]["subs"][0]["sub_id"])
        self.assertEqual(rv.approved_rows(state, cards), [{"user_id": "u", "idea_id": "i_1", "summary": "S",
                                                           "keywords": ["k2"], "score": 0.9}])

    def test_save_writes_the_user_file_and_the_combined_file_for_step_5(self):
        rv.toggle_idea(self.state, card(self.cards, "user_a_c05"))
        result = self.save()
        self.assertEqual((result["ideas"], result["details"]), (4, 15))
        saved = json.loads(Path(self.approved_dir, "user_a.json").read_text())
        self.assertEqual(saved["user_id"], "user_a")
        self.assertEqual(saved["approved_at"], "2026-10-03T21:00:00Z")
        self.assertEqual(len(saved["ideas"]), 4)
        self.assertNotIn("Disease A", json.dumps(saved["review"]))  # the record holds IDs, never text

        b_cards = cards_for("user_b")
        self.save("user_b", rv.new_state(b_cards), b_cards)
        self.save()  # saving again replaces, never duplicates
        combined = json.loads(self.matching_file.read_text())["ideas"]
        self.assertEqual(len(combined), 4 + 4)
        self.assertEqual({r["user_id"] for r in combined}, {"user_a", "user_b"})

    def test_choices_come_back_next_time_and_new_ideas_start_included(self):
        c1 = card(self.cards, "user_a_c01")
        rv.toggle_sub(self.state, c1, c1["subs"][0]["sub_id"])
        rv.toggle_idea(self.state, card(self.cards, "user_a_c02"))
        rv.remove_idea(self.state, card(self.cards, "user_a_c04"))
        self.save()

        again = rv.start_state("user_a", self.cards, approved_dir=self.approved_dir)
        self.assertEqual(rv.review_record(again, self.cards), rv.review_record(self.state, self.cards))
        self.assertEqual(rv.review_record(again, self.cards),
                         rv.load_saved_record("user_a", approved_dir=self.approved_dir))

        rows, _ = rv.load_ranked_rows("user_a", ranked_dir="/nonexistent")
        new_cards = rv.build_cards(rows + [{"user_id": "user_a", "idea_id": "user_a_c99", "main_idea": "New idea",
                                            "insights": ["x"], "rank_score": 0.99}])
        again = rv.start_state("user_a", new_cards, approved_dir=self.approved_dir)
        self.assertEqual(rv.idea_status(again, card(new_cards, "user_a_c99")), "all")
        self.assertNotEqual(rv.review_record(again, new_cards),  # so the page shows "not saved yet"
                            rv.load_saved_record("user_a", approved_dir=self.approved_dir))

    def test_nothing_the_user_did_not_see_is_copied(self):
        cards = rv.build_cards([
            {"user_id": "user_a", "idea_id": "x", "main_idea": "Shown title", "summary": "Unseen summary",
             "insights": ["seen detail"], "keywords": ["unseen keyword"], "offers": ["unseen offer"],
             "description": "unseen text", "raw_text": "chat", "rank_score": 0.5, "evidence": ["a_s01"]},
            {"user_id": "user_a", "idea_id": "y", "main_idea": "Details stored as objects",
             "insights": [{"text": "never shown"}], "rank_score": 0.4},
        ])
        rows = rv.approved_rows(rv.new_state(cards), cards)
        self.assertEqual(rows[0], {"user_id": "user_a", "idea_id": "x", "main_idea": "Shown title",
                                   "insights": ["seen detail"], "rank_score": 0.5, "evidence": ["a_s01"]})
        self.assertNotIn("never shown", json.dumps(rows))

    def test_rows_without_ids_get_a_stable_id_and_the_owner(self):
        rows = [{"main_idea": "No ID here", "insights": ["d"]}, {"main_idea": "Another", "insights": ["e"]}]
        cards = rv.build_cards(rows)
        self.assertEqual({c["idea_id"] for c in cards}, {c["idea_id"] for c in rv.build_cards(rows[::-1])})
        self.save(state=rv.new_state(cards), cards=cards)
        saved = json.loads(Path(self.approved_dir, "user_a.json").read_text())["ideas"]
        self.assertEqual({r["user_id"] for r in saved}, {"user_a"})
        self.assertEqual({r["idea_id"] for r in saved}, {c["idea_id"] for c in cards})

    def test_saving_with_nothing_checked_withdraws_the_users_ideas(self):
        self.save()
        for c in self.cards:
            rv.toggle_idea(self.state, c)
        result = self.save()
        self.assertEqual(result["ideas"], 0)
        self.assertEqual(json.loads(self.matching_file.read_text())["ideas"], [])

    def test_a_damaged_file_from_another_user_does_not_block_saving(self):
        self.approved_dir.mkdir(parents=True)
        Path(self.approved_dir, "user_b.json").write_text("{broken")
        self.save()
        self.assertEqual(len(json.loads(self.matching_file.read_text())["ideas"]), 5)

    def test_cannot_save_someone_elses_ideas(self):
        with self.assertRaises(rv.ReviewError) as e:
            self.save("user_b")
        self.assertEqual(e.exception.code, "wrong_owner")


if __name__ == "__main__":
    unittest.main()
