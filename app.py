#!/usr/bin/env python3
"""
app.py  --  Markdown/PDF editor frontend for the md2pdf workflow.
Run:   python app.py
Open:  http://localhost:2380

Shortcuts: Ctrl+S = save   Ctrl+Enter = compile
"""
import os
import subprocess
import hashlib
import sys
import html
from threading import BoundedSemaphore, Lock
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file
from services.llm import llm, CHAT_MODELS, CHAT_TIMEOUT_SECONDS, CONNECTION_TIMEOUT_SECONDS
from services.documents import DOCUMENT_LOCK, atomic_write
from services.workspaces import configure_hosted, hosted_mode, input_directory, output_directory, valid_filename
from werkzeug.middleware.proxy_fix import ProxyFix

BASE    = Path(__file__).parent
SCRIPT  = BASE / "services" / "md2pdf.py"
DEF_IN  = BASE / "data" / "input"
DEF_OUT = BASE / "data" / "output"

# Where the optional "Share with nbow.io" button sends the visitor.
#
# It is a whole origin and not a path because static/share.js checks every
# incoming postMessage against it: the consent window is the only page allowed
# to ask this app for a document, and the check is what makes that true. Point
# it at http://localhost:4321 to work against a local copy of the website.
#
# Nothing is sent from here. The document travels only after the visitor
# confirms it in that window, which runs on nbow.io and enforces the cookie
# consent, the acknowledgements and the hourly limit. See docs/share.md.
SHARE_BASE = os.environ.get("NBOW_SHARE_BASE", "https://nbow.io").rstrip("/")

app = Flask(__name__)
configure_hosted(app)
if app.config.get("MD2PDF_HOSTED"):
    app.config["MAX_CONTENT_LENGTH"] = 2_000_000
    # Only the loopback website proxy can reach the production listener.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=0, x_proto=1, x_host=0, x_prefix=1)
app.register_blueprint(llm)
COMPILE_SLOTS = BoundedSemaphore(2)
COMPILE_LOCK = Lock()
COMPILING = set()


@app.errorhandler(ValueError)
def invalid_request(error):
    return jsonify(error=str(error)), 400


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify(error="The request is too large. Use a smaller document or start a new chat."), 413


@app.before_request
def check_hosted_request():
    if hosted_mode() and request.method == "POST":
        if request.headers.get("Origin") not in (None, request.host_url.rstrip("/")):
            return jsonify(error="Cross-origin requests are not allowed."), 403
        if not request.is_json:
            return jsonify(error="Send a JSON request."), 415


@app.after_request
def hosted_headers(response):
    if hosted_mode():
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response


def json_body():
    body = request.get_json()
    if not isinstance(body, dict):
        raise ValueError("Expected a JSON object.")
    return body

# ── helpers ───────────────────────────────────────────────────────────────────

def _guard_md(name: str, dir_: str | Path) -> Path | None:
    """Resolve path and block traversal; only .md files allowed."""
    if not isinstance(name, str) or not name.endswith(".md") or (hosted_mode() and not valid_filename(name, ".md")):
        return None
    base   = Path(str(dir_)).resolve()
    target = (base / name).resolve()
    if base not in target.parents:
        return None
    return target


def _guard_pdf(name: str, dir_: str | Path) -> Path | None:
    """Resolve PDF path and block traversal."""
    if not isinstance(name, str) or not name.endswith(".pdf") or (hosted_mode() and not valid_filename(name, ".pdf")):
        return None
    base   = Path(str(dir_)).resolve()
    target = (base / name).resolve()
    if base not in target.parents:
        return None
    return target


# ── API ───────────────────────────────────────────────────────────────────────

@app.get("/api/files")
def api_files():
    d = input_directory(request.args.get("dir"), DEF_IN)
    names = sorted(p.name for p in d.glob("*.md") if p.is_file()) if d.is_dir() else []
    return jsonify(names)


@app.get("/api/file/<name>")
def api_get(name):
    p = _guard_md(name, input_directory(request.args.get("dir"), DEF_IN))
    if not p or not p.exists():
        return "", 404
    with DOCUMENT_LOCK:
        raw = p.read_bytes()
    response = Response(raw.decode("utf-8"), mimetype="text/plain")
    response.headers["X-Document-Revision"] = hashlib.sha256(raw).hexdigest()
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/api/file/<name>")
def api_save(name):
    body = json_body()
    p = _guard_md(name, input_directory(body.get("dir"), DEF_IN))
    if not p:
        return jsonify(error="invalid"), 400
    p.parent.mkdir(parents=True, exist_ok=True)
    content = body.get("content", "")
    if not isinstance(content, str):
        return jsonify(error="Content must be text."), 400
    with DOCUMENT_LOCK:
        if body.get("create_only") and p.exists():
            return jsonify(error="That file already exists. Choose another name."), 409
        expected = body.get("disk_revision")
        if expected is not None and (not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != expected):
            return jsonify(error="The file changed on disk. Reload it before saving."), 409
        atomic_write(p, content)
    return jsonify(ok=True, disk_revision=hashlib.sha256(content.encode("utf-8")).hexdigest())


