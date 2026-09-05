import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from openai import APITimeoutError

from app import app
from services.documents import apply_line_edits
from services.llm import DEFAULT_BASE_URL, CHAT_TIMEOUT_SECONDS, CONNECTION_TIMEOUT_SECONDS


class ChatBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "trip.md"
        self.path.write_text("# Trip\n\nVienna\nBratislava\n", encoding="utf-8")
        self.client = app.test_client()
        patcher = patch("services.llm.OpenAI")
        self.factory = patcher.start()
        self.addCleanup(patcher.stop)
        # Avoid constructing real HTTP clients in mocked API tests.
        http = patch("services.llm.DefaultHttpxClient")
        http.start()
        self.addCleanup(http.stop)
        self.api = self.factory.return_value.__enter__.return_value

    def document(self):
        return {"filename": "trip.md", "input_dir": self.temp.name,
                "content": self.path.read_text(encoding="utf-8"),
                "disk_revision": hashlib.sha256(self.path.read_bytes()).hexdigest()}

    def body(self):
        return {"api_key": "test-key-never-log", "model": "gpt-test",
                "messages": [{"role": "user", "content": "Change Vienna to Wien."}],
                "document": self.document()}

    def answer(self, edits=None):
        self.api.responses.create.return_value = SimpleNamespace(output_text=json.dumps({
            "reply": "Updated the city name.", "edits": edits if edits is not None else [
                {"start_line": 3, "end_line": 3, "replacement": ["Wien"]}]}))

    def test_context_includes_unsaved_numbered_lines_and_does_not_write_until_apply(self):
        self.answer()
        body = self.body()
        body["document"]["content"] += "Unsaved note\n"
        original = self.path.read_bytes()
        response = self.client.post("/api/llm/chat", json=body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.path.read_bytes(), original)
        sent = self.api.responses.create.call_args.kwargs
        self.assertIn('"line": 5, "text": "Unsaved note"', sent["input"][0]["content"])
        self.assertFalse(sent["store"])
        self.assertNotIn(body["api_key"], json.dumps(sent))
        saved = self.client.post("/api/llm/apply", json={
            "document": body["document"], "edits": response.json["edits"],
            "disk_revision": response.json["disk_revision"]})
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "# Trip\n\nWien\nBratislava\nUnsaved note\n")
        self.assertEqual(saved.json["disk_revision"], hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_next_turn_loads_updated_context(self):
        self.answer()
        body = self.body()
        first = self.client.post("/api/llm/chat", json=body).json
        self.client.post("/api/llm/apply", json={"document": body["document"], **first})
        self.answer([])
        second = self.client.post("/api/llm/chat", json=self.body())
        self.assertEqual(second.status_code, 200)
        self.assertIn('"text": "Wien"', self.api.responses.create.call_args.kwargs["input"][0]["content"])

    def test_question_does_not_edit(self):
        self.answer([])
        before = self.path.read_bytes()
        response = self.client.post("/api/llm/chat", json=self.body())
        self.assertEqual(response.json["edits"], [])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.client.post("/api/llm/apply", json={
            "document": self.document(), "disk_revision": response.json["disk_revision"],
            "edits": []}).status_code, 400)

    def test_conflicts_before_chat_and_before_apply(self):
        self.answer()
        body = self.body()
        first = self.client.post("/api/llm/chat", json=body).json
        self.path.write_text("External update", encoding="utf-8")
        before_calls = self.api.responses.create.call_count
        self.assertEqual(self.client.post("/api/llm/chat", json=body).status_code, 409)
        self.assertEqual(self.api.responses.create.call_count, before_calls)
        self.assertEqual(self.client.post("/api/llm/apply", json={"document": body["document"], **first}).status_code, 409)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "External update")

    def test_invalid_model_edits_are_not_written(self):
        self.answer([{"start_line": 999, "end_line": 999, "replacement": ["bad"]}])
        before = self.path.read_bytes()
        self.assertEqual(self.client.post("/api/llm/chat", json=self.body()).status_code, 502)
        self.api.responses.create.return_value.output_text = "not json"
        self.assertEqual(self.client.post("/api/llm/chat", json=self.body()).status_code, 502)
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_document_and_traversal(self):
        for document in (None, {}, {**self.document(), "filename": "../outside.md"},
                         {**self.document(), "filename": "app.py"}):
            with self.subTest(document=document):
                body = {**self.body(), "document": document}
                self.assertEqual(self.client.post("/api/llm/chat", json=body).status_code, 400)
        self.api.responses.create.assert_not_called()

    def test_model_list_and_fixed_openai_endpoint(self):
        self.api.models.list.return_value = [SimpleNamespace(id=name) for name in
            ("gpt-4.1-mini", "gpt-image-test", "text-embedding-test", "gpt-4.1-mini-2025-04-14", "gpt-3.5-turbo")]
        response = self.client.post("/api/llm/models", json={"api_key": "test-only", "base_url": "https://example.org"})
        self.assertEqual(response.json["models"], ["gpt-4.1-mini"])
        self.assertEqual(self.factory.call_args.kwargs["base_url"], DEFAULT_BASE_URL)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_different_models_receive_current_context_and_produce_valid_edits(self):
        for model in ("gpt-4.1-mini", "gpt-4o-mini", "gpt-5-mini"):
            with self.subTest(model=model):
                self.answer()
                body = {**self.body(), "model": model}
                result = self.client.post("/api/llm/chat", json=body)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(self.api.responses.create.call_args.kwargs["model"], model)
                self.assertTrue(self.api.responses.create.call_args.kwargs["text"]["format"]["strict"])
                saved = self.client.post("/api/llm/apply", json={"document": body["document"], **result.json})
                self.assertEqual(saved.status_code, 200)

    def test_model_catalog_is_compact_and_preserves_order(self):
        from services.llm import CHAT_MODELS
        self.api.models.list.return_value = [SimpleNamespace(id=name) for name in
            [*reversed(CHAT_MODELS), "gpt-4.1-mini-2025-04-14", "chatgpt-4o-latest", "o1-preview"]]
        result = self.client.post("/api/llm/models", json={"api_key": "test-only"})
        self.assertEqual(result.json["models"], list(CHAT_MODELS))

    def test_no_key_and_cross_origin_rejected(self):
        self.assertEqual(self.client.post("/api/llm/models", json={}).status_code, 400)
        self.assertEqual(self.client.post("/api/llm/apply", json={}, headers={"Origin": "https://other.example"}).status_code, 403)

    def test_chat_timeout_and_reasoning_are_model_specific(self):
        for model in ("gpt-5", "gpt-5-mini", "gpt-4.1-mini"):
            with self.subTest(model=model):
                self.answer([])
                response = self.client.post("/api/llm/chat", json={**self.body(), "model": model})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.factory.call_args.kwargs["timeout"], CHAT_TIMEOUT_SECONDS)
                options = self.api.responses.create.call_args.kwargs
                if model.startswith("gpt-5"):
                    self.assertEqual(options["reasoning"], {"effort": "low"})
                else:
                    self.assertNotIn("reasoning", options)
        self.api.models.list.return_value = [SimpleNamespace(id="gpt-4.1-mini")]
        self.client.post("/api/llm/models", json={"api_key": "test"})
        self.assertEqual(self.factory.call_args.kwargs["timeout"], CONNECTION_TIMEOUT_SECONDS)

    def test_timeout_does_not_write_and_reports_retry(self):
        self.api.responses.create.side_effect = APITimeoutError(request=SimpleNamespace())
        before = self.path.read_bytes()
        response = self.client.post("/api/llm/chat", json=self.body())
        self.assertEqual(response.status_code, 504)
        self.assertIn(str(CHAT_TIMEOUT_SECONDS), response.json["error"])
        self.assertIn("Nothing was changed", response.json["error"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_ranges_get_one_correction_with_remaining_time(self):
        invalid = {"reply": "Change city.", "edits": [
            {"start_line": 3, "end_line": 4, "replacement": ["Wien", "Bratislava"]},
            {"start_line": 3, "end_line": 3, "replacement": ["Wien"]}]}
        valid = {"reply": "Change city.", "edits": [
            {"start_line": 3, "end_line": 3, "replacement": ["Wien"]}]}
        self.api.responses.create.side_effect = [SimpleNamespace(output_text=json.dumps(invalid)),
                                                SimpleNamespace(output_text=json.dumps(valid))]
        before = self.path.read_bytes()
        response = self.client.post("/api/llm/chat", json=self.body())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["edits"], valid["edits"])
        calls = self.api.responses.create.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertLessEqual(calls[1].kwargs["timeout"], calls[0].kwargs["timeout"])
        self.assertIn("overlap", calls[1].kwargs["input"][-1]["content"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_regular_save_revision_guards_chat_writes(self):
        response = self.client.get("/api/file/trip.md", query_string={"dir": self.temp.name})
        revision = response.headers["X-Document-Revision"]
        body = {"content": "New text", "dir": self.temp.name, "disk_revision": revision}
        self.assertEqual(self.client.post("/api/file/trip.md", json=body).status_code, 200)
        self.assertEqual(self.client.post("/api/file/trip.md", json=body).status_code, 409)


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
