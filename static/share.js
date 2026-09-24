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
	const RECEIPT_PATTERN = /^[0-9A-HJKMNP-TV-Z]{5}(?:-[0-9A-HJKMNP-TV-Z]{5}){3}$/;
	const UNKNOWN_MESSAGE = "The server did not confirm whether this document was stored. Check the nbow.io window before trying again.";
	const FAILURE_MESSAGES = {
		corpus_unavailable: "Sharing is temporarily unavailable. Nothing was sent.",
		grant_required: "Sharing permission expired. Confirm your consent in the nbow.io window and try again.",
		consent_required: "Confirm your consent in the nbow.io window before sharing.",
		hourly_limit_reached: "The hourly sharing limit has been reached. Nothing was sent.",
		network_limit_reached: "The sharing limit for this network has been reached. Nothing was sent.",
		too_large: "This document is too large to share. Nothing was sent.",
		empty_document: "This document is empty. Nothing was sent.",
		unknown_client: "This version of the app cannot share. Reload it and try again.",
		cross_site_request: "The sharing request was refused. Nothing was sent.",
	};

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
	let closedTimer = null;
	let sharedContent = null;
	let offeredContent = null;
	let handedOff = false;
	let resultReceived = false;
	const confirmation = document.getElementById("share-confirm");
	const resultDialog = document.getElementById("share-result");

	function status(message, state) {
		const node = document.getElementById("share-status");
		node.textContent = message;
		node.dataset.state = state || "";
		const error = document.getElementById("share-confirm-error");
		if (error) error.textContent = state === "error" ? message : "";
	}

	function showReceipt(receipt) {
		const node = document.getElementById("share-receipt");
		node.textContent = receipt || "";
		node.hidden = !receipt;
		document.getElementById("share-receipt-label").hidden = !receipt;
	}

	function showResult(title, message, state, receipt = null) {
		status(message, state);
		resultDialog.dataset.state = state;
		document.getElementById("share-result-title").textContent = title;
		document.getElementById("share-result-message").textContent = message;
		const receiptNode = document.getElementById("share-result-receipt");
		receiptNode.textContent = receipt || "";
		receiptNode.hidden = !receipt;
		document.getElementById("share-result-copy").hidden = !receipt;
		document.getElementById("share-result-copy-status").textContent = "";
		if (confirmation.open) confirmation.close();
		if (!resultDialog.open) resultDialog.showModal();
	}

	function showFailure(data) {
		const knownMessage = FAILURE_MESSAGES[data.error];
		const notSent = data.outcome === "not_sent" ||
			(data.outcome !== "unknown" && Boolean(knownMessage));
		// Only the website window we opened can reach here. Render its localized
		// explanation as bounded plain text, never as markup or a driver error.
		const message = typeof data.message === "string" && data.message.trim()
			? data.message.trim().slice(0, 1200)
			: notSent ? knownMessage || "Nothing was sent to the corpus. Check the nbow.io window for details."
				: UNKNOWN_MESSAGE;
		showResult(notSent ? "Not shared with nbow.io" : "Sharing could not be confirmed", message, "error");
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
		if (closedTimer) clearInterval(closedTimer);
		readyTimer = null;
		closedTimer = null;
		popup = null;
		sharedContent = null;
		handedOff = false;
		resultReceived = false;
	}

	function popupClosed() {
		if (!resultReceived) {
			showFailure({outcome: handedOff ? "unknown" : "not_sent",
				message: handedOff ? UNKNOWN_MESSAGE : "The sharing window closed. Nothing was sent."});
		}
		cleanup();
	}

	window.addEventListener("message", (event) => {
		// Three checks, all required: the right origin, the window we actually
		// opened, and our own protocol marker. Any page may post to us.
		if (event.origin !== shareOrigin) return;
		if (!popup || event.source !== popup) return;
		const data = event.data;
		if (!data || data.source !== MESSAGE_SOURCE_IN) return;

		if (data.type === "ready") {
			// One handoff per explicit choice. Reloads and "share another" may
			// never pick up a later draft or resubmit the previous document.
			if (handedOff || sharedContent === null) return;
			if (readyTimer) clearTimeout(readyTimer);
			const content = sharedContent;
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
			handedOff = true;
			resultReceived = false;
			status("Waiting for your confirmation in the nbow.io window…", "");
			return;
		}

		if (data.type === "sending" && handedOff) {
			resultReceived = false;
			if (resultDialog.open) resultDialog.close();
			status("Sending to nbow.io…", "");
			return;
		}

		if (data.type === "result") {
			if (readyTimer) clearTimeout(readyTimer);
			readyTimer = null;
			resultReceived = true;
			if (data.ok === true && handedOff && typeof data.receipt === "string" && RECEIPT_PATTERN.test(data.receipt)) {
				showReceipt(data.receipt);
				showResult("Shared with nbow.io", "The document was stored in the nbow.io corpus. Keep this receipt to request deletion later.", "ok", data.receipt);
			} else {
				showFailure(data.ok === true ? {outcome: "unknown"} : data);
			}
			return;
		}

		if (data.type === "closed") popupClosed();
	});

	function openSharing(content) {
		if (!content || !content.trim()) {
			status("Open a Markdown file first.", "error");
			return false;
		}

		if (popup && !popup.closed) {
			popup.close();
		}
		cleanup();
		sharedContent = content;

		const url = `${shareBase}/${language()}/products/aiconsulting/code-agents/share`;
		// No `noopener` in the feature string, in any form: the handshake needs
		// window.opener on the other side, and a browser that parsed a
		// `noopener=no` token as "on" would break it in a way that looks like
		// the window simply never answering.
		// Called only from a click/tap, never after an awaited save/compile:
		// mobile browsers require this user gesture to open the review window.
		// A fresh window also avoids reusing a timed-out popup whose delayed
		// unload message could otherwise cancel this new handoff.
		popup = window.open(url, "_blank", "width=780,height=880");
		if (!popup) {
			status("Your browser blocked the window. Allow popups for this page.", "error");
			cleanup();
			return false;
		}

		status("Opening the nbow.io sharing window…", "");
		closedTimer = setInterval(() => { if (popup?.closed) popupClosed(); }, 500);
		readyTimer = setTimeout(() => {
			showFailure({outcome: "not_sent", message: "The sharing window did not respond. Nothing was sent."});
			cleanup();
		}, READY_TIMEOUT_MS);
		return true;
	}

	button.addEventListener("click", () => openSharing(currentContent()));

	window.addEventListener("md2pdf:share-offer", (event) => {
		const content = event.detail?.content;
		if (!confirmation || typeof content !== "string" || !content.trim()) return;
		offeredContent = content;
		status("Nothing is shared with the corpus until you confirm on nbow.io.", "");
		document.getElementById("share-confirm-result").textContent =
			event.detail.action === "compile" ? "Compiled OK" : "Saved";
		if (!confirmation.open) confirmation.showModal();
	});
	document.getElementById("share-confirm-open").addEventListener("click", () => {
		if (openSharing(offeredContent)) confirmation.close();
	});
	document.getElementById("share-confirm-cancel").addEventListener("click", () => {
		confirmation.close();
	});
	confirmation.addEventListener("close", () => { offeredContent = null; });
	document.getElementById("share-result-close").addEventListener("click", () => resultDialog.close());
	document.getElementById("share-result-copy").addEventListener("click", async () => {
		const receiptNode = document.getElementById("share-result-receipt");
		const copyStatus = document.getElementById("share-result-copy-status");
		try {
			await navigator.clipboard.writeText(receiptNode.textContent);
			copyStatus.textContent = "Receipt copied.";
		} catch (_) {
			const range = document.createRange();
			range.selectNodeContents(receiptNode);
			const selection = window.getSelection();
			selection.removeAllRanges();
			selection.addRange(range);
			copyStatus.textContent = "Select and copy the receipt above.";
		}
	});

	status("Nothing is shared with the corpus until you confirm on nbow.io.", "");
})();
