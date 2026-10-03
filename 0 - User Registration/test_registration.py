"""Checks for Step 0. Run from the repo root:

    .venv/bin/python -m unittest discover -s "0 - User Registration"
"""

import json
import tempfile
import unittest
from pathlib import Path

import registration as reg


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data_file = Path(self.tmp.name) / "data" / "users.json"

    def tearDown(self):
        self.tmp.cleanup()

    def create(self, pseudonym="neuro_lab_17", consent=True, **kwargs):
        return reg.create_user(pseudonym, consent, data_file=self.data_file, **kwargs)

    def test_demo_users_match_the_shared_fixture_ids(self):
        demos = {u["user_id"]: u["pseudonym"] for u in reg.demo_users()}
        self.assertEqual(demos, {"user_a": "researcher_014", "user_b": "cellbio_027"})

    def test_create_user_saves_record_in_agreed_format(self):
        user = self.create(name="Ada Lovelace", email="ada@example.com")
        self.assertEqual(
            set(user), {"user_id", "pseudonym", "connection_intent", "is_demo_account", "private", "consent"}
        )
        self.assertEqual(user["connection_intent"], "research collaboration")
        self.assertIs(user["consent"]["process_imported_chats"], True)
        self.assertTrue(user["consent"]["timestamp"].endswith("Z"))
        saved = json.loads(self.data_file.read_text())
        self.assertEqual(saved, [user])

    def test_consent_is_required(self):
        with self.assertRaises(reg.RegistrationError) as ctx:
            self.create(consent=False)
        self.assertEqual(ctx.exception.code, "consent_required")
        self.assertFalse(self.data_file.exists())

    def test_pseudonym_rules(self):
        for bad in ["", "ab", "Has Caps", "x" * 31, "bad-dash"]:
            with self.assertRaises(reg.RegistrationError, msg=bad):
                self.create(pseudonym=bad)

    def test_pseudonym_cannot_be_taken_twice_or_reuse_demo_names(self):
        self.create(pseudonym="neuro_lab_17")
        for taken in ["neuro_lab_17", "researcher_014"]:
            with self.assertRaises(reg.RegistrationError) as ctx:
                self.create(pseudonym=taken)
            self.assertEqual(ctx.exception.code, "pseudonym_taken")

    def test_pseudonym_cannot_contain_real_name(self):
        with self.assertRaises(reg.RegistrationError) as ctx:
            self.create(pseudonym="lovelace_lab", name="Ada Lovelace")
        self.assertEqual(ctx.exception.code, "pseudonym_reveals_name")

    def test_public_view_hides_private_details(self):
        user = self.create(name="Ada Lovelace", email="ada@example.com", affiliation="MIT")
        public = reg.public_view(user)
        self.assertEqual(public, {"pseudonym": "neuro_lab_17", "connection_intent": "research collaboration"})


if __name__ == "__main__":
    unittest.main()
