"""Temporary, isolated document directories for the public hosted editor."""
import os
import re
import secrets
import shutil
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from threading import RLock

from flask import current_app, g, has_request_context, jsonify, session


WORKSPACE_TTL = 24 * 60 * 60
CLEANUP_INTERVAL = 5 * 60
MAX_DOCUMENT_BYTES = 1024 * 1024
MAX_DOCUMENTS = 20
MAX_WORKSPACE_BYTES = 10 * 1024 * 1024
_TOKEN = re.compile(r"[0-9a-f]{64}\Z")
_RESERVED = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)
_MARKER = ".last-used"


def _enabled(value):
    return value is True or str(value).lower() in {"1", "true", "yes", "on"}


def hosted_mode():
    return has_request_context() and bool(current_app.config.get("MD2PDF_HOSTED"))


def valid_filename(name, suffix):
    """Hosted files are flat names, safe on both Windows and Linux."""
    return (isinstance(name, str) and 0 < len(name) <= 180
            and name.endswith(suffix) and name not in {".", ".."}
            and not any(c in name for c in '/\\:<>"|?*')
            and not any(ord(c) < 32 for c in name)
            and name == name.strip() and not name.endswith(".")
            and not _RESERVED.match(name))


def _linked(path):
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def _safe_workspace(path, root):
    return (bool(_TOKEN.fullmatch(path.name)) and not _linked(path)
            and path.is_dir() and path.resolve().parent == root
            and (path / _MARKER).is_file() and not _linked(path / _MARKER)
            and all((path / name).is_dir() and not _linked(path / name)
                    for name in ("input", "output")))


def _cleanup(root, now, active):
    """Only remove expired directories created by this service under its root."""
    removed = 0
    for candidate in root.iterdir():
        if candidate.name in active:
            continue
        try:
            if (_safe_workspace(candidate, root)
                    and now - (candidate / _MARKER).stat().st_mtime >= WORKSPACE_TTL):
                shutil.rmtree(candidate)
                removed += 1
        except OSError:
            # A concurrent worker may already have removed this directory.
            continue
    return removed


def _workspace_root(configuration=None):
    configuration = configuration or {}
    return Path(configuration.get("MD2PDF_WORKSPACE_ROOT")
                or os.environ.get("MD2PDF_WORKSPACE_ROOT")
                or Path(tempfile.gettempdir()) / "md2pdf-workspaces").resolve()


def cleanup_expired(root=None):
    """Scheduled cleanup does not need a running Flask app or a signing key."""
    root = Path(root).resolve() if root is not None else _workspace_root()
    return _cleanup(root, time.time(), {}) if root.is_dir() else 0