@app.post("/api/compile")
def api_compile():
    b      = json_body()
    in_d   = str(input_directory(b.get("input_dir"), DEF_IN))
    out_d  = str(output_directory(b.get("output_dir"), DEF_OUT))
    font_style = b.get("font_style", "default")
    font_size  = b.get("font_size",  "10")
    page_size  = b.get("page_size",  "A4")
    doc_style  = b.get("doc_style",  "plain")
    fname      = b.get("filename")

    if hosted_mode() and not fname:
        return jsonify(error="Choose a Markdown file to compile."), 400

    cmd = [sys.executable, str(SCRIPT), "--input-dir", in_d, "--output-dir", out_d]
    if font_style in ("serif", "typewriter"):
        cmd += ["--font-style", font_style]
    if font_size in ("8", "12"):
        cmd += ["--font-size", font_size]
    if page_size in ("A2", "A6"):
        cmd += ["--page-size", page_size]
    if doc_style in ("plain", "article", "beamer"):
        cmd += ["--doc-style", doc_style]
    if fname:
        target = _guard_md(fname, in_d)
        if not target or not target.is_file():
            return jsonify(error="Markdown file not found."), 400
        cmd.append(str(target))
    if hosted_mode():
        cmd.append("--hosted")
    job = (in_d, fname)
    with COMPILE_LOCK:
        if job in COMPILING or not COMPILE_SLOTS.acquire(blocking=False):
            return jsonify(ok=False, error="The converter is busy. Try again shortly."), 429
        COMPILING.add(job)

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if hosted_mode():
            return jsonify(ok=(r.returncode == 0), out="", err="" if r.returncode == 0 else "Could not compile this document. Check its Markdown and diagrams.")
        return jsonify(ok=(r.returncode == 0), out=r.stdout, err=r.stderr)
    except subprocess.TimeoutExpired:
        return jsonify(ok=False, out="", err="Timeout after 120 s")
    finally:
        with COMPILE_LOCK:
            COMPILING.remove(job)
            COMPILE_SLOTS.release()


@app.get("/pdf/<name>")
def serve_pdf(name):
    d = output_directory(request.args.get("dir"), DEF_OUT)
    p = _guard_pdf(name, d)
    if not p or not p.exists():
        return "PDF not found -- compile first.", 404
    resp = send_file(str(p), mimetype="application/pdf")
    resp.headers["Cache-Control"] = "no-store"
    return resp


# ── page ──────────────────────────────────────────────────────────────────────

@app.get("/")
def index():
    options = ''.join(f'<option value="{name}">{name}</option>' for name in CHAT_MODELS)
    page = (PAGE.replace('__CHAT_MODEL_OPTIONS__', options)
            .replace('__CHAT_TIMEOUT_MS__', str((CHAT_TIMEOUT_SECONDS + 15) * 1000))
            .replace('__CONNECTION_TIMEOUT_MS__', str((CONNECTION_TIMEOUT_SECONDS + 15) * 1000))
            .replace('__SHARE_BASE__', html.escape(SHARE_BASE, quote=True))
            .replace('__APP_BASE__', html.escape(request.script_root, quote=True))
            .replace('__HOSTED__', 'true' if hosted_mode() else 'false')
            .replace('__SHARE_CLIENT__', 'md2pdf-web' if hosted_mode() else 'md2pdf-desktop'))
    return Response(page, content_type="text/html; charset=utf-8")


PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="md2pdf-base" content="__APP_BASE__">
<title>md2pdf</title>
<link rel="stylesheet"
  href="__APP_BASE__/static/vendor/codemirror/codemirror.min.css">
<link rel="stylesheet"
  href="__APP_BASE__/static/vendor/codemirror/dracula.min.css">
<script src="__APP_BASE__/static/vendor/codemirror/codemirror.min.js"></script>
<script src="__APP_BASE__/static/vendor/codemirror/markdown.min.js"></script>
<style>
:root {
  --panel-w: 272px;
  --bg:      #1e1e2e;
  --surface: #181825;
  --crust:   #11111b;
  --border:  #313244;
  --accent:  #89b4fa;
  --green:   #a6e3a1;
  --red:     #f38ba8;
  --text:    #cdd6f4;
  --muted:   #6c7086;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
[hidden], body[data-hosted="true"] .local-only, body[data-hosted="false"] .hosted-only { display: none !important; }
body {
  display: flex; height: 100vh; overflow: hidden;
  background: var(--bg); color: var(--text);
  font-family: "Segoe UI", system-ui, sans-serif; font-size: 13px;
}

/* ── settings panel ─────────────────────────────────────── */
#panel {
  width: var(--panel-w);
  background: var(--surface);
  border-right: 1px solid var(--border);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width .22s ease, opacity .22s ease;
}
#panel.hidden { width: 0; opacity: 0; border-right: none; }

