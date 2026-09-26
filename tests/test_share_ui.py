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
window.sendResult = result => window.opener.postMessage({
  source: 'nbow-corpus-share', type: 'result', ...result
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

    def open_controls(self, page):
        if "hidden" in (page.locator("#panel").get_attribute("class") or "").split():
            page.locator("#fab").click()
        expect(page.locator("#panel")).not_to_have_class("hidden")

    def assert_document_returned(self, page, profile, action, content):
        self.assertEqual(page.evaluate("cm.getValue()"), content)
        self.assertEqual(page.evaluate("current"), "document.md")
        target = page.locator("#pdf-pane" if action == "compile" else "#editor-pane")
        expect(target).to_be_focused()
        if profile == "phone":
            expect(page.locator("#panel")).to_have_class("hidden")
            expect(target).to_be_in_viewport(ratio=0.95)
            # Returning to the document must not reopen the phone keyboard.
            self.assertNotEqual(page.evaluate("document.activeElement.tagName"), "TEXTAREA")

    def compile_test_pdf(self, command, **_kwargs):
        source = Path(command[command.index("--hosted") - 1])
        output = Path(command[command.index("--output-dir") + 1])
        (output / source.with_suffix(".pdf").name).write_bytes(b"%PDF-1.4\nMobile return test")
        return subprocess.CompletedProcess(command, 0, "", "")

    def test_manual_save_compile_and_repeat_save_ask_on_desktop_and_phone(self):
        self.compiler.side_effect = self.compile_test_pdf
        for profile in PROFILES:
            with self.subTest(profile=profile), self.editor_page(profile) as (page, requests):
                content = "# Saved locally\n\nKeep this private unless I share it.\n"
                page.evaluate("text => cm.setValue(text)", content)
                modal = page.locator("#share-confirm")
                for action in ("save", "compile", "save"):
                    self.open_controls(page)
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
                    self.assert_document_returned(page, profile, action, content)
                    if action == "compile":
                        expect(page.locator("#pdf-frame")).to_be_visible()
                        self.assertIn("/pdf/document.pdf?", page.locator("#pdf-frame").get_attribute("src"))

                # Actual autosave runs after an editor change, with no offer.
                self.open_controls(page)
                page.locator("label.toggle:has(#s-auto)").click()
                expect(page.locator("#s-auto")).to_be_checked()
                automatic = content + "\nAutosaved change.\n"
                page.evaluate("text => cm.setValue(text)", automatic)
                page.wait_for_function("!dirty && !savePending")
                expect(modal).to_be_hidden()
                self.assertEqual(page.request.get(
                    self.origin + PREFIX + "/api/file/document.md").text(), automatic)
                self.assert_no_sharing(page, requests)

    def test_success_closes_review_and_returns_to_saved_or_compiled_document(self):
        self.compiler.side_effect = self.compile_test_pdf
        receipt = "ABCDE-12345-FGHJK-67890"
        for profile in PROFILES:
            for action in ("save", "compile", "direct"):
                with self.subTest(profile=profile, action=action), self.editor_page(profile) as (page, requests):
                    content = "# Return to my document\n\nKeep this text after sharing.\n"
                    page.evaluate("text => cm.setValue(text)", content)
                    if action != "direct":
                        page.locator("#btn-" + action).click()
                        expect(page.locator("#share-confirm")).to_be_visible()
                    with page.expect_popup() as event:
                        page.locator("#share-open" if action == "direct" else "#share-confirm-open").click()
                    popup = event.value
                    popup.wait_for_load_state()
                    popup.evaluate("sendReady()")
                    popup.wait_for_function("receivedDocuments.length === 1")
                    self.assertEqual(popup.evaluate("receivedDocuments[0].content"), content)

                    # The application must close the review tab itself once it
                    # has received the receipt; manually closing it hid the bug.
                    with popup.expect_event("close"):
                        popup.evaluate("receipt => sendResult({ok: true, receipt, outcome: 'stored'})", receipt)
                    expect(page.locator("#share-result")).to_be_visible()
                    expect(page.locator("#share-result-receipt")).to_have_text(receipt)
                    page.locator("#share-result-close").click()
                    expect(page.locator("#share-result")).to_be_hidden()
                    self.assert_document_returned(page, profile, action, content)
                    if action == "compile":
                        expect(page.locator("#pdf-frame")).to_be_visible()
                        self.assertTrue(page.request.get(
                            self.origin + PREFIX + "/pdf/document.pdf").body().startswith(b"%PDF"))
                    self.assertEqual(requests, [])

    def test_cancelled_review_returns_to_phone_document_without_claiming_it_was_shared(self):
        self.compiler.side_effect = self.compile_test_pdf
        for action in ("save", "compile"):
            with self.subTest(action=action), self.editor_page("phone") as (page, requests):
                content = "# Keep my saved document\n\nI chose not to share.\n"
                page.evaluate("text => cm.setValue(text)", content)
                page.locator("#btn-" + action).click()
                expect(page.locator("#share-confirm")).to_be_visible()
                with page.expect_popup() as event:
                    page.locator("#share-confirm-open").click()
                popup = event.value
                popup.wait_for_load_state()
                popup.evaluate("sendReady()")
                popup.wait_for_function("receivedDocuments.length === 1")
                with popup.expect_event("close"):
                    popup.evaluate("sendResult({ok: false, error: 'cancelled', outcome: 'not_sent', message: 'Nothing was sent.'})")
                expect(page.locator("#share-result-title")).to_have_text("Not shared with nbow.io")
                expect(page.locator("#share-result-receipt")).to_be_hidden()
                page.keyboard.press("Escape")
                expect(page.locator("#share-result")).to_be_hidden()
                self.assert_document_returned(page, "phone", action, content)
                self.assertEqual(requests, [])

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

                receipt = "ABCDE-12345-FGHJK-67890"
                popup.evaluate("""receipt => window.opener.postMessage({
                  source: 'nbow-corpus-share', type: 'result', ok: true, receipt
                }, '*')""", receipt)
                expect(page.locator("#share-status")).to_have_attribute("data-state", "ok")
                expect(page.locator("#share-receipt")).to_be_visible()
                expect(page.locator("#share-receipt")).to_have_text(receipt)
                expect(page.locator("#share-result")).to_be_visible()
                self.assertTrue(popup.is_closed())
                page.locator("#share-result-close").click()
                expect(page.locator("#editor-pane")).to_be_focused()
                self.assertEqual(requests, [])

                # Merely offering another share must keep the previous receipt.
                for action in ("save", "compile"):
                    self.open_controls(page)
                    page.locator("#btn-" + action).click()
                    expect(page.locator("#share-confirm")).to_be_visible()
                    expect(page.locator("#share-receipt")).to_have_text(receipt)
                    page.keyboard.press("Escape")
                    expect(page.locator("#share-confirm")).to_be_hidden()
                    expect(page.locator("#pdf-pane" if action == "compile" else "#editor-pane")).to_be_focused()
                    self.open_controls(page)
                    expect(page.locator("#share-receipt")).to_be_visible()
                    expect(page.locator("#share-receipt")).to_have_text(receipt)
                    self.assertEqual(requests, [])

                # The standalone button still offers the current unsaved text,
                # frozen at the click instead of at the remote handshake.
                unsaved = "# Explicit unsaved share\n"
                page.evaluate("text => cm.setValue(text)", unsaved)
                self.open_controls(page)
                with page.expect_popup() as event:
                    page.locator("#share-open").click()
                popup = event.value
                popup.wait_for_load_state()
                expect(page.locator("#share-receipt")).to_have_text(receipt)
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

    def test_share_result_is_visible_with_panel_collapsed_and_keeps_last_receipt(self):
        receipt = "ABCDE-12345-FGHJK-67890"
        for profile in PROFILES:
            with self.subTest(profile=profile), self.editor_page(profile) as (page, requests):
                page.evaluate("cm.setValue('# Explicit sharing outcome test')")
                with page.expect_popup() as event:
                    page.locator("#share-open").click()
                popup = event.value
                popup.wait_for_load_state()
                popup.evaluate("sendReady()")
                popup.wait_for_function("receivedDocuments.length === 1")
                page.locator("#btn-close").click()
                expect(page.locator("#panel")).to_have_class("hidden")

                popup.evaluate("receipt => sendResult({ok: true, receipt, outcome: 'stored'})", receipt)
                modal = page.locator("#share-result")
                expect(modal).to_be_visible()
                expect(page.locator("#share-result-title")).to_have_text("Shared with nbow.io")
                expect(page.locator("#share-result-receipt")).to_have_text(receipt)
                bounds = modal.bounding_box()
                self.assertGreaterEqual(bounds["x"], 0)
                self.assertLessEqual(bounds["x"] + bounds["width"], PROFILES[profile]["viewport"]["width"])
                self.assertLessEqual(bounds["y"] + bounds["height"], PROFILES[profile]["viewport"]["height"])
                page.evaluate("""() => Object.defineProperty(navigator, 'clipboard', {
                  configurable: true, value: {writeText: async text => { window.copiedReceipt = text; }}
                })""")
                page.locator("#share-result-copy").click()
                expect(page.locator("#share-result-copy-status")).to_have_text("Receipt copied.")
                self.assertEqual(page.evaluate("copiedReceipt"), receipt)
                page.locator("#share-result-close").click()
                self.assertTrue(popup.is_closed())

                # Each later attempt gets its own result. The previous receipt
                # remains available and explicitly belongs to the last success.
                cases = [
                    ({"ok": False, "error": "storage_unavailable", "outcome": "not_sent",
                      "message": "Storage is unavailable. Nothing was stored."},
                     "Not shared with nbow.io", "Storage is unavailable. Nothing was stored."),
                    ({"ok": False, "error": "network_error", "outcome": "unknown",
                      "message": "The connection was lost after sending. Storage could not be confirmed."},
                     "Sharing could not be confirmed", "The connection was lost after sending. Storage could not be confirmed."),
                    ({"ok": True, "receipt": "malformed-receipt"},
                     "Sharing could not be confirmed", "The server did not confirm whether this document was stored."),
                    ({"ok": False, "error": "corpus_unavailable"},
                     "Not shared with nbow.io", "Sharing is temporarily unavailable. Nothing was sent."),
                    ({"ok": False},
                     "Sharing could not be confirmed", "The server did not confirm whether this document was stored."),
                ]
                for result, title, message in cases:
                    with self.subTest(result=result):
                        page.locator("#fab").click()
                        with page.expect_popup() as event:
                            page.locator("#share-open").click()
                        popup = event.value
                        popup.wait_for_load_state()
                        popup.evaluate("sendReady()")
                        popup.wait_for_function("receivedDocuments.length === 1")
                        page.locator("#btn-close").click()
                        popup.evaluate("result => sendResult(result)", result)
                        expect(modal).to_be_visible()
                        expect(page.locator("#share-result-title")).to_have_text(title)
                        expect(page.locator("#share-result-message")).to_contain_text(message)
                        expect(page.locator("#share-result-receipt")).to_be_hidden()
                        expect(page.locator("#share-result-copy")).to_be_hidden()
                        expect(page.locator("#share-receipt")).to_have_text(receipt)
                        expect(page.locator("#share-receipt-label")).to_have_text("Last confirmed receipt")
                        self.assertFalse(popup.is_closed())
                        self.assertEqual(requests, [])
                        page.locator("#share-result-close").click()
                        popup.close()

    def test_grant_failure_before_handoff_and_popup_close_have_explicit_outcomes(self):
        for profile in PROFILES:
            with self.subTest(profile=profile), self.editor_page(profile) as (page, requests):
                page.evaluate("cm.setValue('# Sharing outcome test')")
                with page.expect_popup() as event:
                    page.locator("#share-open").click()
                popup = event.value
                popup.wait_for_load_state()
                page.locator("#btn-close").click()
                popup.evaluate("""sendResult({ok: false, error: 'grant_required', outcome: 'not_sent',
                  message: 'Confirm consent in the nbow.io window. Nothing was sent.'})""")
                expect(page.locator("#share-result")).to_be_visible()
                expect(page.locator("#share-result-title")).to_have_text("Not shared with nbow.io")
                expect(page.locator("#share-result-message")).to_contain_text("Confirm consent")
                self.assertEqual(popup.evaluate("receivedDocuments"), [])
                page.locator("#share-result-close").click()
                popup.close()

                for handoff in (False, True):
                    page.locator("#fab").click()
                    with page.expect_popup() as event:
                        page.locator("#share-open").click()
                    popup = event.value
                    popup.wait_for_load_state()
                    if handoff:
                        popup.evaluate("sendReady()")
                        popup.wait_for_function("receivedDocuments.length === 1")
                    page.locator("#btn-close").click()
                    popup.close()
                    expect(page.locator("#share-result")).to_be_visible()
                    title = "Sharing could not be confirmed" if handoff else "Not shared with nbow.io"
                    expect(page.locator("#share-result-title")).to_have_text(title)
                    page.locator("#share-result-close").click()
                    self.assertEqual(requests, [])

    def test_closing_during_retry_does_not_keep_a_previous_rejection(self):
        for profile in PROFILES:
            with self.subTest(profile=profile), self.editor_page(profile) as (page, requests):
                page.evaluate("cm.setValue('# Explicit retry')")
                with page.expect_popup() as event:
                    page.locator("#share-open").click()
                popup = event.value
                popup.wait_for_load_state()
                popup.evaluate("sendReady()")
                popup.wait_for_function("receivedDocuments.length === 1")
                popup.evaluate("sendResult({ok: false, error: 'hourly_limit_reached', outcome: 'not_sent'})")
                expect(page.locator("#share-result-title")).to_have_text("Not shared with nbow.io")
                popup.evaluate("window.opener.postMessage({source: 'nbow-corpus-share', type: 'sending'}, '*')")
                expect(page.locator("#share-result")).to_be_hidden()
                expect(page.locator("#share-status")).to_have_text("Sending to nbow.io…")
                popup.close()
                expect(page.locator("#share-result")).to_be_visible()
                expect(page.locator("#share-result-title")).to_have_text("Sharing could not be confirmed")
                self.assertEqual(requests, [])

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
                self.assert_document_returned(page, profile, "save", "# Do not send automatically")
                self.open_controls(page)
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
