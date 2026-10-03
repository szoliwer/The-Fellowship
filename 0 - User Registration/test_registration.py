"""Checks for Step 0. Run from the repo root:

    .venv/bin/python -m unittest discover -s "0 - User Registration"
"""

import json
import sqlite3
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

import registration as reg

PASSWORD = "correct horse battery"  # test value only


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "fellowship.db"

    def tearDown(self):
        self.tmp.cleanup()

    def create(self, pseudonym="neuro_lab_17", email="ada@example.com", password=PASSWORD, consent=True, **kw):
        return reg.create_account(pseudonym, email, password, consent, db_file=self.db, **kw)

    def test_demo_users_match_the_shared_fixture_ids(self):
        demos = {u["user_id"]: u["pseudonym"] for u in reg.demo_users(self.db)}
        self.assertEqual(demos, {"user_a": "researcher_014", "user_b": "cellbio_027"})

    def test_create_account_returns_agreed_record(self):
        user = self.create(name="Ada Lovelace", affiliation="MIT")
        self.assertEqual(
            set(user), {"user_id", "pseudonym", "connection_intent", "is_demo_account", "private", "consent"}
        )
        self.assertEqual(user["private"], {"name": "Ada Lovelace", "email": "ada@example.com", "affiliation": "MIT"})
        self.assertFalse(user["is_demo_account"])
        self.assertIs(user["consent"]["process_imported_chats"], True)
        self.assertEqual(reg.get_user(user["user_id"], self.db), user)

    def test_password_is_never_stored_in_plain_text(self):
        self.create()
        raw = self.db.read_bytes()
        self.assertNotIn(PASSWORD.encode(), raw)
        with sqlite3.connect(self.db) as conn:
            stored = conn.execute("SELECT password_hash FROM credentials").fetchone()[0]
        self.assertTrue(stored.startswith("scrypt$"))

    def test_users_export_for_later_steps_has_no_password_data(self):
        self.create()
        exported = json.loads((self.db.parent / "users.json").read_text())
        self.assertEqual([u["pseudonym"] for u in exported], ["researcher_014", "cellbio_027", "neuro_lab_17"])
        self.assertNotIn("scrypt", json.dumps(exported))

    def test_users_export_has_the_fields_step_5_reads(self):
        self.create(name="Ada Lovelace")
        exported = {u["pseudonym"]: u for u in json.loads((self.db.parent / "users.json").read_text())}
        u = exported["neuro_lab_17"]
        self.assertEqual(u["name"], "neuro_lab_17")            # intros use the pseudonym, never the real name
        self.assertEqual(u["private"]["name"], "Ada Lovelace")  # the real name stays under private only
        self.assertIs(u["consent"]["analyse_chats"], True)
        self.assertEqual(u["match_types"], ["similar", "complementary"])
        self.assertEqual(u["looking_for"], ["collaborator"])

    def test_declined_consent_is_passed_on_to_matching(self):
        user = reg.get_user("user_a", self.db)
        user["consent"]["process_imported_chats"] = False
        self.assertIs(reg.for_matching(user)["consent"]["analyse_chats"], False)

    def test_log_in_with_right_password_case_insensitive_email(self):
        user = self.create()
        self.assertEqual(reg.log_in("  ADA@example.com ", PASSWORD, db_file=self.db), user)

    def test_wrong_password_and_unknown_email_give_the_same_error(self):
        self.create()
        for email, password in [("ada@example.com", "wrong password!"), ("nobody@example.com", PASSWORD)]:
            with self.assertRaises(reg.RegistrationError) as ctx:
                reg.log_in(email, password, db_file=self.db)
            self.assertEqual(ctx.exception.code, "bad_credentials")

    def test_lockout_after_repeated_wrong_passwords(self):
        self.create()
        now = reg._now()
        for _ in range(reg.MAX_FAILED_LOGINS):
            with self.assertRaises(reg.RegistrationError):
                reg.log_in("ada@example.com", "wrong password!", db_file=self.db, now=now)
        with self.assertRaises(reg.RegistrationError) as ctx:
            reg.log_in("ada@example.com", PASSWORD, db_file=self.db, now=now)
        self.assertEqual(ctx.exception.code, "locked")
        later = now + timedelta(minutes=reg.LOCKOUT_MINUTES + 1)
        self.assertEqual(reg.log_in("ada@example.com", PASSWORD, db_file=self.db, now=later)["pseudonym"],
                         "neuro_lab_17")

    def test_demo_accounts_cannot_be_logged_into_with_a_password(self):
        with self.assertRaises(reg.RegistrationError):
            reg.log_in("", "", db_file=self.db)

    def test_consent_is_required(self):
        with self.assertRaises(reg.RegistrationError) as ctx:
            self.create(consent=False)
        self.assertEqual(ctx.exception.code, "consent_required")

    def test_input_rules(self):
        cases = [
            (dict(pseudonym="Has Caps"), "invalid_pseudonym"),
            (dict(pseudonym="ab"), "invalid_pseudonym"),
            (dict(email="not-an-email"), "invalid_email"),
            (dict(password="short"), "weak_password"),
            (dict(password="neuro_lab_17"), "weak_password"),
            (dict(pseudonym="lovelace_lab", name="Ada Lovelace"), "pseudonym_reveals_name"),
        ]
        for kwargs, code in cases:
            with self.assertRaises(reg.RegistrationError, msg=code) as ctx:
                self.create(**kwargs)
            self.assertEqual(ctx.exception.code, code)

    def test_email_and_pseudonym_must_be_unique(self):
        self.create()
        with self.assertRaises(reg.RegistrationError) as ctx:
            self.create(pseudonym="other_lab_99", email="ADA@example.com")
        self.assertEqual(ctx.exception.code, "email_taken")
        for taken in ["neuro_lab_17", "researcher_014"]:
            with self.assertRaises(reg.RegistrationError) as ctx:
                self.create(pseudonym=taken, email="new@example.com")
            self.assertEqual(ctx.exception.code, "pseudonym_taken")

    def test_public_view_hides_private_details(self):
        user = self.create(name="Ada Lovelace", affiliation="MIT")
        self.assertEqual(reg.public_view(user),
                         {"pseudonym": "neuro_lab_17", "connection_intent": "research collaboration"})


if __name__ == "__main__":
    unittest.main()
