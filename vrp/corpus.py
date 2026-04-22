"""JS corpus extraction from VRP PoC attachments for Fuzzilli/V8 fuzzers."""

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

from vrp.models import Issue
from vrp.utils import logger

_SKIP_MIME_PREFIXES: tuple[str, ...] = ("video/", "image/", "audio/")

_BINARY_MIME_SET: frozenset[str] = frozenset({
    "application/zip",
    "application/x-zip-compressed",
    "application/x-7z-compressed",
    "application/x-bzip2",
    "application/x-gzip",
    "application/pdf",
    "application/msword",
    "application/vnd.android.package-archive",
    "application/x-x509-ca-cert",
    "application/octet-stream",
})


class _ScriptExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_script: bool = False
        self._current: list[str] = []
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag == "script":
            if "src" not in dict(attrs):
                self._in_script = True
                self._current = []
            else:
                self._in_script = False

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            if self._in_script and self._current:
                block = "".join(self._current).strip()
                if block:
                    self.blocks.append(block)
            self._in_script = False

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._current.append(data)


def extract_js_from_html(content: str) -> Optional[str]:
    parser = _ScriptExtractor()
    try:
        parser.feed(content)
    except Exception as exc:
        logger.warning("HTML parse error: %s", exc)
        return None
    if not parser.blocks:
        return None
    return "\n// ---\n".join(parser.blocks)


def extract_js_from_attachment(path: Path, mime_type: str) -> Optional[str]:
    suffix = path.suffix.lower()
    mime = mime_type.lower()
    is_html = suffix in (".html", ".htm") or mime in ("text/html", "application/xhtml+xml")
    is_js = suffix == ".js" or mime in ("text/javascript", "application/javascript")

    if not is_html and not is_js:
        return None

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("Cannot read attachment %s: %s", path, exc)
        return None

    if is_html:
        return extract_js_from_html(content)
    return content.strip() or None


def _safe_stem(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    safe = re.sub(r"[^\w\-]", "_", stem)
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe or "attachment"


def write_issue_corpus(issue: Issue, idir: Path, corpus_dir: Path, min_size: int = 10) -> int:
    corpus_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for att in issue.attachments:
        if att.local_path is None:
            continue

        mime = att.mime_type.lower()
        if any(mime.startswith(p) for p in _SKIP_MIME_PREFIXES):
            continue
        if mime in _BINARY_MIME_SET:
            continue

        att_path = idir / att.local_path
        if not att_path.exists():
            continue

        js = extract_js_from_attachment(att_path, mime)
        if js is None or len(js) < min_size:
            continue

        stem = _safe_stem(att.filename)
        out = corpus_dir / f"{issue.id}_{stem}.js"
        if out.exists():
            out = corpus_dir / f"{issue.id}_{stem}_{att.id}.js"

        out.write_text(js, encoding="utf-8")
        count += 1

    return count
