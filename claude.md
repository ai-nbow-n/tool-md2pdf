# claude.md — Project notes for tool-md2pdf

## Project overview

A self-contained Markdown-to-PDF tool with a browser-based editor frontend.
Write and preview Markdown documents; compile them to PDF via a headless
Chromium browser so Mermaid diagrams render natively. An optional chat
assistant edits the open document with validated line edits, and the same
application runs unchanged as a public, sandboxed editor on nbow.io.

---

## File structure

```
tool-md2pdf/
├── .gitattributes              # deploy/ shell, conf and systemd files stay LF
├── .gitignore                  # .venv/, browsers/, data/output/, apikey.txt
├── .venv/                      # Python virtual environment (gitignored)
├── app.py                      # Flask editor frontend + inline PAGE template (:2380)
├── requirements.txt            # playwright, markdown, Pygments, flask, bleach
├── requirements-hosted.txt     # requirements.txt + gunicorn (server deployment)
├── data/
│   ├── input/                  # drop .md files here (desktop use)
│   └── output/                 # generated PDFs (gitignored)
├── docs/
│   ├── chat.md                 # the editing assistant
│   ├── hosting.md              # nbow.io deployment and visitor storage
│   ├── live-chat-results.md    # live model, timeout and prompt measurements
│   └── share.md                # the optional nbow.io corpus donation
├── services/
│   ├── md2pdf.py               # CLI conversion tool (Playwright + markdown)
│   ├── documents.py            # line edits, revision checks, atomic saves
│   ├── llm.py                  # /api/llm blueprint (server's Ollama, qwen3:1.7b)
│   └── workspaces.py           # hosted sessions, per-browser workspaces, cleanup
├── static/
│   ├── chat.js                 # chat UI
│   ├── corpus-info.{js,css}    # corpus explainer beside the share button (sends nothing)
│   ├── files.js                # browser import and Markdown/PDF downloads
│   ├── i18n.js                 # interface translations (en/de/es)
│   ├── nbow.ico                # footer icon, a copy of nbow.io's favicon
│   ├── share.js                # the nbow.io sharing popup handshake
│   └── vendor/                 # CodeMirror 5.65.16, Mermaid 12.0.0 (+ licenses)
├── deploy/
│   ├── install.sh              # VPS installer run by the website Actions console
│   ├── run-release.sh          # root wrapper; accepts exactly one commit SHA
│   ├── configure_nginx.py      # adds the md2pdf locations to the website site
│   ├── smoke.py                # post-deploy check of the installed hosted editor
│   ├── nginx-md2pdf*.conf      # location snippets (assets, long requests, proxy)
│   ├── md2pdf.service          # systemd unit (gunicorn, one worker)
│   ├── md2pdf-cleanup.*        # hourly expired-workspace timer + service
│   ├── md2pdf-chromium.apparmor  # Chromium user-namespace permission on Ubuntu
│   └── md2pdf.env.example      # /etc/md2pdf.env template
├── scripts/
│   └── live_chat_smoke.py      # explicit live chat test against a real Ollama (free)
└── tests/                      # unittest suite (several drive real Chromium)
```

---

## Setup (one-time)

```powershell
# From the project root
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\playwright install chromium
```

---

## Usage

### Editor UI

```powershell
.venv\Scripts\python app.py
# Open http://localhost:2380
# Ctrl+S = save   Ctrl+Enter = compile
```

The layout controls in the panel map to CLI flags: font style, font size, page
size and document style. Compilation runs `services/md2pdf.py` as a subprocess
with a 120 s timeout; two compilations may run at once, and a repeat of the same
(directory, file) job is refused with HTTP 429 rather than queued.

### CLI (md2pdf.py directly)

