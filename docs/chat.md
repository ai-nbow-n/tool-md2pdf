# Markdown chat

Install dependencies with `.venv\Scripts\python -m pip install -r requirements.txt`
and start `app.py`. In **API connection**, choose a model, enter an OpenAI API key,
and click **Connect**. The compact list contains stable editor-compatible model
aliases; connection narrows it to those listed for your account and preserves
your choice when available. The status displays the selected model.
Open a Markdown file and click the bottom-right chat bubble.

Switch models without reconnecting or clearing the conversation. You can also
switch while a response is running: the current response finishes with its
original model, and the next message uses the new selection. Each assistant
message is labeled with the model that handled it. Account-specific permissions
and quotas are checked by OpenAI when a request is sent.

The key and chat history stay in the current page session, without local storage
or server persistence. Each chat request includes the current Markdown, including
unsaved edits. The backend uses the OpenAI SDK, with response storage disabled.
Model availability, quota, and billing depend on the supplied API account.

Chat generation has a 180-second backend time budget; the browser waits 15
seconds longer and displays elapsed time. Connection checks use a shorter
30-second timeout. GPT-5 and GPT-5 mini use low reasoning effort for interactive
editing. Invalid line ranges get one correction attempt within the same time
budget; the file is written only after a complete valid batch and version checks.

When you request an edit, the app saves validated line changes and updates the
editor. Ordinary questions return text without saving. Compile to refresh the PDF.
Editor Undo can reverse a chat edit; Save persists the undo. Switching files
clears the conversation.

## Backend contract

- `POST /api/llm/models`: accepts `api_key`; returns available text-model candidates.
- `GET /api/file/<name>?dir=...`: returns Markdown and an `X-Document-Revision`
  SHA-256 header. Keep that revision with the loaded document.
- `POST /api/llm/chat`: accepts `api_key`, `model`, `messages`, and `document`.
  `document` contains `filename`, optional `input_dir`, current editor `content`,
  and the loaded `disk_revision`. The backend validates the file revision and
  supplies the current content as numbered lines. Returns `reply`, `edits`, and
  `disk_revision`; this endpoint does not write files.
- `POST /api/llm/apply`: accepts the original `document`, returned `edits`, and
  returned `disk_revision`. Call only after checking the editor still matches
  its original snapshot. Returns saved `content` and its new `disk_revision`.

Each edit has `start_line`, `end_line`, and `replacement` (an array of lines).
Ranges are 1-based and inclusive, relative to the original snapshot. An empty
replacement deletes lines. `end_line = start_line - 1` inserts before a line.
The trailing newline is represented by a final empty numbered line. At most 100
nonoverlapping edits are accepted; invalid batches are rejected in full.

The apply endpoint checks the disk revision again and saves through atomic file
replacement. App saves share a lock with chat saves. Conflicts return HTTP 409,
preserving the newer file; reload before retrying. The frontend also refuses
edits if local content changed during inference. Files changed by external
programs are checked immediately before saving; unrelated programs do not
participate in the app's lock.

The API destination is fixed to OpenAI. Neither model output nor document content
can select other files or execute commands. API error responses omit raw provider
messages so credentials cannot be echoed into the chat.

Implementation references: [OpenAI Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create)
and [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

Run tests with `.venv\Scripts\python -B -m unittest discover -s tests -v`.
Chat tests use a fake OpenAI client and temporary Markdown files; the browser
test loads the editor's existing CodeMirror CDN assets. A real key is needed
to verify account access and live model behavior.

To reproduce live tests with the ignored `apikey.txt` file, run
`.venv\Scripts\python -B scripts/live_chat_smoke.py`. This makes billable calls
against GPT-5, GPT-5 mini, and GPT-4.1 mini. It uses temporary document copies and
puts sanitized reports and edited copies under `data/output/`; it does not edit
the source itinerary or print the key. HTTP success and valid edit ranges do not
guarantee every requested semantic change was made: inspect the edited copy too.
