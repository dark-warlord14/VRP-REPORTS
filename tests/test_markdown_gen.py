"""Tests for vrp/markdown_gen.py."""

from pathlib import Path
from unittest.mock import patch

from vrp.parser import build_issue
from vrp.utils import save_json

from tests.fixtures import ISSUE_ID, make_raw_metadata, make_raw_updates


def _setup_issue(issues_dir: Path, issue_id: str, **raw_u_kwargs) -> Path:
    """Write raw_updates.json, raw_metadata.json, and report.json to a temp issues dir."""
    raw_u = make_raw_updates(**raw_u_kwargs)
    raw_m = make_raw_metadata()
    issue = build_issue(issue_id, raw_u, raw_m)
    idir = issues_dir / issue_id
    idir.mkdir(parents=True, exist_ok=True)
    save_json(idir / "raw_updates.json", raw_u)
    save_json(idir / "raw_metadata.json", raw_m)
    save_json(idir / "report.json", issue.model_dump())
    return idir


class TestGenerateReportMarkdown:
    def test_returns_false_when_no_report_json(self, tmp_path):
        issues_dir = tmp_path / "issues"
        idir = issues_dir / ISSUE_ID
        idir.mkdir(parents=True)
        # no report.json written

        with patch("vrp.markdown_gen.ISSUES_DIR", issues_dir):
            from vrp.markdown_gen import generate_report_markdown
            result = generate_report_markdown(ISSUE_ID)
        assert result is False

    def test_creates_report_md(self, tmp_path):
        issues_dir = tmp_path / "issues"
        _setup_issue(issues_dir, ISSUE_ID)

        with patch("vrp.markdown_gen.ISSUES_DIR", issues_dir):
            from vrp.markdown_gen import generate_report_markdown
            result = generate_report_markdown(ISSUE_ID)

        assert result is True
        assert (issues_dir / ISSUE_ID / "report.md").exists()

    def test_title_in_output(self, tmp_path):
        issues_dir = tmp_path / "issues"
        _setup_issue(issues_dir, ISSUE_ID)

        with patch("vrp.markdown_gen.ISSUES_DIR", issues_dir):
            from vrp.markdown_gen import generate_report_markdown
            generate_report_markdown(ISSUE_ID)

        content = (issues_dir / ISSUE_ID / "report.md").read_text()
        assert "# " in content  # H1 title present

    def test_bounty_section_present(self, tmp_path):
        issues_dir = tmp_path / "issues"
        _setup_issue(issues_dir, ISSUE_ID)

        with patch("vrp.markdown_gen.ISSUES_DIR", issues_dir):
            from vrp.markdown_gen import generate_report_markdown
            generate_report_markdown(ISSUE_ID)

        content = (issues_dir / ISSUE_ID / "report.md").read_text()
        assert "## Bounty Award" in content

    def test_description_in_output(self, tmp_path):
        issues_dir = tmp_path / "issues"
        _setup_issue(issues_dir, ISSUE_ID, description="Use-after-free in BlinkRenderer")

        with patch("vrp.markdown_gen.ISSUES_DIR", issues_dir):
            from vrp.markdown_gen import generate_report_markdown
            generate_report_markdown(ISSUE_ID)

        content = (issues_dir / ISSUE_ID / "report.md").read_text()
        assert "Use-after-free in BlinkRenderer" in content

    def test_footer_present(self, tmp_path):
        issues_dir = tmp_path / "issues"
        _setup_issue(issues_dir, ISSUE_ID)

        with patch("vrp.markdown_gen.ISSUES_DIR", issues_dir):
            from vrp.markdown_gen import generate_report_markdown
            generate_report_markdown(ISSUE_ID)

        content = (issues_dir / ISSUE_ID / "report.md").read_text()
        assert "issues.chromium.org" in content

    def test_attachment_link_when_local_path(self, tmp_path):
        issues_dir = tmp_path / "issues"
        idir = _setup_issue(issues_dir, ISSUE_ID, attachments=[[1, "text/html", 100, "poc.html"]])
        # Simulate the file existing locally
        att_dir = idir / "attachments"
        att_dir.mkdir()
        (att_dir / "poc.html").write_text("<html>poc</html>")
        # Patch local_path into report.json
        import json
        report = json.loads((idir / "report.json").read_text())
        report["attachments"][0]["local_path"] = "attachments/poc.html"
        save_json(idir / "report.json", report)

        with patch("vrp.markdown_gen.ISSUES_DIR", issues_dir):
            from vrp.markdown_gen import generate_report_markdown
            generate_report_markdown(ISSUE_ID)

        content = (issues_dir / ISSUE_ID / "report.md").read_text()
        assert "[poc.html]" in content

    def test_parse_updates_not_called_twice(self, tmp_path):
        """Verify the DRY fix: parse_updates called exactly once per report."""
        issues_dir = tmp_path / "issues"
        _setup_issue(issues_dir, ISSUE_ID)

        call_count = 0
        original = __import__("vrp.parser", fromlist=["parse_updates"]).parse_updates

        def counting_parse_updates(raw, issue_id=""):
            nonlocal call_count
            call_count += 1
            return original(raw, issue_id)

        with patch("vrp.markdown_gen.ISSUES_DIR", issues_dir), \
             patch("vrp.markdown_gen.parse_updates", counting_parse_updates):
            from vrp.markdown_gen import generate_report_markdown
            generate_report_markdown(ISSUE_ID)

        assert call_count == 1, f"parse_updates called {call_count} times, expected 1"