#panel-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 14px 10px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.logo { font-weight: 700; font-size: 15px; color: var(--accent); }
.panel-head-controls { display: flex; align-items: center; gap: 6px; }
#language-select {
  appearance: none; background: transparent; color: var(--muted);
  border: 1px solid transparent; border-radius: 5px; padding: 5px;
  font: 600 11px "Segoe UI", sans-serif; cursor: pointer;
}
#language-select:hover, #language-select:focus-visible { color: var(--text); border-color: var(--border); }
#language-select option { background: var(--surface); color: var(--text); }

#btn-close {
  background: none; border: 1px solid var(--border); color: var(--muted);
  border-radius: 6px; width: 28px; height: 28px; cursor: pointer; font-size: 14px;
  display: flex; align-items: center; justify-content: center;
  transition: color .15s, border-color .15s;
}
#btn-close:hover { color: var(--accent); border-color: var(--accent); }

/* file + actions block */
#panel-actions {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  display: flex; flex-direction: column; gap: 9px;
  flex-shrink: 0;
}
#file-select {
  width: 100%; background: var(--bg); color: var(--text);
  border: 1px solid var(--border); border-radius: 6px;
  padding: 6px 8px; font-size: 13px; cursor: pointer;
}
#file-select:focus { outline: none; border-color: var(--accent); }

#btn-row { display: flex; gap: 7px; }
.btn {
  border-radius: 6px; border: none; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: filter .15s; white-space: nowrap; padding: 6px 12px;
}
.btn:hover  { filter: brightness(1.15); }
.btn:active { filter: brightness(.88); }
.btn:disabled { opacity: .38; cursor: not-allowed; filter: none; }
#btn-save    { background: var(--bg); color: var(--text); border: 1px solid var(--border); flex-shrink: 0; }
#file-actions .btn { background: var(--bg); color: var(--text); border: 1px solid var(--border); }
#btn-open { flex: 1; }
#btn-compile { background: var(--accent); color: #1e1e2e; flex: 1; }

