# md2pdf

A Markdown editor that turns your documents into PDFs, with live preview, Mermaid
diagrams, several page and font styles, and an optional editing assistant that runs
on a local language model.

- **Hosted**: open it at <https://instrumentainternationalia.com/md2pdf/>. Your document
  is sent to that server for conversion and kept in a temporary workspace that is
  deleted after 24 hours of inactivity; the
  [privacy notice](https://instrumentainternationalia.com/privacy/) describes exactly what is processed.
- **On your own machine**: nothing leaves your computer except what you choose to
  share. Steps below.

## Run it locally

Python 3.11 or later.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt        # Windows: .venv\Scripts\pip
.venv/bin/playwright install chromium            # Windows: .venv\Scripts\playwright
.venv/bin/python app.py                          # Windows: .venv\Scripts\python app.py
```

Then open <http://localhost:2380>. `Ctrl+S` saves, `Ctrl+Enter` compiles.

The editing assistant needs [Ollama](https://ollama.com) with a model pulled
(`ollama pull qwen3:1.7b`); without it the editor and the PDF conversion work as usual.
`MD2PDF_OLLAMA_URL` and `MD2PDF_LLM_MODEL` change where and what it asks. Check a
model's licence before using it (`ollama show <model> --license`).

Deployment on a server is described in [docs/hosting.md](docs/hosting.md).

## Licence

md2pdf is licensed under the [Apache License 2.0](LICENSE).
Copyright 2026 Nicolas Gonzalez Albornoz.

It ships CodeMirror and Mermaid, and Mermaid's build includes further open-source
packages, among them ELK under the Eclipse Public License 2.0. All of them keep their own
licences, listed with their sources in [NOTICE](NOTICE). The name "Instrumenta Internationalia" and its
mark (`static/icon.svg`) are not covered by the Apache License.
