#!/usr/bin/env bash
# Invoked by the Actions console's deploy-md2pdf workflow on the website VPS.
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
  echo 'Run the installer with sudo.' >&2
  exit 1
fi
cd /opt/md2pdf
if [ "$(pwd -P)" != /opt/md2pdf ] || [ ! -f requirements-hosted.txt ]; then
  echo 'Expected the md2pdf checkout at /opt/md2pdf.' >&2
  exit 1
fi
export DEBIAN_FRONTEND=noninteractive
export PLAYWRIGHT_BROWSERS_PATH=/opt/md2pdf/browsers
umask 022

apt-get update -qq
apt-get install -y --no-install-recommends python3-venv fonts-dejavu-core
python3 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-hosted.txt
.venv/bin/python -m playwright install --with-deps chromium

if ! id md2pdf >/dev/null 2>&1; then
  useradd --system --home-dir /var/lib/md2pdf --shell /usr/sbin/nologin md2pdf
fi
install -d -o md2pdf -g md2pdf -m 700 /var/lib/md2pdf /var/lib/md2pdf/workspaces
# Never rotate the signing key during an ordinary deployment.
python3 - <<'PY'
from pathlib import Path
import os
import secrets
path = Path('/etc/md2pdf.env')
if not path.exists():
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write('MD2PDF_HOSTED=1\nMD2PDF_SECRET_KEY=' + secrets.token_hex(32) + '\n'
                     'MD2PDF_WORKSPACE_ROOT=/var/lib/md2pdf/workspaces\n'
                     'PLAYWRIGHT_BROWSERS_PATH=/opt/md2pdf/browsers\n'
                     'NBOW_SHARE_BASE=https://nbow.io\n')
values = dict(line.split('=', 1) for line in path.read_text().splitlines()
              if line and not line.startswith('#') and '=' in line)
required = {'MD2PDF_HOSTED': '1', 'MD2PDF_WORKSPACE_ROOT': '/var/lib/md2pdf/workspaces',
            'PLAYWRIGHT_BROWSERS_PATH': '/opt/md2pdf/browsers'}
if any(values.get(key) != value for key, value in required.items()):
    raise SystemExit('Existing /etc/md2pdf.env has incompatible hosting paths or mode; review it before deploying.')
if len(values.get('MD2PDF_SECRET_KEY', '')) < 32 or values['MD2PDF_SECRET_KEY'].startswith('replace-'):
    raise SystemExit('Set a strong signing secret in /etc/md2pdf.env before deploying.')
path.chmod(0o600)
PY

# Ubuntu restricts user namespaces by application. Grant only the root-owned
# Playwright Chromium binaries the namespace access their sandbox needs.
# Do not weaken the host-wide sysctl or pass --no-sandbox.
if [ "$(cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns 2>/dev/null || true)" = 1 ]; then
  install -m 644 deploy/md2pdf-chromium.apparmor /etc/apparmor.d/md2pdf-chromium
  apparmor_parser -r /etc/apparmor.d/md2pdf-chromium
fi

install -m 644 deploy/md2pdf.service deploy/md2pdf-cleanup.service deploy/md2pdf-cleanup.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable md2pdf md2pdf-cleanup.timer
systemctl restart md2pdf
systemctl start md2pdf-cleanup.timer
.venv/bin/python deploy/smoke.py

# Install the narrow website locations only after the backend really converts.
python3 deploy/configure_nginx.py
systemctl reload nginx
echo 'md2pdf deployed; backend conversion and isolated workspaces verified.'
