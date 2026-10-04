"""Checks for Step 2. Run from the repo root (free: uses a fake classifier, no API calls):

    .venv/bin/python -m unittest discover -s "2 - Noise Filter"
"""

import sys
import tempfile
import time
import unittest
from pathlib import Path

import screening as sc

sys.path.insert(0, str(sc.REPO_ROOT / "1 - Data Collection"))
import importer as im  # noqa: E402

M = sc.REDACTION_MARKER


def ans(decision, reason="none", cats=(), redact=(), remove=()):
    """A classifier answer. redact: (message number, exact quote) pairs; remove: message numbers."""
    return {"decision": decision, "exclusion_reason": reason, "sensitive_categories": list(cats),
            "redactions": [{"message": n, "quote": q} for n, q in redact],
            "remove_message_numbers": list(remove), "explanation": "Fake explanation."}


# What a correct classifier should say about the demo history (shared brief, section 11).
EXPECTED = {
    "In fibroblasts": ans("eligible"),
    "Our immunofluorescence": ans("eligible"),
    "I'm honestly uncertain": ans("eligible"),
    "We're using an LLM": ans("eligible"),
    "Following up on extraction": ans("eligible"),
    "I've had headaches": ans("exclude", "sensitive", ["personal_health"]),
    "Help me plan repayments": ans("exclude", "sensitive", ["financial"]),
    "I land at 14:20": ans("exclude", "administrative"),
}

# A synthetic mixed chat: research with personal details woven into the user's own sentences,
# plus a drafted email that is entirely personal.
MIXED_CHAT = (
    "User: Does AI capex look like a bubble by the price-share test? I'm asking for my thesis at Example U.\n"
    "Assistant: Partly: prices and capex shares decouple after 2024.\n"
    "User: Draft an email to Prof. Example saying I'm Jane Testperson and my uncle is a senator.\n"
    "Assistant: Dear Prof. Example, my name is Jane Testperson...\n"
    "User: Back to the research: what would falsify the bubble story for Jane Testperson's thesis?\n"
    "Assistant: A capability-threshold event study would."
)
CLEAN_MIXED = ans("clean", cats=["own_identity", "third_party_personal"],
                  redact=[(0, "for my thesis at Example U"), (4, "Jane Testperson")], remove=[2, 3])


class FakeClassifier:
    model = "fake"

    def __init__(self, answers=None, fail=False, delay=0.0):
        self.calls, self.stages, self.timings = [], [], []
        self.answers = answers if answers is not None else EXPECTED
        self.fail = fail
        self.delay = delay

    def __call__(self, text, stage="first"):
        start = time.monotonic()
        time.sleep(self.delay)
        self.timings.append((start, time.monotonic()))
        self.calls.append(text)
        self.stages.append(stage)
        if self.fail:
            raise sc.ScreeningError("no_connection", "Couldn't reach the AI service.", retryable=True)
        for key, answer in self.answers.items():
            if key in text:
                return answer
        return ans("eligible")


class RuleTests(unittest.TestCase):
    def test_rules_catch_secrets_and_numbers(self):
        cases = {
            "my key is sk-ant-abcdefghijklmnopqrstuvwxyz123": ["credential"],
            "password: hunter22": ["credential"],
            "card 4111 1111 1111 1111 exp 12/29": ["card_number"],
            "IBAN GB82WEST12345698765432": ["bank_account"],
            "SSN 123-45-6789": ["id_number"],
            "my passport number is X1234567": ["id_number"],
            "Driver's license: D123-4567-8901": ["id_number"],
            "national insurance AB 12 34 56 C": ["id_number"],
            "tax ID 98-7654321 for the grant": ["id_number"],
            "patient MRN-0000123": ["medical_record"],
        }
        for text, hits in cases.items():
            self.assertEqual(sc.rule_hits(text), hits, msg=text)

    def test_rules_ignore_normal_research_text(self):
        sources, _ = im.parse_demo_history("user_a")
        for s in sources[:5]:
            self.assertEqual(sc.rule_hits(s["raw_text"]), [], msg=s["source_id"])
        for text in ["Run 2026-09-04 gave 1234567890123 reads", "p < 0.05 across 4,000,000 cells",
                     "the password problem in cryptography research",
                     "passport data are used in migration studies", "sample ID 10234 in the cohort",
                     "national ID systems and digital identity research"]:
            self.assertEqual(sc.rule_hits(text), [], msg=text)

    def test_instructions_cover_the_owners_rules(self):
        for phrase in ["even a single passing mention", "Drafts of emails", "family members (always",
                       "academic record", "admissions", "degree program", "career and recruiting plans",
                       "own company and project names", "EXACT text to blank out", "[title]",
                       "flipped a meaning", "never turn a personal matter into a research interest",
                       "what decides is whether real research", "woven through it is \"clean\""]:
            self.assertIn(phrase, sc.SYSTEM_PROMPT)

    def test_masking_contact_details(self):
        masked = sc.mask_contact_details("Email ada@lab.org or call +1 617-555-0134. Date 2026-09-04.")
        self.assertEqual(masked, "Email [email removed] or call [phone removed]. Date 2026-09-04.")