```powershell
# Convert all *.md in data/input/ → data/output/
.venv\Scripts\python services\md2pdf.py

# Convert a specific file
.venv\Scripts\python services\md2pdf.py path\to\file.md

# Custom directories
.venv\Scripts\python services\md2pdf.py --input-dir C:\docs --output-dir C:\pdfs

# Skip Mermaid CDN (offline; diagrams won't render)
.venv\Scripts\python services\md2pdf.py --no-mermaid-cdn

# Layout
.venv\Scripts\python services\md2pdf.py --font-style serif    # default | serif | typewriter
.venv\Scripts\python services\md2pdf.py --font-size 12        # 8 | 10 | 12 (pt)
.venv\Scripts\python services\md2pdf.py --page-size A6        # A2 | A4 | A6
.venv\Scripts\python services\md2pdf.py --doc-style article   # plain | article | beamer

# Untrusted input: sanitized HTML, bundled Mermaid, no network access
.venv\Scripts\python services\md2pdf.py --hosted
```

`beamer` turns the page landscape and `article` sets two columns.
`_page_dimensions()` is the single place that knows about the rotation; both the
print viewport and the Mermaid scaling read from it.

### Hosted website

The editor also runs under `/{lang}/products/aiconsulting/code-agents/md2pdf/`
on nbow.io. The sibling website repository proxies that path to the loopback
Python service. Setup and systemd files are documented in [docs/hosting.md](docs/hosting.md).
`MD2PDF_HOSTED=1` requires a stable `MD2PDF_SECRET_KEY` and enables isolated,
temporary browser workspaces. Every document path, including chat edits, must
go through `services/workspaces.py`; never trust server directories from clients.
The hosted renderer sanitizes HTML, uses bundled Mermaid, and blocks networking.
Desktop use remains the default. Frontend URLs must use `window.md2pdfUrl()` so
localized paths work (in the inline template, `__APP_BASE__/static/...`).
Browser assets are vendored in `static/vendor/`. The editor page itself loads
nothing from another origin, so a visitor's browser contacts only nbow.io: the
footer uses `static/nbow.ico` and an inline SVG GitHub mark (a `github.com`
favicon was removed for this reason). Keep new icons and fonts local too.

---

## Hosted mode — what changes

`configure_hosted(app)` runs at import and is the switch for everything below;
`hosted_mode()` is the check to use anywhere else. None of it is active for
ordinary desktop use.

| Variable | Default | Meaning |
|---|---|---|
| `MD2PDF_HOSTED` | `0` | Enables sessions, workspaces and the sandboxed renderer |
| `MD2PDF_SECRET_KEY` | — | Required when hosted; must stay stable across restarts |
| `MD2PDF_WORKSPACE_ROOT` | `<temp>/md2pdf-workspaces` | Where per-browser workspaces live |
| `MD2PDF_MAX_WORKSPACES` | `1000` | Capacity; over it, expired ones are swept, then HTTP 503 |
| `MD2PDF_HOURLY_BYTES` | `104857600` | Stored-Markdown growth allowed per network per rolling hour; over it, HTTP 429 |
| `MD2PDF_COOKIE_SECURE` | `1` | Set to `0` only for HTTP localhost testing |
| `NBOW_SHARE_BASE` | `https://nbow.io` | Corpus popup origin *and* postMessage allowlist |

- A signed, essential `md2pdf_session` cookie carries a 64-hex workspace token.
  `input_directory()` and `output_directory()` refuse any client-supplied
  directory and return that request's workspace instead.
- Limits per workspace: 1 MB per document, 20 documents, 10 MB of Markdown,
  24 h of inactivity before expiry. Requests sweep expired workspaces and the
  systemd timer sweeps hourly, so physical removal can lag by up to an hour.
