import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask, g, jsonify, request

from services.documents import DOCUMENT_LOCK, atomic_write, document_path
from services.workspaces import (
    WORKSPACE_TTL, configure_hosted, input_directory, output_directory,
    hosted_mode, valid_filename, validate_save,
)


class HostedWorkspaceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True, MD2PDF_HOSTED=True, MD2PDF_SECRET_KEY="test-workspace-signing-key",
            MD2PDF_WORKSPACE_ROOT=str(self.root / "workspaces"), MD2PDF_COOKIE_SECURE=False,
        )
        configure_hosted(self.app)

        @self.app.errorhandler(ValueError)
        def invalid(error):
            return jsonify(error=str(error)), 400

        @self.app.get("/documents")
        def documents():
            directory = input_directory(request.args.get("dir"), "unused")
            return jsonify(files=sorted(p.name for p in directory.glob("*.md")),
                           workspace=g.md2pdf_workspace.name)

        @self.app.route("/document/<path:name>", methods=["GET", "POST"])
        def document(name):
            body = request.get_json(silent=True) or {}
            directory = input_directory(body.get("dir", request.args.get("dir")), "unused")
            if not valid_filename(name, ".md"):
                raise ValueError("Invalid filename")
            path = directory / name
            if request.method == "POST":
                with DOCUMENT_LOCK:
                    atomic_write(path, body["content"])
            return path.read_text(encoding="utf-8") if path.exists() else ("Missing", 404)

        @self.app.post("/chat-document")
        def chat_document():
            path = document_path(request.get_json())
            return path.read_text(encoding="utf-8")

        @self.app.get("/output")
        def output():
            return str(output_directory(request.args.get("dir"), "unused"))

        self.client = self.app.test_client()

    def workspace(self, client=None):
        result = (client or self.client).get("/documents")
        self.assertEqual(result.status_code, 200)
        return self.root / "workspaces" / result.json["workspace"]

    def test_two_browsers_have_separate_inputs_outputs_and_chat_documents(self):
        other = self.app.test_client()
        first = self.workspace()
        second = self.workspace(other)
        self.assertNotEqual(first, second)
        self.assertEqual(self.client.post("/document/document.md", json={"content": "Private draft"}).status_code, 200)
        self.assertEqual(other.get("/document/document.md").text, "")
        self.assertEqual(self.client.post("/chat-document", json={"filename": "document.md"}).text, "Private draft")
        self.assertEqual(other.post("/chat-document", json={"filename": "document.md"}).text, "")
        self.assertNotEqual(self.client.get("/output").text, other.get("/output").text)
        self.assertEqual((first / "input" / "document.md").read_text(), "Private draft")
        self.assertEqual((second / "input" / "document.md").read_text(), "")

    def test_client_directories_cannot_access_other_workspace_or_server_files(self):
        workspace = self.workspace()
        for directory in (str(workspace / "input"), str(self.root), "../", "C:\\Windows", "/etc"):
            with self.subTest(directory=directory):
                self.assertEqual(self.client.get("/documents", query_string={"dir": directory}).status_code, 400)
                self.assertEqual(self.client.get("/output", query_string={"dir": directory}).status_code, 400)
                self.assertEqual(self.client.post("/document/document.md", json={"dir": directory, "content": "bad"}).status_code, 400)
                self.assertEqual(self.client.post("/chat-document", json={"filename": "document.md", "input_dir": directory}).status_code, 400)
        self.assertEqual((workspace / "input" / "document.md").read_text(), "")

    def test_chat_requires_flat_filename(self):
        workspace = self.workspace()
        nested = workspace / "input" / "nested"
        nested.mkdir()
        (nested / "note.md").write_text("Hidden", encoding="utf-8")
        for name in ("../document.md", "nested/note.md", "nested\\note.md", "/document.md", "C:document.md"):
            with self.subTest(name=name):
                response = self.client.post("/chat-document", json={"filename": name})
                self.assertEqual(response.status_code, 400)

    def test_expired_session_rotates_and_only_expired_managed_workspace_is_removed(self):
        expired = self.workspace()
        self.client.post("/document/document.md", json={"content": "Expired draft"})
        other = self.app.test_client()
        active = self.workspace(other)
        unrelated = expired.parent / ("a" * 64)
        unrelated.mkdir()
        (unrelated / "keep.txt").write_text("Unmanaged", encoding="utf-8")
        old = time.time() - WORKSPACE_TTL - 60
        os.utime(expired / ".last-used", (old, old))
        self.app.extensions["md2pdf_workspaces"]["last_cleanup"] = 0
        replacement = self.workspace()
        self.assertNotEqual(expired, replacement)
        self.assertFalse(expired.exists())
        self.assertTrue(active.exists())
        self.assertTrue(unrelated.exists())
        self.assertEqual(self.client.get("/document/document.md").text, "")

    def test_missing_workspace_does_not_reuse_old_cookie_identifier(self):
        self.workspace()
        missing = "b" * 64
        with self.client.session_transaction() as cookie:
            cookie["md2pdf_workspace"] = missing
        replacement = self.workspace()
        self.assertNotEqual(replacement.name, missing)
        self.assertFalse((replacement.parent / missing).exists())

    def test_invalid_session_identifier_cannot_select_parent_directory(self):
        with self.client.session_transaction() as cookie:
            cookie["md2pdf_workspace"] = "../../outside"
        workspace = self.workspace()
        self.assertEqual(workspace.parent, self.root / "workspaces")
        self.assertEqual(len(workspace.name), 64)
        self.assertFalse((self.root / "outside").exists())

    def test_document_quota_rejects_new_file_but_allows_update(self):
        workspace = self.workspace()
        for number in range(19):
            (workspace / "input" / f"{number}.md").write_text("", encoding="utf-8")
        response = self.client.post("/document/extra.md", json={"content": "New"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("20 documents", response.json["error"])
        self.assertFalse((workspace / "input" / "extra.md").exists())
        self.assertEqual(self.client.post("/document/document.md", json={"content": "Updated"}).status_code, 200)

    def test_size_limits_count_utf8_bytes_and_preserve_original(self):
        self.client.post("/document/document.md", json={"content": "Original"})
        with patch("services.workspaces.MAX_DOCUMENT_BYTES", 10):
            response = self.client.post("/document/document.md", json={"content": "\u00e9" * 6})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/document/document.md").text, "Original")
        with patch("services.workspaces.MAX_WORKSPACE_BYTES", 12):
            response = self.client.post("/document/second.md", json={"content": "12345"})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(self.client.post("/document/document.md", json={"content": "Short"}).status_code, 200)

    def test_cleanup_does_not_follow_links(self):
        workspace = self.workspace()
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("Private", encoding="utf-8")
        link = workspace.parent / ("c" * 64)
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Creating symbolic links is not permitted on this host.")
        self.app.extensions["md2pdf_workspaces"]["last_cleanup"] = 0
        self.workspace()
        self.assertEqual((outside / "keep.txt").read_text(), "Private")
        self.assertTrue(link.is_symlink())

    def test_active_workspace_is_not_removed_by_cleanup(self):
        workspace = self.workspace()
        old = time.time() - WORKSPACE_TTL - 60
        os.utime(workspace / ".last-used", (old, old))
        state = self.app.extensions["md2pdf_workspaces"]
        state["active"][workspace.name] = 1
        state["last_cleanup"] = 0
        self.workspace(self.app.test_client())
        self.assertTrue(workspace.exists())

    def test_cookie_is_signed_http_only_and_same_site(self):
        response = self.client.get("/documents")
        cookie = response.headers["Set-Cookie"]
        self.assertIn("md2pdf_session=", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertIn("Expires=", cookie)

    def test_cleanup_command_works_without_signing_secret(self):
        workspace = self.workspace()
        old = time.time() - WORKSPACE_TTL - 60
        os.utime(workspace / ".last-used", (old, old))
        environment = dict(os.environ, MD2PDF_WORKSPACE_ROOT=str(workspace.parent))
        environment.pop("MD2PDF_SECRET_KEY", None)
        result = subprocess.run([sys.executable, "-m", "services.workspaces", "--cleanup"],
                                env=environment, capture_output=True, text=True, check=True)
        self.assertIn("Removed 1 expired workspace", result.stdout)
        self.assertFalse(workspace.exists())


class WorkspaceConfigurationTests(unittest.TestCase):
    def test_hosted_requires_explicit_signing_secret(self):
        app = Flask(__name__)
        app.config["MD2PDF_HOSTED"] = True
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "MD2PDF_SECRET_KEY"):
                configure_hosted(app)

    def test_local_directories_and_writes_keep_existing_behavior(self):
        self.assertFalse(hosted_mode())
        app = Flask(__name__)
        app.config["MD2PDF_HOSTED"] = False
        configure_hosted(app)
        with app.test_request_context():
            self.assertEqual(input_directory("custom/input", "default"), Path("custom/input"))
            self.assertEqual(output_directory(None, "custom/output"), Path("custom/output"))
            validate_save(Path("outside.md"), "A" * (1024 * 1024 + 1))

    def test_capacity_rejects_new_browsers_and_keeps_existing_browser_working(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = Flask(__name__)
            app.config.update(TESTING=True, MD2PDF_HOSTED=True,
                              MD2PDF_SECRET_KEY="test-workspace-signing-key",
                              MD2PDF_WORKSPACE_ROOT=temporary,
                              MD2PDF_MAX_WORKSPACES=1, MD2PDF_COOKIE_SECURE=False)
            configure_hosted(app)

            @app.get("/")
            def index():
                return "Ready"

            first = app.test_client()
            self.assertEqual(first.get("/").status_code, 200)
            self.assertEqual(app.test_client().get("/").status_code, 503)
            self.assertEqual(first.get("/").status_code, 200)


if __name__ == "__main__":
    unittest.main()