#status { display: flex; align-items: center; gap: 7px; min-height: 18px; }
#dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--muted); flex-shrink: 0; transition: background .3s;
}
#dot.ok   { background: var(--green); }
#dot.err  { background: var(--red); }
#dot.busy { background: var(--accent); animation: pulse 1s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.25} }
#status-msg { font-size: 11.5px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* settings options block */
#panel-settings {
  padding: 14px;
  overflow-y: auto;
  display: flex; flex-direction: column; gap: 16px;
  flex: 1;
}
#panel-settings h3 {
  font-size: 10px; text-transform: uppercase; letter-spacing: .09em;
  color: var(--muted); border-bottom: 1px solid var(--border); padding-bottom: 6px;
}
.sg { display: flex; flex-direction: column; gap: 5px; }
.sg label { font-size: 11px; color: var(--muted); }
.sg input[type=text], .sg input[type=password], .sg input[type=url], .sg select {
  background: var(--bg); border: 1px solid var(--border); border-radius: 5px;
  color: var(--text); padding: 5px 8px; font-size: 12px; width: 100%;
}
.sg input[type=text]:focus { outline: none; border-color: var(--accent); }
.sg select { cursor: pointer; }
.connection-note { font-size: 11px; color: var(--muted); line-height: 1.5; }
#api-status[data-state=ok] { color: var(--green); }
#api-status[data-state=error], #chat-status[data-state=error] { color: var(--red); }
#share-status[data-state=ok] { color: var(--green); }
#share-status[data-state=error] { color: var(--red); }
#share-receipt {
  display: block; margin-top: 6px; padding: 5px 7px;
  background: var(--bg); border: 1px solid var(--green); border-radius: 5px;
  color: var(--green); font-family: monospace; font-size: 11.5px;
  letter-spacing: .04em; user-select: all; word-break: break-all;
}
#share-receipt[hidden] { display: none; }
#api-connect { background: var(--accent); color: var(--crust); }
#chat-bubble {
  position: fixed; bottom: 20px; right: 20px; z-index: 50;
  width: 52px; height: 52px; border: none; border-radius: 50%;
  background: var(--accent); color: var(--crust); cursor: pointer;
  display: grid; place-items: center; box-shadow: 0 4px 20px #0005;
}
#chat-window {
  position: fixed; bottom: 84px; right: 20px; z-index: 50;
  width: min(400px, calc(100vw - 32px)); height: min(540px, calc(100dvh - 110px));
  background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
  box-shadow: 0 8px 36px #0006; display: flex; flex-direction: column; overflow: hidden;
}
#chat-window[hidden] { display: none; }
#chat-head { display: flex; align-items: center; gap: 10px; padding: 12px; border-bottom: 1px solid var(--border); }
#chat-title { flex: 1; }
.chat-action { background: transparent; color: var(--text); border: 1px solid var(--border); border-radius: 5px; padding: 4px 7px; cursor: pointer; }
#chat-messages { flex: 1; min-height: 0; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 10px; }
.chat-message { padding: 9px 11px; border-radius: 9px; background: var(--bg); white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.5; }
.chat-message.user { background: #28364d; margin-left: 26px; }
.chat-message.assistant { margin-right: 14px; }
.chat-message strong { display: block; color: var(--accent); font-size: 10px; margin-bottom: 4px; }
#chat-status { padding: 0 12px 8px; font-size: 11px; color: var(--muted); }
#chat-form { display: flex; align-items: flex-end; gap: 8px; padding: 10px; border-top: 1px solid var(--border); }
#chat-input { flex: 1; min-width: 0; resize: vertical; max-height: 140px; background: var(--bg); color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: 8px; font: inherit; }
#chat-send { background: var(--accent); color: var(--crust); }
.row { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.row span { font-size: 12px; color: var(--muted); line-height: 1.3; }
.toggle { position: relative; width: 36px; height: 20px; flex-shrink: 0; }
.toggle input { opacity: 0; width: 0; height: 0; position: absolute; }
.track {
  position: absolute; inset: 0; background: var(--border);
  border-radius: 20px; cursor: pointer; transition: background .2s;
}
.track::before {
  content: ""; position: absolute; width: 14px; height: 14px;
  left: 3px; top: 3px; background: #fff; border-radius: 50%; transition: transform .2s;
}
.toggle input:checked + .track { background: var(--accent); }
.toggle input:checked + .track::before { transform: translateX(16px); }

.hint { font-size: 11px; color: var(--muted); line-height: 1.7; margin-top: auto; }
.hint kbd {
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 3px; padding: 0 4px; font-size: 10px; font-family: monospace;
}
.panel-footer {
  padding: 10px 14px 14px;
  border-top: 1px solid var(--border);
  display: flex; flex-direction: column; gap: 6px;
  flex-shrink: 0;
}
.panel-footer a {
  display: flex; align-items: center; gap: 7px;
  font-size: 11px; color: var(--muted); text-decoration: none;
  transition: color .15s;
}
.panel-footer a:hover { color: var(--text); }
.panel-footer img { width: 14px; height: 14px; border-radius: 2px; opacity: .7; }
.panel-footer a:last-child img { filter: invert(1); }
.font-btns { display: flex; gap: 5px; }
.font-btn {
  flex: 1; padding: 5px 0; border-radius: 5px; cursor: pointer; border: 1px solid var(--border);
  background: var(--bg); color: var(--muted); font-size: 11px; font-weight: 600; transition: all .15s;
}
.font-btn:hover { border-color: var(--accent); color: var(--text); }
.font-btn.active { background: var(--accent); color: #1e1e2e; border-color: var(--accent); }
.font-btn.serif-btn { font-family: Georgia, serif; }
.font-btn.mono-btn  { font-family: "Courier New", monospace; letter-spacing: -.03em; }

/* panel toggle: small rect button in the editor pane bar */
#fab {
  height: 16px; padding: 0 6px; border-radius: 3px; flex-shrink: 0;
  border: 1px solid transparent; background: transparent; color: var(--muted);
  font-size: 10px; letter-spacing: .06em; cursor: pointer;
  display: flex; align-items: center; gap: 3px;
  transition: background .15s, color .15s, border-color .15s;
}
#fab:hover { border-color: var(--border); color: var(--text); }
#fab.active { border-color: var(--accent); color: var(--accent); background: var(--surface); }
#fab:not(.active) { visibility: hidden; pointer-events: none; }

/* ── editor ─────────────────────────────────────────────── */
#editor-pane {
  flex: 1; display: flex; flex-direction: column; min-width: 0;
  border-right: 1px solid var(--border);
}
.pane-bar {
  height: 26px; padding: 0 10px; display: flex; align-items: center;
  justify-content: space-between; flex-shrink: 0;
  background: var(--surface); border-bottom: 1px solid var(--border);
  font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: .07em;
}
#cm-wrap { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.CodeMirror {
  flex: 1; height: 100% !important;
  font-family: "Cascadia Code","Fira Code","Consolas",monospace;
  font-size: 13px; line-height: 1.65;
}
.CodeMirror-scroll { height: 100%; }

