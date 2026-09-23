"""Add the md2pdf locations to the existing website; validate before reload."""
import re
import subprocess
from pathlib import Path


INCLUDE = '  include /etc/nginx/snippets/md2pdf.conf;'


def configured_site(text):
    if INCLUDE.strip() in text:
        return text
    # The first nbow.io block is the HTTPS site on this VPS. Refuse a different
    # layout so an infrastructure change cannot silently target another site.
    blocks = re.split(r'(?m)^server\s*\{', text)
    matches = [i for i, block in enumerate(blocks) if
               re.search(r'(?m)^\s*server_name\s+nbow\.io\s+www\.nbow\.io;', block)
               and re.search(r'(?m)^\s*listen\s+443\s+ssl\s*;', block)]
    if len(matches) != 1:
        raise ValueError('Expected exactly one nbow.io HTTPS server block; review Nginx configuration.')
    index = matches[0]
    blocks[index] = re.sub(r'(?m)^(\s*server_name\s+nbow\.io\s+www\.nbow\.io;)',
                           lambda match: match[0] + '\n' + INCLUDE, blocks[index], count=1)
    return 'server {'.join(blocks)


def main():
    site = Path('/etc/nginx/sites-enabled/nbow.io').resolve(strict=True)
    source = Path(__file__).resolve().parent
    snippets = Path('/etc/nginx/snippets')
    snippets.mkdir(exist_ok=True)
    updates = {
        snippets / 'md2pdf.conf': (source / 'nginx-md2pdf.conf').read_bytes(),
        snippets / 'md2pdf-proxy.conf': (source / 'nginx-md2pdf-proxy.conf').read_bytes(),
        site: configured_site(site.read_text()).encode(),
    }
    originals = {path: path.read_bytes() if path.exists() else None for path in updates}
    # Never leave a backup in sites-enabled: Nginx includes every file there.
    backup = Path('/var/backups/md2pdf/nginx-nbow.io.before-md2pdf')
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        backup.write_bytes(originals[site])
    try:
        for path, data in updates.items():
            path.write_bytes(data)
        subprocess.run(['nginx', '-t'], check=True)
    except Exception:
        for path, original in originals.items():
            if original is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(original)
        raise
    print('Nginx md2pdf locations configured and syntax checked.')


if __name__ == '__main__':
    main()
