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

CLAUDE_EXPORT = [  # synthetic, in the shape of claude.ai's conversations.json
    {
        "uuid": "c-0001", "name": "Assay controls", "created_at": "2026-09-01T10:00:00.123456Z",
        "chat_messages": [
            {"uuid": "m1", "sender": "human", "text": "Which controls rule out assay artifacts?",
             "created_at": "2026-09-01T10:00:01Z"},
            {"uuid": "m2", "sender": "assistant", "text": "",
             "content": [{"type": "text", "text": "Use a pathway blocker and an unaffected protein."}],
             "files": [{"file_kind": "image", "file_name": "plot.png"}],
             "created_at": "2026-09-01T10:00:05Z"},
        ],
    },
    {"uuid": "c-0002", "name": "", "created_at": "2026-09-02T10:00:00Z", "chat_messages": []},
]


def make_zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


class DemoHistoryTests(unittest.TestCase):
    def setUp(self):
        self.sources, self.skipped = im.parse_demo_history("user_a", imported_at="2026-10-03T20:00:00Z")
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

    def test_hidden_system_messages_skipped_and_images_marked(self):
        texts = [m["text"] for m in self.by_id["a_s04"]["messages"]]
        self.assertIn("[image omitted]\nHere's a screenshot of two runs on the same paper. "
                      "The second run missed two variants.", texts)
        self.assertNotIn("file-service", self.by_id["a_s04"]["raw_text"])

    def test_second_demo_researcher_has_own_history(self):
        sources, _ = im.parse_demo_history("user_b")
        self.assertEqual([s["source_id"] for s in sources], ["b_s01", "b_s02"])
        self.assertTrue(all(s["user_id"] == "user_b" for s in sources))
        self.assertIn("pilot", sources[0]["raw_text"])

    def test_demo_history_only_for_demo_researchers(self):
        with self.assertRaises(im.ImportFailed) as ctx:
            im.parse_demo_history("user_x")
        self.assertEqual(ctx.exception.code, "demo_not_available")


