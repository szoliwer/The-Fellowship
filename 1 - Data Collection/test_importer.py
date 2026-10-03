"""Checks for Step 1. Run from the repo root:

    .venv/bin/python -m unittest discover -s "1 - Data Collection"
"""

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import importer as im

FIXTURE_BYTES = im.DEMO_FIXTURE.read_bytes()


class DemoHistoryTests(unittest.TestCase):
    def setUp(self):
        self.sources, self.skipped = im.import_demo_history("user_a", imported_at="2026-10-03T20:00:00Z")
        self.by_id = {s["source_id"]: s for s in self.sources}

    def test_baseline_nine_conversations_with_shared_ids(self):
        self.assertEqual(sorted(self.by_id), [f"a_s{i:02d}" for i in range(1, 10)])
        self.assertEqual(self.skipped, [])

    def test_every_source_is_owned_and_has_provenance(self):
        for s in self.sources:
            self.assertEqual(s["user_id"], "user_a")
            self.assertEqual(s["source_type"], "demo")
            p = s["provenance"]
            self.assertEqual(p["original_conversation_id"], s["source_id"])
            self.assertTrue(p["title"])
            self.assertTrue(p["created_at"].endswith("Z"))
            self.assertEqual(p["imported_at"], "2026-10-03T20:00:00Z")
            self.assertEqual(p["message_ids"], [m["message_id"] for m in s["messages"]])
            self.assertIsNone(p["derived_from_source_id"])

    def test_roles_and_order_are_preserved(self):
        s = self.by_id["a_s01"]
        self.assertEqual([m["role"] for m in s["messages"]], ["user", "assistant", "user", "assistant"])
        self.assertTrue(s["raw_text"].startswith("User: In fibroblasts"))
        self.assertIn("\n\nAssistant: It's a reasonable hypothesis", s["raw_text"])

    def test_only_the_selected_branch_is_imported(self):
        self.assertNotIn("ABANDONED-BRANCH", self.by_id["a_s02"]["raw_text"])

    def test_hidden_system_messages_and_images_are_skipped(self):
        for s in self.sources:
            self.assertTrue(all(m["role"] in ("user", "assistant") for m in s["messages"]))
        texts = [m["text"] for m in self.by_id["a_s04"]["messages"]]
        self.assertIn("Here's a screenshot of two runs on the same paper. The second run missed two variants.", texts)
        self.assertNotIn("file-service", self.by_id["a_s04"]["raw_text"])

    def test_demo_history_only_for_its_demo_owner(self):
        with self.assertRaises(im.ImportFailed) as ctx:
            im.import_demo_history("user_b")
        self.assertEqual(ctx.exception.code, "demo_not_available")


