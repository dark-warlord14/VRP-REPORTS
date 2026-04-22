"""Tests for vrp/corpus.py."""



from vrp.corpus import (
    extract_js_from_attachment,
    extract_js_from_html,
    write_issue_corpus,
)
from vrp.models import Attachment, Issue


def _make_issue(issue_id: str = "123456", attachments: list[Attachment] | None = None) -> Issue:
    return Issue(
        id=issue_id,
        url=f"https://issues.chromium.org/issues/{issue_id}",
        title="Test Issue",
        component="Blink>JavaScript",
        severity="S1-High",
        bounty_confirmed=True,
        attachments=attachments or [],
    )


class TestExtractJsFromHtml:
    def test_single_inline_script(self):
        html = "<html><body><script>console.log('hi');</script></body></html>"
        result = extract_js_from_html(html)
        assert result is not None
        assert "console.log('hi');" in result

    def test_external_script_only_returns_none(self):
        html = '<html><head><script src="https://cdn.js/lib.js"></script></head></html>'
        assert extract_js_from_html(html) is None

    def test_multiple_inline_scripts_concatenated(self):
        html = (
            "<html><body>"
            "<script>var a = 1;</script>"
            "<script>var b = 2;</script>"
            "</body></html>"
        )
        result = extract_js_from_html(html)
        assert result is not None
        assert "var a = 1;" in result
        assert "var b = 2;" in result
        assert "// ---" in result

    def test_no_scripts_returns_none(self):
        assert extract_js_from_html("<html><body><p>No scripts.</p></body></html>") is None

    def test_mixed_external_and_inline(self):
        html = (
            '<html><head><script src="ext.js"></script></head>'
            '<body><script>var x = 42;</script></body></html>'
        )
        result = extract_js_from_html(html)
        assert result is not None
        assert "var x = 42;" in result

    def test_empty_inline_script_returns_none(self):
        assert extract_js_from_html("<html><body><script>   </script></body></html>") is None

    def test_plain_text_returns_none(self):
        assert extract_js_from_html("This is not HTML.") is None


class TestExtractJsFromAttachment:
    def test_js_file_returned_directly(self, tmp_path):
        f = tmp_path / "poc.js"
        f.write_text("var x = 1;", encoding="utf-8")
        assert extract_js_from_attachment(f, "text/javascript") == "var x = 1;"

    def test_html_file_extracts_scripts(self, tmp_path):
        f = tmp_path / "poc.html"
        f.write_text("<script>var x = 2;</script>", encoding="utf-8")
        result = extract_js_from_attachment(f, "text/html")
        assert result is not None
        assert "var x = 2;" in result

    def test_html_extension_overrides_octet_stream_mime(self, tmp_path):
        f = tmp_path / "poc.html"
        f.write_text("<script>var y = 3;</script>", encoding="utf-8")
        result = extract_js_from_attachment(f, "application/octet-stream")
        assert result is not None
        assert "var y = 3;" in result

    def test_binary_extension_and_mime_returns_none(self, tmp_path):
        f = tmp_path / "data.bin"
        f.write_bytes(b"\x00\x01\x02")
        assert extract_js_from_attachment(f, "application/octet-stream") is None

    def test_empty_js_file_returns_none(self, tmp_path):
        f = tmp_path / "empty.js"
        f.write_text("   ", encoding="utf-8")
        assert extract_js_from_attachment(f, "text/javascript") is None

    def test_missing_file_returns_none(self, tmp_path):
        assert extract_js_from_attachment(tmp_path / "nonexistent.js", "text/javascript") is None

    def test_xhtml_mime_treated_as_html(self, tmp_path):
        f = tmp_path / "poc.xhtml"
        f.write_text("<script>var z = 4;</script>", encoding="utf-8")
        result = extract_js_from_attachment(f, "application/xhtml+xml")
        assert result is not None

    def test_js_mime_with_html_extension_parses_as_html(self, tmp_path):
        f = tmp_path / "poc.html"
        f.write_text("<script>var w = 5;</script>", encoding="utf-8")
        result = extract_js_from_attachment(f, "text/javascript")
        assert result is not None
        assert "var w = 5;" in result


