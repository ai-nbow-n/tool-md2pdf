"""Browser integration against a local Flask server and a fake Ollama."""
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server, WSGIRequestHandler
from app import app
import services.llm as llm_module
from services.llm import CHAT_MODEL, CHAT_TIMEOUT_SECONDS, CONNECTION_TIMEOUT_SECONDS, MAX_DOCUMENT_CHARS


class QuietHandler(WSGIRequestHandler):
    def log(self, *args, **kwargs):
        pass


class FakeOllama:
    """Answers /api/tags with the server model and /api/chat from a queue."""

    def __init__(self):
        self.chats = []
        self.reply = {"reply": "Changed the title.", "edits": [{"find": "# Original", "replace": "# Updated"}]}
        self.hook = None

    def __call__(self, path, payload=None, timeout=None):
        if path == "/api/tags":
            return {"models": [{"name": CHAT_MODEL}]}
        self.chats.append(payload)
        if self.hook:
            self.hook()
        return {"message": {"content": json.dumps(self.reply)}}


class ChatBrowserTests(unittest.TestCase):
    def test_new_and_whitespace_documents_are_written_then_edited(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = FakeOllama()
            llm_module._STATUS["checked"] = 0.0
            with patch("app.DEF_IN", root), patch("services.documents.DEFAULT_INPUT", root), \
                    patch("services.llm._ollama", side_effect=fake):
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
                        page.wait_for_function("document.getElementById('api-status').dataset.state === 'ok'")
                        self.assertTrue(page.locator("#chat-input").is_disabled())
                        page.locator("#chat-bubble").click()

                        for filename, initial_content in (("new.md", ""), ("whitespace.md", " \n\t\n")):
                            with self.subTest(filename=filename):
                                # Exercise the New button, including creating the file before chat.
                                page.once("dialog", lambda dialog, name=filename: dialog.accept(name))
                                page.locator("#btn-new").click()
                                page.wait_for_function(
                                    "name => window.markdownChat?.snapshot()?.filename === name",
                                    arg=filename)
                                self.assertTrue(page.locator("#chat-input").is_enabled())
                                self.assertEqual(page.locator(".chat-message").count(), 0)
                                source = root / filename
                                self.assertEqual(source.read_text(encoding="utf-8"), "")
                                if initial_content:
                                    # The current editor, including unsaved blank text, decides writing mode.
                                    page.evaluate("text => cm.setValue(text)", initial_content)
                                    self.assertTrue(page.evaluate("dirty"))
                                original_revision = page.evaluate("window.markdownChat.snapshot().disk_revision")
                                markdown = "# Neuron\n\n## Parts\n\n- Soma\n- Axon"
                                fake.reply = {"markdown": markdown, "reply": "I wrote a neuron overview."}
                                with page.expect_request("**/api/llm/chat") as request:
                                    page.locator("#chat-input").fill("Write a brief overview of neuron anatomy.")
                                    page.locator("#chat-input").press("Enter")
                                self.assertEqual(request.value.post_data_json["document"]["content"], initial_content)
                                page.wait_for_function("document.querySelectorAll('.chat-message.assistant').length === 1")
                                self.assertEqual(source.read_text(encoding="utf-8"), markdown + "\n")
                                self.assertEqual(page.evaluate("cm.getValue()"), markdown + "\n")
                                self.assertFalse(page.evaluate("dirty"))
                                snapshot = page.evaluate("window.markdownChat.snapshot()")
                                self.assertNotEqual(snapshot["disk_revision"], original_revision)
                                self.assertEqual(snapshot["disk_revision"], hashlib.sha256(source.read_bytes()).hexdigest())
                                self.assertEqual(fake.chats[-1]["format"], llm_module.WRITE_SCHEMA)
                                self.assertNotIn("<document", fake.chats[-1]["messages"][0]["content"])

                                # Writing must transition to ordinary editing with the saved text as context.
                                fake.reply = {"reply": "Changed the title.", "edits": [
                                    {"find": "# Neuron", "replace": "# Neuron anatomy"}]}
                                page.locator("#chat-input").fill("Change the title to Neuron anatomy.")
                                page.locator("#chat-input").press("Enter")
                                page.wait_for_function("document.querySelectorAll('.chat-message.assistant').length === 2")
                                expected = markdown.replace("# Neuron", "# Neuron anatomy", 1) + "\n"
                                self.assertEqual(source.read_text(encoding="utf-8"), expected)
                                self.assertEqual(page.evaluate("cm.getValue()"), expected)
                                self.assertEqual(fake.chats[-1]["format"], llm_module.EDIT_SCHEMA)
                                messages = fake.chats[-1]["messages"]
                                self.assertIn(markdown, messages[0]["content"])
                                self.assertEqual([message["role"] for message in messages],
                                                 ["system", "user", "assistant", "user"])
                        self.assertEqual(errors, [])
                        browser.close()
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)

    def test_chat_edit_follow_up_and_stale_edit_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sample.md"
            source.write_text("# Original\n\nKeep this line.\n", encoding="utf-8")
            fake = FakeOllama()
            llm_module._STATUS["checked"] = 0.0
            with patch("app.DEF_IN", root), patch("services.documents.DEFAULT_INPUT", root), \
                    patch("services.llm._ollama", side_effect=fake):
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
                        # No key, no model choice, no third-party provider on the page.
                        self.assertEqual(page.locator("#api-key, #api-model, #api-connect, #api-disconnect").count(), 0)
                        self.assertNotIn("OpenAI", page.content())
                        self.assertGreater(int(page.locator('#chat-window').get_attribute('data-chat-timeout')), CHAT_TIMEOUT_SECONDS * 1000)
                        self.assertGreater(int(page.locator('#chat-window').get_attribute('data-connection-timeout')), CONNECTION_TIMEOUT_SECONDS * 1000)
                        page.wait_for_function("document.getElementById('api-status').dataset.state === 'ok'")
                        self.assertEqual(page.locator("#api-status").inner_text(), "Ready · " + CHAT_MODEL)
                        self.assertIn(str(MAX_DOCUMENT_CHARS), page.locator("#assistant-limit").inner_text())
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
                        self.assertEqual(fake.chats[-1]["model"], CHAT_MODEL)
                        self.assertIn(CHAT_MODEL, page.locator(".chat-message.assistant strong").last.inner_text())
                        # A second turn receives the revised document and the conversation.
                        fake.reply = {"reply": "The title is Updated.", "edits": []}
                        page.locator("#chat-input").fill("What is the title?")
                        page.locator("#chat-input").press("Enter")
                        page.wait_for_function("document.querySelectorAll('.chat-message.assistant').length === 2")
                        messages = fake.chats[-1]["messages"]
                        self.assertIn("# Updated", messages[0]["content"])
                        self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant", "user"])
                        # A local edit made during inference must prevent stale assistant edits.
                        started, release = threading.Event(), threading.Event()

                        def hold():
                            started.set()
                            release.wait(timeout=10)
                        fake.hook = hold
                        fake.reply = {"reply": "Another title.", "edits": [{"find": "# Updated", "replace": "# Stale AI title"}]}
                        page.locator("#chat-input").fill("Change the title again.")
                        page.locator("#chat-input").press("Enter")
                        self.assertTrue(started.wait(timeout=5))
                        page.wait_for_function("/Thinking.*[0-9]+s/.test(document.getElementById('chat-status').textContent)")
                        page.evaluate("cm.replaceRange('My local change', {line: 0, ch: 0}, {line: 0, ch: 9})")
                        release.set()
                        page.wait_for_function("document.getElementById('chat-status').dataset.state === 'error'")
                        self.assertIn("My local change", page.evaluate("cm.getValue()"))
                        self.assertNotIn("Stale AI title", source.read_text(encoding="utf-8"))
                        self.assertEqual(page.locator("#chat-input").input_value(), "Change the title again.")
                        fake.hook = None
                        fake.reply = {"reply": "Kept the local change.", "edits": []}
                        page.locator("#chat-input").press("Enter")
                        page.wait_for_function("document.querySelectorAll('.chat-message.assistant').length === 3")
                        page.locator("#chat-close").click()
                        self.assertFalse(page.locator("#chat-window").is_visible())
                        self.assertEqual(errors, [])
                        browser.close()
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