def configure_hosted(app):
    """Configure signed browser sessions; local use keeps its existing paths."""
    app.config["MD2PDF_HOSTED"] = _enabled(
        app.config.get("MD2PDF_HOSTED", os.environ.get("MD2PDF_HOSTED", "0")))
    if not app.config["MD2PDF_HOSTED"]:
        return
    if "md2pdf_workspaces" in app.extensions:
        return
    secret = app.config.get("MD2PDF_SECRET_KEY") or os.environ.get("MD2PDF_SECRET_KEY")
    if not secret:
        raise RuntimeError("Set MD2PDF_SECRET_KEY before starting the hosted editor.")
    root = _workspace_root(app.config)
    maximum = int(app.config.get("MD2PDF_MAX_WORKSPACES",
                                os.environ.get("MD2PDF_MAX_WORKSPACES", "1000")))
    if maximum < 1:
        raise ValueError("MD2PDF_MAX_WORKSPACES must be a positive integer.")
    root.mkdir(parents=True, exist_ok=True)
    app.config.update(
        SECRET_KEY=secret,
        SESSION_COOKIE_NAME="md2pdf_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=_enabled(app.config.get(
            "MD2PDF_COOKIE_SECURE", os.environ.get("MD2PDF_COOKIE_SECURE", "1"))),
        PERMANENT_SESSION_LIFETIME=timedelta(seconds=WORKSPACE_TTL),
        SESSION_REFRESH_EACH_REQUEST=True,
    )
    state = {"root": root, "lock": RLock(), "active": {}, "last_cleanup": 0.0}
    app.extensions["md2pdf_workspaces"] = state

    @app.before_request
    def prepare_workspace():
        now = time.time()
        with state["lock"]:
            token = session.get("md2pdf_workspace")
            workspace = root / token if isinstance(token, str) and _TOKEN.fullmatch(token) else None
            if (workspace is None or not _safe_workspace(workspace, root)
                    or now - (workspace / _MARKER).stat().st_mtime >= WORKSPACE_TTL):
                count = sum(1 for p in root.iterdir() if _TOKEN.fullmatch(p.name))
                if count >= maximum:
                    _cleanup(root, now, state["active"])
                    count = sum(1 for p in root.iterdir() if _TOKEN.fullmatch(p.name))
                    if count >= maximum:
                        return jsonify(error="The hosted editor is at capacity. Please try again later."), 503
                while True:
                    token = secrets.token_hex(32)
                    workspace = root / token
                    try:
                        workspace.mkdir(mode=0o700)
                        break
                    except FileExistsError:
                        continue
                (workspace / "input").mkdir(mode=0o700)
                (workspace / "output").mkdir(mode=0o700)
                (workspace / "input" / "document.md").write_text("", encoding="utf-8")
                session["md2pdf_workspace"] = token
            session.permanent = True
            (workspace / _MARKER).touch()
            g.md2pdf_workspace = workspace
            g.md2pdf_input = workspace / "input"
            g.md2pdf_output = workspace / "output"
            state["active"][token] = state["active"].get(token, 0) + 1
            g.md2pdf_workspace_token = token
            if now - state["last_cleanup"] >= CLEANUP_INTERVAL:
                _cleanup(root, now, state["active"])
                state["last_cleanup"] = now

    @app.teardown_request
    def release_workspace(_error):
        token = g.pop("md2pdf_workspace_token", None)
        if token:
            with state["lock"]:
                remaining = state["active"].get(token, 1) - 1
                if remaining:
                    state["active"][token] = remaining
                else:
                    state["active"].pop(token, None)


def _directory(requested, default, attribute):
    if hosted_mode():
        if requested is not None and requested != "":
            raise ValueError("Server directories cannot be selected in the hosted editor.")
        return getattr(g, attribute)
    return Path(requested or default)


def input_directory(requested, default):
    return _directory(requested, default, "md2pdf_input")


def output_directory(requested, default):
    return _directory(requested, default, "md2pdf_output")


def validate_save(path, content):
    """Call under the document lock before replacing a hosted Markdown file."""
    if not hosted_mode():
        return
    path = Path(path)
    base = g.md2pdf_input.resolve()
    if (not valid_filename(path.name, ".md") or _linked(path)
            or path.resolve().parent != base):
        raise ValueError("Select a Markdown filename in your browser workspace.")
    if not isinstance(content, str):
        raise ValueError("Content must be text.")
    size = len(content.encode("utf-8"))
    if size > MAX_DOCUMENT_BYTES:
        raise ValueError("Hosted documents are limited to 1 MB each.")
    documents = [p for p in base.glob("*.md") if p.is_file() and not _linked(p)]
    if not path.exists() and len(documents) >= MAX_DOCUMENTS:
        raise ValueError("A browser workspace can contain at most 20 documents.")
    total = sum(p.stat().st_size for p in documents if p.resolve() != path.resolve()) + size
    if total > MAX_WORKSPACE_BYTES:
        raise ValueError("A browser workspace can contain at most 10 MB of Markdown.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cleanup", action="store_true", required=True,
                        help="Remove hosted workspaces idle for at least 24 hours.")
    parser.parse_args()
    print(f"Removed {cleanup_expired()} expired workspace(s).")
