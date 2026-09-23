# claude.md — Project notes for tool-md2pdf

## Project overview

A self-contained Markdown-to-PDF tool with a browser-based editor frontend.
Write and preview Markdown documents; compile them to PDF via a headless
Chromium browser so Mermaid diagrams render natively.

---

## File structure

```
tool-md2pdf/
├── .gitignore                  # ignores .venv/ and data/output/
├── .venv/                      # Python virtual environment (gitignored)
├── app.py                      # Flask editor frontend (http://localhost:2380)
├── requirements.txt            # playwright, markdown, Pygments, flask
├── data/
│   ├── input/                  # drop .md files here
│   └── output/                 # generated PDFs (gitignored)
├── docs/
│   ├── chat.md                 # the editing assistant
│   └── share.md                # the optional nbow.io corpus donation
├── static/
│   ├── chat.js                 # chat UI
│   ├── i18n.js                 # interface translations (en/de/es)
│   └── share.js                # the nbow.io sharing popup handshake
└── services/
    └── md2pdf.py               # CLI conversion tool (Playwright + markdown)
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

### Hosted website

The editor also runs under `/{lang}/products/aiconsulting/code-agents/md2pdf/`
on nbow.io. The sibling website repository proxies that path to the loopback
Python service. Setup and systemd files are documented in [docs/hosting.md](docs/hosting.md).
`MD2PDF_HOSTED=1` requires a stable `MD2PDF_SECRET_KEY` and enables isolated,
temporary browser workspaces. Every document path, including chat edits, must
go through `services/workspaces.py`; never trust server directories from clients.
The hosted renderer sanitizes HTML, uses bundled Mermaid, and blocks networking.
Desktop use remains the default. Frontend URLs must use `window.md2pdfUrl()` so
localized paths work. Browser assets are vendored in `static/vendor/`.

### Editor UI

```powershell
.venv\Scripts\python app.py
# Open http://localhost:2380
# Ctrl+S = save   Ctrl+Enter = compile
```

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

# Font styles
.venv\Scripts\python services\md2pdf.py --font-style serif
.venv\Scripts\python services\md2pdf.py --font-style typewriter
```

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
  only governs the separate corpus donation. Its client ID is `md2pdf-web`.
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

## How it works

1. Mermaid ` ```mermaid ``` ` blocks are extracted **before** markdown parsing (prevents
   double-escaping of `<br/>` in node labels) and replaced with `<div class="mermaid">`.
2. Remaining markdown is converted to HTML via the `markdown` library
   (extensions: tables, fenced_code, codehilite, toc, attr_list, footnotes, nl2br).
3. The HTML is wrapped in a full document with Mermaid.js loaded from CDN
   and a custom CSS stylesheet (A4 page, Segoe UI, styled tables, blockquotes, etc.).
4. Playwright opens a headless Chromium instance, loads the HTML, waits for
   `data-processed="true"` on all `.mermaid` divs, then scales diagrams and prints to PDF.

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
`width="100%"` attribute.

### Problem 4 — diagram fits one page but leaves the preceding page blank

**Cause:** The h2 heading + diagram height > one page (971 px). Chromium's print
engine honoured `page-break-inside: avoid` by pushing the diagram to the next page,
leaving page N with only the heading.

**Fix:** Subtract the heading + top-margin height (~65 px) from the available page
height when computing `MAX_H`:

```javascript
// inside page.evaluate() in convert_file()
const MAX_H = (297 - 40) / 25.4 * 96 - 65;  // ~906 px
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
