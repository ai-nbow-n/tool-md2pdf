#!/usr/bin/env python3
"""
md2pdf.py — Convert Markdown files to PDF with full Mermaid diagram support.

Uses a headless Chromium browser (via Playwright) so Mermaid.js renders
natively — no extra CLI tools required beyond the Python packages below.

Setup (run once):
    pip install -r requirements.txt
    playwright install chromium

Usage:
    python md2pdf.py                         # all *.md in ./input/ -> ./output/
    python md2pdf.py report.md notes.md      # specific files
    python md2pdf.py --input-dir /my/docs --output-dir /my/pdfs
    python md2pdf.py --no-mermaid-cdn        # use bundled mermaid (offline-safe)
"""

from __future__ import annotations

import argparse
import base64
import re
import sys
import textwrap
import time
from pathlib import Path

# ─── CSS injected into every generated HTML page ─────────────────────────────

PAGE_CSS = """
@page {
    size: A4;
    margin: 2cm 2.2cm 2cm 2.2cm;
}

* { box-sizing: border-box; }

body {
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.55;
    color: #1a1a1a;
}

h1 {
    font-size: 22pt;
    font-weight: 700;
    margin: 0 0 6pt;
    color: #1a1a1a;
}
h2 {
    font-size: 13pt;
    font-weight: 700;
    color: #1a3a5c;
    border-bottom: 1.5px solid #1a3a5c;
    padding-bottom: 3pt;
    margin-top: 20pt;
    page-break-after: avoid;
}
h3 {
    font-size: 11pt;
    font-weight: 600;
    color: #2c5282;
    margin-top: 14pt;
    page-break-after: avoid;
}
h4 { font-size: 10.5pt; font-weight: 600; margin-top: 10pt; }

p { margin: 5pt 0; }

/* ── Tables ──────────────────────────────────────────────── */
table {
    border-collapse: collapse;
    width: 100%;
    margin: 10pt 0 14pt;
    font-size: 9.2pt;
    page-break-inside: avoid;
}
thead th {
    background: #1a3a5c;
    color: #ffffff;
    padding: 5pt 8pt;
    text-align: left;
    font-weight: 600;
    font-size: 8.5pt;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}
tbody td {
    padding: 4.5pt 8pt;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
}
tbody tr:nth-child(even) td { background: #f7fafc; }
tbody tr:first-child td { border-top: 1px solid #cbd5e0; }

/* ── Code ────────────────────────────────────────────────── */
code {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 8.8pt;
    background: #edf2f7;
    padding: 1pt 4pt;
    border-radius: 2pt;
    color: #2d3748;
}
pre {
    background: #f7fafc;
    border: 1px solid #e2e8f0;
    border-left: 3px solid #4a90d9;
    border-radius: 3pt;
    padding: 8pt 10pt;
    font-size: 8.5pt;
    overflow-x: auto;
    page-break-inside: avoid;
    margin: 8pt 0;
}
pre code { background: none; padding: 0; border-radius: 0; }

/* ── Blockquotes (used for confirmations, notes, tips) ───── */
blockquote {
    border-left: 4px solid #3182ce;
    background: #ebf8ff;
    margin: 8pt 0;
    padding: 6pt 12pt;
    border-radius: 0 3pt 3pt 0;
    font-size: 9.5pt;
    color: #2c5282;
    page-break-inside: avoid;
}
blockquote p { margin: 2pt 0; }

/* ── Horizontal rule ─────────────────────────────────────── */
hr {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 14pt 0;
}

/* ── Links ───────────────────────────────────────────────── */
a { color: #2b6cb0; text-decoration: none; }

/* ── Mermaid diagrams ────────────────────────────────────── */
.mermaid {
    text-align: center;
    margin: 16pt 0;
    page-break-inside: avoid;
}
.mermaid svg {
    max-width: 100%;
    height: auto;
}

/* ── Syntax highlighting (Pygments monokai-like) ─────────── */
.highlight { background: #f7fafc; }
.highlight .k  { color: #7c3aed; font-weight: bold; }
.highlight .s  { color: #047857; }
.highlight .c  { color: #9ca3af; font-style: italic; }
.highlight .n  { color: #1e40af; }
.highlight .o  { color: #dc2626; }
"""

# Font style overrides -- appended based on --font-style
PAGE_CSS_SERIF = """
body {
    font-family: Georgia, "Times New Roman", serif;
    line-height: 1.7;
    color: #1a1208;
}
h1 { color: #1a1208; }
h2 { color: #3d2b1a; border-bottom-color: #3d2b1a; }
h3 { color: #5a3e28; }
thead th { background: #3d2b1a; }
blockquote { border-left-color: #8b6340; background: #faf5ec; color: #3d2b1a; }
"""

