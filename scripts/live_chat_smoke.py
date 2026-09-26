"""Explicit live test of the editing assistant against a real Ollama.

Free: the model runs on the server (or wherever MD2PDF_OLLAMA_URL points), with
no API key. Uses a temporary copy of a sample itinerary, so nothing real is
edited. Prints timing, each reply, and the lines each set of edits removed and
added. HTTP 200 and valid edits do not mean every requested change was made:
read the removed/added lines.

To test the production model from a workstation, open a tunnel first, e.g.
    ssh -N -L 11500:127.0.0.1:11434 <server>
and run with MD2PDF_OLLAMA_URL=http://127.0.0.1:11500.
"""
import argparse
import hashlib
import sys
import tempfile
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from app import app  # noqa: E402
from services.documents import apply_line_edits  # noqa: E402

CITIES = ["Munich", "Salzburg", "Vienna", "Bratislava", "Budapest", "Prague"]
REQUESTS = [
    "Change the title to 'Rail trip through Central Europe'.",
    "Remove Salzburg from the trip: delete its whole day and update the totals to five cities and 600 EUR.",
    "How many cities does the trip visit, and which is the last one?",
]


def sample():
    lines = ["# Central Europe rail trip", ""]
    for day, city in enumerate(CITIES, 1):
        lines += [f"## Day {day}: {city}", "",
                  f"Arrive in {city} by train and walk the old town.",
                  f"Dinner at a local restaurant in {city}.", "",
                  f"| Hotel | Central hotel in {city} |", "|---|---|", "| Budget | 120 EUR |", ""]
    lines += ["## Totals", "", "Six days, six cities, about 720 EUR in total.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, help="Markdown file to use instead of the built-in sample")
    args = parser.parse_args()
    document = args.source.read_text(encoding="utf-8").replace("\r\n", "\n") if args.source else sample()
    client = app.test_client()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "trip.md"
        for text in REQUESTS:
            path.write_text(document, encoding="utf-8")
            body = {"messages": [{"role": "user", "content": text}],
                    "document": {"filename": path.name, "input_dir": tmp, "content": document,
                                 "disk_revision": hashlib.sha256(path.read_bytes()).hexdigest()}}
            started = time.monotonic()
            response = client.post("/api/llm/chat", json=body)
            data = response.get_json() or {}
            print(f"\n=== {text}\nHTTP {response.status_code} in {time.monotonic() - started:.0f}s")
            if response.status_code != 200:
                print("error:", data.get("error"))
                continue
            print("reply:", data["reply"])
            after = apply_line_edits(document, data["edits"]) if data["edits"] else document
            before_lines, after_lines = document.split("\n"), after.split("\n")
            print("removed:", [line for line in before_lines if line and line not in after_lines])
            print("added:", [line for line in after_lines if line and line not in before_lines])


if __name__ == "__main__":
    main()
