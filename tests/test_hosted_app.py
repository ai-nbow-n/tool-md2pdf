"""The public app uses the real routes inside isolated, mounted Flask apps."""
import hashlib
import json
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlsplit

from flask import Flask, Response
from playwright.sync_api import sync_playwright
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import WSGIRequestHandler, make_server

import app as editor
from services.llm import llm
from services.workspaces import configure_hosted


PREFIX = "/en/products/aiconsulting/code-agents/md2pdf"


def hosted_app(root):
    application = Flask(__name__, static_folder=editor.app.static_folder)
    application.config.update(
        TESTING=True, MD2PDF_HOSTED=True, MD2PDF_SECRET_KEY="hosted-integration-test-key",
        MD2PDF_COOKIE_SECURE=False, MD2PDF_WORKSPACE_ROOT=str(root),
        MAX_CONTENT_LENGTH=2_000_000,
    )
    configure_hosted(application)
    application.register_blueprint(llm)
    application.register_error_handler(ValueError, editor.invalid_request)
    application.register_error_handler(413, editor.request_too_large)
    application.before_request(editor.check_hosted_request)
    application.after_request(editor.hosted_headers)
    for rule in editor.app.url_map.iter_rules():
        if rule.endpoint != "static" and not rule.endpoint.startswith("llm."):
            application.add_url_rule(rule.rule, endpoint=rule.endpoint,
                                     view_func=editor.app.view_functions[rule.endpoint],
                                     methods=rule.methods)
    return application


class QuietHandler(WSGIRequestHandler):
    def log(self, *args, **kwargs):
        pass


class HostedAppTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.app = hosted_app(self.root / "workspaces")
        self.client = self.app.test_client()

    def test_documents_pdf_and_chat_are_isolated_between_clients(self):
        other = self.app.test_client()
        self.assertEqual(self.client.get("/api/files").json, ["document.md"])
        saved = self.client.post("/api/file/private.md", json={"content": "# Private draft"})
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(other.get("/api/files").json, ["document.md"])
        self.assertEqual(other.get("/api/file/private.md").status_code, 404)

        def compile_pdf(command, **_kwargs):
            self.assertIn("--hosted", command)
            source = Path(command[command.index("--hosted") - 1])
            output = Path(command[command.index("--output-dir") + 1])
            (output / source.with_suffix(".pdf").name).write_bytes(b"%PDF-1.4\nPrivate PDF")
            return subprocess.CompletedProcess(command, 0, "Internal path", "")

        with patch("app.subprocess.run", side_effect=compile_pdf):
            response = self.client.post("/api/compile", json={"filename": "private.md"})
        self.assertEqual(response.json, {"ok": True, "out": "", "err": ""})
        with self.client.get("/pdf/private.pdf") as pdf:
            self.assertTrue(pdf.data.startswith(b"%PDF"))
        self.assertEqual(other.get("/pdf/private.pdf").status_code, 404)

        body = {"api_key": "test-key", "model": "gpt-4.1-mini",
                "messages": [{"role": "user", "content": "Read this"}],
                "document": {"filename": "private.md", "content": "# Private draft",
                             "disk_revision": saved.json["disk_revision"]}}
        with patch("services.llm.OpenAI") as provider, patch("services.llm.DefaultHttpxClient"):
            self.assertEqual(other.post("/api/llm/chat", json=body).status_code, 400)
            provider.return_value.__enter__.return_value.responses.create.assert_not_called()

    def test_forged_server_paths_and_cross_origin_mutations_are_rejected(self):
        self.client.get("/api/files")
        outside = self.root / "outside.md"
        outside.write_text("Keep private", encoding="utf-8")
        for route in ("/api/files", "/api/file/outside.md", "/pdf/outside.pdf"):
            self.assertEqual(self.client.get(route, query_string={"dir": str(self.root)}).status_code, 400)
        self.assertEqual(self.client.post("/api/file/outside.md", json={
            "dir": str(self.root), "content": "Bad"}).status_code, 400)
        with patch("app.subprocess.run") as compiler:
            for field in ("input_dir", "output_dir"):
                self.assertEqual(self.client.post("/api/compile", json={
                    "filename": "document.md", field: str(self.root)}).status_code, 400)
            self.assertEqual(self.client.post("/api/compile", json={"filename": "../outside.md"}).status_code, 400)
            compiler.assert_not_called()
        with patch("services.llm.OpenAI") as provider, patch("services.llm.DefaultHttpxClient"):
            response = self.client.post("/api/llm/chat", json={
                "api_key": "test-key", "model": "gpt-4.1-mini",
                "messages": [{"role": "user", "content": "Read"}],
                "document": {"filename": "outside.md", "input_dir": str(self.root),
                             "content": "Keep private", "disk_revision": hashlib.sha256(outside.read_bytes()).hexdigest()}})
            self.assertEqual(response.status_code, 400)
            provider.return_value.__enter__.return_value.responses.create.assert_not_called()
        self.assertEqual(self.client.post("/api/file/document.md", json={"content": "Bad"},
                                         headers={"Origin": "https://another.example"}).status_code, 403)
        self.assertEqual(self.client.post("/api/file/document.md", data="Bad").status_code, 415)
        self.assertEqual(outside.read_text(), "Keep private")

    def test_create_only_and_revision_conflicts_preserve_existing_text(self):
        self.client.post("/api/file/document.md", json={"content": "Original"})
        for body in ({"content": "Replace", "create_only": True},
                     {"content": "Replace", "disk_revision": "0" * 64}):
            self.assertEqual(self.client.post("/api/file/document.md", json=body).status_code, 409)
        response = self.client.get("/api/file/document.md")
        self.assertEqual(response.text, "Original")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(self.client.post("/api/file/document.md", json=[]).status_code, 400)

    def test_oversized_json_is_rejected_before_document_write(self):
        response = self.client.post("/api/file/document.md", json={"content": "a" * (2 * 1024 * 1024)})
        self.assertEqual(response.status_code, 413)
        self.assertIn("request is too large", response.json["error"])
        self.assertEqual(self.client.get("/api/file/document.md").text, "")

    def test_concurrent_compiles_reject_duplicates_and_excess_jobs_then_recover(self):
        self.client.get("/api/files")
        duplicate = self.app.test_client()
        duplicate.set_cookie("md2pdf_session", self.client.get_cookie("md2pdf_session").value)
        other = self.app.test_client()
        other.get("/api/files")
        pending = threading.Barrier(3)
        release = threading.Event()
        results = []

        def delayed_compile(command, **_kwargs):
            if not release.is_set():
                pending.wait(timeout=10)
                release.wait(timeout=10)
            return subprocess.CompletedProcess(command, 0, "", "")

        def compile_in_thread(client):
            results.append(client.post("/api/compile", json={"filename": "document.md"}).status_code)

        with patch("app.subprocess.run", side_effect=delayed_compile):
            threads = [threading.Thread(target=compile_in_thread, args=(client,))
                       for client in (self.client, other)]
            for thread in threads:
                thread.start()
            try:
                pending.wait(timeout=10)
                self.assertEqual(duplicate.post("/api/compile", json={"filename": "document.md"}).status_code, 429)
                third = self.app.test_client()
                self.assertEqual(third.post("/api/compile", json={"filename": "document.md"}).status_code, 429)
            finally:
                release.set()
                for thread in threads:
                    thread.join(timeout=10)
            self.assertEqual(results, [200, 200])
            self.assertEqual(duplicate.post("/api/compile", json={"filename": "document.md"}).status_code, 200)

    def test_browser_import_save_chat_compile_download_and_create_under_website_path(self):
        mounted = DispatcherMiddleware(Response("Missing", status=404), {PREFIX: self.app})
        server = make_server("127.0.0.1", 0, mounted, threaded=True, request_handler=QuietHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch("services.llm.OpenAI") as factory, patch("services.llm.DefaultHttpxClient"):
                provider = factory.return_value.__enter__.return_value
                provider.models.list.return_value = [SimpleNamespace(id="gpt-4.1-mini")]
                provider.responses.create.return_value = SimpleNamespace(output_text=json.dumps({
                    "reply": "Updated the title.", "edits": [
                        {"start_line": 1, "end_line": 1, "replacement": ["# Chat updated"]}]}))
                with sync_playwright() as pw:
                    browser = pw.chromium.launch()
                    try:
                        page = browser.new_page(viewport={"width": 1440, "height": 1100})
                        page.route("https://nbow.io/favicon.ico", lambda route: route.abort())
                        errors, requests, static_statuses = [], [], []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.on("request", lambda request: requests.append(urlsplit(request.url).path))
                        page.on("response", lambda response: static_statuses.append(response.status)
                                if "/static/" in response.url else None)
                        origin = f"http://127.0.0.1:{server.server_port}"
                        page.goto(origin + PREFIX + "/", wait_until="networkidle")
                        page.wait_for_function("window.markdownChat?.snapshot()?.filename === 'document.md'")
                        self.assertTrue(page.locator("#s-in").is_hidden())
                        self.assertTrue(page.locator("#s-out").is_hidden())
                        self.assertEqual(page.locator("#share-open").get_attribute("data-client-id"), "md2pdf-web")

                        imported = "# Imported\n\nM\u00fcnchen\n"
                        page.locator("#file-upload").set_input_files({
                            "name": "trip.md", "mimeType": "text/markdown", "buffer": imported.encode("utf-8")})
                        page.wait_for_function("window.markdownChat.snapshot()?.filename === 'trip.md'")
                        self.assertEqual(page.evaluate("cm.getValue()"), imported)
                        edited = "# Edited\n\nM\u00fcnchen\n\n```mermaid\nflowchart LR\n A[Munich] --> B[Vienna]\n```\n"
                        page.evaluate("text => cm.setValue(text)", edited)
                        page.locator("#btn-save").click()
                        page.wait_for_function("!dirty && document.getElementById('status-msg').textContent === 'Saved'")
                        self.assertEqual(page.request.get(origin + PREFIX + "/api/file/trip.md").text(), edited)

                        page.locator("#api-key").fill("browser-test-key")
                        page.locator("#api-connect").click()
                        page.wait_for_function("document.getElementById('api-status').dataset.state === 'ok'")
                        page.locator("#chat-bubble").click()
                        page.locator("#chat-input").fill("Update the title")
                        page.locator("#chat-input").press("Enter")
                        page.wait_for_function("document.getElementById('chat-status').textContent.startsWith('Line edits saved')")
                        expected = edited.replace("# Edited", "# Chat updated")
                        self.assertEqual(page.evaluate("cm.getValue()"), expected)
                        self.assertNotIn("browser-test-key", page.evaluate("JSON.stringify(localStorage)"))
                        self.assertEqual(factory.call_args.kwargs["api_key"], "browser-test-key")

                        page.locator("#btn-compile").click()
                        page.wait_for_function("!document.getElementById('btn-download-pdf').disabled", timeout=60000)
                        self.assertEqual(page.locator("#status-msg").inner_text(), "Compiled OK")
                        with page.expect_download() as pdf_event:
                            page.locator("#btn-download-pdf").click()
                        pdf = pdf_event.value
                        self.assertEqual(pdf.suggested_filename, "trip.pdf")
                        self.assertTrue(Path(pdf.path()).read_bytes().startswith(b"%PDF"))
                        with page.expect_download() as markdown_event:
                            page.locator("#btn-download-md").click()
                        self.assertEqual(Path(markdown_event.value.path()).read_text(encoding="utf-8"), expected)

                        second = browser.new_context()
                        self.assertEqual(second.request.get(origin + PREFIX + "/api/files").json(), ["document.md"])
                        self.assertEqual(second.request.get(origin + PREFIX + "/api/file/trip.md").status, 404)
                        self.assertEqual(second.request.get(origin + PREFIX + "/pdf/trip.pdf").status, 404)
                        second.close()

                        page.once("dialog", lambda dialog: dialog.accept("new-note"))
                        page.locator("#btn-new").click()
                        page.wait_for_function("window.markdownChat.snapshot()?.filename === 'new-note.md'")
                        self.assertEqual(page.evaluate("cm.getValue()"), "")
                        self.assertTrue(page.locator("#btn-download-pdf").is_disabled())
                        # An external revision makes the save fail; switching must keep this draft.
                        page.evaluate("cm.setValue('Unsaved draft to keep')")
                        page.request.post(origin + PREFIX + "/api/file/new-note.md", data={"content": "External revision"})
                        page.once("dialog", lambda dialog: dialog.accept())
                        page.locator("#file-select").select_option("trip.md")
                        page.wait_for_function("document.getElementById('dot').className === 'err'")
                        self.assertEqual(page.evaluate("current"), "new-note.md")
                        self.assertEqual(page.locator("#file-select").input_value(), "new-note.md")
                        self.assertEqual(page.evaluate("cm.getValue()"), "Unsaved draft to keep")
                        self.assertTrue(page.evaluate("dirty"))
                        self.assertEqual(page.request.get(origin + PREFIX + "/api/file/new-note.md").text(), "External revision")
                        page.reload(wait_until="networkidle")
                        self.assertEqual(page.locator("#api-key").input_value(), "")
                        for route in ("models", "chat", "apply"):
                            self.assertIn(PREFIX + "/api/llm/" + route, requests)
                        application_requests = [path for path in requests if any(part in path for part in ("/api/", "/static/", "/pdf/"))]
                        self.assertTrue(all(path.startswith(PREFIX + "/") for path in application_requests))
                        self.assertTrue(static_statuses and all(status == 200 for status in static_statuses))
                        self.assertEqual(errors, [])
                    finally:
                        browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
