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
import html
import re
import secrets
import sys
import textwrap
import time
from pathlib import Path

# ─── CSS injected into every generated HTML page ─────────────────────────────

PAGE_CSS = """
@page {
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

PAGE_CSS_PLAIN = ""  # plain = base CSS only, no layout overrides

PAGE_CSS_ARTICLE = """
/* Two-column layout; tables, diagrams, and section headings span both columns */
body   { columns: 2; column-gap: 1.2cm; column-fill: balance; }
h1, h2, hr, table, .mermaid, pre { column-span: all; }
"""

PAGE_CSS_BEAMER = """
/* Landscape @page is injected via _overrides based on selected page size */
body { font-size: 11pt; line-height: 1.5; }

.slide             { page-break-before: always; }
.slide:first-child { page-break-before: auto; }

/* Title slide */
.title-slide {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 13cm;
    text-align: center;
    padding: 2cm 1cm;
}
.title-slide h1 {
    font-size: 30pt;
    color: #1a3a5c;
    border-bottom: 3pt solid #1a3a5c;
    padding-bottom: 14pt;
    margin-bottom: 10pt;
}
.title-slide p, .title-slide strong { font-size: 13pt; color: #555; }

/* Slide section header */
.slide h2 {
    font-size: 20pt;
    background: #1a3a5c;
    color: #fff;
    padding: 8pt 12pt;
    border: none;
    margin: 0 0 14pt;
    page-break-after: avoid;
}

/* Table of contents slide */
.toc-list { font-size: 13pt; line-height: 2; margin: 8pt 0 0 18pt; }

.slide h3 { font-size: 13pt; color: #2a5a8c; }
"""

# Page dimensions in mm — used for viewport sizing and Mermaid scaling
_PAGE_WIDTH_MM:  dict[str, float] = {"A2": 420, "A4": 210, "A6": 105}
_PAGE_HEIGHT_MM: dict[str, float] = {"A2": 594, "A4": 297, "A6": 148}


def _page_dimensions(page_size: str, doc_style: str) -> tuple[float, float]:
    width, height = _PAGE_WIDTH_MM[page_size], _PAGE_HEIGHT_MM[page_size]
    return (height, width) if doc_style == "beamer" else (width, height)

# ─── Mermaid.js CDN and init script ──────────────────────────────────────────

MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"
MERMAID_BUNDLE = Path(__file__).resolve().parent.parent / "static" / "vendor" / "mermaid.min.js"

# Hosted source text never executes scripts or loads resources. Trusted Mermaid is
# injected through the browser automation API, outside the document's markup.
HOSTED_CSP = ("default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; "
              "img-src data:; base-uri 'none'; form-action 'none'; frame-src 'none'; "
              "object-src 'none'; connect-src 'none'")

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
  {security_policy}
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

def _protect_mermaid_blocks(md_text: str, hosted: bool = False) -> tuple[str, dict[str, str]]:
    """Extract ```mermaid blocks before markdown parsing, return (text, map)."""
    blocks: dict[str, str] = {}
    idx = 0

    def replacer(m: re.Match) -> str:
        nonlocal idx
        key = f"MERMAID_BLOCK_{secrets.token_hex(16) if hosted else idx}_END"
        source = m.group(1).strip()
        blocks[key] = f'<div class="mermaid">{html.escape(source) if hosted else source}</div>'
        idx += 1
        return key

    text = re.sub(r"```mermaid\s*\n(.*?)```", replacer, md_text, flags=re.DOTALL)
    return text, blocks


def _transform_beamer(body: str) -> str:
    """Split HTML body into slide divs at each <h2> boundary, prepend TOC slide."""
    parts    = re.split(r'(?=<h2[\s>])', body)
    intro    = parts[0]
    sections = parts[1:]

    toc_items = [
        m.group(1)
        for s in sections
        for m in [re.match(r'<h2[^>]*>(.*?)</h2>', s, re.DOTALL)]
        if m
    ]

    slides = [f'<div class="slide title-slide">{intro}</div>']

    if toc_items:
        toc_li = ''.join(f'<li>{t}</li>' for t in toc_items)
        slides.append(
            '<div class="slide toc-slide">'
            '<h2>Contents</h2>'
            f'<ol class="toc-list">{toc_li}</ol>'
            '</div>'
        )

    for section in sections:
        if section.strip():
            slides.append(f'<div class="slide">{section}</div>')

    return '\n'.join(slides)


def _sanitize_hosted_html(body: str) -> str:
    """Keep printable Markdown formatting, never executable or embedded HTML."""
    import bleach
    from bleach.css_sanitizer import CSSSanitizer

    def attributes(tag, name, value):
        if name in ("class", "id", "title", "style"):
            return True
        if tag == "a" and name == "href":
            return value.startswith(("https://", "http://", "mailto:", "#"))
        if tag == "img":
            if name in ("alt", "width", "height"):
                return True
            if name == "src":
                return bool(re.match(r"\Adata:image/(?:png|jpeg|gif|webp);base64,[A-Za-z0-9+/=]+\Z", value))
        return tag in ("td", "th") and name in ("colspan", "rowspan")

    return bleach.clean(
        body,
        tags={"p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote",
              "pre", "code", "div", "span", "strong", "em", "b", "i", "del", "s",
              "sup", "sub", "ul", "ol", "li", "dl", "dt", "dd", "a", "img",
              "table", "thead", "tbody", "tfoot", "tr", "th", "td"},
        attributes=attributes,
        protocols={"http", "https", "mailto", "data"},
        css_sanitizer=CSSSanitizer(allowed_css_properties={
            "color", "background-color", "font-weight", "font-style", "text-align",
            "text-decoration", "white-space"}),
        strip=True,
    )


def md_to_html(md_text: str, title: str = "", use_cdn: bool = True, font_style: str = "default", font_size: str = "10", page_size: str = "A4", doc_style: str = "plain", hosted: bool = False) -> str:
    """Convert Markdown source to a complete HTML document string."""
    try:
        import markdown
    except ImportError:
        sys.exit("Missing dependency: pip install markdown")

    if hosted:
        if len(md_text.encode("utf-8")) > 1024 * 1024:
            raise ValueError("Markdown must contain at most 1 MiB of UTF-8 text.")
        if (font_style not in ("default", "serif", "typewriter") or font_size not in ("8", "10", "12")
                or page_size not in _PAGE_WIDTH_MM or doc_style not in ("plain", "article", "beamer")):
            raise ValueError("Invalid PDF formatting option.")
    protected, mermaid_map = _protect_mermaid_blocks(md_text, hosted=hosted)

    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "codehilite", "toc", "attr_list", "footnotes", "nl2br"],
        extension_configs={
            "codehilite": {"css_class": "highlight", "guess_lang": False, "noclasses": True},
            "toc": {"title": ""},
        },
    )
    body = md.convert(protected)
    if hosted:
        body = _sanitize_hosted_html(body)

    # Restore mermaid blocks — markdown may have wrapped the placeholder in <p>
    for key, block in mermaid_map.items():
        body = body.replace(f"<p>{key}</p>", block)
        body = body.replace(key, block)

    if doc_style == "beamer":
        body = _transform_beamer(body)

    mermaid_script = f'<script src="{MERMAID_CDN}"></script>' if use_cdn and not hosted else ""
    mermaid_init = MERMAID_INIT if not hosted and (mermaid_map or use_cdn) else ""

    _font_extra  = {"serif": PAGE_CSS_SERIF, "typewriter": PAGE_CSS_TYPEWRITER}.get(font_style, "")
    _style_extra = {"article": PAGE_CSS_ARTICLE, "beamer": PAGE_CSS_BEAMER}.get(doc_style, "")
    _extra = _font_extra + _style_extra
    width, height = _page_dimensions(page_size, doc_style)
    # Explicit dimensions also support A2, which Chromium's named paper sizes omit.
    margins = "1.5cm 2cm" if doc_style == "beamer" else "2cm 2.2cm"
    _overrides = f"\n@page {{ size: {width}mm {height}mm; margin: {margins}; }}"
    _overrides += f"\nbody {{ font-size: {font_size}pt; }}"
    if doc_style == "beamer":
        # Keep the title slide within even the smallest selected paper size.
        _overrides += f"\n.title-slide {{ min-height: {height - 30}mm; padding: 5mm; }}"
    return HTML_TEMPLATE.format(
        title=html.escape(title) if hosted else title,
        security_policy=(f'<meta http-equiv="Content-Security-Policy" '
                         f'content="{HOSTED_CSP.format(nonce=secrets.token_urlsafe(24))}">') if hosted else "",
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


def _fit_diagrams(page, page_size: str, doc_style: str) -> None:
    """Fit each complete diagram within both printable dimensions, preserving aspect ratio."""
    width, height = _page_dimensions(page_size, doc_style)
    horizontal_margin = 40 if doc_style == "beamer" else 44
    vertical_margin = 30 if doc_style == "beamer" else 40
    page.evaluate("""({maxWidth, maxHeight}) => {
        document.querySelectorAll('.mermaid svg').forEach(svg => {
            const vb = svg.viewBox?.baseVal;
            if (!vb || vb.height <= 0 || vb.width <= 0) return;
            const containerWidth = svg.parentElement.getBoundingClientRect().width;
            const availableWidth = Math.min(maxWidth, containerWidth || maxWidth);
            const scale = Math.min(1, availableWidth / vb.width, maxHeight / vb.height);
            svg.style.height = (vb.height * scale) + 'px';
            svg.style.width = (vb.width * scale) + 'px';
            svg.style.maxWidth = '100%';
            svg.style.display = 'block';
            svg.style.margin = '0 auto';
            svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
            svg.removeAttribute('width');
            svg.removeAttribute('height');
        });
    }""", {"maxWidth": (width - horizontal_margin) / 25.4 * 96 - 16,
            "maxHeight": (height - vertical_margin) / 25.4 * 96 - 65})


def _hosted_page(browser):
    """A fresh browser context without network access or service workers."""
    context = browser.new_context(service_workers="block", accept_downloads=False)
    context.route("**/*", lambda route: route.abort())
    return context.new_page()


def _render_hosted_mermaid(page) -> None:
    if not page.locator(".mermaid").count():
        return
    # The packaged JavaScript is trusted application code, never fetched in
    # response to a document URL. Its nonce is generated after sanitization, so
    # no source text can authorize a script in the rendered document.
    policy = page.locator('meta[http-equiv="Content-Security-Policy"]').get_attribute("content")
    nonce = re.search(r"'nonce-([^']+)'", policy).group(1)
    page.evaluate("""({source, nonce}) => {
        const script = document.createElement('script');
        script.nonce = nonce;
        script.textContent = source;
        document.head.appendChild(script);
    }""", {"source": MERMAID_BUNDLE.read_text(encoding="utf-8"), "nonce": nonce})
    try:
        page.evaluate("""async () => {
            mermaid.initialize({
                startOnLoad: false, securityLevel: 'strict', theme: 'default',
                flowchart: {htmlLabels: true, curve: 'linear'},
                maxTextSize: 50000, maxEdges: 500, suppressErrorRendering: true,
                secure: ['secure', 'securityLevel', 'startOnLoad', 'maxTextSize',
                         'maxEdges', 'suppressErrorRendering', 'dompurifyConfig']
            });
            await Promise.race([
                mermaid.run({nodes: document.querySelectorAll('.mermaid')}),
                new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 20000))
            ]);
        }""")
    except Exception:
        # Mermaid's errors contain source excerpts; never expose them in logs.
        raise ValueError("A Mermaid diagram could not be rendered. Check its syntax and size.") from None


def convert_file(input_path: Path, output_path: Path, use_cdn: bool = True, font_style: str = "default", font_size: str = "10", page_size: str = "A4", doc_style: str = "plain", hosted: bool = False) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit(
            "Missing dependency: pip install playwright\n"
            "Then run:           playwright install chromium"
        )

    md_text = input_path.read_text(encoding="utf-8")
    html = md_to_html(md_text, title=input_path.stem, use_cdn=use_cdn, font_style=font_style, font_size=font_size, page_size=page_size, doc_style=doc_style, hosted=hosted)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(chromium_sandbox=hosted)
        page = _hosted_page(browser) if hosted else browser.new_page()

        # Match viewport to paper so content fills the full width (critical for A2)
        width, height = _page_dimensions(page_size, doc_style)
        _vw = int(width / 25.4 * 96)
        _vh = int(height / 25.4 * 96)
        page.set_viewport_size({"width": _vw, "height": _vh})

        # Layout in print media so @page { size } controls the content column width
        page.emulate_media(media="print")

        # Load HTML; wait for network (fetches Mermaid CDN) to go idle
        page.set_content(html, wait_until="load" if hosted else "networkidle", timeout=30_000)

        # Wait until Mermaid finishes rendering all diagrams (max 20 s)
        if hosted:
            _render_hosted_mermaid(page)
        else:
            try:
                page.wait_for_function(_wait_for_mermaid_js(), timeout=20_000)
            except Exception:
                # Diagrams may not have rendered; continue anyway
                pass

        _fit_diagrams(page, page_size, doc_style)

        page.pdf(
            path=str(output_path),
            width=f"{width}mm",
            height=f"{height}mm",
            prefer_css_page_size=True,
            print_background=True,
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
        "--hosted",
        action="store_true",
        help="Render untrusted Markdown with sanitized HTML and no resource requests",
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
    parser.add_argument(
        "--doc-style",
        choices=["plain", "article", "beamer"],
        default="plain",
        help="Document style: plain (default), article (two-column), beamer (landscape slides)",
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
    doc_style  = args.doc_style

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
            convert_file(f, out, use_cdn=use_cdn, font_style=font_style, font_size=font_size, page_size=page_size, doc_style=doc_style, hosted=args.hosted)
            elapsed = time.monotonic() - t0
            print(f"  OK  {f.name}  ->  {out.name}  ({elapsed:.1f}s)")
        except Exception as exc:
            if args.hosted:
                exc = ValueError("Conversion failed. Check document syntax and size.")
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