PAGE_CSS_TYPEWRITER = """
body {
    font-family: "Courier New", Courier, monospace;
    font-size: 10pt;
    line-height: 1.85;
    color: #111;
}
h1, h2, h3, h4 { font-family: "Courier New", Courier, monospace; }
h1 { font-size: 18pt; }
h2 { font-size: 11pt; color: #111; border-bottom: 1px solid #555; border-bottom-color: #555; }
h3 { font-size: 10pt; color: #333; }
thead th { background: #333; }
blockquote { border-left-color: #555; background: #f5f5f0; color: #222; }
code, pre { font-family: "Courier New", Courier, monospace; }
"""

# Page heights in mm — used to compute Mermaid diagram scaling limit
_PAGE_HEIGHT_MM: dict[str, float] = {"A2": 594, "A4": 297, "A6": 148}

# ─── Mermaid.js CDN and init script ──────────────────────────────────────────

MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"

MERMAID_INIT = """
<script>
  mermaid.initialize({
    startOnLoad: true,
    theme: 'default',
    flowchart: { htmlLabels: true, curve: 'linear' },
    securityLevel: 'loose'
  });
</script>
"""

# ─── HTML template ───────────────────────────────────────────────────────────

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  {mermaid_script}
  {mermaid_init}
  <style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""

# ─── Markdown → HTML conversion ──────────────────────────────────────────────

def _protect_mermaid_blocks(md_text: str) -> tuple[str, dict[str, str]]:
    """Extract ```mermaid blocks before markdown parsing, return (text, map)."""
    blocks: dict[str, str] = {}
    idx = 0

    def replacer(m: re.Match) -> str:
        nonlocal idx
        key = f"MERMAID_BLOCK_{idx}_END"
        blocks[key] = f'<div class="mermaid">{m.group(1).strip()}</div>'
        idx += 1
        return key

    text = re.sub(r"```mermaid\s*\n(.*?)```", replacer, md_text, flags=re.DOTALL)
    return text, blocks


def md_to_html(md_text: str, title: str = "", use_cdn: bool = True, font_style: str = "default", font_size: str = "10", page_size: str = "A4") -> str:
    """Convert Markdown source to a complete HTML document string."""
    try:
        import markdown
    except ImportError:
        sys.exit("Missing dependency: pip install markdown")

    protected, mermaid_map = _protect_mermaid_blocks(md_text)

    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "codehilite", "toc", "attr_list", "footnotes", "nl2br"],
        extension_configs={
            "codehilite": {"css_class": "highlight", "guess_lang": False, "noclasses": True},
            "toc": {"title": ""},
        },
    )
    body = md.convert(protected)

    # Restore mermaid blocks — markdown may have wrapped the placeholder in <p>
    for key, block in mermaid_map.items():
        body = body.replace(f"<p>{key}</p>", block)
        body = body.replace(key, block)

    mermaid_script = f'<script src="{MERMAID_CDN}"></script>' if use_cdn else ""
    mermaid_init = MERMAID_INIT if (mermaid_map or use_cdn) else ""

    _extra = {"serif": PAGE_CSS_SERIF, "typewriter": PAGE_CSS_TYPEWRITER}.get(font_style, "")
    _overrides = ""
    if font_size != "10":
        _overrides += f"\nbody {{ font-size: {font_size}pt; }}"
    if page_size != "A4":
        _overrides += f"\n@page {{ size: {page_size}; margin: 2cm 2.2cm 2cm 2.2cm; }}"
    return HTML_TEMPLATE.format(
        title=title,
        mermaid_script=mermaid_script,
        mermaid_init=mermaid_init,
        css=PAGE_CSS + _extra + _overrides,
        body=body,
    )


# ─── PDF rendering via Playwright ────────────────────────────────────────────

def _wait_for_mermaid_js() -> str:
    """JS expression that resolves true once all Mermaid diagrams are rendered."""
    return """
        () => {
            const divs = document.querySelectorAll('.mermaid');
            if (divs.length === 0) return true;
            return [...divs].every(d => d.getAttribute('data-processed') === 'true');
        }
    """