/* ── pdf ──────────────────────────────────────────────────── */
#pdf-pane { flex: 1; display: flex; flex-direction: column; min-width: 0; background: #525659; }
#pdf-frame { flex: 1; border: none; width: 100%; display: none; }
#pdf-ph {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 10px; color: var(--muted);
}
#pdf-ph .icon { font-size: 52px; opacity: .22; }

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
@media (max-width: 760px) {
  body { flex-wrap: wrap; overflow: auto; height: auto; min-height: 100vh; }
  #panel { width: 100%; max-height: 48vh; }
  #panel.hidden { height: 0; }
  #editor-pane, #pdf-pane { width: 100%; flex: none; height: 60vh; }
}
</style>
</head>
<body data-hosted="__HOSTED__">

<!-- SETTINGS PANEL -->
<div id="panel">

  <div id="panel-head">
    <span class="logo">md2pdf</span>
    <div class="panel-head-controls">
      <select id="language-select" aria-label="Language" title="Language">
        <option value="en" lang="en">EN</option>
        <option value="de" lang="de">DE</option>
        <option value="es" lang="es">ES</option>
      </select>
      <button id="btn-close" title="Hide panel">&laquo;</button>
    </div>
  </div>

  <div id="panel-actions">
    <div class="font-btns" id="file-actions">
      <button class="btn" id="btn-new">New</button>
      <button class="btn" id="btn-open">Open Markdown</button>
      <input id="file-upload" type="file" accept=".md,text/markdown,text/plain" hidden>
    </div>
    <select id="file-select"><option value="">-- no files --</option></select>
    <div id="btn-row">
      <button class="btn" id="btn-save"    disabled>Save</button>
      <button class="btn" id="btn-compile" disabled>&#x25B6; Compile</button>
    </div>
    <div class="font-btns">
      <button class="chat-action" id="btn-download-md" disabled>Download Markdown</button>
      <button class="chat-action" id="btn-download-pdf" disabled>Download PDF</button>
    </div>
    <p class="connection-note hosted-only">Files are processed on nbow.io in your temporary workspace and expire after 24 hours of inactivity. Download your work to keep it. Corpus sharing is optional.</p>
    <div id="status">
      <div id="dot"></div>
      <span id="status-msg">Ready</span>
    </div>
  </div>

  <div id="panel-settings">
    <h3 class="local-only">Configuration</h3>
    <div class="sg local-only">
      <label>Input directory</label>
      <input type="text" id="s-in" placeholder="default: ./data/input">
    </div>
    <div class="sg local-only">
      <label>Output directory</label>
      <input type="text" id="s-out" placeholder="default: ./data/output">
    </div>

    <h3>Options</h3>
    <div class="sg">
      <label>PDF font</label>
      <div class="font-btns">
        <button class="font-btn active"    id="fs-default"    onclick="setFontStyle('default')">Sans</button>
        <button class="font-btn serif-btn" id="fs-serif"      onclick="setFontStyle('serif')">Serif</button>
        <button class="font-btn mono-btn"  id="fs-typewriter" onclick="setFontStyle('typewriter')">Type</button>
      </div>
    </div>
    <div class="sg">
      <label>Font size</label>
      <div class="font-btns">
        <button class="font-btn" id="fz-8"  onclick="setFontSize('8')">8</button>
        <button class="font-btn active" id="fz-10" onclick="setFontSize('10')">10</button>
        <button class="font-btn" id="fz-12" onclick="setFontSize('12')">12</button>
      </div>
    </div>
    <div class="sg">
      <label>Page size</label>
      <div class="font-btns">
        <button class="font-btn" id="ps-A2" onclick="setPageSize('A2')">A2</button>
        <button class="font-btn active" id="ps-A4" onclick="setPageSize('A4')">A4</button>
        <button class="font-btn" id="ps-A6" onclick="setPageSize('A6')">A6</button>
      </div>
    </div>
    <div class="sg">
      <label>Style</label>
      <div class="font-btns">
        <button class="font-btn" id="ds-article" onclick="setDocStyle('article')">Article</button>
        <button class="font-btn active" id="ds-plain" onclick="setDocStyle('plain')">Plain</button>
        <button class="font-btn" id="ds-beamer" onclick="setDocStyle('beamer')">Beamer</button>
      </div>
    </div>
    <div class="sg">
      <div class="row">
        <span>Auto-save on change<br><small style="font-size:10.5px;opacity:.6">(2 s debounce)</small></span>
        <label class="toggle"><input type="checkbox" id="s-auto"><span class="track"></span></label>
      </div>
    </div>

    <h3>API connection</h3>
    <div class="sg">
      <label for="api-model">Model</label>
      <select id="api-model">__CHAT_MODEL_OPTIONS__</select>
      <span class="connection-note">Choose a model, then connect. You can switch anytime for the next message.</span>
    </div>
    <div class="sg">
      <label for="api-key">API key</label>
      <input type="password" id="api-key" placeholder="Paste your OpenAI API key" autocomplete="off" spellcheck="false">
    </div>
    <div class="font-btns">
      <button class="btn" id="api-connect">Connect</button>
      <button class="chat-action" id="api-disconnect">Disconnect</button>
    </div>
    <p id="api-status" class="connection-note" role="status">Not connected</p>
    <p class="connection-note">Your key is cleared on reload. Chat includes the open Markdown, including unsaved changes. Requested edits are saved to that file.</p>

    <h3>Share with nbow.io</h3>
    <p class="connection-note">Optional. Contribute this document to the public Markdown corpus for research into how technical documents are written.</p>
    <button class="btn" id="share-open" data-share-base="__SHARE_BASE__" data-client-id="__SHARE_CLIENT__" data-client-version="1">Share with nbow.io</button>
    <p id="share-status" class="connection-note" role="status"></p>
    <code id="share-receipt" class="connection-note" hidden></code>
    <p class="connection-note">A window opens on nbow.io. It shows you the exact text, asks you to confirm twice, and only then sends it. The file name is never sent. Three documents per hour.</p>

    <p class="hint">
      <kbd>Ctrl</kbd>+<kbd>S</kbd> &nbsp;Save<br>
      <kbd>Ctrl</kbd>+<kbd>Enter</kbd> &nbsp;Compile
    </p>
  </div>

  <div class="panel-footer">
    <a href="https://nbow.io/impressum" target="_blank" rel="noopener">
      <img src="https://nbow.io/favicon.ico" alt="">
      nbow.io &mdash; Impressum
    </a>
    <a href="https://github.com/ai-nbow-n/tool-md2pdf" target="_blank" rel="noopener">
      GitHub: ai-nbow-n/tool-md2pdf
    </a>
  </div>
