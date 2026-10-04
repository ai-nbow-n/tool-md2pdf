"""The licence files and the editor's legal links to the site that hosts it."""
import unittest
from pathlib import Path

from app import app

ROOT = Path(__file__).resolve().parent.parent


class LicenceTests(unittest.TestCase):
    def test_licence_and_notice_ship(self):
        licence = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Apache License", licence)
        self.assertIn("Version 2.0, January 2004", licence)
        notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
        # Every licence a browser receives with the vendored assets is named,
        # the EPL 2.0 of ELK with the place its source code is available.
        for name in ("CodeMirror", "Mermaid", "Eclipse Public License 2.0",
                     "https://github.com/kieler/elkjs", "DOMPurify", "lodash-es"):
            self.assertIn(name, notice)
        for path in ("static/vendor/codemirror/LICENSE", "static/vendor/mermaid.LICENSE"):
            self.assertTrue((ROOT / path).is_file(), path)

    def test_editor_links_legal_notice_privacy_and_licence(self):
        with app.test_client() as client:
            html = client.get("/").get_data(as_text=True)
        self.assertIn('href="https://instrumentainternationalia.com/impressum/"', html)
        self.assertIn('href="https://instrumentainternationalia.com/privacy/"', html)
        self.assertIn("nicofreeride/tool-md2pdf/blob/master/NOTICE", html)
        self.assertIn('src="/static/icon.svg"', html)


if __name__ == "__main__":
    unittest.main()