class ChatGPTExportTests(unittest.TestCase):
    def test_real_uploads_get_owner_specific_ids(self):
        a, _ = im.import_chatgpt_export(FIXTURE_BYTES, "conversations.json", "user_x")
        b, _ = im.import_chatgpt_export(FIXTURE_BYTES, "conversations.json", "user_y")
        self.assertTrue(all(s["source_id"].startswith("src_") for s in a))
        self.assertTrue(all(s["source_type"] == "chatgpt_json" for s in a))
        self.assertTrue({s["source_id"] for s in a}.isdisjoint({s["source_id"] for s in b}))
        again, _ = im.import_chatgpt_export(FIXTURE_BYTES, "conversations.json", "user_x")
        self.assertEqual([s["source_id"] for s in a], [s["source_id"] for s in again])

    def test_zip_export(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("export-2026/conversations.json", FIXTURE_BYTES)
            zf.writestr("export-2026/user.json", "{}")
        sources, _ = im.import_chatgpt_export(buf.getvalue(), "chatgpt-export.zip", "user_x")
        self.assertEqual(len(sources), 9)

    def test_clear_errors_for_bad_input(self):
        cases = [
            (b"not json", "c.json", "malformed_json"),
            (b"[]", "c.json", "empty_export"),
            (b'{"hello": 1}', "c.json", "not_a_chatgpt_export"),
            (b"%PDF", "notes.pdf", "unsupported_file_type"),
            (b"not a zip", "export.zip", "bad_zip"),
            (b'[{"title": "x", "mapping": {}}]', "c.json", "nothing_importable"),
        ]
        for data, name, code in cases:
            with self.assertRaises(im.ImportFailed, msg=code) as ctx:
                im.import_chatgpt_export(data, name, "user_x")
            self.assertEqual(ctx.exception.code, code)
            self.assertEqual(set(ctx.exception.as_dict()), {"code", "message", "retryable"})

    def test_zip_without_conversations(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("user.json", "{}")
        with self.assertRaises(im.ImportFailed) as ctx:
            im.import_chatgpt_export(buf.getvalue(), "export.zip", "user_x")
        self.assertEqual(ctx.exception.code, "missing_conversations_json")

    def test_empty_conversations_are_reported_not_imported(self):
        export = json.loads(FIXTURE_BYTES)[:1] + [{"title": "Empty", "id": "e1", "mapping": {
            "root": {"id": "root", "message": None, "parent": None, "children": []}}, "current_node": "root"}]
        sources, skipped = im.import_chatgpt_export(json.dumps(export).encode(), "c.json", "user_x")
        self.assertEqual(len(sources), 1)
        self.assertEqual(skipped, [{"title": "Empty", "reason": "no user or assistant messages"}])

    def test_import_requires_a_user(self):
        with self.assertRaises(im.ImportFailed) as ctx:
            im.import_chatgpt_export(FIXTURE_BYTES, "c.json", "")
        self.assertEqual(ctx.exception.code, "missing_user")


class PastedTextTests(unittest.TestCase):
    def test_labelled_turns(self):
        text = "User: How do I test this?\nIt has two lines.\nChatGPT: Use a control.\nYou: Thanks"
        [s], _ = im.import_pasted_text(text, "user_x", title="Pasted test")
        self.assertEqual(s["source_type"], "pasted_text")
        self.assertEqual([m["role"] for m in s["messages"]], ["user", "assistant", "user"])
        self.assertEqual(s["messages"][0]["text"], "How do I test this?\nIt has two lines.")
        self.assertEqual(s["provenance"]["title"], "Pasted test")

    def test_unlabelled_text_is_one_user_message(self):
        [s], _ = im.import_pasted_text("Just my notes on assays.", "user_x")
        self.assertEqual([m["role"] for m in s["messages"]], ["user"])
        self.assertEqual(s["provenance"]["title"], "Just my notes on assays.")

    def test_empty_paste(self):
        with self.assertRaises(im.ImportFailed) as ctx:
            im.import_pasted_text("   ", "user_x")
        self.assertEqual(ctx.exception.code, "empty_paste")


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_load_and_reimport_without_duplicates(self):
        sources, _ = im.import_demo_history("user_a")
        im.save_sources("user_a", sources, self.dir)
        im.save_sources("user_a", sources, self.dir)
        self.assertEqual(len(im.load_sources("user_a", self.dir)), 9)
        saved = json.loads((self.dir / "user_a.json").read_text())
        self.assertEqual(saved["schema_version"], "1.0")
        self.assertEqual(saved["user_id"], "user_a")

    def test_cannot_save_someone_elses_chats(self):
        sources, _ = im.import_demo_history("user_a")
        with self.assertRaises(im.ImportFailed) as ctx:
            im.save_sources("user_b", sources, self.dir)
        self.assertEqual(ctx.exception.code, "wrong_owner")
        self.assertFalse((self.dir / "user_b.json").exists())

    def test_users_cannot_read_other_files(self):
        with self.assertRaises(im.ImportFailed):
            im.load_sources("../users", self.dir)


if __name__ == "__main__":
    unittest.main()