</div>


<!-- EDITOR -->
<div id="editor-pane">
  <div class="pane-bar"><button id="fab" title="Toggle panel">&#x2699;</button><span>Editor</span></div>
  <div id="cm-wrap">
    <textarea id="editor"></textarea>
  </div>
</div>

<!-- PDF PREVIEW -->
<div id="pdf-pane">
  <div class="pane-bar"><span></span><span>PDF Preview</span></div>
  <div id="pdf-ph"><div class="icon">&#x1F4C4;</div><span>Compile to see preview</span></div>
  <iframe id="pdf-frame"></iframe>
</div>

<button id="chat-bubble" aria-label="Open chat" aria-expanded="false" aria-controls="chat-window" title="Chat">
  <svg width="25" height="25" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5Z"/></svg>
</button>
<section id="chat-window" role="dialog" aria-labelledby="chat-title" data-chat-timeout="__CHAT_TIMEOUT_MS__" data-connection-timeout="__CONNECTION_TIMEOUT_MS__" hidden>
  <div id="chat-head">
    <strong id="chat-title">Chat</strong>
    <button id="chat-new" class="chat-action">New chat</button>
    <button id="chat-close" class="chat-action" aria-label="Close chat">&#x2715;</button>
  </div>
  <div id="chat-messages" role="log" aria-live="polite" aria-label="Conversation">
    <p class="connection-note" id="chat-empty">Connect your API in settings, choose a model, and say hello.</p>
  </div>
  <p id="chat-status" role="status">Not connected</p>
  <form id="chat-form">
    <textarea id="chat-input" rows="2" maxlength="12000" placeholder="Message…" aria-label="Chat message" disabled></textarea>
    <button id="chat-send" class="btn" type="submit" disabled>Send</button>
  </form>
</section>

<script>
window.md2pdfUrl = path => document.querySelector('meta[name="md2pdf-base"]').content + path;
</script>
<script src="__APP_BASE__/static/i18n.js"></script>
<script>
const hosted = document.body.dataset.hosted === 'true';
let current = null, diskRevision = null, chatApplying = false, savePending = null, dirty = false, autoTimer = null, fontStyle = 'default', fontSize = '10', pageSize = 'A4', docStyle = 'plain';

// ── CodeMirror ────────────────────────────────────────────────────────────────
const cm = CodeMirror.fromTextArea(document.getElementById("editor"), {
  mode: "markdown", theme: "dracula",
  lineNumbers: true, lineWrapping: true,
  tabSize: 2, indentWithTabs: false, autofocus: true,
  extraKeys: { "Ctrl-S": () => save(), "Cmd-S": () => save() },
});
cm.setSize("100%", "100%");
cm.on("change", () => {
  markDirty(true);
  if (!chatApplying && document.getElementById("s-auto").checked) {
    clearTimeout(autoTimer);
    autoTimer = setTimeout(() => save(true), 2000);
  }
});

// ── panel toggle ──────────────────────────────────────────────────────────────
const panel = document.getElementById("panel");
const fab   = document.getElementById("fab");

function openPanel()  { panel.classList.remove("hidden"); fab.classList.remove("active"); savePrefs(); }
function closePanel() { panel.classList.add("hidden");    fab.classList.add("active");    savePrefs(); }

