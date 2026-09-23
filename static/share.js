/* Hand the open document to nbow.io's consent window — and nothing else.
 *
 * WHY A POPUP AND NOT A POST FROM HERE.
 *
 * This app runs on your machine, at localhost. nbow.io's cookie consent lives
 * in nbow.io's own storage, which this origin cannot read, and nbow.io's server
 * has no reason to believe a claim made by a page it did not serve. So this
 * file does not send anything. It opens a window on nbow.io, waits to be asked,
 * hands over the text, and reports what comes back. Every decision — whether
 * consent exists, whether the visitor agrees, whether the limit is reached — is
 * made over there, where it can be enforced.
 *
 * WHAT IS HANDED OVER. The editor's current text, including unsaved changes,
 * and nothing more. Not the file name, not the input directory, not the disk
 * revision: `snapshot()` returns all four and this file deliberately reads only
 * `content`. A file name is usually the most revealing thing about a document
 * ("offer_acme_2026.md"), and the cleanest way to keep it out of a corpus is to
 * never put it on the wire.
 *
 * The receipt that comes back is shown here so it can be copied before the
 * window is closed. It is the only way to have that document deleted later.
 */
(() => {
	"use strict";

	const MESSAGE_SOURCE_IN = "nbow-corpus-share";
	const MESSAGE_SOURCE_OUT = "nbow-corpus-client";
	/** Give up if the window never says hello — blocked, offline, or 404. */
	const READY_TIMEOUT_MS = 20000;

	const button = document.getElementById("share-open");
	if (!button) return;
	const CLIENT_ID = button.dataset.clientId || "md2pdf-desktop";

	const shareBase = button.dataset.shareBase;
	const clientVersion = button.dataset.clientVersion || null;
	let shareOrigin;
	try {
		shareOrigin = new URL(shareBase).origin;
	} catch (_) {
		button.disabled = true;
		return;
	}

	let popup = null;
	let readyTimer = null;

	function status(message, state) {
		const node = document.getElementById("share-status");
		node.textContent = message;
		node.dataset.state = state || "";
	}

	function showReceipt(receipt) {
		const node = document.getElementById("share-receipt");
		node.textContent = receipt || "";
		node.hidden = !receipt;
	}

	function language() {
		const selected = document.documentElement.lang;
		if (["en", "de", "es"].includes(selected)) return selected;
		try {
			const stored = localStorage.getItem("md2pdf-language");
			if (["en", "de", "es"].includes(stored)) return stored;
		} catch (_) {
			/* storage unavailable; English is a fine default */
		}
		return "en";
	}

	function currentContent() {
		const snapshot = window.markdownChat && window.markdownChat.snapshot();
		// Only the text. See the note at the top about the file name.
		return snapshot ? snapshot.content : null;
	}

	function cleanup() {
		if (readyTimer) clearTimeout(readyTimer);
		readyTimer = null;
		popup = null;
	}

	window.addEventListener("message", (event) => {
		// Three checks, all required: the right origin, the window we actually
		// opened, and our own protocol marker. Any page may post to us.
		if (event.origin !== shareOrigin) return;
		if (!popup || event.source !== popup) return;
		const data = event.data;
		if (!data || data.source !== MESSAGE_SOURCE_IN) return;

		if (data.type === "ready") {
			if (readyTimer) clearTimeout(readyTimer);
			const content = currentContent();
			if (!content) {
				status("Open a Markdown file first.", "error");
				return;
			}
			popup.postMessage(
				{
					source: MESSAGE_SOURCE_OUT,
					type: "document",
					client: CLIENT_ID,
					clientVersion: clientVersion,
					content: content,
				},
				shareOrigin,
			);
			status("Waiting for your confirmation in the nbow.io window…", "");
			return;
		}

		if (data.type === "result") {
			if (data.ok) {
				status("Shared. Keep the receipt to have it deleted later.", "ok");
				showReceipt(data.receipt);
			} else {
				status("Not shared. See the nbow.io window for the reason.", "error");
				showReceipt(null);
			}
			return;
		}

		if (data.type === "closed") cleanup();
	});

	button.addEventListener("click", () => {
		if (!currentContent()) {
			status("Open a Markdown file first.", "error");
			return;
		}

		showReceipt(null);

		if (popup && !popup.closed) {
			popup.focus();
			status("The sharing window is already open.", "");
			return;
		}

		const url = `${shareBase}/${language()}/products/aiconsulting/code-agents/share`;
		// No `noopener` in the feature string, in any form: the handshake needs
		// window.opener on the other side, and a browser that parsed a
		// `noopener=no` token as "on" would break it in a way that looks like
		// the window simply never answering.
		popup = window.open(url, "nbow-corpus-share", "width=780,height=880");
		if (!popup) {
			status("Your browser blocked the window. Allow popups for this page.", "error");
			return;
		}

		status("Opening the nbow.io sharing window…", "");
		readyTimer = setTimeout(() => {
			status("The sharing window did not respond. Nothing was sent.", "error");
			cleanup();
		}, READY_TIMEOUT_MS);
	});

	status("Nothing is shared with the corpus until you confirm on nbow.io.", "");
})();
