# Markdown chat

The editing assistant runs on a language model served by Ollama. On nbow.io that
is the server's own `qwen3:1.7b` (Apache 2.0), reached on the loopback interface:
there is no API key, no model choice, and no third-party provider. Locally, set
`MD2PDF_OLLAMA_URL` (default `http://127.0.0.1:11434`) and `MD2PDF_LLM_MODEL`
(default `qwen3:1.7b`) and pull the model with `ollama pull qwen3:1.7b`. Check a
model's licence before configuring it: `qwen2.5:3b` is research-only (see
[live-chat-results.md](live-chat-results.md)).

Install dependencies with `.venv\Scripts\python -m pip install -r requirements.txt`.
For local use, keep `ollama serve` running in another terminal unless the Ollama
app or service is already running, then start `.venv\Scripts\python app.py`.
If a Python syntax error stopped the app, start it again after fixing the source;
the stopped reloader cannot restart itself.
The **Assistant** section of the settings panel shows whether
the model answers and the longest document it reads. Open a Markdown file and
click the bottom-right chat bubble.

Chat history stays in the current page session, without local storage or server
persistence. Each chat request includes the current Markdown, including unsaved
edits. Ollama is called without streaming and keeps only its model and prompt
cache in memory; nothing is logged.

## Budgets, and why they are small

Measured on the production VPS (2 vCPUs, no GPU), see
[live-chat-results.md](live-chat-results.md): a 3B model reads about 13–14 prompt
tokens per second and writes about 5, and a cold start costs up to 17 s; the
1.7B default answered the three test requests in 9–43 s. So:

- one generation at a time; a second request gets HTTP 429 and is asked to
  retry in a minute (`Retry-After: 60`);
- 180 s per generation, the browser waiting 15 s longer and showing elapsed time;
- documents up to `MD2PDF_LLM_MAX_DOCUMENT_CHARS` characters (default 4,000) and
  conversations up to 4,000 characters; longer ones are refused before the model
  runs;
- on the hosted editor, `MD2PDF_LLM_HOURLY_SECONDS` seconds of generation per
  network per rolling hour (default 600), charged after each generation with the
  time it actually took, and kept like the save allowance: keyed hashes of the
  /24 or /48, in memory only, pruned on every request and forgotten on restart;
- a message longer than 4,000 characters is refused, and an answer cut off at
  the output limit is reported as too large rather than retried.

Later turns are faster than the first: Ollama reuses its prompt cache while the
document is unchanged.

## How edits work

The model answers in JSON (Ollama structured output) with a short `reply` and a
list of `edits`, each a passage to `find`, copied from the document, and its
`replace`ment. The app, not the model, then:

1. locates each passage exactly, character for character, and requires exactly
   one occurrence (overlapping occurrences count); a passage with different
   spacing is sent back to the model rather than guessed, because a tolerant
   match once edited inside words and changed indentation;
2. rejects edits that overlap, are missing, or are ambiguous, and gives the model
   one correction round within the same time budget;
3. applies the edits to a copy and turns the difference into 1-based line edits,
   checked by replaying them with `apply_line_edits`.

Quoting text is more reliable for a small model than counting line numbers, and a
wrong quote is caught instead of deleting the wrong lines. In a document with
content, an empty `find` adds its text at the end, after one blank line. A
replacement containing the prompt's `<document>` tags is refused unless the
document already contains them.

An empty document (including whitespace or a leading UTF-8 BOM alone) has
nothing to quote or ask about, so it gets its own short
prompt with no `<document>` block: the model returns the whole new document as
`markdown` (a title, sections, lists) and a one-sentence `reply`, with up to
1,024 output tokens instead of 512. Given the edit format, the model answered in
chat or wrote the `<document>` wrapper into the file (see
[live-chat-results.md](live-chat-results.md)).

When you request an edit, the app saves the validated line changes and updates the
editor. Ordinary questions return text without saving; on an empty document, a
request for text is written into it. Compile to refresh the PDF.
Editor Undo can reverse a chat edit; Save persists the undo. Switching files
clears the conversation.

A small model on two CPUs is a modest assistant: check what it did before
relying on it. Editor Undo reverses a chat edit.

## Backend contract

- `POST /api/llm/status`: returns `model`, `available` (Ollama answers and has the
  model; cached 30 s), `max_document_chars` and `max_message_chars`.
- `GET /api/file/<name>?dir=...`: returns Markdown and an `X-Document-Revision`
  SHA-256 header. Keep that revision with the loaded document.
- `POST /api/llm/chat`: accepts `messages` and `document`. `document` contains
  `filename`, optional `input_dir`, current editor `content`, and the loaded
  `disk_revision`. The backend validates the file revision, sends the document to
  the model inside `<document>` tags (an empty document is not sent; the model
  writes a new one), and returns `reply`, `edits` (line edits)
  and `disk_revision`; this endpoint does not write files. Errors: 400 invalid
  request, 409 revision conflict, 413 document too long, 429 busy or hourly
  allowance spent, 502 unusable answer, 503 model unavailable, 504 time budget.
- `POST /api/llm/apply`: accepts the original `document`, returned `edits`, and
  returned `disk_revision`. Call only after checking the editor still matches
  its original snapshot. Returns saved `content` and its new `disk_revision`.

Each line edit has `start_line`, `end_line`, and `replacement` (an array of lines).
Ranges are 1-based and inclusive, relative to the original snapshot. An empty
replacement deletes lines. `end_line = start_line - 1` inserts before a line.
At most 100 nonoverlapping edits are accepted; invalid batches are rejected in full.

The apply endpoint checks the disk revision again and saves through atomic file
replacement. App saves share a lock with chat saves. Conflicts return HTTP 409,
preserving the newer file; reload before retrying. The frontend also refuses
edits if local content changed during inference.

Neither model output nor document content can select other files or execute
commands, and the document is marked as data in the instructions.

Run tests with `.venv\Scripts\python -B -m unittest discover -s tests`. Chat tests use a fake
Ollama (`services.llm._ollama` patched) and temporary Markdown files.
`scripts/live_chat_smoke.py` runs three requests against a real Ollama (free; it
uses temporary copies) and prints timing, replies and the lines each edit changed.