document.getElementById("btn-close").addEventListener("click", closePanel);
fab.addEventListener("click", openPanel);

// ── prefs ─────────────────────────────────────────────────────────────────────
const KEY = "md2pdf-editor";
function loadPrefs() {
  let p = {};
  try { p = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (_) { /* Preferences are optional. */ }
  if (!p || typeof p !== 'object') p = {};
  document.getElementById("s-in").value  = hosted ? "" : p.inDir || "";
  document.getElementById("s-out").value = hosted ? "" : p.outDir || "";
  document.getElementById("s-auto").checked = !!p.auto;
  setFontStyle(p.fontStyle || 'default');
  setFontSize(p.fontSize || '10');
  setPageSize(p.pageSize || 'A4');  setDocStyle(p.docStyle || 'plain');  if (p.panel === false) { panel.classList.add("hidden"); fab.classList.add("active"); }
}
function savePrefs() {
  try {
  localStorage.setItem(KEY, JSON.stringify({
    inDir:     document.getElementById("s-in").value,
    outDir:    document.getElementById("s-out").value,
    auto:      document.getElementById("s-auto").checked,
    fontStyle: fontStyle,
    fontSize:  fontSize,
    pageSize:  pageSize,
    docStyle:  docStyle,
    panel:     !panel.classList.contains("hidden"),
  }));
  } catch (_) { /* Continue when browser storage is unavailable. */ }
}
["s-in","s-out","s-auto"].forEach(id =>
  document.getElementById(id).addEventListener("change", () => {
    savePrefs(); if (id === "s-in") loadFiles();
  })
);

function setFontStyle(name) {
  fontStyle = name;
  ['default','serif','typewriter'].forEach(n =>
    document.getElementById('fs-' + n).classList.toggle('active', n === name)
  );
  savePrefs();
}
function setFontSize(size) {
  fontSize = size;
  ['8','10','12'].forEach(n =>
    document.getElementById('fz-' + n).classList.toggle('active', n === size)
  );
  savePrefs();
}
function setPageSize(size) {
  pageSize = size;
  ['A2','A4','A6'].forEach(n =>
    document.getElementById('ps-' + n).classList.toggle('active', n === size)
  );
  savePrefs();
}
function setDocStyle(name) {
  docStyle = name;
  ['article','plain','beamer'].forEach(n =>
    document.getElementById('ds-' + n).classList.toggle('active', n === name)
  );
  savePrefs();
}

const inDir  = () => hosted ? null : document.getElementById("s-in").value.trim() || null;
const outDir = () => hosted ? null : document.getElementById("s-out").value.trim() || null;
function setStatus(msg, type = "") {
  document.getElementById("status-msg").textContent = msg;
  document.getElementById("dot").className = type;
}
function markDirty(v) {
  dirty = v;
  document.title = (v && current) ? `● ${current}` : (current || "md2pdf");
}

// ── files ─────────────────────────────────────────────────────────────────────
async function loadFiles() {
  const qs = inDir() ? "?dir=" + encodeURIComponent(inDir()) : "";
  const response = await fetch(window.md2pdfUrl("/api/files") + qs);
  if (!response.ok) throw new Error('Could not load your files. Reload to start a new workspace.');
  const files = await response.json();
  const sel = document.getElementById("file-select");
  const prev = sel.value;
  sel.innerHTML = "";
  if (!files.length) { sel.innerHTML = '<option value="">-- no files --</option>'; return; }
  files.forEach(f => { const o = document.createElement("option"); o.value = o.textContent = f; sel.appendChild(o); });
  if (files.includes(prev)) sel.value = prev;
  else { sel.value = files[0]; await openFile(files[0]); }
}
async function openFile(name) {
  if (!name || chatApplying) return;
  if (dirty && current && confirm(`Save changes to ${current}?`) && !await save(true)) {
    document.getElementById('file-select').value = current;
    return;
  }
  const qs  = inDir() ? "?dir=" + encodeURIComponent(inDir()) : "";
  const res = await fetch(window.md2pdfUrl(`/api/file/${encodeURIComponent(name)}`) + qs);
  if (!res.ok) return setStatus("Failed to load " + name, "err");
  cm.setValue(await res.text()); cm.clearHistory(); cm.scrollTo(0, 0);
  current = name; diskRevision = res.headers.get('X-Document-Revision'); markDirty(false);
  document.getElementById("pdf-frame").src = 'about:blank';
  document.getElementById("pdf-frame").style.display = 'none';
  document.getElementById("pdf-ph").style.display = '';
  document.getElementById("btn-download-pdf").disabled = true;
  document.getElementById("btn-download-md").disabled = false;
  window.dispatchEvent(new Event('markdown-file-changed'));
  document.getElementById("btn-save").disabled    = false;
  document.getElementById("btn-compile").disabled = false;
  setStatus(name); refreshPdf();
}
document.getElementById("file-select").addEventListener("change", e => openFile(e.target.value));

// ── save ──────────────────────────────────────────────────────────────────────
async function save(silent = false) {
  if (!current || chatApplying) return false;
  if (savePending) return savePending;
  const filename = current;
  const body = { content: cm.getValue(), disk_revision: diskRevision };
  if (inDir()) body.dir = inDir();
  savePending = (async () => {
  const res = await fetch(window.md2pdfUrl(`/api/file/${encodeURIComponent(filename)}`),
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json();
  if (res.ok && current === filename && (inDir() || undefined) === body.dir) {
    diskRevision = data.disk_revision;
    if (cm.getValue() === body.content) markDirty(false);
    if (!silent) setStatus("Saved", "ok");
  } else if (!res.ok) setStatus(data.error || "Save failed", "err");
  return res.ok;
  })();
  try { return await savePending; }
  catch (_) { setStatus('Save failed. Check your connection and try again.', 'err'); return false; }
  finally { savePending = null; }
}
document.getElementById("btn-save").addEventListener("click", () => save());

// ── compile ───────────────────────────────────────────────────────────────────
async function compile() {
  if (!current || chatApplying) return;
  if (!await save(true)) return;
  setStatus("Compiling...", "busy");
  document.getElementById("btn-compile").disabled = true;
  const body = { filename: current, font_style: fontStyle, font_size: fontSize, page_size: pageSize, doc_style: docStyle };
  if (inDir())  body.input_dir  = inDir();
  if (outDir()) body.output_dir = outDir();
  try {
  const data = await fetch(window.md2pdfUrl("/api/compile"),
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
  ).then(r => r.json());
  if (data.ok) { setStatus("Compiled OK", "ok"); refreshPdf(); }
  else {
    const tail = (data.error || data.err || data.out || "error").split("\n").filter(Boolean).slice(-2).join(" | ");
    setStatus("Error -- " + tail, "err");
    console.error(data.out, data.err);
  }
  } catch (_) { setStatus("Could not compile. Check your connection and try again.", "err"); }
  finally { document.getElementById("btn-compile").disabled = false; }
}
document.getElementById("btn-compile").addEventListener("click", compile);

// ── pdf ───────────────────────────────────────────────────────────────────────
function refreshPdf() {
  if (!current) return;
  const pdfName = current.replace(/\.md$/, ".pdf");
  const qs = new URLSearchParams({ t: Date.now() });
  if (outDir()) qs.set("dir", outDir());
  const filename = current;
  const url = window.md2pdfUrl(`/pdf/${encodeURIComponent(pdfName)}?${qs}`);
  fetch(url, { method: "HEAD" }).then(r => {
    if (current !== filename) return;
    const fr = document.getElementById("pdf-frame"), ph = document.getElementById("pdf-ph");
    if (r.ok) { fr.src = url; fr.style.display = "block"; ph.style.display = "none"; document.getElementById('btn-download-pdf').disabled = false; }
  }).catch(() => setStatus('Could not load PDF. Try compiling again.', 'err'));
}

// ── keyboard ──────────────────────────────────────────────────────────────────
document.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); compile(); }
  if ((e.ctrlKey || e.metaKey) && e.key === "s" && !e.shiftKey) { e.preventDefault(); save(); }
});

