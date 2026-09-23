# Sharing a document with nbow.io

Optional. md2pdf works exactly the same if you never press the button, and it
makes no network request of its own.

The **Share with nbow.io** button in the settings panel contributes the document
you have open to a public research corpus about how technical Markdown is
written — how long documents get, which features are actually used, where
converters break. What is collected, kept and deleted is described on
<https://nbow.io/en/products/aiconsulting/code-agents#markdown-corpus>.

## Why it opens a window instead of posting

md2pdf runs at `localhost`. nbow.io's cookie consent lives in nbow.io's own
browser storage, which this origin cannot read, and nbow.io's server has no
reason to believe a consent claim made by a page it never served. A dialog drawn
here could only *assert* that you agreed.

So the button opens a page on nbow.io instead. That page reads the real consent
state, shows you the text, collects the confirmations and asks its own server
for a short-lived submission grant. The upload is refused without that grant, so
the gate is enforced where it can be, rather than promised where it cannot.

This is also why the button cannot be made to work offline, and why it is the
one part of md2pdf that needs the internet.

## What happens, in order

1. You press **Share with nbow.io**. A window opens at
   `<share base>/<language>/products/aiconsulting/code-agents/share`. The
   language follows the panel's own selector.
2. That window says it is ready. Only then does md2pdf post it the document.
3. The window checks your nbow.io cookie consent. Sharing needs the
   **Statistics + Experience** level; below it, the send button stays disabled
   and the cookie banner is one click away in the same window.
4. It shows you the complete text that would be sent, with its size, line and
   word counts, and asks you to confirm two things: that you have read it, and
   that it contains no personal or confidential data.
5. On **Send**, nbow.io stores the document and returns a receipt code. md2pdf
   shows that code under the button so you can copy it before closing.

Nothing leaves your machine before step 5.

## What is sent

The editor's current text, including unsaved changes. That is all.

**The file name is never sent.** `window.markdownChat.snapshot()` returns the
file name, the input directory and the disk revision alongside the content, and
`static/share.js` deliberately reads only `content`. A file name is usually the
most revealing thing about a document — `offer_acme_2026.md` names a client —
and the reliable way to keep it out of a corpus is to never put it on the wire.

nbow.io additionally records which tool sent the document, the interface
language, and the time and level of your consent. It does not record your IP
address, your browser identification or the page you came from.

## The receipt

The receipt code is the only handle on your document. nbow.io stores only its
SHA-256, so it can check a code you present but cannot work back from a stored
document to you. Presenting the code in the same window deletes that document
immediately, with no account and no consent needed.

Keep the code if you might want the document withdrawn. Nobody can recover it
for you, and without it nobody — including nbow — can tell which row is yours.

## Limits

| | |
|---|---|
| Documents per hour | 3 |
| Maximum size | 256 kB |
| Retention | 24 months, then deleted automatically |

The hourly limit is counted against the consent you gave, not against you. A
second, higher limit is counted against your network so that discarding the
cookie does not reset the first; nbow.io's privacy policy describes how that
counter is built and why it cannot be turned back into an address.

## Pointing it somewhere else

```powershell
$env:NBOW_SHARE_BASE = "http://localhost:4321"
.venv\Scripts\python app.py
```

`NBOW_SHARE_BASE` sets the origin of the sharing window and defaults to
`https://nbow.io`. `static/share.js` checks every incoming `postMessage` against
that exact origin, so a window from anywhere else cannot talk to md2pdf. Use it
to test against a local checkout of the website; note that the local site needs
`CORPUS_DB_URL` and `CORPUS_GRANT_SECRET` set, or its endpoints answer 503 and
the window says sharing is switched off.
