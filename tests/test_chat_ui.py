"""Browser integration against a local Flask server and a fake OpenAI client."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server, WSGIRequestHandler
from app import app
from services.llm import CHAT_TIMEOUT_SECONDS, CONNECTION_TIMEOUT_SECONDS


class QuietHandler(WSGIRequestHandler):
    def log(self, *args, **kwargs):
        pass


class ChatBrowserTests(unittest.TestCase):
    def test_connect_chat_edit_and_disconnect(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sample.md"
            source.write_text("# Original\n\nKeep this line.\n", encoding="utf-8")
            with patch("app.DEF_IN", root), patch("services.documents.DEFAULT_INPUT", root), \
                    patch("services.llm.OpenAI") as factory, patch("services.llm.DefaultHttpxClient"):
                provider = factory.return_value.__enter__.return_value
                provider.models.list.return_value = [SimpleNamespace(id=name) for name in
                    ("gpt-4.1-mini", "gpt-5-mini", "gpt-4o-mini", "gpt-4.1-mini-2025-04-14", "gpt-3.5-turbo")]
                provider.responses.create.return_value = SimpleNamespace(output_text=json.dumps({
                    "reply": "Changed the title.", "edits": [
                        {"start_line": 1, "end_line": 1, "replacement": ["# Updated"]}]}))
                server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=QuietHandler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    with sync_playwright() as pw:
                        browser = pw.chromium.launch()
                        page = browser.new_page(viewport={"width": 1280, "height": 900})
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.goto(f"http://127.0.0.1:{server.server_port}", wait_until="networkidle")
                        page.wait_for_function("window.markdownChat?.snapshot()?.filename === 'sample.md'")
                        self.assertEqual(page.locator("#api-url").count(), 0)
                        self.assertGreater(int(page.locator('#chat-window').get_attribute('data-chat-timeout')), CHAT_TIMEOUT_SECONDS * 1000)
                        self.assertGreater(int(page.locator('#chat-window').get_attribute('data-connection-timeout')), CONNECTION_TIMEOUT_SECONDS * 1000)
                        # Selection is possible even before entering a key.
                        self.assertTrue(page.locator("#api-model").is_enabled())
                        page.locator("#api-model").select_option("gpt-5-mini")
                        page.locator("#api-key").fill("test-key")
                        self.assertEqual(page.locator("#api-model").input_value(), "gpt-5-mini")
                        page.locator("#api-connect").click()
                        page.wait_for_function("document.getElementById('api-status').dataset.state === 'ok'")
                        self.assertEqual(page.locator("#api-model option").count(), 3)
                        self.assertEqual(page.locator("#api-model").input_value(), "gpt-5-mini")
                        self.assertEqual(page.locator("#api-status").inner_text(), "Connected · gpt-5-mini")
                        page.locator("#chat-bubble").click()
                        self.assertTrue(page.locator("#chat-window").is_visible())
                        # Unsaved editor content must be included and retained on disk.
                        page.evaluate("cm.replaceRange('Unsaved note\\n', {line: cm.lastLine(), ch: 0})")
                        page.locator("#chat-input").fill("Change the title to Updated.")
                        page.locator("#chat-input").press("Enter")
                        page.wait_for_function("document.getElementById('chat-status').textContent.startsWith('Line edits saved')")
                        self.assertEqual(source.read_text(encoding="utf-8"), "# Updated\n\nKeep this line.\nUnsaved note\n")
                        self.assertEqual(page.evaluate("cm.getValue()"), source.read_text(encoding="utf-8"))
                        self.assertFalse(page.evaluate("dirty"))
                        self.assertEqual(provider.responses.create.call_args.kwargs["model"], "gpt-5-mini")
                        self.assertIn("gpt-5-mini", page.locator(".chat-message.assistant strong").last.inner_text())
                        page.locator("#api-model").select_option("gpt-4o-mini")
                        self.assertEqual(page.locator("#api-status").inner_text(), "Connected · gpt-4o-mini")
                        # A second turn receives the revised document and conversation.
                        provider.responses.create.return_value = SimpleNamespace(output_text=json.dumps({"reply": "The title is Updated.", "edits": []}))
                        page.locator("#chat-input").fill("What is the title?")
                        page.locator("#chat-input").press("Enter")
                        page.wait_for_function("document.querySelectorAll('.chat-message.assistant').length === 2")
                        inputs = provider.responses.create.call_args.kwargs["input"]
                        self.assertIn("# Updated", inputs[0]["content"])
                        self.assertEqual(len(inputs), 4)
                        self.assertEqual(provider.responses.create.call_args.kwargs["model"], "gpt-4o-mini")
                        self.assertEqual(provider.models.list.call_count, 1)
                        # A local edit made during inference must prevent stale AI edits.
                        started, release = threading.Event(), threading.Event()
                        def delayed_reply(**kwargs):
                            started.set()
                            release.wait(timeout=10)
                            return SimpleNamespace(output_text=json.dumps({"reply": "Another title.", "edits": [
                                {"start_line": 1, "end_line": 1, "replacement": ["# Stale AI title"]}]}))
                        provider.responses.create.side_effect = delayed_reply
                        page.locator("#chat-input").fill("Change the title again.")
                        page.locator("#chat-input").press("Enter")
                        self.assertTrue(started.wait(timeout=5))
                        page.wait_for_function("/Thinking.*[0-9]+s/.test(document.getElementById('chat-status').textContent)")
                        # Switching mid-request affects only the next request.
                        self.assertTrue(page.locator("#api-model").is_enabled())
                        page.locator("#api-model").select_option("gpt-4.1-mini")
                        self.assertIn("next message: gpt-4.1-mini", page.locator("#chat-status").inner_text())
                        self.assertEqual(provider.responses.create.call_args.kwargs["model"], "gpt-4o-mini")
                        page.evaluate("cm.replaceRange('My local change', {line: 0, ch: 0}, {line: 0, ch: 9})")
                        release.set()
                        page.wait_for_function("document.getElementById('chat-status').dataset.state === 'error'")
                        self.assertIn("My local change", page.evaluate("cm.getValue()"))
                        self.assertNotIn("Stale AI title", source.read_text(encoding="utf-8"))
                        self.assertEqual(page.locator("#chat-input").input_value(), "Change the title again.")
                        provider.responses.create.side_effect = None
                        provider.responses.create.return_value = SimpleNamespace(output_text=json.dumps({"reply": "Kept the local change.", "edits": []}))
                        page.locator("#chat-input").press("Enter")
                        page.wait_for_function("document.querySelectorAll('.chat-message.assistant').length === 3")
                        self.assertEqual(provider.responses.create.call_args.kwargs["model"], "gpt-4.1-mini")
                        self.assertEqual(page.locator("#api-status").inner_text(), "Connected · gpt-4.1-mini")
                        self.assertIn("gpt-4.1-mini", page.locator(".chat-message.assistant strong").last.inner_text())
                        self.assertNotIn("test-key", page.evaluate("JSON.stringify(localStorage)"))
                        page.locator("#chat-close").click()
                        self.assertFalse(page.locator("#chat-window").is_visible())
                        page.locator("#api-disconnect").click()
                        self.assertEqual(page.locator("#api-key").input_value(), "")
                        self.assertTrue(page.locator("#api-model").is_enabled())
                        self.assertEqual(errors, [])
                        browser.close()
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
