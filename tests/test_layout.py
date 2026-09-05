import itertools
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import app
from services.md2pdf import convert_file, md_to_html, _fit_diagrams, _page_dimensions
from playwright.sync_api import sync_playwright


class LayoutTests(unittest.TestCase):
    def test_diagrams_fit_width_and_height(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.emulate_media(media="print")
            for size, style, (svg_width, svg_height) in itertools.product(
                ("A2", "A4", "A6"), ("plain", "article", "beamer"),
                ((8000, 300), (300, 8000), (4000, 4000)),
            ):
                with self.subTest(size=size, style=style, shape=(svg_width, svg_height)):
                    width, height = _page_dimensions(size, style)
                    page.set_viewport_size({"width": int(width / 25.4 * 96), "height": int(height / 25.4 * 96)})
                    svg = f'<div class="mermaid"><svg viewBox="0 0 {svg_width} {svg_height}"></svg></div>'
                    page.set_content(md_to_html(svg, use_cdn=False, page_size=size, doc_style=style))
                    _fit_diagrams(page, size, style)
                    bounds = page.locator(".mermaid svg").bounding_box()
                    self.assertLessEqual(bounds["width"], (width - (40 if style == "beamer" else 44)) / 25.4 * 96)
                    self.assertLessEqual(bounds["height"], (height - (30 if style == "beamer" else 40)) / 25.4 * 96 - 64)
                    # Chromium rounds layout dimensions to fractions of a CSS pixel.
                    self.assertAlmostEqual(bounds["height"], bounds["width"] * svg_height / svg_width, delta=0.5)
            browser.close()

    def test_api_preserves_every_option_combination(self):
        with app.test_client() as client, patch("app.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "", "")
            for style, size, font, points in itertools.product(
                ("plain", "article", "beamer"), ("A2", "A4", "A6"),
                ("default", "serif", "typewriter"), ("8", "10", "12"),
            ):
                with self.subTest(style=style, size=size, font=font, points=points):
                    response = client.post("/api/compile", json={
                        "doc_style": style, "page_size": size,
                        "font_style": font, "font_size": points,
                    })
                    self.assertTrue(response.json["ok"])
                    from services.md2pdf import _build_parser
                    args = _build_parser().parse_args(run.call_args.args[0][2:])
                    self.assertEqual((args.doc_style, args.page_size, args.font_style, args.font_size),
                                     (style, size, font, points))

    def test_rendered_columns_and_fonts(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.emulate_media(media="print")
            for style, size, font, points in itertools.product(
                ("plain", "article", "beamer"), ("A2", "A4", "A6"),
                ("default", "serif", "typewriter"), ("8", "10", "12"),
            ):
                with self.subTest(style=style, size=size, font=font, points=points):
                    page.set_content(md_to_html("# Title\n\n" + "Paragraph of text.\n\n" * 10,
                        use_cdn=False, doc_style=style, page_size=size,
                        font_style=font, font_size=points))
                    css = page.evaluate("""() => {
                        const s = getComputedStyle(document.body);
                        return {columns: s.columnCount, size: parseFloat(s.fontSize)};
                    }""")
                    self.assertEqual(css["columns"], "2" if style == "article" else "auto")
                    self.assertAlmostEqual(css["size"], int(points) * 96 / 72, places=3)
                    if style == "article":
                        positions = page.locator("p").evaluate_all("els => els.map(e => e.getBoundingClientRect().x)")
                        self.assertGreater(len(set(positions)), 1)
            browser.close()

    def test_pdf_paper_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.md"
            source.write_text("# Title\n\nIntroduction.\n\n## Section\n\nSome content.", encoding="utf-8")
            for style, (size, dimensions) in itertools.product(
                ("plain", "article", "beamer"),
                (("A2", (420, 594)), ("A4", (210, 297)), ("A6", (105, 148))),
            ):
                with self.subTest(style=style, size=size):
                    output = Path(directory) / "sample.pdf"
                    convert_file(source, output, use_cdn=False, doc_style=style, page_size=size)
                    boxes = re.findall(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", output.read_bytes())
                    self.assertTrue(boxes)
                    expected = dimensions[::-1] if style == "beamer" else dimensions
                    for box in boxes:
                        for actual, mm in zip(box, expected):
                            self.assertAlmostEqual(float(actual) * 25.4 / 72, mm, delta=0.5)


if __name__ == "__main__":
    unittest.main()
