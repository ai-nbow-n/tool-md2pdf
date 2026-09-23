#!/usr/bin/env python3
"""Check the installed hosted editor without credentials or third-party APIs.

By default, contact the loopback service with the website's proxy headers.
Use --url https://nbow.io/en/products/aiconsulting/code-agents/md2pdf/ to check
the public website route instead. Only new synthetic workspaces are written;
they expire through the service's ordinary cleanup. No documents or cookies
are printed, and existing workspaces are never selected or deleted.
"""
import argparse
import json
import sys
import time
import uuid
from html.parser import HTMLParser
from http.cookies import SimpleCookie
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


PREFIX = "/en/products/aiconsulting/code-agents/md2pdf"
LOOPBACK_URL = "http://127.0.0.1:2380"
COOKIE_NAME = "md2pdf_session"


class SmokeFailure(Exception):
    """A diagnostic safe to include in deployment output."""


class ServiceUnavailable(SmokeFailure):
    """A connection failure that may be transient during service startup."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the explicit session cookie to a redirect destination.
        return None


class PageDetails(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hosted = False
        self.prefix = None
        self.assets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "body":
            self.hosted = attrs.get("data-hosted") == "true"
        if tag == "meta" and attrs.get("name") == "md2pdf-base":
            self.prefix = attrs.get("content")
        if tag == "script" and attrs.get("src"):
            self.assets.append(attrs["src"])
        if tag == "link" and attrs.get("rel") == "stylesheet" and attrs.get("href"):
            self.assets.append(attrs["href"])


class Client:
    def __init__(self, base_url, *, proxy_headers):
        self.base_url = base_url.rstrip("/")
        parsed = urlsplit(self.base_url)
        self.headers = {"Origin": f"{parsed.scheme}://{parsed.netloc}"}
        if proxy_headers:
            self.headers.update({
                "Host": "nbow.io",
                "Origin": "https://nbow.io",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Prefix": PREFIX,
            })
        # Do not send loopback requests through an environment HTTP proxy.
        self.opener = build_opener(ProxyHandler({}), NoRedirects())
        self.cookie = None

    def request(self, path, *, body=None, expected=200, timeout=20):
        headers = dict(self.headers)
        if self.cookie:
            # Secure cookies intentionally remain Secure. CookieJar would not
            # replay one over this trusted loopback HTTP connection.
            headers["Cookie"] = self.cookie
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(self.base_url + path, data=data, headers=headers)
        try:
            response = self.opener.open(request, timeout=timeout)
        except HTTPError as error:
            response = error
        except (URLError, OSError, ValueError) as error:
            raise ServiceUnavailable(f"Request failed ({type(error).__name__}).") from None
        with response:
            if response.status != expected:
                failure = ServiceUnavailable if response.status in (502, 503, 504) else SmokeFailure
                raise failure(f"Expected HTTP {expected}, received HTTP {response.status}.")
            for header in response.headers.get_all("Set-Cookie", []):
                cookies = SimpleCookie()
                cookies.load(header)
                if COOKIE_NAME in cookies:
                    cookie = cookies[COOKIE_NAME]
                    if not (cookie["secure"] and cookie["httponly"]
                            and cookie["samesite"].lower() == "lax"):
                        raise SmokeFailure("The hosted session cookie lacks its security attributes.")
                    self.cookie = f"{COOKIE_NAME}={cookie.coded_value}"
            if not self.cookie:
                raise SmokeFailure("The hosted service did not issue a session cookie.")
            try:
                payload = response.read(4 * 1024 * 1024 + 1)
            except OSError as error:
                raise SmokeFailure(f"Response read failed ({type(error).__name__}).") from None
            if len(payload) > 4 * 1024 * 1024:
                raise SmokeFailure("Smoke response exceeds 4 MB.")
            return payload, response.headers

    def json(self, path, **kwargs):
        payload, headers = self.request(path, **kwargs)
        if headers.get_content_type() != "application/json":
            raise SmokeFailure("Expected a JSON API response.")
        try:
            return json.loads(payload)
        except (ValueError, UnicodeDecodeError):
            raise SmokeFailure("The API response contains invalid JSON.") from None


def require(condition, message):
    if not condition:
        raise SmokeFailure(message)


def run_smoke(base_url=LOOPBACK_URL, *, proxy_headers=True):
    prefix = PREFIX if proxy_headers else urlsplit(base_url).path.rstrip("/")
    client = Client(base_url, proxy_headers=proxy_headers)
    print("Checking hosted page and bundled assets...", flush=True)
    startup_deadline = time.monotonic() + 30
    while True:
        try:
            page, headers = client.request("/", timeout=min(5, max(0.1, startup_deadline - time.monotonic())))
            break
        except ServiceUnavailable:
            remaining = startup_deadline - time.monotonic()
            if remaining <= 0:
                raise SmokeFailure("The hosted service did not become ready within 30 seconds.") from None
            time.sleep(min(1, remaining))
    require(headers.get_content_type() == "text/html", "Expected the editor HTML page.")
    details = PageDetails()
    try:
        details.feed(page.decode("utf-8"))
    except UnicodeDecodeError:
        raise SmokeFailure("The editor page is not UTF-8.") from None
    require(details.hosted, "The editor is not running in hosted mode.")
    require(details.prefix == prefix, "The editor's localized base path is incorrect.")
    require(bool(details.assets), "The editor page has no bundled assets.")
    for asset in details.assets:
        require(asset.startswith(prefix + "/static/"), "An editor asset lacks its localized prefix.")
        payload, asset_headers = client.request(asset[len(prefix):])
        require(bool(payload) and asset_headers.get_content_type() != "text/html",
                "A bundled asset is missing or returned an HTML error page.")

    print("Checking a fresh workspace and Markdown save...", flush=True)
    require(client.json("/api/files") == ["document.md"], "A fresh workspace has unexpected files.")
    filename = "deployment-smoke-" + uuid.uuid4().hex + ".md"
    content = "# Deployment check\n\n```mermaid\nflowchart LR\n  A[Markdown] --> B[PDF]\n```\n"
    saved = client.json("/api/file/" + filename, body={"content": content, "create_only": True})
    require(isinstance(saved, dict) and saved.get("ok") is True, "Saving the smoke document failed.")
    document, _ = client.request("/api/file/" + filename)
    require(document == content.encode("utf-8"), "Saved Markdown did not round trip.")

    print("Compiling Markdown and Mermaid with the real renderer (up to 120 seconds)...", flush=True)
    compiled = client.json("/api/compile", body={"filename": filename}, timeout=135)
    require(isinstance(compiled, dict) and compiled.get("ok") is True,
            "PDF compilation failed; check the renderer installation and Chromium sandbox.")
    pdf_path = "/pdf/" + filename.removesuffix(".md") + ".pdf"
    pdf, headers = client.request(pdf_path)
    require(headers.get_content_type() == "application/pdf" and pdf.startswith(b"%PDF-"),
            "The renderer did not produce a downloadable PDF.")

    print("Checking document and PDF isolation between browser sessions...", flush=True)
    other = Client(base_url, proxy_headers=proxy_headers)
    require(other.json("/api/files") == ["document.md"], "A second session can see unexpected files.")
    require(other.cookie != client.cookie, "The service reused a session between independent clients.")
    other.request("/api/file/" + filename, expected=404)
    other.request(pdf_path, expected=404)
    files = client.json("/api/files")
    require(isinstance(files, list) and filename in files, "The first session lost its saved document.")
    print("PASS: hosted page, assets, save, Mermaid/PDF compilation, download, and session isolation.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Public HTTPS app URL, including its localized md2pdf path.")
    args = parser.parse_args()
    if args.url:
        parsed = urlsplit(args.url)
        if (parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password
                or parsed.query or parsed.fragment):
            parser.error("--url must be an HTTPS URL without credentials, query, or fragment.")
    try:
        run_smoke(args.url or LOOPBACK_URL, proxy_headers=not bool(args.url))
    except SmokeFailure as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        # Avoid printing arbitrary server responses or cookie values in CI logs.
        print(f"FAIL: Smoke check stopped ({type(error).__name__}).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
