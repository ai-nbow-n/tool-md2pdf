import hashlib
import http.client
import io
import json
import os
import socket
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from app import app
import services.llm as llm_module
from services.documents import apply_line_edits
from services.llm import (AssistantUnavailable, CHAT_MODEL, CHAT_TIMEOUT_SECONDS, EDIT_SCHEMA,
                          MAX_CONVERSATION_CHARS, MAX_DOCUMENT_CHARS, TRUNCATED, WRITE_INSTRUCTIONS,
                          WRITE_SCHEMA, to_line_edits)


def answer(reply="Updated the city name.", edits=None):
    """What Ollama's /api/chat returns, carrying the model's JSON."""
    if edits is None:
        edits = [{"find": "Vienna", "replace": "Wien"}]
    return {"message": {"role": "assistant", "content": json.dumps({"reply": reply, "edits": edits})}}


class ChatBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "trip.md"
        self.path.write_text("# Trip\n\nVienna\nBratislava\n", encoding="utf-8")
        self.client = app.test_client()
        patcher = patch("services.llm._ollama")
        self.ollama = patcher.start()
        self.addCleanup(patcher.stop)
        self.ollama.return_value = answer()
        llm_module._RATE["events"].clear()

    def document(self):
        return {"filename": "trip.md", "input_dir": self.temp.name,
                "content": self.path.read_text(encoding="utf-8"),
                "disk_revision": hashlib.sha256(self.path.read_bytes()).hexdigest()}

    def body(self, text="Change Vienna to Wien."):
        return {"messages": [{"role": "user", "content": text}], "document": self.document()}

    def sent(self, call=-1):
        path, payload = self.ollama.call_args_list[call].args[:2]
        self.assertEqual(path, "/api/chat")
        return payload

    def test_context_includes_unsaved_text_and_does_not_write_until_apply(self):
        body = self.body()
        body["document"]["content"] += "Unsaved note\n"
        original = self.path.read_bytes()
        response = self.client.post("/api/llm/chat", json=body)
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(self.path.read_bytes(), original)
        payload = self.sent()
        self.assertEqual(payload["model"], CHAT_MODEL)
        self.assertIs(payload["stream"], False)
        self.assertEqual(payload["format"], EDIT_SCHEMA)
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertIn("Unsaved note", payload["messages"][0]["content"])
        self.assertIn('<document name="trip.md">', payload["messages"][0]["content"])
        self.assertNotIn("api_key", json.dumps(payload))
        self.assertEqual(response.json["edits"], [{"start_line": 3, "end_line": 3, "replacement": ["Wien"]}])
        saved = self.client.post("/api/llm/apply", json={
            "document": body["document"], "edits": response.json["edits"],
            "disk_revision": response.json["disk_revision"]})
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "# Trip\n\nWien\nBratislava\nUnsaved note\n")
        self.assertEqual(saved.json["disk_revision"], hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_next_turn_loads_updated_context(self):
        body = self.body()
        first = self.client.post("/api/llm/chat", json=body).json
        self.client.post("/api/llm/apply", json={"document": body["document"], **first})
        self.ollama.return_value = answer("The first city is Wien.", [])
        second = self.client.post("/api/llm/chat", json=self.body("Which city is first?"))
        self.assertEqual(second.status_code, 200)
        self.assertIn("Wien", self.sent()["messages"][0]["content"])

    def test_question_does_not_edit(self):
        self.ollama.return_value = answer("Two cities.", [])
        before = self.path.read_bytes()
        response = self.client.post("/api/llm/chat", json=self.body("How many cities?"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["edits"], [])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.client.post("/api/llm/apply", json={
            "document": self.document(), "disk_revision": response.json["disk_revision"],
            "edits": []}).status_code, 400)

    def test_empty_document_is_written_from_its_own_prompt(self):
        # Nothing to quote or ask about: the model writes the whole document,
        # and never sees a <document> wrapper it could copy into the file.
        self.path.write_text("\n", encoding="utf-8")
        self.ollama.return_value = {"message": {"content": json.dumps({
            "markdown": "# Neuron\n\n## Parts\n\n- Soma\n- Axon", "reply": "I wrote an overview."})}}
        response = self.client.post("/api/llm/chat", json=self.body("Provide anatomy of a neuron"))
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(response.json["reply"], "I wrote an overview.")
        payload = self.sent()
        self.assertEqual(payload["format"], WRITE_SCHEMA)
        self.assertEqual(payload["messages"][0]["content"], WRITE_INSTRUCTIONS)
        self.assertNotIn("<document", payload["messages"][0]["content"])
        self.assertGreater(payload["options"]["num_predict"], llm_module.OPTIONS["num_predict"])
        saved = self.client.post("/api/llm/apply", json={
            "document": self.document(), "edits": response.json["edits"],
            "disk_revision": response.json["disk_revision"]})
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "# Neuron\n\n## Parts\n\n- Soma\n- Axon\n")

    def test_empty_document_without_a_request_for_text_only_replies(self):
        self.path.write_text("", encoding="utf-8")
        self.ollama.return_value = {"message": {"content": json.dumps({
            "markdown": "", "reply": "Tell me what to write."})}}
        response = self.client.post("/api/llm/chat", json=self.body("hello"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["edits"], [])
        self.assertEqual(self.path.read_text(encoding="utf-8"), "")

    def test_conflicts_before_chat_and_before_apply(self):
        body = self.body()
        first = self.client.post("/api/llm/chat", json=body).json
        self.path.write_text("External update", encoding="utf-8")
        calls = self.ollama.call_count
        self.assertEqual(self.client.post("/api/llm/chat", json=body).status_code, 409)
        self.assertEqual(self.ollama.call_count, calls)
        self.assertEqual(self.client.post("/api/llm/apply", json={"document": body["document"], **first}).status_code, 409)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "External update")

    def test_unmatched_edits_and_bad_json_are_not_written(self):
        before = self.path.read_bytes()
        self.ollama.return_value = answer(edits=[{"find": "Salzburg", "replace": "x"}])
        response = self.client.post("/api/llm/chat", json=self.body())
        self.assertEqual(response.status_code, 502)
        self.assertEqual(self.ollama.call_count, 2)  # one correction round
        self.ollama.return_value = {"message": {"content": "not json"}}
        self.assertEqual(self.client.post("/api/llm/chat", json=self.body()).status_code, 502)
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_document_and_traversal(self):
        for document in (None, {}, {**self.document(), "filename": "../outside.md"},
                         {**self.document(), "filename": "app.py"}):
            with self.subTest(document=document):
                body = {**self.body(), "document": document}
                self.assertEqual(self.client.post("/api/llm/chat", json=body).status_code, 400)
        self.ollama.assert_not_called()

    def test_document_and_conversation_caps(self):
        body = self.body()
        body["document"]["content"] = "x" * (MAX_DOCUMENT_CHARS + 1)
        response = self.client.post("/api/llm/chat", json=body)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json["max_document_chars"], MAX_DOCUMENT_CHARS)
        long_message = self.client.post("/api/llm/chat", json=self.body("y" * (MAX_CONVERSATION_CHARS + 1)))
        self.assertEqual(long_message.status_code, 400)
        self.assertIn("message is too long", long_message.json["error"])
        long_chat = self.body()
        long_chat["messages"] = [{"role": "user", "content": "y" * 3000},
                                 {"role": "assistant", "content": "z" * 3000},
                                 {"role": "user", "content": "Again?"}]
        self.assertIn("Start a new chat", self.client.post("/api/llm/chat", json=long_chat).json["error"])
        self.ollama.assert_not_called()

    def test_status_reports_model_and_availability(self):
        llm_module._STATUS["checked"] = float("-inf")
        self.ollama.return_value = {"models": [{"name": CHAT_MODEL}, {"name": "llama3.2:1b"}]}
        response = self.client.post("/api/llm/status", json={})
        self.assertEqual(response.json, {"model": CHAT_MODEL, "available": True,
                                         "max_document_chars": MAX_DOCUMENT_CHARS,
                                         "max_message_chars": MAX_CONVERSATION_CHARS})
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(self.ollama.call_args.args, ("/api/tags",))
        for failure in (AssistantUnavailable("down"), TimeoutError()):
            llm_module._STATUS["checked"] = float("-inf")
            self.ollama.side_effect = failure
            self.assertIs(self.client.post("/api/llm/status", json={}).json["available"], False)
        self.ollama.side_effect = None
        for tags in ({"models": [{"name": "llama3.2:1b"}]}, {"models": "odd"}, ["odd"]):
            llm_module._STATUS["checked"] = float("-inf")
            self.ollama.return_value = tags
            self.assertIs(self.client.post("/api/llm/status", json={}).json["available"], False)
        llm_module._STATUS["checked"] = float("-inf")

    def test_cross_origin_and_non_json_rejected(self):
        self.assertEqual(self.client.post("/api/llm/apply", json={}, headers={"Origin": "https://other.example"}).status_code, 403)
        self.assertEqual(self.client.post("/api/llm/chat", data="x").status_code, 415)

    def test_timeout_does_not_write_and_reports_budget(self):
        self.ollama.side_effect = TimeoutError()
        before = self.path.read_bytes()
        response = self.client.post("/api/llm/chat", json=self.body())
        self.assertEqual(response.status_code, 504)
        self.assertIn(str(CHAT_TIMEOUT_SECONDS), response.json["error"])
        self.assertIn("Nothing was changed", response.json["error"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_unavailable_model_is_503(self):
        self.ollama.side_effect = AssistantUnavailable("The assistant's model is not installed on this server.")
        response = self.client.post("/api/llm/chat", json=self.body())
        self.assertEqual(response.status_code, 503)
        self.assertIn("not installed", response.json["error"])

    def test_one_correction_with_remaining_time(self):
        self.path.write_text("# Trip\n\nVienna\nVienna again\n", encoding="utf-8")
        self.ollama.side_effect = [answer(edits=[{"find": "Vienna", "replace": "Wien"}]),
                                   answer(edits=[{"find": "Vienna\nVienna again", "replace": "Wien\nVienna again"}])]
        before = self.path.read_bytes()
        response = self.client.post("/api/llm/chat", json=self.body())
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(response.json["edits"], [{"start_line": 3, "end_line": 3, "replacement": ["Wien"]}])
        calls = self.ollama.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertLessEqual(calls[1].kwargs["timeout"], calls[0].kwargs["timeout"])
        correction = calls[1].args[1]["messages"][-1]
        self.assertEqual(correction["role"], "user")
        self.assertIn("occurs more than once", correction["content"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_one_generation_at_a_time(self):
        self.assertTrue(llm_module._SLOT.acquire(blocking=False))
        try:
            response = self.client.post("/api/llm/chat", json=self.body())
        finally:
            llm_module._SLOT.release()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["Retry-After"], "60")
        self.ollama.assert_not_called()

    def test_hosted_network_allowance_counts_generation_time(self):
        def slow(*args, **kwargs):
            time.sleep(0.6)
            return answer()
        self.ollama.side_effect = slow
        with patch("services.llm.hosted_mode", return_value=True), patch("services.llm.HOURLY_SECONDS", 1):
            headers = {"X-Real-IP": "203.0.113.7"}
            codes = [self.client.post("/api/llm/chat", json=self.body(), headers=headers).status_code
                     for _ in range(3)]
            self.assertEqual(codes, [200, 200, 429])
            self.assertEqual(self.ollama.call_count, 2)
            # Another network is unaffected; the address is kept only as a keyed hash.
            other = self.client.post("/api/llm/chat", json=self.body(), headers={"X-Real-IP": "198.51.100.9"})
            self.assertEqual(other.status_code, 200)
            self.assertNotIn("203.0.113", json.dumps(list(llm_module._RATE["events"])))
        llm_module._RATE["events"].clear()

    def test_truncated_answer_is_not_retried(self):
        self.ollama.return_value = {"done_reason": "length", "message": {"content": '{"reply": "Upd'}}
        response = self.client.post("/api/llm/chat", json=self.body())
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json["error"], TRUNCATED)
        self.assertEqual(self.ollama.call_count, 1)

    def test_failed_generation_releases_the_slot(self):
        self.ollama.side_effect = AssistantUnavailable("down")
        self.assertEqual(self.client.post("/api/llm/chat", json=self.body()).status_code, 503)
        self.assertTrue(llm_module._SLOT.acquire(blocking=False))
        llm_module._SLOT.release()

    def test_empty_reply_with_edits_gets_a_default_reply(self):
        self.ollama.return_value = answer(reply="  ")
        response = self.client.post("/api/llm/chat", json=self.body())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["reply"].strip())

    def test_regular_save_revision_guards_chat_writes(self):
        response = self.client.get("/api/file/trip.md", query_string={"dir": self.temp.name})
        revision = response.headers["X-Document-Revision"]
        body = {"content": "New text", "dir": self.temp.name, "disk_revision": revision}
        self.assertEqual(self.client.post("/api/file/trip.md", json=body).status_code, 200)
        self.assertEqual(self.client.post("/api/file/trip.md", json=body).status_code, 409)


class FindReplaceTests(unittest.TestCase):
    DOC = "# Trip\n\n## Day 1: Munich\n\nWalk.\n\n## Day 2: Salzburg\n\nWalk.\n\n## Totals\n\nSix days.\n"

    def check(self, edits, expected):
        line_edits = to_line_edits(self.DOC, edits)
        self.assertEqual(apply_line_edits(self.DOC, line_edits), expected)
        return line_edits

    def test_delete_whole_lines(self):
        self.check([{"find": "## Day 2: Salzburg\n\nWalk.\n\n", "replace": ""}],
                   "# Trip\n\n## Day 1: Munich\n\nWalk.\n\n## Totals\n\nSix days.\n")

    def test_edit_within_a_line_and_insert_before_anchor(self):
        self.check([{"find": "Six days.", "replace": "Five days."},
                    {"find": "## Totals", "replace": "## Notes\n\nBook early.\n\n## Totals"}],
                   "# Trip\n\n## Day 1: Munich\n\nWalk.\n\n## Day 2: Salzburg\n\nWalk.\n\n"
                   "## Notes\n\nBook early.\n\n## Totals\n\nFive days.\n")

    def test_whitespace_differences_are_refused_not_guessed(self):
        # A dropped blank line is sent back to the model, never guessed: a
        # tolerant match once edited inside words and changed indentation.
        for find in ("## Totals\nSix days.", " Walk.", "Six  days."):
            with self.subTest(find=find), self.assertRaisesRegex(ValueError, "not in the document"):
                to_line_edits(self.DOC, [{"find": find, "replace": "x"}])
        with self.assertRaisesRegex(ValueError, "not in the document"):
            to_line_edits("Contents: catalog\n", [{"find": " cat\n", "replace": " dog\n"}])

    def test_overlapping_occurrences_are_ambiguous(self):
        for content, find in (("ababa\n", "aba"), ("| a | b | c |\n|---|---|---|\n", "---|---")):
            with self.subTest(find=find), self.assertRaisesRegex(ValueError, "more than once"):
                to_line_edits(content, [{"find": find, "replace": "x"}])

    def test_missing_ambiguous_overlapping_and_malformed_are_refused(self):
        for edits, message in (
            ([{"find": "Vienna", "replace": "x"}], "not in the document"),
            ([{"find": "Walk.", "replace": "Run."}], "more than once"),
            ([{"find": "## Day 2: Salzburg", "replace": "x"}, {"find": "Salzburg\n\nWalk.", "replace": "y"}], "same passage"),
            ([{"find": "", "replace": "  \n"}], "needs text"),
            ([{"find": "", "replace": "A"}, {"find": "", "replace": "B"}], "one edit"),
            ([{"find": "Six days.", "replace": '<document name="trip.md">'}], "<document> tags"),
            ([{"find": "Six", "replace": 5}], "\"find\" and \"replace\""),
            ([{"text": "Six"}], "\"find\" and \"replace\""),
            ("not a list", "at most"),
        ):
            with self.subTest(edits=edits), self.assertRaisesRegex(ValueError, message):
                to_line_edits(self.DOC, edits)

    def test_empty_document_can_be_written_once(self):
        line_edits = to_line_edits("", [{"find": "", "replace": "# New\n\nText.\n"}])
        self.assertEqual(apply_line_edits("", line_edits), "# New\n\nText.\n")
        with self.assertRaisesRegex(ValueError, "one edit"):
            to_line_edits("", [{"find": "", "replace": "B"}, {"find": "", "replace": "A"}])
        with self.assertRaisesRegex(ValueError, "<document> tags"):
            to_line_edits("", [{"find": "", "replace": '<document name="a.md">\n\n</document>'}])

    def test_empty_find_appends_after_one_blank_line(self):
        self.check([{"find": "", "replace": "\n\n## Notes\n\nBook early."}],
                   self.DOC + "\n## Notes\n\nBook early.\n")
        for content, expected in (("Text", "Text\n\nMore.\n"), ("Text\n", "Text\n\nMore.\n"),
                                  ("Text\n\n\n", "Text\n\n\nMore.\n")):
            with self.subTest(content=content):
                line_edits = to_line_edits(content, [{"find": "", "replace": "More."}])
                self.assertEqual(apply_line_edits(content, line_edits), expected)

    def test_document_tags_already_in_the_document_may_be_edited(self):
        doc = "Wrap it in <document> and </document>.\n"
        self.assertEqual(apply_line_edits(doc, to_line_edits(doc, [{"find": "Wrap", "replace": "Put"}])),
                         "Put it in <document> and </document>.\n")


class OllamaTransportTests(unittest.TestCase):
    """The real _ollama, with the HTTP opener patched: every failure maps to a
    clean assistant error, never to an unhandled 500."""

    def call(self, effect):
        with patch.object(llm_module._OPENER, "open", side_effect=effect):
            return llm_module._ollama("/api/tags")

    def test_error_mapping(self):
        not_found = urllib.error.HTTPError("u", 404, "nf", {}, io.BytesIO(b""))
        server_error = urllib.error.HTTPError("u", 500, "err", {}, io.BytesIO(b""))
        with self.assertRaisesRegex(AssistantUnavailable, "not installed"):
            self.call(not_found)
        for effect in (server_error, urllib.error.URLError(ConnectionRefusedError()),
                       http.client.IncompleteRead(b"x"), http.client.BadStatusLine("x"), OSError("x")):
            with self.subTest(effect=type(effect).__name__), self.assertRaises(AssistantUnavailable):
                self.call(effect)
        for effect in (urllib.error.URLError(socket.timeout()), socket.timeout(), TimeoutError()):
            with self.subTest(effect=type(effect).__name__), self.assertRaises(TimeoutError):
                self.call(effect)

    def test_non_json_answer(self):
        class Body(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False
        with patch.object(llm_module._OPENER, "open", return_value=Body(b"<html>")):
            with self.assertRaises(AssistantUnavailable):
                llm_module._ollama("/api/tags")

    def test_empty_settings_fall_back_to_defaults(self):
        with patch.dict(os.environ, {"MD2PDF_LLM_MODEL": ""}):
            self.assertEqual(llm_module._setting("MD2PDF_LLM_MODEL", "qwen2.5:1.5b"), "qwen2.5:1.5b")
        for bad in ("", "127.0.0.1:11434", "file:///etc/passwd"):
            with self.subTest(url=bad), self.assertRaises(ValueError):
                llm_module._ollama_url(bad)


class LineEditTests(unittest.TestCase):
    def test_insert_replace_delete_use_original_line_numbers(self):
        result = apply_line_edits("one\ntwo\nthree\nfour\n", [
            {"start_line": 4, "end_line": 4, "replacement": []},
            {"start_line": 1, "end_line": 0, "replacement": ["zero"]},
            {"start_line": 2, "end_line": 2, "replacement": ["TWO", "extra"]},
        ])
        self.assertEqual(result, "zero\none\nTWO\nextra\nthree\n")

    def test_invalid_ranges_and_overlaps(self):
        for edits in (
            [{"start_line": True, "end_line": 1, "replacement": []}],
            [{"start_line": 0, "end_line": 0, "replacement": []}],
            [{"start_line": 1, "end_line": 1, "replacement": ["a\nb"]}],
            [{"start_line": 1, "end_line": 2, "replacement": []},
             {"start_line": 2, "end_line": 2, "replacement": []}],
        ):
            with self.subTest(edits=edits), self.assertRaises(ValueError):
                apply_line_edits("one\ntwo\n", edits)

    def test_empty_document_and_unicode(self):
        self.assertEqual(apply_line_edits("", [{"start_line": 1, "end_line": 1,
            "replacement": ["# München → Sofía", ""]}]), "# München → Sofía\n")


if __name__ == "__main__":
    unittest.main()