class TestGenerateAllMarkdown:
    def test_generates_for_all_issues(self, tmp_path):
        issues_dir = tmp_path / "issues"
        for i in range(3):
            _setup_issue(issues_dir, f"10000000{i}")

        with patch("vrp.markdown_gen.ISSUES_DIR", issues_dir):
            from vrp.markdown_gen import generate_all_markdown
            count = generate_all_markdown()

        assert count == 3
        for i in range(3):
            assert (issues_dir / f"10000000{i}" / "report.md").exists()

    def test_skips_dirs_without_report_json(self, tmp_path):
        issues_dir = tmp_path / "issues"
        _setup_issue(issues_dir, "good_issue")
        (issues_dir / "no_report").mkdir()

        with patch("vrp.markdown_gen.ISSUES_DIR", issues_dir):
            from vrp.markdown_gen import generate_all_markdown
            count = generate_all_markdown()

        assert count == 1

    def test_skips_report_md_newer_than_report_json(self, tmp_path):
        """When report.md is newer than report.json, skip regeneration."""
        import time
        issues_dir = tmp_path / "issues"
        _setup_issue(issues_dir, ISSUE_ID)
        idir = issues_dir / ISSUE_ID

        with patch("vrp.markdown_gen.ISSUES_DIR", issues_dir):
            from vrp.markdown_gen import generate_all_markdown
            # First run: generates report.md
            count1 = generate_all_markdown()
        assert count1 == 1

        # Touch report.md so its mtime is strictly newer than report.json
        time.sleep(0.05)
        (idir / "report.md").touch()

        # Overwrite report.md with sentinel content to detect if regenerated
        sentinel = "SENTINEL_DO_NOT_OVERWRITE"
        (idir / "report.md").write_text(sentinel)
        # Set report.md mtime after report.json
        time.sleep(0.05)
        (idir / "report.md").touch()

        with patch("vrp.markdown_gen.ISSUES_DIR", issues_dir):
            from vrp.markdown_gen import generate_all_markdown
            count2 = generate_all_markdown()

        # Should be skipped (count=0), sentinel should still be there
        assert count2 == 0
        assert (idir / "report.md").read_text() == sentinel

    def test_force_flag_regenerates_even_if_up_to_date(self, tmp_path):
        """force=True bypasses the mtime check."""
        import time
        issues_dir = tmp_path / "issues"
        _setup_issue(issues_dir, ISSUE_ID)
        idir = issues_dir / ISSUE_ID

        with patch("vrp.markdown_gen.ISSUES_DIR", issues_dir):
            from vrp.markdown_gen import generate_all_markdown
            generate_all_markdown()

        # Stamp report.md as newer, write sentinel
        time.sleep(0.05)
        (idir / "report.md").touch()
        sentinel = "SENTINEL"
        (idir / "report.md").write_text(sentinel)
        time.sleep(0.05)
        (idir / "report.md").touch()

        with patch("vrp.markdown_gen.ISSUES_DIR", issues_dir):
            from vrp.markdown_gen import generate_all_markdown
            count = generate_all_markdown(force=True)

        # Should regenerate
        assert count == 1
        assert (idir / "report.md").read_text() != sentinel
