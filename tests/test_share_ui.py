"""Saving on desktop and phones offers sharing without submitting a document.

The editor and its sharing client are real. Only PDF compilation and the remote
receiver are substituted; the receiver deliberately waits for the test to send
the handshake so edits made while a popup loads cannot escape unnoticed.
"""
import json
import subprocess
import tempfile
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

from flask import Response
from playwright.sync_api import expect, sync_playwright
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import make_server

from test_hosted_app import PREFIX, QuietHandler, hosted_app


PROFILES = {
    "desktop": {"viewport": {"width": 1440, "height": 1100}},
    "phone": {"viewport": {"width": 390, "height": 844},
              "is_mobile": True, "has_touch": True, "device_scale_factor": 3},
}
RECEIVER = """<!doctype html><html><body><p>Sharing receiver</p><script>
window.receivedDocuments = [];
window.processedReadies = 0;
window.addEventListener('message', event => {
  if (event.source === window.opener && event.data?.source === 'nbow-corpus-client') {
    window.receivedDocuments.push(event.data);
  }
  if (event.source === window.opener && event.data?.source === 'share-ui-test-ready-processed') {
    window.processedReadies++;
  }
});
window.sendReady = () => window.opener.postMessage({
  source: 'nbow-corpus-share', type: 'ready'
}, '*');
</script></body></html>"""


class ShareUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        application = hosted_app(Path(temporary.name) / "workspaces")
        mounted = DispatcherMiddleware(Response("Missing", status=404), {PREFIX: application})
        server = make_server("127.0.0.1", 0, mounted, threaded=True, request_handler=QuietHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server():
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.addCleanup(stop_server)
        self.origin = f"http://127.0.0.1:{server.server_port}"
        self.compiler = self.enterContext(patch("app.subprocess.run", return_value=
                                                subprocess.CompletedProcess([], 0, "", "")))
        self.enterContext(patch("app.SHARE_BASE", "https://nbow.io"))

    @contextmanager
    def editor_page(self, profile):
        context = self.browser.new_context(**PROFILES[profile])
        corpus_requests, errors = [], []

        def refuse_corpus(route):
            # A regression must never reach a live corpus during a test.
            route.fulfill(status=500, content_type="application/json", body='{"ok":false}')

        context.on("request", lambda request: corpus_requests.append(request.url)
                   if urlsplit(request.url).path.startswith("/api/corpus/") else None)
        context.route("**/api/corpus/**", refuse_corpus)
        context.route("https://nbow.io/favicon.ico", lambda route: route.abort())
        context.route("https://nbow.io/*/products/aiconsulting/code-agents/share",
                      lambda route: route.fulfill(content_type="text/html", body=RECEIVER))
        context.add_init_script("""(() => {
          window.shareGestures = [];
          const originalOpen = window.open;
          window.open = (...args) => {
            window.shareGestures.push(navigator.userActivation.isActive);
            return originalOpen.apply(window, args);
          };
        })();""")
        page = context.new_page()
        page.set_default_timeout(10000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(self.origin + PREFIX + "/", wait_until="networkidle")
            page.wait_for_function("window.markdownChat?.snapshot()?.filename === 'document.md'")
            yield page, corpus_requests
            self.assertEqual(errors, [])
        finally:
            context.close()

    def assert_no_sharing(self, page, corpus_requests):
        self.assertEqual(corpus_requests, [])
        self.assertEqual(page.evaluate("shareGestures"), [])

    def test_manual_save_compile_and_repeat_save_ask_on_desktop_and_phone(self):
        for profile in PROFILES:
            with self.subTest(profile=profile), self.editor_page(profile) as (page, requests):
                content = "# Saved locally\n\nKeep this private unless I share it.\n"
                page.evaluate("text => cm.setValue(text)", content)
                modal = page.locator("#share-confirm")
                for action in ("save", "compile", "save"):
                    page.locator("#btn-" + action).click()
                    expect(modal).to_be_visible()
                    self.assertIn("nbow.io", modal.inner_text())
                    self.assert_no_sharing(page, requests)
                    self.assertEqual(page.request.get(
                        self.origin + PREFIX + "/api/file/document.md").text(), content)
                    if action == "compile":
                        page.keyboard.press("Escape")
                    else:
                        page.locator("#share-confirm-cancel").click()
                    expect(modal).to_be_hidden()
                    self.assert_no_sharing(page, requests)

                # Actual autosave runs after an editor change, with no offer.
                page.locator("label.toggle:has(#s-auto)").click()
                expect(page.locator("#s-auto")).to_be_checked()
                automatic = content + "\nAutosaved change.\n"
                page.evaluate("text => cm.setValue(text)", automatic)
                page.wait_for_function("!dirty && !savePending")
                expect(modal).to_be_hidden()
                self.assertEqual(page.request.get(
                    self.origin + PREFIX + "/api/file/document.md").text(), automatic)
                self.assert_no_sharing(page, requests)

    def test_confirmed_snapshot_survives_edits_while_the_popup_loads(self):
        for profile in PROFILES:
            with self.subTest(profile=profile), self.editor_page(profile) as (page, requests):
                # This listener runs after the application's handler and returns
                # a marker after any document message it sends. Waiting for that
                # marker lets the no-replay assertion avoid arbitrary sleeps.
                page.evaluate("""() => window.addEventListener('message', event => {
                  if (event.origin === 'https://nbow.io' &&
                      event.data?.source === 'nbow-corpus-share' && event.data.type === 'ready') {
                    event.source.postMessage({source: 'share-ui-test-ready-processed'}, event.origin);
                  }
                })""")
                saved = "# Confirmed Markdown\n\nMünchen\n"
                page.evaluate("text => cm.setValue(text)", saved)
                page.locator("#btn-save").click()
                expect(page.locator("#share-confirm")).to_be_visible()
                page.evaluate("cm.setValue('# Later edit before approval')")
                with page.expect_popup() as event:
                    page.locator("#share-confirm-open").click()
                popup = event.value
                popup.wait_for_load_state()
                page.evaluate("cm.setValue('# Later edit while popup loads')")
                popup.evaluate("sendReady()")
                popup.wait_for_function("receivedDocuments.length === 1")
                payload = popup.evaluate("receivedDocuments[0]")
                self.assertEqual(payload["content"], saved)
                self.assertEqual(payload["client"], "md2pdf-web")
                self.assertEqual(set(payload), {"source", "type", "client", "clientVersion", "content"})
                self.assertEqual(page.evaluate("shareGestures"), [True])
                self.assertEqual(requests, [])
                expect(page.locator("#share-confirm")).to_be_hidden()

                # A second handshake cannot replay the document or pick up
                # a newer editor draft without another explicit share click.
                page.evaluate("cm.setValue('# Later draft must never be replayed')")
                popup.evaluate("sendReady()")
                popup.wait_for_function("processedReadies === 2")
                self.assertEqual(popup.evaluate("receivedDocuments"), [payload])

                receipt = "ABCDE-12345-FGHIJ-67890"
                popup.evaluate("""receipt => window.opener.postMessage({
                  source: 'nbow-corpus-share', type: 'result', ok: true, receipt
                }, '*')""", receipt)
                expect(page.locator("#share-status")).to_have_attribute("data-state", "ok")
                expect(page.locator("#share-receipt")).to_be_visible()
                expect(page.locator("#share-receipt")).to_have_text(receipt)
                self.assertEqual(requests, [])
                popup.close()

                # Merely offering another share must keep the previous receipt.
                for action in ("save", "compile"):
                    page.locator("#btn-" + action).click()
                    expect(page.locator("#share-confirm")).to_be_visible()
                    expect(page.locator("#share-receipt")).to_have_text(receipt)
                    page.keyboard.press("Escape")
                    expect(page.locator("#share-confirm")).to_be_hidden()
                    expect(page.locator("#share-receipt")).to_be_visible()
                    expect(page.locator("#share-receipt")).to_have_text(receipt)
                    self.assertEqual(requests, [])

                # The standalone button still offers the current unsaved text,
                # frozen at the click instead of at the remote handshake.
                unsaved = "# Explicit unsaved share\n"
                page.evaluate("text => cm.setValue(text)", unsaved)
                with page.expect_popup() as event:
                    page.locator("#share-open").click()
                popup = event.value
                popup.wait_for_load_state()
                expect(page.locator("#share-receipt")).to_be_hidden()
                page.evaluate("cm.setValue('# Never approved')")
                popup.evaluate("sendReady()")
                popup.wait_for_function("receivedDocuments.length === 1")
                self.assertEqual(popup.evaluate("receivedDocuments[0].content"), unsaved)
                self.assertEqual(page.evaluate("shareGestures"), [True, True])
                self.assertEqual(requests, [])

    def test_pending_autosave_serializes_manual_saves_and_duplicate_compiles(self):
        for profile in PROFILES:
            with self.subTest(profile=profile), self.editor_page(profile) as (page, requests):
                file_url = self.origin + PREFIX + "/api/file/document.md"
                paused, save_statuses, compile_requests = [], [], []

                def hold_first_save(route):
                    if not paused:
                        paused.append(route)
                    else:
                        route.continue_()

                page.route(file_url, hold_first_save)
                page.on("response", lambda response: save_statuses.append(response.status)
                        if response.url == file_url and response.request.method == "POST" else None)
                page.on("request", lambda request: compile_requests.append(request)
                        if request.url == self.origin + PREFIX + "/api/compile" else None)
                page.evaluate("""() => {
                  cm.setValue('# Concurrent save');
                  window.raceSaves = null;
                  Promise.all([save(true), save(), save()]).then(results => window.raceSaves = results);
                }""")
                page.wait_for_function("savePending !== null")
                self.assertEqual(len(paused), 1)
                paused[0].continue_()
                page.wait_for_function("raceSaves !== null")
                self.assertEqual(page.evaluate("raceSaves"), [True, True, True])
                self.assertEqual(save_statuses, [200, 200, 200])
                expect(page.locator("#share-confirm")).to_be_visible()
                page.locator("#share-confirm-cancel").click()
                self.assert_no_sharing(page, requests)

                # A failed background request also settles the queued manual
                # save without an unhandled rejection or an offer to share.
                paused.clear()
                page.evaluate("""() => {
                  cm.setValue('# Keep this failed network save');
                  window.failedSaves = null;
                  Promise.all([save(true), save()]).then(results => window.failedSaves = results);
                }""")
                page.wait_for_function("savePending !== null")
                self.assertEqual(len(paused), 1)
                paused[0].abort("failed")
                page.wait_for_function("failedSaves !== null")
                self.assertEqual(page.evaluate("failedSaves"), [False, False])
                expect(page.locator("#share-confirm")).to_be_hidden()
                self.assert_no_sharing(page, requests)

                paused.clear()
                self.compiler.reset_mock()
                page.evaluate("""() => {
                  cm.setValue('# Concurrent compile');
                  window.raceCompilesFinished = false;
                  Promise.all([compile(), compile(), compile()]).then(() => window.raceCompilesFinished = true);
                }""")
                page.wait_for_function("savePending !== null")
                self.assertEqual(len(paused), 1)
                paused[0].continue_()
                page.wait_for_function("raceCompilesFinished")
                self.compiler.assert_called_once()
                self.assertEqual(len(compile_requests), 1)
                self.assertEqual(save_statuses, [200, 200, 200, 200])
                expect(page.locator("#share-confirm")).to_be_visible()
                page.locator("#share-confirm-cancel").click()
                self.assert_no_sharing(page, requests)

    def test_blocked_popup_never_sends_and_the_next_save_asks_again(self):
        for profile in PROFILES:
            with self.subTest(profile=profile), self.editor_page(profile) as (page, requests):
                page.evaluate("""() => {
                  cm.setValue('# Do not send automatically');
                  window.open = () => {
                    shareGestures.push(navigator.userActivation.isActive);
                    return null;
                  };
                }""")
                page.locator("#btn-save").click()
                expect(page.locator("#share-confirm")).to_be_visible()
                page.locator("#share-confirm-open").click()
                expect(page.locator("#share-confirm-error")).to_contain_text("blocked")
                expect(page.locator("#share-confirm")).to_be_visible()
                self.assertEqual(page.evaluate("shareGestures"), [True])
                self.assertEqual(requests, [])
                page.locator("#share-confirm-cancel").click()
                page.locator("#btn-save").click()
                expect(page.locator("#share-confirm")).to_be_visible()
                page.locator("#share-confirm-cancel").click()
                self.assertEqual(page.evaluate("shareGestures"), [True])
                self.assertEqual(requests, [])

    def test_save_and_compile_failures_never_offer_sharing(self):
        for profile in PROFILES:
            with self.subTest(profile=profile), self.editor_page(profile) as (page, requests):
                page.evaluate("cm.setValue('# Keep this failed save private')")
                file_url = self.origin + PREFIX + "/api/file/document.md"
                page.route(file_url, lambda route: route.fulfill(
                    status=409, content_type="application/json",
                    body=json.dumps({"error": "The document changed; reload first."})))
                self.compiler.reset_mock()
                for action in ("save", "compile"):
                    with page.expect_response(file_url):
                        page.locator("#btn-" + action).click()
                    expect(page.locator("#status-msg")).to_contain_text("reload first")
                    expect(page.locator("#share-confirm")).to_be_hidden()
                    self.assert_no_sharing(page, requests)
                self.compiler.assert_not_called()

                page.unroute(file_url)
                self.compiler.return_value = subprocess.CompletedProcess([], 1, "", "Invalid Markdown")
                page.locator("#btn-compile").click()
                page.wait_for_function("document.getElementById('status-msg').textContent.startsWith('Error')")
                expect(page.locator("#share-confirm")).to_be_hidden()
                self.assert_no_sharing(page, requests)
                self.compiler.return_value = subprocess.CompletedProcess([], 0, "", "")


if __name__ == "__main__":
    unittest.main()
