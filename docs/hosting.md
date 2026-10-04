# md2pdf on instrumentainternationalia.com

The site mounts the live app at `https://instrumentainternationalia.com/md2pdf/`.
The site itself is static (Astro, served by nginx), but PDF compilation and the
editing assistant need a running Python service, so nginx proxies `/md2pdf/` to a
loopback-only Gunicorn and tells the app its prefix with `X-Forwarded-Prefix`.
The editor, API, scripts and PDFs all live under that prefix.

## Install the service on the VPS

These commands assume a Debian/Ubuntu server, a checkout at `/opt/md2pdf`, Python
3.10 or newer and the site's nginx server block already in place (a `server`
block with `server_name instrumentainternationalia.com www.instrumentainternationalia.com;`
and `listen 443 ssl;`). Run them as root.

```sh
git clone https://github.com/nicofreeride/tool-md2pdf.git /opt/md2pdf
cd /opt/md2pdf
bash deploy/install.sh
```

`deploy/install.sh` does the whole thing and is safe to run again for updates:
installs `python3-venv` and the DejaVu fonts, creates the virtualenv from
`requirements-hosted.txt`, installs Playwright's Chromium with its system
libraries under `/opt/md2pdf/browsers`, creates the unprivileged `md2pdf` user
and `/var/lib/md2pdf/workspaces` (mode 700), writes `/etc/md2pdf.env` once with
a random `MD2PDF_SECRET_KEY` (and refuses an existing file with a weak key or
other paths), loads the AppArmor profile Chromium's sandbox needs on Ubuntu
24.04+ (`apparmor_restrict_unprivileged_userns`), installs and starts the
systemd units, runs `deploy/smoke.py` (a real Markdown/Mermaid conversion plus
an isolation check against the service), and finally `deploy/configure_nginx.py`
adds the `/md2pdf/` locations to the site's HTTPS block, validates with `nginx -t`
and reloads. If validation fails the original configuration is restored; a copy
of the site file before the first change is kept under `/var/backups/md2pdf/`.

Updating later is the same: `git -C /opt/md2pdf pull` (or check out a commit),
then `bash deploy/install.sh`. `deploy/run-release.sh` is a root-owned wrapper
for exactly that (one 40-character commit SHA, no local modifications allowed)
for a deploy account allowed to run only it through sudo; it is optional.

Manual equivalent, if the installer cannot be used:

```sh
cd /opt/md2pdf
python3 -m venv .venv
.venv/bin/pip install -r requirements-hosted.txt
PLAYWRIGHT_BROWSERS_PATH=/opt/md2pdf/browsers .venv/bin/python -m playwright install --with-deps chromium
useradd --system --home-dir /var/lib/md2pdf --shell /usr/sbin/nologin md2pdf
install -d -o md2pdf -g md2pdf -m 700 /var/lib/md2pdf/workspaces
install -m 600 deploy/md2pdf.env.example /etc/md2pdf.env   # then set MD2PDF_SECRET_KEY
install -m 644 deploy/md2pdf.service deploy/md2pdf-cleanup.service deploy/md2pdf-cleanup.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now md2pdf md2pdf-cleanup.timer
python3 deploy/configure_nginx.py && systemctl reload nginx
```

`MD2PDF_SECRET_KEY` is the output of `.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))'`
and must stay stable across restarts. No provider API key belongs in `/etc/md2pdf.env`:
the assistant uses the server's own Ollama (`deploy/md2pdf.env.example` documents
`MD2PDF_OLLAMA_URL` and `MD2PDF_LLM_MODEL`; pull `qwen3:1.7b` before enabling it).
Without Ollama the editor and the PDF conversion work as usual and the assistant
reports itself unavailable.

Run the service as its dedicated unprivileged user. Chromium's hosted renderer
requires its sandbox; Linux user namespaces must be available to that user.
Do not turn off the browser sandbox to work around a host restriction.

Keep port 2380 bound to loopback. Flask trusts the scheme and path prefix set by
exactly one nginx proxy (`deploy/nginx-md2pdf-proxy.conf`), which replaces
incoming forwarding headers; it must be the only caller able to reach the
backend. This follows
[Flask's reverse-proxy guidance](https://flask.palletsprojects.com/en/stable/deploying/proxy_fix/).
Use one Gunicorn worker: file revision locks and the two simultaneous compilation
slots are shared by its threads. Additional workers require shared locking.

## Visitor workflow and storage

Visitors start with an empty `document.md`, can create or open Markdown files,
edit and save them, compile with the usual layout options, and download Markdown
or PDF. The optional editing assistant runs on the server's own model
(`qwen3:1.7b` under Ollama, on loopback); no document text leaves the server and
chat history is never saved by the service.

An essential, signed `md2pdf_session` cookie selects an isolated workspace.
Client-supplied server directories are rejected everywhere, including assistant
edits. Files expire after 24 hours of workspace inactivity. Expired workspaces
are removed during requests and by the hourly timer (so physical removal can
take up to one further hour). Download documents to keep them. The service does
not import the repository's `data/input` files into visitor workspaces.

Each workspace holds at most 20 documents, 1 MB each and 10 MB in total. Because
a visitor can start a fresh workspace by discarding the cookie, stored Markdown
is also limited per network: saves, imports and assistant edits from one IPv4
/24 or IPv6 /48 may add at most 100 MB (`MD2PDF_HOURLY_BYTES`) in any rolling
hour, across all of its workspaces. Only growth counts, so rewriting a document
at the same size (every autosave) is always allowed. Over the limit, the save is
refused with HTTP 429, a `Retry-After` header and a message saying when to retry;
the file on disk is left unchanged. The counters exist only in the service's
memory, keyed by an HMAC under a random per-process key, and are dropped after
an hour or on restart. No address is written to disk.

The editor's assets and the hosted Mermaid renderer are bundled. Hosted Markdown
is sanitized before rendering, and the renderer cannot fetch document URLs or
local files. Remote images and embedded active HTML are therefore omitted in
the hosted version. Ordinary desktop conversion remains unchanged.

Conversion processes text on the server and nothing else: there is no corpus,
no sharing and no analytics. The footer links to the site's legal notice and
privacy page (`MD2PDF_SITE_BASE`, default `https://instrumentainternationalia.com`).

## Local verification

```powershell
$env:MD2PDF_HOSTED = '1'
$env:MD2PDF_SECRET_KEY = 'local-testing-only-change-in-production'
$env:MD2PDF_COOKIE_SECURE = '0' # only for HTTP localhost testing
$env:MD2PDF_WORKSPACE_ROOT = "$env:TEMP/md2pdf-hosted-test"
.venv/Scripts/python app.py
```

Two separate browser profiles must see different files; saving, compilation,
PDF downloads and chat must stay under the app's route. Unset the `MD2PDF_*`
variables to run the original local editor again.
