"""Exercise untrusted Markdown in the same Chromium path used by hosted jobs."""
import contextlib
import io
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from playwright.sync_api import sync_playwright

from services.md2pdf import (
    _hosted_page, _render_hosted_mermaid, main, md_to_html,
)


class HostedRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(chromium_sandbox=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = _hosted_page(self.browser)
        self.addCleanup(self.page.context.close)

    def test_markup_and_mermaid_cannot_execute_or_navigate(self):
        source = """# Report
<script>window.documentLeaked = true; location = 'http://127.0.0.1/secret';</script>
<meta http-equiv="refresh" content="0;url=file:///etc/passwd">
<base href="http://127.0.0.1/">
<iframe src="file:///etc/passwd"></iframe>
<object data="http://169.254.169.254/latest/meta-data/"></object>
<form action="http://127.0.0.1/"><input autofocus onfocus="window.documentLeaked=true"></form>
<img src="http://127.0.0.1/secret" onerror="window.documentLeaked=true">
<svg onload="window.documentLeaked=true"><foreignObject><script>bad()</script></foreignObject></svg>
[Unsafe](javascript:alert(1))

```mermaid
graph LR
A["</div><script>window.documentLeaked=true</script>"] --> B[Done]
```
"""
        requests = []
        self.page.on("request", lambda request: requests.append(request.url))
        self.page.set_content(md_to_html(source, title="</title><script>window.documentLeaked=true</script>", hosted=True))
        self.assertEqual(self.page.url, "about:blank")
        self.assertIsNone(self.page.evaluate("window.documentLeaked"))
        self.assertEqual(self.page.locator("script, iframe, object, form, input, base").count(), 0)
        self.assertEqual(self.page.locator("[onerror], [onload], [onfocus]").count(), 0)
        self.assertEqual(self.page.locator("meta[http-equiv=refresh]").count(), 0)
        self.assertEqual(self.page.locator(".mermaid").count(), 1)
        self.assertIn("</div><script>", self.page.locator(".mermaid").text_content())
        self.assertEqual(self.page.locator("a[href^='javascript:']").count(), 0)
        self.assertEqual(requests, [])
        _render_hosted_mermaid(self.page)
        self.assertEqual(self.page.locator(".mermaid svg").count(), 1)
        self.assertIsNone(self.page.evaluate("window.documentLeaked"))
        self.assertEqual(self.page.url, "about:blank")
        self.assertEqual(requests, [])
        # Even a script that bypasses the sanitizer is rejected by the CSP.
        self.page.evaluate("""() => {
            const script = document.createElement('script');
            script.textContent = 'window.documentLeaked=true';
            document.body.appendChild(script);
        }""")
        self.assertIsNone(self.page.evaluate("window.documentLeaked"))

    def test_browser_context_cannot_reach_loopback_or_local_files(self):
        received = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                received.append(self.path)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"private document")

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_port}/secret"
        with tempfile.TemporaryDirectory() as directory:
            private_file = Path(directory) / "secret.html"
            private_file.write_text("<h1>Private document</h1>", encoding="utf-8")
            # Omit CSP deliberately to prove the independent request blocker.
            self.page.set_content("<p>Blank</p>")
            for target in (url, private_file.as_uri()):
                with self.subTest(target=target), self.assertRaises(Exception):
                    self.page.goto(target, timeout=3000)
            self.assertEqual(received, [])
            self.assertNotIn("Private document", self.page.content())

    def test_mermaid_tables_code_and_embedded_images_render_offline(self):
        source = """# Report

| City | Day |
| --- | --- |
| Vienna | Monday |

```python
print('hello')
```

```mermaid
%%{init: {"securityLevel": "loose"}}%%
graph LR
A[Vienna] --> B[Munich]
```

![pixel](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jP1sAAAAASUVORK5CYII=)
"""
        requests = []
        self.page.on("request", lambda request: requests.append(request.url))
        self.page.set_content(md_to_html(source, hosted=True))
        _render_hosted_mermaid(self.page)
        self.assertEqual(self.page.locator(".mermaid svg").count(), 1)
        self.assertIn("Vienna", self.page.locator(".mermaid").inner_text())
        self.assertEqual(self.page.evaluate("mermaid.mermaidAPI.getConfig().securityLevel"), "strict")
        self.assertEqual(self.page.locator("tbody td").all_text_contents(), ["Vienna", "Monday"])
        self.assertIn("print('hello')", self.page.locator("pre").inner_text())
        self.assertEqual(self.page.locator("img").evaluate("image => image.naturalWidth"), 1)
        self.assertFalse([url for url in requests if not url.startswith("data:")])
        pdf = self.page.pdf()
        self.assertTrue(pdf.startswith(b"%PDF-"))

    def test_hosted_pdf_uses_requested_paper_and_rejects_invalid_diagram(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "report.md"
            output = Path(directory) / "report.pdf"
            source.write_text("# Report\n\n```mermaid\ngraph LR\nA --> B\n```", encoding="utf-8")
            result = subprocess.run([
                sys.executable, "services/md2pdf.py", "--hosted", "--page-size", "A6",
                "--doc-style", "beamer", "--output-dir", directory, str(source),
            ], capture_output=True, text=True, timeout=60, cwd=Path(__file__).resolve().parent.parent)
            self.assertEqual(result.returncode, 0, result.stderr)
            box = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)", output.read_bytes())
            self.assertIsNotNone(box)
            self.assertAlmostEqual(float(box[1]) * 25.4 / 72, 148, delta=0.5)
            self.assertAlmostEqual(float(box[2]) * 25.4 / 72, 105, delta=0.5)
        self.page.set_content(md_to_html("```mermaid\nTOP_SECRET_INVALID_DIAGRAM\n```", hosted=True))
        with self.assertRaises(ValueError) as error:
            _render_hosted_mermaid(self.page)
        self.assertNotIn("TOP_SECRET", str(error.exception))

    def test_hosted_cli_redacts_renderer_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "report.md"
            source.write_text("# Document", encoding="utf-8")
            stderr = io.StringIO()
            with patch("sys.argv", ["md2pdf", "--hosted", "--output-dir", directory, str(source)]), \
                    patch("services.md2pdf.convert_file", side_effect=ValueError("TOP_SECRET_DOCUMENT_TEXT")), \
                    contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()), \
                    self.assertRaises(SystemExit):
                main()
            self.assertNotIn("TOP_SECRET", stderr.getvalue())
            self.assertIn("Conversion failed", stderr.getvalue())

    def test_hosted_size_limit_counts_utf8_bytes_and_options_are_validated(self):
        self.assertIn("<p>", md_to_html("x" * 200_001, hosted=True))
        with self.assertRaisesRegex(ValueError, "1 MiB"):
            md_to_html("\u00e9" * (512 * 1024 + 1), hosted=True)
        with self.assertRaisesRegex(ValueError, "formatting option"):
            md_to_html("# Report", hosted=True, font_size="10; color: red")


if __name__ == "__main__":
    unittest.main()