// The chat uses the loaded editor snapshot; a short lock protects only its save.
window.markdownChat = {
  snapshot: () => current && diskRevision ? {
    filename: current, input_dir: inDir(), content: cm.getValue(), disk_revision: diskRevision,
  } : null,
  async settle() { if (savePending) await savePending; },
  lock(value) {
    chatApplying = value;
    clearTimeout(autoTimer);
    cm.setOption('readOnly', value);
    ['file-select', 's-in', 'btn-save', 'btn-compile'].forEach(id => document.getElementById(id).disabled = value || !current);
    ['btn-new', 'btn-open'].forEach(id => document.getElementById(id).disabled = value);
  },
  updated(data) {
    const scroll = cm.getScrollInfo();
    cm.replaceRange(data.content, {line: 0, ch: 0}, {line: cm.lastLine(), ch: cm.getLine(cm.lastLine()).length}, 'chat-edit');
    cm.scrollTo(scroll.left, scroll.top);
    diskRevision = data.disk_revision;
    markDirty(false);
    setStatus('Chat edits saved — compile to update PDF', 'ok');
  },
};

// ── init ──────────────────────────────────────────────────────────────────────
loadPrefs();
loadFiles().catch(error => setStatus(error.message, 'err'));
</script>
<script src="__APP_BASE__/static/files.js"></script>
<script src="__APP_BASE__/static/chat.js"></script>
<script src="__APP_BASE__/static/share.js"></script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=2380, debug=not app.config.get("MD2PDF_HOSTED"))
