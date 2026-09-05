"""Explicit live API test using a local key file and temporary document copies.

Runs billable requests. Never logs credentials, raw provider errors, or document text.
"""
import argparse
import hashlib
import json
import re
import sys
import tempfile
import time
import threading
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from app import app
from services.documents import apply_line_edits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=["gpt-5", "gpt-5-mini", "gpt-4.1-mini"])
    parser.add_argument("--key-file", type=Path, default=BASE / "apikey.txt")
    parser.add_argument("--source", type=Path, default=BASE / "data/input/munich_sofia_2026.md")
    parser.add_argument("--report", type=Path, default=BASE / "data/output/live-chat-tests.json")
    args = parser.parse_args()
    key = args.key_file.read_text(encoding="utf-8-sig").strip()
    if not key or "\n" in key:
        raise SystemExit("Key file must contain only the API key on one line.")
    original = args.source.read_bytes()
    source_text = original.decode("utf-8").replace("\r\n", "\n")
    diagnostic = threading.local()

    def validate(content, edits):
        try:
            return apply_line_edits(content, edits)
        except ValueError as exc:
            diagnostic.validation_error = str(exc)
            artifact = args.report.parent / (args.report.stem + "-" + diagnostic.model + "-rejected.json")
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text(json.dumps(edits, ensure_ascii=False, indent=2), encoding="utf-8")
            raise

    def run(model):
        started = time.monotonic()
        result = {"model": model}
        diagnostic.model = model
        diagnostic.validation_error = None
        try:
            with tempfile.TemporaryDirectory(prefix="md2pdf-live-") as directory, app.test_client() as client:
                path = Path(directory) / "trip.md"
                path.write_bytes(source_text.encode("utf-8"))
                document = {"filename": path.name, "input_dir": directory, "content": source_text,
                            "disk_revision": hashlib.sha256(path.read_bytes()).hexdigest()}
                response = client.post("/api/llm/chat", json={"api_key": key, "model": model,
                    "document": document, "messages": [{"role": "user", "content":
                    "remove salzburg from the trip and make the diagram coherent"}]})
                result.update(status=response.status_code, seconds=round(time.monotonic() - started, 2))
                data = response.get_json() or {}
                if response.status_code != 200:
                    result["error"] = data.get("error", "Request failed")
                    if diagnostic.validation_error:
                        result["validation_error"] = diagnostic.validation_error
                else:
                    result["edit_count"] = len(data["edits"])
                    saved = client.post("/api/llm/apply", json={"document": document,
                        "disk_revision": data["disk_revision"], "edits": data["edits"]})
                    result["save_status"] = saved.status_code
                    if saved.status_code == 200:
                        updated = path.read_text(encoding="utf-8")
                        result["salzburg_removed"] = not re.search(r"salzburg|salzburgo", updated, re.I)
                        result["mermaid_blocks"] = updated.count("```mermaid")
                        # Check the model's returned graph with the actual renderer later.
                        artifact = args.report.parent / (args.report.stem + "-" + model + ".md")
                        artifact.parent.mkdir(parents=True, exist_ok=True)
                        artifact.write_text(updated, encoding="utf-8")
        except Exception as exc:
            result.update(error_type=type(exc).__name__, seconds=round(time.monotonic() - started, 2))
        print(json.dumps(result), flush=True)
        return result

    with patch("services.llm.apply_line_edits", side_effect=validate), ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(run, args.models))
    if args.source.read_bytes() != original:
        raise SystemExit("Source file changed during testing; test only wrote to temporary/output files.")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
