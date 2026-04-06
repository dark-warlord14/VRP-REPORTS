"""Tests for vrp/utils.py."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from vrp.utils import download_file, load_json, sanitize_filename, save_json

# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------

class TestSanitizeFilename:
    def test_clean_name_unchanged(self):
        assert sanitize_filename("poc.html") == "poc.html"
        assert sanitize_filename("asan.log") == "asan.log"

    def test_path_separators_replaced(self):
        result = sanitize_filename("path/to/file.txt")
        assert "/" not in result

    def test_backslash_replaced(self):
        result = sanitize_filename("path\\file.txt")
        assert "\\" not in result

    def test_colon_replaced(self):
        result = sanitize_filename("C:file.txt")
        assert ":" not in result

    def test_multiple_underscores_collapsed(self):
        result = sanitize_filename("a//b")
        assert "__" not in result

    def test_empty_string_returns_unnamed(self):
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("   ") == "unnamed"

    def test_spaces_preserved(self):
        # Spaces are not in the blacklist
        result = sanitize_filename("my file.html")
        assert result == "my file.html"


# ---------------------------------------------------------------------------
# save_json / load_json
# ---------------------------------------------------------------------------

class TestJsonIO:
    def test_round_trip(self, tmp_path):
        data = {"id": "123", "bounty": 5000.0, "tags": ["a", "b"]}
        path = tmp_path / "test.json"
        save_json(path, data)
        loaded = load_json(path)
        assert loaded == data

    def test_save_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "nested" / "deep" / "data.json"
        save_json(path, {"x": 1})
        assert path.exists()

    def test_load_missing_returns_none(self, tmp_path):
        result = load_json(tmp_path / "nonexistent.json")
        assert result is None

    def test_load_corrupt_returns_none(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{ this is not json }")
        result = load_json(path)
        assert result is None

    def test_load_unicode(self, tmp_path):
        data = {"title": "漏洞报告 🐛"}
        path = tmp_path / "unicode.json"
        save_json(path, data)
        assert load_json(path)["title"] == "漏洞报告 🐛"

    def test_save_uses_indent(self, tmp_path):
        path = tmp_path / "pretty.json"
        save_json(path, {"a": 1})
        content = path.read_text()
        assert "\n" in content  # indented, not compact


# ---------------------------------------------------------------------------
# download_file
# ---------------------------------------------------------------------------

def _make_aiohttp_mocks(status=200, content=b"file content", content_type="application/octet-stream"):
    """Build a properly structured aiohttp session mock.

    aiohttp usage pattern in download_file:
        async with aiohttp.ClientSession(...) as session:   # session_cm
            async with session.get(url, ...) as resp:       # resp_cm (sync call → async CM)
                resp.status, resp.headers, resp.content.iter_chunked(...)
    """
    # The response object
    resp = MagicMock()
    resp.status = status
    resp.headers = {"content-type": content_type}

    async def iter_chunked(size):
        yield content

    resp.content = MagicMock()
    resp.content.iter_chunked = iter_chunked

    # async with session.get(...) as resp  →  resp_cm.__aenter__ returns resp
    resp_cm = MagicMock()
    resp_cm.__aenter__ = AsyncMock(return_value=resp)
    resp_cm.__aexit__ = AsyncMock(return_value=False)

    # session.get(...) is a plain synchronous call that returns resp_cm
    session = MagicMock()
    session.get = MagicMock(return_value=resp_cm)

    # async with aiohttp.ClientSession(...) as session  →  session_cm.__aenter__ returns session
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)

    return session_cm


class TestDownloadFile:
    def test_successful_download(self, tmp_path):
        dest = tmp_path / "output.bin"

        async def run():
            mocks = _make_aiohttp_mocks(200, b"hello")
            with patch("vrp.utils.aiohttp.ClientSession", return_value=mocks):
                return await download_file("https://example.com/f", str(dest))

        result = asyncio.run(run())
        assert result is True
        assert dest.read_bytes() == b"hello"

    def test_html_rejected_when_non_html_expected(self, tmp_path):
        dest = tmp_path / "att.bin"

        async def run():
            mocks = _make_aiohttp_mocks(200, b"<html>login</html>", "text/html")
            with patch("vrp.utils.aiohttp.ClientSession", return_value=mocks):
                return await download_file(
                    "https://example.com/f", str(dest),
                    expected_mime="application/octet-stream"
                )

        result = asyncio.run(run())
        assert result is False
        assert not dest.exists()

    def test_html_allowed_when_html_expected(self, tmp_path):
        dest = tmp_path / "poc.html"

        async def run():
            mocks = _make_aiohttp_mocks(200, b"<html>poc</html>", "text/html")
            with patch("vrp.utils.aiohttp.ClientSession", return_value=mocks):
                return await download_file(
                    "https://example.com/poc.html", str(dest),
                    expected_mime="text/html"
                )

        result = asyncio.run(run())
        assert result is True

    def test_non_200_returns_false(self, tmp_path):
        dest = tmp_path / "out.bin"

        async def run():
            mocks = _make_aiohttp_mocks(403)
            with patch("vrp.utils.aiohttp.ClientSession", return_value=mocks):
                return await download_file("https://example.com/f", str(dest))

        result = asyncio.run(run())
        assert result is False