class ExportTests(unittest.TestCase):
    def test_chatgpt_json_and_zip(self):
        a, _ = im.parse_upload(FIXTURE_BYTES, "conversations.json", "user_x")
        z, _ = im.parse_upload(make_zip({"export/conversations.json": FIXTURE_BYTES, "export/user.json": "{}"}),
                               "chatgpt-export.zip", "user_x")
        self.assertEqual(len(a), 9)
        self.assertEqual([s["source_id"] for s in a], [s["source_id"] for s in z])
        self.assertTrue(all(s["source_type"] == "chatgpt_json" and s["source_id"].startswith("src_") for s in a))

    def test_only_dialogue_messages_are_imported(self):
        conv = json.loads(FIXTURE_BYTES)[0]
        leaf = conv["current_node"]
        extras = [("thoughts", "HIDDEN-THOUGHTS"), ("reasoning_recap", "HIDDEN-RECAP"), ("code", "HIDDEN-CODE")]
        for i, (ctype, text) in enumerate(extras):
            node_id = f"extra-{i}"
            conv["mapping"][node_id] = {"id": node_id, "parent": leaf, "children": [], "message": {
                "id": node_id, "author": {"role": "assistant"}, "create_time": None,
                "content": {"content_type": ctype, "parts": [text]}, "metadata": {}}}
            conv["mapping"][leaf]["children"].append(node_id)
            leaf = node_id
        conv["current_node"] = leaf
        [s], _ = im.parse_upload(json.dumps([conv]).encode(), "c.json", "user_x")
        self.assertNotIn("HIDDEN", s["raw_text"])
        self.assertEqual(len(s["messages"]), 4)

    def test_ids_are_per_owner_and_stable(self):
        a, _ = im.parse_upload(FIXTURE_BYTES, "conversations.json", "user_x")
        b, _ = im.parse_upload(FIXTURE_BYTES, "conversations.json", "user_y")
        again, _ = im.parse_upload(FIXTURE_BYTES, "conversations.json", "user_x")
        self.assertTrue({s["source_id"] for s in a}.isdisjoint({s["source_id"] for s in b}))
        self.assertEqual([s["source_id"] for s in a], [s["source_id"] for s in again])

    def test_claude_export(self):
        data = json.dumps(CLAUDE_EXPORT).encode()
        sources, skipped = im.parse_upload(make_zip({"conversations.json": data, "users.json": "[]"}),
                                           "claude-export.zip", "user_x")
        [s] = sources
        self.assertEqual(s["source_type"], "claude_json")
        self.assertEqual(s["provenance"]["title"], "Assay controls")
        self.assertEqual(s["provenance"]["created_at"], "2026-09-01T10:00:00Z")
        self.assertEqual([m["role"] for m in s["messages"]], ["user", "assistant"])
        self.assertEqual(s["messages"][1]["text"], "Use a pathway blocker and an unaffected protein.\n[image omitted]")
        self.assertEqual(skipped, [{"title": "Untitled conversation", "reason": "no user or assistant messages"}])

    def test_clear_errors_for_bad_input(self):
        cases = [
            (b"not json", "c.json", "malformed_json"),
            (b"[]", "c.json", "empty_export"),
            (b'{"hello": 1}', "c.json", "not_a_chat_export"),
            (b"%PDF-1.7", "paper.pdf", "unsupported_file_type"),
            (b"not a zip", "export.zip", "bad_zip"),
            (b"", "notes.md", "empty_file"),
            (b"\x00\x01binary", "notes.txt", "not_text"),
            (make_zip({"photo.png": b"\x89PNG"}), "photos.zip", "nothing_importable"),
            (b'[{"title": "x", "mapping": {}}]', "c.json", "nothing_importable"),
        ]
        for data, name, code in cases:
            with self.assertRaises(im.ImportFailed, msg=code) as ctx:
                im.parse_upload(data, name, "user_x")
            self.assertEqual(ctx.exception.code, code, msg=name)
            self.assertEqual(set(ctx.exception.as_dict()), {"code", "message", "retryable"})

    def test_import_requires_a_user(self):
        with self.assertRaises(im.ImportFailed) as ctx:
            im.parse_upload(FIXTURE_BYTES, "c.json", "")
        self.assertEqual(ctx.exception.code, "missing_user")


