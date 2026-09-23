# md2pdf on nbow.io

The website mounts the live app at
`https://nbow.io/en/products/aiconsulting/code-agents/md2pdf/`
(also `de` and `es`). Unlike the Treatise's static export, PDF compilation and
the editing assistant need a running Python service. The website proxies this
path to a loopback-only service; the editor, API, scripts and PDFs all use the
same localized prefix.

## Install the service on the website VPS

These commands assume a Debian/Ubuntu server, a checkout at `/opt/md2pdf`, and
Python 3.10 or newer. Run the administrative commands with sudo as necessary.
Publish the changes in both `tool-md2pdf` and the sibling `website` repository
before deploying; installing only one side does not expose a working editor.

```sh
git clone https://github.com/ai-nbow-n/tool-md2pdf.git /opt/md2pdf
cd /opt/md2pdf
python3 -m venv .venv
.venv/bin/pip install -r requirements-hosted.txt
PLAYWRIGHT_BROWSERS_PATH=/opt/md2pdf/browsers .venv/bin/python -m playwright install --with-deps chromium
sudo useradd --system --home-dir /var/lib/md2pdf --shell /usr/sbin/nologin md2pdf
sudo install -d -o md2pdf -g md2pdf -m 700 /var/lib/md2pdf/workspaces
sudo install -m 600 deploy/md2pdf.env.example /etc/md2pdf.env
```

Replace `MD2PDF_SECRET_KEY` in `/etc/md2pdf.env` with the output of
`.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))'`.
Keep this key stable across restarts. No provider API key belongs in this file.

```sh
sudo install -m 644 deploy/md2pdf.service deploy/md2pdf-cleanup.service deploy/md2pdf-cleanup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now md2pdf md2pdf-cleanup.timer
```

Run the service as its dedicated unprivileged user. Chromium's hosted renderer
requires its sandbox; Linux user namespaces must be available to that user.
Do not turn off the browser sandbox to work around a host restriction.

In the website repository, set the GitHub Actions repository variable
`MD2PDF_UPSTREAM` to `http://127.0.0.1:2380`, then deploy the website changes.
Both website and Treatise deploy workflows preserve this setting in
`.env.production`. The website's missing-service page gives a clear temporary
unavailability message until the backend is configured and reachable.

Keep port 2380 bound to loopback. Flask trusts the scheme and path prefix set by
exactly one website proxy. That proxy replaces incoming forwarding headers;
it must be the only caller able to reach the backend. This follows
[Flask's reverse-proxy guidance](https://flask.palletsprojects.com/en/stable/deploying/proxy_fix/).
Use one Gunicorn worker: file revision locks and the two simultaneous compilation
slots are shared by its threads. Additional workers require shared locking.

## Visitor workflow and storage

Visitors start with an empty `document.md`, can create or open Markdown files,
edit and save them, compile with the usual layout options, and download Markdown
or PDF. The optional editing assistant uses the visitor's own API key and the
existing transient proxy. Keys and chat history are never saved by the service.

An essential, signed `md2pdf_session` cookie selects an isolated workspace.
Client-supplied server directories are rejected everywhere, including assistant
edits. Files expire after 24 hours of workspace inactivity. Expired workspaces
are removed during requests and by the hourly timer (so physical removal can
take up to one further hour). Download documents to keep them. The service does
not import the repository's `data/input` files into visitor workspaces.

The editor's assets and the hosted Mermaid renderer are bundled. Hosted Markdown
is sanitized before rendering, and the renderer cannot fetch document URLs or
local files. Remote images and embedded active HTML are therefore omitted in
the hosted version. Ordinary desktop conversion remains unchanged.

Conversion processes text on nbow.io. It does **not** add it to the research
corpus. **Share with nbow.io** still opens the existing consent page and requires
the visitor's explicit confirmation, using the `md2pdf-web` client identifier.

## Local verification

```powershell
$env:MD2PDF_HOSTED = '1'
$env:MD2PDF_SECRET_KEY = 'local-testing-only-change-in-production'
$env:MD2PDF_COOKIE_SECURE = '0' # only for HTTP localhost testing
$env:MD2PDF_WORKSPACE_ROOT = "$env:TEMP/md2pdf-hosted-test"
.venv/Scripts/python app.py
```

For the website dev server, set `MD2PDF_UPSTREAM=http://127.0.0.1:2380` and open
the localized app route. Two separate browser profiles must see different files;
saving, compilation, PDF downloads and chat must stay under that route. Unset
the `MD2PDF_*` variables to run the original local editor again.