- Workspaces cost nothing to create, so `validate_save()` also charges each
  save's *growth* (new size minus old, never negative) to the visitor's network
  (IPv4 /24, IPv6 /48, from nginx's `X-Real-IP`): 100 MB per rolling hour
  across all its workspaces. Rewrites at the same size, i.e. every autosave,
  are free. Counters are keyed HMACs in process memory only, forgotten after an
  hour or on restart; `atomic_write()` charges only after the replace succeeds.
- Requests: 2 MB body cap, JSON-only POSTs, same-origin `Origin` check,
  `ProxyFix` trusting exactly one proxy for scheme and path prefix, and
  `no-store` / `nosniff` / `no-referrer` / `SAMEORIGIN` on every response.
- Compilation failures return a generic message. Mermaid's own errors quote
  document text, so they must never reach logs or the browser.

---

## Chat assistant

`services/llm.py` is a `/api/llm` blueprint (`/status`, `/chat`, `/apply`) over
the server's own Ollama (`MD2PDF_OLLAMA_URL`, default loopback; model
`MD2PDF_LLM_MODEL`, default `qwen3:1.7b`, Apache 2.0 — never `qwen2.5:3b`,
whose licence is research-only); `services/documents.py` owns the
document side. Full behaviour is in [docs/chat.md](docs/chat.md), with the
measurements behind every budget in
[docs/live-chat-results.md](docs/live-chat-results.md). What matters in the code:

- **No third party, no key.** Since 2026-09-25 the assistant runs on the
  server's model; it replaced a bring-your-own-key OpenAI proxy, and nothing may
  send document text off the server again without the privacy policy saying so
  first. Chat history is per tab; Ollama keeps only its model and prompt cache.
- **Edits are quoted passages, validated here.** The model returns
  `{"find", "replace"}` pairs; `to_line_edits()` locates each passage exactly
  once (character for character; overlapping occurrences count as ambiguous;
  no whitespace tolerance — it once edited inside words), rejects missing,
  ambiguous and overlapping ones,
  and converts the result to 1-based line edits that `apply_line_edits()`
  replays and checks. One corrective round trip is allowed inside the same time
  budget. Nothing is written until a whole batch validates. Line numbers were
  tried first and a 3B model got them wrong (see the results doc). An empty
  `find` appends to the end; a replacement carrying the `<document>` tags is
  refused.
- **An empty document is written, not edited.** It gets `WRITE_INSTRUCTIONS`
  and `WRITE_SCHEMA` (`markdown` first, then `reply`, 1,024 output tokens) and
  no `<document>` block. With the edit format the 1.7B model answered in chat
  or wrote the wrapper into the file.
- **Measure every prompt or schema change on the real model.** Rewording the
  edit prompt, or adding an `append` field, made `qwen3:1.7b` edit documents in
  answer to plain questions; the schema's property order also changes what it
  writes. A local `ollama serve` with `qwen3:1.7b` pulled runs the same build:
  run `scripts/live_chat_smoke.py` plus empty-document requests and questions,
  and record the results in the results doc.
- **Saves are optimistic and atomic.** Every read returns a SHA-256
  `disk_revision`; saves and chat edits pass it back and get HTTP 409 if the file
  changed underneath. Writes go through `atomic_write()` under `DOCUMENT_LOCK`.
- **The document is data.** `INSTRUCTIONS` says so explicitly, the document sits
  inside `<document>` tags (an empty one is not sent at all), and the app — not
  the model — performs every write.
  Keep it that way when editing the prompt.
- **The server has 2 vCPUs.** One generation at a time (`_SLOT`, others get 429);
  180 s per generation, 10 s for status checks; documents up to 4,000 characters
  and conversations up to 4,000; hosted, 600 s of generation per network per
  hour, charged after the fact and held as keyed hashes in memory like the save
  allowance. The browser timeouts are
  generated from these constants, so change them in `services/llm.py` and the
  page follows.

---

## Sharing with nbow.io (optional)

`static/share.js` adds a **Share with nbow.io** button that contributes the open
document to a public Markdown research corpus. Full description in
[docs/share.md](docs/share.md); the parts worth knowing before editing the code:

- **Nothing is sent from here.** The button opens a window on nbow.io and posts
  the document to it only after that window says it is ready. Every check —
  cookie consent, the two acknowledgements, the three-per-hour limit — happens
  on nbow.io, because consent lives in nbow.io's storage and this app runs at
  `localhost`, where it can neither read that state nor be believed about it.
  Hosted conversion already processes documents on nbow.io; the sharing button
  only governs the separate corpus donation. The client ID is `md2pdf-web` when
  hosted and `md2pdf-desktop` locally.