class TestWriteIssueCorpus:
    def _make_att(self, att_id: int, filename: str, mime: str, local_path: str) -> Attachment:
        return Attachment(
            id=att_id,
            filename=filename,
            mime_type=mime,
            size_bytes=100,
            url="https://example.com/att",
            local_path=local_path,
        )

    def test_writes_js_from_html_poc(self, tmp_path):
        idir = tmp_path / "issues" / "111"
        att_dir = idir / "attachments"
        att_dir.mkdir(parents=True)
        (att_dir / "poc.html").write_text("<script>var exploit = true;</script>")

        issue = _make_issue("111", [
            self._make_att(1, "poc.html", "text/html", "attachments/poc.html")
        ])
        corpus_dir = tmp_path / "corpus"
        count = write_issue_corpus(issue, idir, corpus_dir)

        assert count == 1
        files = list(corpus_dir.glob("111_*.js"))
        assert len(files) == 1
        assert "exploit" in files[0].read_text()

    def test_writes_js_attachment_directly(self, tmp_path):
        idir = tmp_path / "issues" / "222"
        att_dir = idir / "attachments"
        att_dir.mkdir(parents=True)
        (att_dir / "poc.js").write_text("function trigger() { return 42; }")

        issue = _make_issue("222", [
            self._make_att(2, "poc.js", "text/javascript", "attachments/poc.js")
        ])
        corpus_dir = tmp_path / "corpus"
        count = write_issue_corpus(issue, idir, corpus_dir)

        assert count == 1

    def test_skips_video_attachment(self, tmp_path):
        idir = tmp_path / "issues" / "333"
        att_dir = idir / "attachments"
        att_dir.mkdir(parents=True)
        (att_dir / "demo.mp4").write_bytes(b"\x00\x01\x02")

        issue = _make_issue("333", [
            self._make_att(3, "demo.mp4", "video/mp4", "attachments/demo.mp4")
        ])
        corpus_dir = tmp_path / "corpus"
        assert write_issue_corpus(issue, idir, corpus_dir) == 0

    def test_skips_zip_attachment(self, tmp_path):
        idir = tmp_path / "issues" / "444"
        att_dir = idir / "attachments"
        att_dir.mkdir(parents=True)
        (att_dir / "files.zip").write_bytes(b"PK\x03\x04")

        issue = _make_issue("444", [
            self._make_att(4, "files.zip", "application/zip", "attachments/files.zip")
        ])
        corpus_dir = tmp_path / "corpus"
        assert write_issue_corpus(issue, idir, corpus_dir) == 0

    def test_min_size_filters_small_snippets(self, tmp_path):
        idir = tmp_path / "issues" / "555"
        att_dir = idir / "attachments"
        att_dir.mkdir(parents=True)
        (att_dir / "poc.js").write_text("x=1")

        issue = _make_issue("555", [
            self._make_att(5, "poc.js", "text/javascript", "attachments/poc.js")
        ])
        corpus_dir = tmp_path / "corpus"
        assert write_issue_corpus(issue, idir, corpus_dir, min_size=10) == 0

    def test_skips_none_local_path(self, tmp_path):
        idir = tmp_path / "issues" / "666"
        idir.mkdir(parents=True)

        att = Attachment(id=6, filename="poc.js", mime_type="text/javascript", size_bytes=100, url="")
        issue = _make_issue("666", [att])
        corpus_dir = tmp_path / "corpus"
        assert write_issue_corpus(issue, idir, corpus_dir) == 0

    def test_collision_handled_by_att_id(self, tmp_path):
        idir = tmp_path / "issues" / "777"
        att_dir = idir / "attachments"
        att_dir.mkdir(parents=True)
        (att_dir / "poc1.js").write_text("var a = trigger_bug_one();")
        (att_dir / "poc2.js").write_text("var b = trigger_bug_two();")

        # Both would produce 777_poc.js — second gets 777_poc_<id>.js
        issue = _make_issue("777", [
            self._make_att(10, "poc.js", "text/javascript", "attachments/poc1.js"),
            self._make_att(11, "poc.js", "text/javascript", "attachments/poc2.js"),
        ])
        corpus_dir = tmp_path / "corpus"
        count = write_issue_corpus(issue, idir, corpus_dir)

        assert count == 2
        files = list(corpus_dir.glob("777_*.js"))
        assert len(files) == 2

    def test_creates_corpus_dir_if_missing(self, tmp_path):
        idir = tmp_path / "issues" / "888"
        idir.mkdir(parents=True)
        issue = _make_issue("888", [])
        corpus_dir = tmp_path / "nonexistent" / "corpus"
        write_issue_corpus(issue, idir, corpus_dir)
        assert corpus_dir.exists()