def convert_file(input_path: Path, output_path: Path, use_cdn: bool = True, font_style: str = "default", font_size: str = "10", page_size: str = "A4") -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit(
            "Missing dependency: pip install playwright\n"
            "Then run:           playwright install chromium"
        )

    md_text = input_path.read_text(encoding="utf-8")
    html = md_to_html(md_text, title=input_path.stem, use_cdn=use_cdn, font_style=font_style, font_size=font_size, page_size=page_size)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()

        # Load HTML; wait for network (fetches Mermaid CDN) to go idle
        page.set_content(html, wait_until="networkidle", timeout=30_000)

        # Wait until Mermaid finishes rendering all diagrams (max 20 s)
        try:
            page.wait_for_function(_wait_for_mermaid_js(), timeout=20_000)
        except Exception:
            # Diagrams may not have rendered; continue anyway
            pass

        # Scale oversized diagrams to fit one page; inline style beats CSS height:auto
        _max_h = int((_PAGE_HEIGHT_MM.get(page_size, 297) - 40) / 25.4 * 96 - 65)
        page.evaluate(f"""
            () => {{
                const MAX_H = {_max_h};
                document.querySelectorAll('.mermaid svg').forEach(svg => {{
                    const vb = svg.viewBox?.baseVal;
                    if (!vb || vb.height <= 0 || vb.width <= 0) return;
                    const scale = vb.height > MAX_H ? MAX_H / vb.height : 1;
                    svg.style.height   = Math.floor(vb.height * scale) + 'px';
                    svg.style.width    = Math.floor(vb.width  * scale) + 'px';
                    svg.style.removeProperty('max-width');
                    svg.removeAttribute('width');
                }});
            }}
        """)

        page.pdf(
            path=str(output_path),
            format=page_size,
            print_background=True,
            margin={"top": "2cm", "right": "2.2cm", "bottom": "2cm", "left": "2.2cm"},
        )
        browser.close()


# ─── CLI ─────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="md2pdf",
        description="Convert Markdown files to PDF with Mermaid support.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Setup (run once):
              pip install -r requirements.txt
              playwright install chromium

            Examples:
              python md2pdf.py
              python md2pdf.py report.md
              python md2pdf.py --input-dir ~/docs --output-dir ~/pdfs
        """),
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help="Markdown files to convert (default: all *.md in input/)",
    )
    parser.add_argument(
        "--input-dir",
        metavar="DIR",
        help="Directory to scan for *.md files (default: <script_dir>/input)",
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        help="Directory to write PDFs to (default: <script_dir>/output)",
    )
    parser.add_argument(
        "--no-mermaid-cdn",
        action="store_true",
        help="Skip loading Mermaid.js from CDN (Mermaid diagrams won't render)",
    )
    parser.add_argument(
        "--font-style",
        choices=["default", "serif", "typewriter"],
        default="default",
        help="PDF font style: default (sans), serif (Georgia), typewriter (Courier)",
    )
    parser.add_argument(
        "--font-size",
        choices=["8", "10", "12"],
        default="10",
        help="PDF body font size in pt (default: 10)",
    )
    parser.add_argument(
        "--page-size",
        choices=["A2", "A4", "A6"],
        default="A4",
        help="PDF page size (default: A4)",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    script_dir = Path(__file__).parent
    input_dir = Path(args.input_dir) if args.input_dir else script_dir.parent / "data" / "input"
    output_dir = Path(args.output_dir) if args.output_dir else script_dir.parent / "data" / "output"
    use_cdn    = not args.no_mermaid_cdn
    font_style = args.font_style
    font_size  = args.font_size
    page_size  = args.page_size

    output_dir.mkdir(parents=True, exist_ok=True)

    if args.files:
        files = [Path(f) for f in args.files]
        for f in files:
            if not f.exists():
                sys.exit(f"File not found: {f}")
    else:
        files = sorted(input_dir.glob("*.md"))

    if not files:
        sys.exit(f"No .md files found in {input_dir}")

    print(f"Converting {len(files)} file(s)  -->  {output_dir}\n")

    errors: list[tuple[Path, Exception]] = []
    for f in files:
        out = output_dir / f.with_suffix(".pdf").name
        t0 = time.monotonic()
        try:
            convert_file(f, out, use_cdn=use_cdn, font_style=font_style, font_size=font_size, page_size=page_size)
            elapsed = time.monotonic() - t0
            print(f"  OK  {f.name}  ->  {out.name}  ({elapsed:.1f}s)")
        except Exception as exc:
            print(f"  ERR {f.name}: {exc}", file=sys.stderr)
            errors.append((f, exc))

    total = len(files)
    ok = total - len(errors)
    print(f"\n{ok}/{total} converted.", end="")
    if errors:
        print(f"  {len(errors)} failed:", file=sys.stderr)
        for f, exc in errors:
            print(f"    {f.name}: {exc}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"  PDFs saved to: {output_dir}")


if __name__ == "__main__":
    main()