class RedactionTests(unittest.TestCase):
    def msgs(self, *texts):
        return [{"message_id": f"m{i}", "role": "user" if i % 2 == 0 else "assistant", "text": t,
                 "created_at": None} for i, t in enumerate(texts)]

    def test_find_spans_everywhere_and_ignores_spacing_differences(self):
        m = self.msgs("I am Jane Testperson.", "Hello Jane\nTestperson!", "Nothing here")
        self.assertEqual(sc.find_spans(m, "Jane Testperson"), [["m0", 5, 20], ["m1", 6, 21]])
        self.assertEqual(sc.find_spans(m, "   "), [])

    def test_overlapping_spans_merge_and_text_is_blanked(self):
        merged = sc.merge_spans([["m0", 5, 10], ["m0", 8, 15], ["m0", 20, 22], ["m1", 0, 3]])
        self.assertEqual(merged, {"m0": [(5, 15), (20, 22)], "m1": [(0, 3)]})
        self.assertEqual(sc.redact_text("abcdefghij", [(2, 4), (6, 8)]), f"ab{M}ef{M}ij")


class ScreeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.out = self.dir / "output"
        im.import_demo("user_a", data_dir=self.dir)

    def tearDown(self):
        self.tmp.cleanup()

    def screen(self, classifier, user_id="user_a"):
        return sc.screen_user(user_id, classify=classifier, data_dir=self.dir, max_workers=1, output_dir=self.out)

    def ids(self, user_id="user_a"):
        """source_ids Step 3 receives: the Markdown files in output/<user_id>/."""
        return sorted(f.stem for f in (self.out / user_id).glob("*.md"))

    def read_handoff(self, user_id, source_id):
        text = (self.out / user_id / f"{source_id}.md").read_text(encoding="utf-8")
        _, header, body = text.split("---\n", 2)
        fields = dict(line.split(": ", 1) for line in header.strip().splitlines())
        return fields, body.strip()

    def import_mixed(self, user_id="user_m"):
        im.import_paste(user_id, MIXED_CHAT, title="AI and financial crisis", data_dir=self.dir)
        return im.load_sources(user_id, self.dir)[0]

    # --- baseline, ordering, privacy of the report ---

    def test_demo_history_gives_the_expected_baseline(self):
        report = self.screen(FakeClassifier())
        eligible = sorted(k for k, e in report.items() if sc.is_eligible(e))
        self.assertEqual(eligible, ["a_s01", "a_s02", "a_s03", "a_s04", "a_s05"])
        self.assertEqual(report["a_s06"]["sensitive_category"], ["personal_health"])
        self.assertEqual(report["a_s07"]["sensitive_category"], ["financial"])
        self.assertEqual(report["a_s08"]["exclusion_reason"], "administrative")
        self.assertEqual(report["a_s09"]["rule_hits"], ["medical_record"])

    def test_cache_warm_up_runs_one_chat_before_the_rest(self):
        fake = FakeClassifier(delay=0.05)
        sc.screen_user("user_a", classify=fake, data_dir=self.dir, max_workers=4, output_dir=self.out)
        first_end = fake.timings[0][1]
        self.assertTrue(all(start >= first_end for start, _ in fake.timings[1:]))
        self.assertEqual(len(fake.calls), 8)

    def test_rule_hits_are_never_sent_to_the_ai(self):
        fake = FakeClassifier()
        self.screen(fake)
        self.assertEqual(len(fake.calls), 8)
        self.assertFalse(any("MRN-0000123" in c for c in fake.calls))

    def test_ai_sees_numbered_messages(self):
        fake = FakeClassifier()
        self.screen(fake)
        call = next(c for c in fake.calls if "In fibroblasts" in c)
        self.assertTrue(call.startswith("[title]\nCould trafficking explain the Disease A phenotype?\n\n"
                                        "[message 0 · User]\nIn fibroblasts"))
        self.assertIn("[message 1 · Assistant]", call)

    def test_report_contains_no_chat_text(self):
        report = self.screen(FakeClassifier())
        dumped = (self.dir / "filter" / "user_a.json").read_text()
        self.assertNotIn("headaches", dumped)
        self.assertNotIn("MRN-0000123", dumped)
        self.assertEqual(set(report["a_s01"]) - {"model"}, {
            "source_id", "title", "content_hash", "prompt_version", "screened_at", "rule_hits", "status",
            "decision", "exclusion_reason", "sensitive_category", "explanation", "removed_message_ids",
            "redacted_spans", "total_messages", "recheck", "error", "owner_excluded"})

    # --- the handoff files (HANDOFF.md) ---

    def test_handoff_folder_has_one_file_per_usable_chat(self):
        self.screen(FakeClassifier())
        self.assertEqual(self.ids(), ["a_s01", "a_s02", "a_s03", "a_s04", "a_s05"])
        self.assertEqual([p.name for p in self.out.iterdir()], ["user_a"])

    def test_handoff_file_format(self):
        self.screen(FakeClassifier())
        fields, body = self.read_handoff("user_a", "a_s01")
        self.assertEqual(list(fields), ["schema_version", "user_id", "source_id", "title", "created_at",
                                        "imported_at", "source_type", "original_conversation_id",
                                        "message_count", "derived_from_source_id"])
        self.assertEqual(fields["schema_version"], '"1.0"')
        self.assertEqual(fields["user_id"], "user_a")
        self.assertEqual(fields["source_id"], "a_s01")
        self.assertEqual(fields["title"], '"Could trafficking explain the Disease A phenotype?"')
        self.assertEqual(fields["created_at"], "2026-09-04T12:00:00Z")
        self.assertEqual(fields["source_type"], "demo")
        self.assertEqual(fields["derived_from_source_id"], "null")
        self.assertTrue(body.startswith("**User:** In fibroblasts"))
        turns = [line for line in body.splitlines() if line.startswith(("**User:** ", "**Assistant:** "))]
        self.assertEqual(int(fields["message_count"]), len(turns))
        self.assertIn("\n\n**Assistant:** It's a reasonable hypothesis", body)
        _, body4 = self.read_handoff("user_a", "a_s04")
        self.assertIn("[image omitted]", body4)

    def test_handoff_quotes_awkward_titles_and_masks_contacts(self):
        im.import_paste("user_q", "User: Email ada@lab.org about assays?\nAssistant: Yes.",
                        title='Q: "bubbles" #1', data_dir=self.dir)
        self.screen(FakeClassifier({}), "user_q")
        [sid] = self.ids("user_q")
        fields, body = self.read_handoff("user_q", sid)
        self.assertEqual(fields["title"], '"Q: \\"bubbles\\" #1"')
        self.assertEqual(fields["created_at"], "null")
        self.assertNotIn("ada@lab.org", body)
        self.assertIn("[email removed]", body)

    def test_handoff_never_contains_held_back_text(self):
        self.screen(FakeClassifier())
        everything = "".join(p.read_text() for p in (self.out / "user_a").glob("*.md"))
        for leak in ["headaches", "repayments", "14:20", "MRN-0000123", "Jordan"]:
            self.assertNotIn(leak, everything)

    # --- cleaning mixed chats: blank out phrases, remove wholly personal messages ---

    def test_mixed_chat_keeps_the_users_own_sentences_with_phrases_blanked(self):
        source = self.import_mixed()
        fake = FakeClassifier({"Jane Testperson": CLEAN_MIXED})
        entry = self.screen(fake, "user_m")[source["source_id"]]
        self.assertEqual(entry["decision"], "cleaned")
        self.assertEqual(fake.stages, ["first", "recheck"])
        self.assertNotIn("Jane Testperson", fake.calls[1])  # the re-check only sees the cleaned copy
        self.assertEqual(sc.cleaning_counts(entry), (2, 2))
        self.assertEqual(sc.cleaning_summary(entry),
                         "Cleaned: 2 personal details blanked out, 2 of 6 messages removed "
                         "(your name, record or applications, other people's personal details)")

        [used] = sc.used_versions("user_m", self.dir)
        texts = [m["text"] for m in used["messages"]]
        self.assertEqual(texts[0], f"Does AI capex look like a bubble by the price-share test? I'm asking {M}.")
        self.assertEqual(texts[2], f"Back to the research: what would falsify the bubble story for {M}'s thesis?")
        self.assertEqual(len(texts), 4)
        self.assertNotIn("Jane Testperson", used["raw_text"])
        self.assertNotIn("senator", used["raw_text"])
        self.assertNotIn("Example U", used["raw_text"])

        self.assertEqual(self.ids("user_m"), [source["source_id"] + "_clean"])
        fields, body = self.read_handoff("user_m", source["source_id"] + "_clean")
        self.assertEqual(fields["derived_from_source_id"], source["source_id"])
        self.assertEqual(fields["message_count"], "4")
        self.assertNotIn("Jane Testperson", body)
        report_text = (self.dir / "filter" / "user_m.json").read_text()
        for personal in ["Jane Testperson", "Example U", "senator"]:
            self.assertNotIn(personal, report_text)  # only positions are stored

    def test_a_quote_is_blanked_everywhere_it_appears(self):
        source = self.import_mixed()
        answer = ans("clean", cats=["own_identity"], redact=[(2, "Jane Testperson")], remove=[3])
        entry = sc.screen_source(source, FakeClassifier({"Jane Testperson": answer}))
        self.assertEqual(entry["decision"], "cleaned")
        cleaned = sc.cleaned_source(source, entry)
        self.assertNotIn("Jane Testperson", cleaned["raw_text"])
        self.assertEqual(cleaned["raw_text"].count(M), 2)  # message 2 and message 4

    def test_quotes_that_cannot_be_matched_remove_their_message(self):
        source = self.import_mixed()
        for quote in ["text that is not in the chat", "AI"]:  # not found / too short to blank safely
            answer = ans("clean", cats=["own_identity"], redact=[(0, quote)], remove=[2, 3])
            entry = sc.screen_source(source, FakeClassifier({"Jane Testperson": answer}))
            self.assertIn(source["messages"][0]["message_id"], entry["removed_message_ids"], msg=quote)

    def test_rechecks_that_find_more_keep_cleaning_until_nothing_is_left(self):
        source = self.import_mixed()
        first = ans("clean", cats=["own_identity"], redact=[(0, "for my thesis at Example U")], remove=[2, 3])
        # The re-check sees 4 messages; message 2 there is the original message 4.
        more = ans("clean", cats=["own_identity"], redact=[(2, "Jane Testperson")])
        fake = FakeClassifier({"Draft an email": first, "Jane Testperson": more})
        entry = sc.screen_source(source, fake)
        self.assertEqual(entry["decision"], "cleaned")
        self.assertEqual([r["decision"] for r in entry["recheck"]], ["clean", "eligible"])
        self.assertEqual(fake.stages, ["first", "recheck", "recheck"])
        self.assertNotIn("Jane Testperson", sc.cleaned_source(source, entry)["raw_text"])

    def test_cleaned_copy_that_fails_the_recheck_is_held_back(self):
        source = self.import_mixed()
        fake = FakeClassifier({"Jane Testperson": CLEAN_MIXED,
                               "price-share test": ans("exclude", "sensitive", ["other_sensitive"])})
        entry = self.screen(fake, "user_m")[source["source_id"]]
        self.assertEqual(entry["exclusion_reason"], "recheck_failed")
        self.assertEqual(self.ids("user_m"), [])

    def test_gives_up_when_rechecks_keep_finding_more(self):
        source = self.import_mixed()
        fake = FakeClassifier({"Assistant]": ans("clean", cats=["own_identity"], remove=[0])})
        entry = self.screen(fake, "user_m")[source["source_id"]]
        self.assertFalse(sc.is_eligible(entry))
        self.assertLessEqual(len(fake.calls), 1 + sc.MAX_RECHECKS)

    def test_removing_most_of_a_chat_is_fine_if_the_recheck_passes(self):
        source = self.import_mixed()  # no "more than half" limit any more: the re-check decides
        fake = FakeClassifier({"price-share test": ans("clean", cats=["own_identity"], remove=[0, 1, 2, 3])})
        entry = self.screen(fake, "user_m")[source["source_id"]]
        self.assertEqual(entry["decision"], "cleaned")
        self.assertEqual(sc.cleaning_counts(entry), (0, 4))
        self.assertEqual(len(fake.calls), 2)

    def test_nothing_of_the_users_own_left_holds_the_chat_back(self):
        source = self.import_mixed()
        fake = FakeClassifier({"Jane Testperson": ans("clean", cats=["own_identity"], remove=[0, 2, 4])})
        entry = self.screen(fake, "user_m")[source["source_id"]]
        self.assertEqual((entry["decision"], entry["exclusion_reason"]), ("exclude", "too_much_personal"))
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(self.ids("user_m"), [])

    # --- titles are screened and cleaned too ---

    def test_personal_title_is_blanked_in_the_handoff(self):
        im.import_paste("user_t", "User: Which IV design suits enforcement timing?\nAssistant: An event study.",
                        title="Grade appeal for Jane Testperson", data_dir=self.dir)
        source = im.load_sources("user_t", self.dir)[0]
        fake = FakeClassifier({"Jane Testperson": ans("clean", cats=["own_identity"],
                                                      redact=[(-1, "Grade appeal for Jane Testperson")])})
        entry = self.screen(fake, "user_t")[source["source_id"]]
        self.assertEqual(entry["decision"], "cleaned")
        self.assertTrue(fake.calls[0].startswith("[title]\nGrade appeal for Jane Testperson"))
        fields, body = self.read_handoff("user_t", source["source_id"] + "_clean")
        self.assertEqual(fields["title"], f'"{M}"')
        self.assertIn("IV design", body)

    def test_unmatched_title_quote_blanks_the_whole_title(self):
        im.import_paste("user_t", "User: Which IV design suits enforcement timing?\nAssistant: An event study.",
                        title="Notes for Jane Testperson", data_dir=self.dir)
        source = im.load_sources("user_t", self.dir)[0]
        fake = FakeClassifier({"Jane Testperson": ans("clean", cats=["own_identity"], redact=[(-1, "not there")])})
        entry = sc.screen_source(source, fake)
        self.assertEqual(sc.cleaned_source(source, entry)["provenance"]["title"], M)

    def test_secret_in_title_holds_the_chat_back_without_ai(self):
        im.import_paste("user_t", "User: Which IV design suits enforcement timing?\nAssistant: An event study.",
                        title="Passport number X1234567 renewal", data_dir=self.dir)
        fake = FakeClassifier()
        entry = list(self.screen(fake, "user_t").values())[0]
        self.assertEqual(entry["rule_hits"], ["id_number"])
        self.assertEqual(fake.calls, [])

    def test_inconsistent_answers_lean_towards_holding_back(self):
        source = self.import_mixed()
        for answer in [ans("clean", cats=["own_identity"]),                        # nothing to remove
                       ans("clean", cats=["own_identity"], remove=[99]),           # out of range
                       ans("eligible", cats=["own_identity"])]:                    # eligible, but found some
            entry = sc.screen_source(source, FakeClassifier({"Jane Testperson": answer}))
            self.assertFalse(sc.is_eligible(entry), msg=answer)
        # "eligible" with things marked is treated as "clean"
        entry = sc.screen_source(source, FakeClassifier({"Jane Testperson": CLEAN_MIXED}))
        self.assertEqual(entry["decision"], "cleaned")

    def test_owner_can_hold_back_a_cleaned_chat(self):
        source = self.import_mixed()
        self.screen(FakeClassifier({"Jane Testperson": CLEAN_MIXED}), "user_m")
        sc.set_owner_excluded("user_m", source["source_id"], True, self.dir, output_dir=self.out)
        self.assertEqual(self.ids("user_m"), [])

    # --- failures, re-screening, owner choices ---

    def test_failures_are_held_back_and_retried_next_time(self):
        report = self.screen(FakeClassifier(fail=True))
        self.assertEqual({e["status"] for k, e in report.items() if k != "a_s09"}, {"failed"})
        self.assertEqual(self.ids(), [])
        report = self.screen(FakeClassifier())
        self.assertEqual(sum(sc.is_eligible(e) for e in report.values()), 5)

    def test_already_screened_chats_are_not_sent_again(self):
        self.screen(FakeClassifier())
        second = FakeClassifier()
        self.screen(second)
        self.assertEqual(second.calls, [])
        im.import_paste("user_a", "User: In fibroblasts a new question\nAssistant: ok", data_dir=self.dir)
        third = FakeClassifier()
        self.screen(third)
        self.assertEqual(len(third.calls), 1)

    def test_invalid_answers_are_failures(self):
        report = self.screen(FakeClassifier({"In fibroblasts": {"decision": "maybe"}}))
        self.assertEqual(report["a_s01"]["status"], "failed")
        self.assertFalse(sc.is_eligible(report["a_s01"]))

    def test_owner_can_hold_back_and_undo(self):
        self.screen(FakeClassifier())
        sc.set_owner_excluded("user_a", "a_s01", True, self.dir, output_dir=self.out)
        self.assertNotIn("a_s01", self.ids())
        self.assertEqual(sc.display_reason(sc.load_report("user_a", self.dir)["a_s01"]),
                         "You chose to hold this back")
        sc.set_owner_excluded("user_a", "a_s01", False, self.dir, output_dir=self.out)
        self.assertIn("a_s01", self.ids())
        sc.set_owner_excluded("user_a", "a_s06", False, self.dir, output_dir=self.out)
        self.assertNotIn("a_s06", self.ids())  # undo never makes a held-back chat eligible

    def test_owner_choice_survives_rescreening(self):
        self.screen(FakeClassifier())
        sc.set_owner_excluded("user_a", "a_s02", True, self.dir, output_dir=self.out)
        report = sc.load_report("user_a", self.dir)
        report["a_s02"]["status"] = "failed"
        sc._save_report("user_a", report, self.dir)
        report = self.screen(FakeClassifier())
        self.assertTrue(report["a_s02"]["owner_excluded"])

    def test_chats_removed_in_step_1_are_forgotten(self):
        self.screen(FakeClassifier())
        self.assertIn("a_s01", self.ids())
        im.remove_sources("user_a", ["a_s01", "a_s06"], data_dir=self.dir)
        report = sc.sync_with_sources("user_a", self.dir, self.out)
        self.assertNotIn("a_s01", self.ids())                      # Step 3 can no longer read it
        self.assertEqual(self.ids(), ["a_s02", "a_s03", "a_s04", "a_s05"])
        self.assertFalse({"a_s01", "a_s06"} & set(report))
        self.assertFalse({"a_s01", "a_s06"} & set(sc.load_report("user_a", self.dir)))

    def test_cost_estimate_skips_rule_hits(self):
        est = sc.estimate_cost(sc.pending_sources("user_a", self.dir))
        self.assertEqual(est["chats_to_send"], 8)
        self.assertGreater(est["dollars"], 0)

    def test_no_classifier_needed_when_nothing_to_screen(self):
        self.assertEqual(sc.screen_user("user_z", data_dir=self.dir, output_dir=self.out), {})


if __name__ == "__main__":
    unittest.main()