class TextTests(unittest.TestCase):
    def parse(self, text, name="notes.md"):
        [s], _ = im.parse_upload(text.encode(), name, "user_x")
        return s

    def roles(self, s):
        return [m["role"] for m in s["messages"]]

    def test_markdown_headings(self):
        s = self.parse("# Assay planning\n\n## User\nWhich assay?\n\n## ChatGPT\nTry pulse-chase.\n\n---\n\n## User\nThanks")
        self.assertEqual(s["source_type"], "text_file")
        self.assertEqual(s["provenance"]["title"], "Assay planning")
        self.assertEqual(self.roles(s), ["user", "assistant", "user"])
        self.assertEqual(s["messages"][1]["text"], "Try pulse-chase.")

    def test_bold_labels_and_quotes(self):
        s = self.parse("**You:** First question\nsecond line\n\n**Claude**: An answer\n> **User:** Follow-up")
        self.assertEqual(self.roles(s), ["user", "assistant", "user"])
        self.assertEqual(s["messages"][0]["text"], "First question\nsecond line")

    def test_chatgpt_copy_paste_said_labels(self):
        s = self.parse("You said:\nIs this a trafficking defect?\nChatGPT said:\nPossibly.", "chat.txt")
        self.assertEqual(self.roles(s), ["user", "assistant"])
        self.assertEqual(s["provenance"]["title"], "chat")

    def test_chatgpt_exporter_extension_style(self):
        # Shape of files saved by browser "export chat" tools: '# you asked' / '# chatgpt response',
        # a 'message time:' line per turn, and a '> From:' source link at the top.
        text = ("> From: https://chatgpt.com/c/synthetic-0001\n\n"
                "# you asked\n\nmessage time: 2026-03-31 11:23:00\n\nDoes AI capex look like a bubble?\n\n"
                "---\n\n# chatgpt response\n\nmessage time: 2026-03-31 11:23:40\n\n"
                "## My bottom line\nPartly.\n\n### Test 1: Price-share decoupling\nIt is:\nmore nuanced.\n\n"
                "---\n\n# you asked\n\nmessage time: 2026-03-31 11:38:53\n\nWhat would falsify it?")
        s = self.parse(text, "AI-and-Financial-Crisis.md")
        self.assertEqual(self.roles(s), ["user", "assistant", "user"])
        self.assertEqual(s["provenance"]["title"], "AI-and-Financial-Crisis")
        self.assertEqual(s["provenance"]["created_at"], "2026-03-31T11:23:00Z")
        self.assertEqual([m["created_at"] for m in s["messages"]],
                         ["2026-03-31T11:23:00Z", "2026-03-31T11:23:40Z", "2026-03-31T11:38:53Z"])
        self.assertTrue(s["messages"][1]["text"].startswith("## My bottom line"))
        self.assertNotIn("message time", s["raw_text"])
        self.assertNotIn("chatgpt.com", s["raw_text"])

    def test_markdown_images_are_marked(self):
        s = self.parse("User: See this plot ![runs](https://example.org/plot.png)\nAssistant: Noted.")
        self.assertEqual(s["messages"][0]["text"], "See this plot [image omitted]")

    def test_prompt_response_headings(self):
        s = self.parse("## Prompt:\nWhich assay?\n\n## Response:\nA pulse-chase.\nResponse: times were short.")
        self.assertEqual(self.roles(s), ["user", "assistant"])
        self.assertIn("Response: times were short.", s["messages"][1]["text"])

    def test_front_matter_is_skipped(self):
        s = self.parse("---\ntitle: x\ndate: 2026-09-01\n---\nUser: Hello\nAssistant: Hi")
        self.assertEqual(self.roles(s), ["user", "assistant"])
        self.assertNotIn("date:", s["raw_text"])

    def test_unlabelled_notes_are_one_user_message(self):
        s = self.parse("Notes on assays.\n\nAI models might help here too.", "lab-notes.txt")
        self.assertEqual(self.roles(s), ["user"])
        self.assertEqual(s["provenance"]["title"], "lab-notes")

    def test_zip_of_text_files(self):
        data = make_zip({
            "chats/a.md": "User: one\nAssistant: two",
            "chats/b.txt": "plain notes",
            "chats/empty.md": "   ",
            "chats/picture.png": b"\x89PNG",
            "__MACOSX/chats/._a.md": "junk",
            ".DS_Store": "junk",
        })
        sources, skipped = im.parse_upload(data, "notes.zip", "user_x")
        self.assertEqual(sorted(s["provenance"]["title"] for s in sources), ["a", "b"])
        self.assertEqual(sorted(s["title"] for s in skipped), ["chats/empty.md", "chats/picture.png"])

    def test_pasted_text(self):
        [s], _ = im.parse_pasted_text("User: How do I test this?\nChatGPT: Use a control.", "user_x", title="T")
        self.assertEqual(s["source_type"], "pasted_text")
        self.assertEqual(self.roles(s), ["user", "assistant"])
        self.assertEqual(s["provenance"]["title"], "T")


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_upload_keeps_original_file_history_and_sources(self):
        result = im.import_file("user_x", FIXTURE_BYTES, "conversations.json", data_dir=self.dir)
        entry = result["upload"]
        self.assertEqual((entry["status"], entry["imported_count"]), ("imported", 9))
        self.assertEqual((self.dir / entry["stored_file"]).read_bytes(), FIXTURE_BYTES)
        self.assertEqual(len(im.load_sources("user_x", self.dir)), 9)
        self.assertTrue(all(s["provenance"]["upload_id"] == entry["upload_id"]
                            for s in im.load_sources("user_x", self.dir)))
        self.assertEqual(im.load_upload_log("user_x", self.dir), [entry])

    def test_reuploading_does_not_duplicate_conversations(self):
        im.import_file("user_x", FIXTURE_BYTES, "conversations.json", data_dir=self.dir)
        second = im.import_file("user_x", FIXTURE_BYTES, "conversations.json", data_dir=self.dir)
        self.assertEqual(second["total_sources"], 9)
        self.assertEqual(len(im.load_upload_log("user_x", self.dir)), 2)

    def test_failed_upload_is_logged_but_the_file_is_not_kept(self):
        with self.assertRaises(im.ImportFailed):
            im.import_file("user_x", b"%PDF-1.7 secret", "passport.pdf", data_dir=self.dir)
        [entry] = im.load_upload_log("user_x", self.dir)
        self.assertEqual(entry["status"], "failed")
        self.assertEqual(entry["error"]["code"], "unsupported_file_type")
        self.assertIsNone(entry["stored_file"])
        self.assertFalse((self.dir / "uploads" / "user_x" / "files").exists())
        self.assertEqual(im.load_sources("user_x", self.dir), [])

    def test_paste_and_demo_are_stored(self):
        im.import_paste("user_a", "User: hi\nAssistant: hello", data_dir=self.dir)
        im.import_demo("user_a", data_dir=self.dir)
        self.assertEqual(len(im.load_sources("user_a", self.dir)), 10)
        self.assertEqual([e["kind"] for e in im.load_upload_log("user_a", self.dir)], ["paste", "demo"])

    def test_users_storage_is_separate(self):
        im.import_file("user_x", FIXTURE_BYTES, "conversations.json", data_dir=self.dir)
        self.assertEqual(im.load_sources("user_y", self.dir), [])
        with self.assertRaises(im.ImportFailed):
            im.save_sources("user_y", im.load_sources("user_x", self.dir), self.dir)
        with self.assertRaises(im.ImportFailed):
            im.load_sources("../users", self.dir)

    def test_removing_one_chat_keeps_the_file_while_others_from_it_remain(self):
        result = im.import_file("user_x", FIXTURE_BYTES, "conversations.json", data_dir=self.dir)
        stored = self.dir / result["upload"]["stored_file"]
        ids = [s["source_id"] for s in im.load_sources("user_x", self.dir)]
        r = im.remove_sources("user_x", ids[:1], data_dir=self.dir)
        self.assertEqual(r, {"removed": 1, "files_deleted": 0, "files_kept": ["conversations.json"]})
        self.assertEqual([s["source_id"] for s in im.load_sources("user_x", self.dir)], ids[1:])
        self.assertTrue(stored.exists())

    def test_removing_the_last_chats_of_an_upload_deletes_its_file(self):
        result = im.import_file("user_x", FIXTURE_BYTES, "conversations.json", data_dir=self.dir)
        stored = self.dir / result["upload"]["stored_file"]
        ids = [s["source_id"] for s in im.load_sources("user_x", self.dir)]
        r = im.remove_sources("user_x", ids, data_dir=self.dir)
        self.assertEqual(r, {"removed": 9, "files_deleted": 1, "files_kept": []})
        self.assertEqual(im.load_sources("user_x", self.dir), [])
        self.assertFalse(stored.exists())
        [entry] = im.load_upload_log("user_x", self.dir)
        self.assertIsNone(entry["stored_file"])
        self.assertTrue(entry["removed_at"])

    def test_removal_only_touches_the_owners_chats(self):
        im.import_paste("user_x", "User: mine\nAssistant: ok", data_dir=self.dir)
        im.import_paste("user_y", "User: theirs\nAssistant: ok", data_dir=self.dir)
        theirs = im.load_sources("user_y", self.dir)[0]["source_id"]
        self.assertEqual(im.remove_sources("user_x", [theirs, "not-a-chat"], data_dir=self.dir)["removed"], 0)
        self.assertEqual(len(im.load_sources("user_y", self.dir)), 1)
        self.assertEqual(len(im.load_sources("user_x", self.dir)), 1)

    def test_stored_filename_is_made_safe(self):
        result = im.import_file("user_x", b"User: hi", "../../etc/evil notes.md", data_dir=self.dir)
        stored = (self.dir / result["upload"]["stored_file"]).resolve()
        self.assertTrue(str(stored).startswith(str((self.dir / "uploads" / "user_x" / "files").resolve())))


if __name__ == "__main__":
    unittest.main()