- **The file name is never sent.** `window.markdownChat.snapshot()` hands back
  `{filename, input_dir, content, disk_revision}` and `share.js` reads only
  `content`. That is a privacy decision, not an oversight: a file name is often
  the most identifying thing about a document. Do not "helpfully" add it.
- **`NBOW_SHARE_BASE`** (default `https://nbow.io`) is both the popup's origin
  and the allowlist `share.js` checks every incoming `postMessage` against. The
  two must stay the same value, or a window from anywhere could feed this app.
  Set it to `http://localhost:4321` to test against a local website checkout.
- The receipt shown under the button is the only way to have a shared document
  deleted afterwards, so it is rendered `user-select: all` and is not cleared
  until the next share.

---

## Tests

```powershell
# Whole suite, from the project root (several tests drive real Chromium)
.venv\Scripts\python -m unittest discover -s tests

# One file
.venv\Scripts\python -m unittest discover -s tests -p test_hosted_renderer.py
```

Discovery must run from the project root: the tests import `app` and `services`,
and `tests/` is deliberately not a package.

| File | Covers |
|---|---|
| `test_layout.py` | Page sizes, doc styles, Mermaid fitting, real PDF output |
| `test_hosted_renderer.py` | Untrusted Markdown through the same Chromium path; no network |
| `test_hosted_app.py` | Hosted routes, session isolation, guards, size limits |
| `test_workspaces.py` | Workspace lifecycle, cleanup, path refusals, save validation |
| `test_llm.py` | Find/replace conversion, appending, `<document>` tag refusal, empty-document write prompt, line edits, revision conflicts, caps, busy slot, network allowance, timeouts, correction path |
| `test_chat_ui.py` | Browser chat flow against a fake Ollama |
| `test_share_ui.py` | Share button flows on desktop and phone profiles against a fake nbow.io popup; never reaches a live corpus |
| `test_deploy.py` | Nginx edit targets only the website HTTPS block and is repeatable |

`scripts/live_chat_smoke.py` is the only test that runs the real model: it is
explicit, costs nothing, and writes to temporary copies. `deploy/smoke.py` checks
an installed hosted service (loopback by default, `--url` for the public route)
without credentials, creating only synthetic workspaces.

---

## Deployment

The normal path: the website's local Actions console runs **deploy-md2pdf** with
a commit SHA, which calls the root-owned `/usr/local/sbin/deploy-md2pdf` wrapper
(`deploy/run-release.sh`), which checks out that SHA under `/opt/md2pdf` and runs
`deploy/install.sh`. The installer provisions the venv, Chromium, the `md2pdf`
system user, the session secret (created once — never rotated by a deployment),
systemd units and Nginx snippets, verifies a real conversion, and restores the
previous Nginx configuration if validation fails. Details and the manual
alternative are in [docs/hosting.md](docs/hosting.md).

Keep port 2380 on loopback and run **one** Gunicorn worker: the revision lock and
the two compilation slots are per process, shared only between its threads.

---

## How it works

1. Mermaid ` ```mermaid ``` ` blocks are extracted **before** markdown parsing (prevents
   double-escaping of `<br/>` in node labels) and replaced with `<div class="mermaid">`.
2. Remaining markdown is converted to HTML via the `markdown` library
   (extensions: tables, fenced_code, codehilite, toc, attr_list, footnotes, nl2br).
3. The HTML is wrapped in a full document with a Mermaid script and a custom CSS
   stylesheet (page size, font style, doc style, styled tables, blockquotes, etc.).
4. Playwright opens a headless Chromium instance, loads the HTML, waits for
   `data-processed="true"` on all `.mermaid` divs, then fits diagrams and prints to PDF.

Desktop and hosted conversion diverge only inside steps 3 and 4:

| | Desktop | `--hosted` |
|---|---|---|
| HTML | as authored | sanitized with `bleach` |
| Mermaid | CDN (`mermaid@10`) | `static/vendor/mermaid.min.js` (12.0.0), injected under a CSP nonce |
| `securityLevel` | `loose` | `strict`, with size/edge caps and a 20 s render timeout |
| Network | allowed | every request routed to `abort()`; service workers blocked |

The nonce is generated *after* sanitization on purpose: no text coming from a
document can ever authorize a script. When updating the Mermaid bundle, pin an
explicit version and update the checksum in `static/vendor/README.md`.

---

## Mermaid diagram — hard-won fixes

### Problem 1 — blank diagram box in VS Code preview

**Cause:** Three issues in the diagram source simultaneously:
- `→` (U+2192) inside edge label strings — Mermaid's lexer treats it as arrow syntax
  even inside quotes, breaking the parse.
- `·`, `–`, `—` Unicode chars in node labels — caused parse failures in some renderers.
- `NAMUR → THON → NAMUR` cycle — dagre layout engine hangs on cycles in `TD` mode.

**Fix:** Replace `→` with `-` or `/` in labels; replace `·`/`–`/`—` with ASCII equivalents;
break the cycle by using a separate node for the return leg.

### Problem 2 — node labels render blank in VS Code preview (`<br/>` stripped)

**Cause:** VS Code's Mermaid renderer uses `securityLevel: 'strict'`, which sanitizes HTML
in labels. `<br/>` is treated as literal text, causing the entire diagram to fail silently.
`\n` inside quoted strings also renders as literal backslash-n in VS Code's bundled Mermaid
version (does not process escape sequences in node label text).

**Fix:** Use only single-line labels. Separate fields with ` / ` (e.g.
`"Munich MUC / 3 Aug 08:32"`). This works in VS Code preview, Playwright PDF, and
every other Mermaid renderer.

### Problem 3 — diagram rendering blank in PDF (Playwright) — `setAttribute` vs CSS

**Cause:** `svg.setAttribute('height', X)` sets an SVG *presentation attribute*
(specificity 0). Our CSS rule `.mermaid svg { height: auto; }` (specificity 0,1,1)
overrides it. The SVG kept its full viewBox height regardless.

**Fix:** Use `svg.style.height = X + 'px'` (inline style, highest specificity) instead
of `setAttribute`. Also clear Mermaid's inline `style.maxWidth` and remove the
`width` and `height` attributes.

### Problem 4 — diagram fits one page but leaves the preceding page blank

**Cause:** The h2 heading + diagram height > one page. Chromium's print engine
honoured `page-break-inside: avoid` by pushing the diagram to the next page,
leaving page N with only the heading.

**Fix:** Subtract the heading + top-margin height (~65 px) from the available page
height. `_fit_diagrams()` derives both bounds from the selected page size and
document style and scales on the tighter one, so the aspect ratio survives:

```python
# services/md2pdf.py — _fit_diagrams()
width, height = _page_dimensions(page_size, doc_style)   # landscape for beamer
horizontal_margin = 40 if doc_style == "beamer" else 44
vertical_margin   = 30 if doc_style == "beamer" else 40
maxWidth  = (width  - horizontal_margin) / 25.4 * 96 - 16
maxHeight = (height - vertical_margin)   / 25.4 * 96 - 65   # ~906 px on A4
```

---

## Path layout notes

- `app.py` resolves paths relative to itself (project root):
  - `SCRIPT  = BASE / "services" / "md2pdf.py"`
  - `DEF_IN  = BASE / "data" / "input"`
  - `DEF_OUT = BASE / "data" / "output"`
- `md2pdf.py` CLI defaults resolve relative to itself (`services/`):
  - `input_dir  = script_dir.parent / "data" / "input"`
  - `output_dir = script_dir.parent / "data" / "output"`
- Hosted mode ignores all of the above for documents: `input_directory()` and
  `output_directory()` return the request's workspace, and a directory supplied
  by a client is an error, not a preference.
