"""Validated line edits and optimistic, atomic Markdown saves."""
import hashlib
import os
import tempfile
from pathlib import Path
from threading import RLock

from services.workspaces import hosted_mode, input_directory, record_growth, valid_filename, validate_save

DOCUMENT_LOCK = RLock()
DEFAULT_INPUT = Path(__file__).resolve().parent.parent / "data" / "input"
MAX_DOCUMENT = 200_000


class DocumentConflict(Exception):
    pass


def document_path(document):
    if not isinstance(document, dict):
        raise ValueError("Open a Markdown file before chatting.")
    name = document.get("filename")
    directory = document.get("input_dir")
    if (not isinstance(name, str) or not name.endswith(".md")
            or (directory is not None and not isinstance(directory, str))):
        raise ValueError("Select a valid Markdown file and input directory.")
    if hosted_mode() and not valid_filename(name, ".md"):
        raise ValueError("Select a Markdown filename in your browser workspace.")
    base = input_directory(directory, DEFAULT_INPUT).resolve()
    path = (base / name).resolve()
    if base not in path.parents or not path.is_file():
        raise ValueError("Markdown file not found in the input directory.")
    return path


def document_snapshot(document):
    path = document_path(document)
    content = document.get("content")
    if not isinstance(content, str) or len(content) > MAX_DOCUMENT:
        raise ValueError("Load a Markdown document of at most 200,000 characters.")
    with DOCUMENT_LOCK:
        revision = hashlib.sha256(path.read_bytes()).hexdigest()
    if document.get("disk_revision") != revision:
        raise DocumentConflict("The file changed on disk. Reload it before continuing the chat.")
    return path, content, revision


def apply_line_edits(content, edits):
    """Ranges are 1-based and inclusive, all against the original snapshot.

    Insert before start_line using end_line=start_line-1; [] deletes a range.
    Splitting on LF preserves blank lines and a final newline as an empty line.
    """
    if not isinstance(edits, list) or len(edits) > 100:
        raise ValueError("Expected at most 100 line edits.")
    lines = content.split("\n")
    ordered = []
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {"start_line", "end_line", "replacement"}:
            raise ValueError("Invalid line edit fields.")
        start, end, replacement = edit["start_line"], edit["end_line"], edit["replacement"]
        if (type(start) is not int or type(end) is not int
                or not 1 <= start <= len(lines) + 1 or not start - 1 <= end <= len(lines)):
            raise ValueError("Line edit is outside the document.")
        if (not isinstance(replacement, list) or any(not isinstance(line, str)
                or "\n" in line or "\r" in line for line in replacement)):
            raise ValueError("Replacement must be an array of individual lines.")
        ordered.append((start, end, replacement))
    ordered.sort(key=lambda edit: edit[0])
    previous_start = previous_end = 0
    for start, end, replacement in ordered:
        if start <= previous_end or start == previous_start:
            raise ValueError("Line edits must not overlap or share a starting line.")
        previous_start, previous_end = start, end
    for start, end, replacement in reversed(ordered):
        lines[start - 1:end] = replacement
    result = "\n".join(lines)
    if len(result) > MAX_DOCUMENT:
        raise ValueError("Edited document exceeds 200,000 characters.")
    return result


def atomic_write(path, content):
    """Caller holds DOCUMENT_LOCK. Replace only after the complete write succeeds."""
    growth = validate_save(path, content)
    fd, temporary = tempfile.mkstemp(prefix=".md2pdf-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        # A save that fails to store must not spend the hourly allowance.
        record_growth(growth)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_edits(document, expected_revision, edits):
    path, content, _ = document_snapshot(document)
    result = apply_line_edits(content, edits)
    if not edits:
        raise ValueError("No line edits to apply.")
    if not isinstance(expected_revision, str) or len(expected_revision) != 64:
        raise ValueError("Missing document revision. Send the chat request again.")
    with DOCUMENT_LOCK:
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_revision:
            raise DocumentConflict("The file changed on disk. Reload it before applying chat edits.")
        atomic_write(path, result)
    return result
