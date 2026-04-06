"""Tests for vrp/index_builder.py."""

import json
from pathlib import Path
from unittest.mock import patch

from vrp.parser import build_issue
from vrp.utils import save_json

from tests.fixtures import make_raw_metadata, make_raw_updates


def _write_report(issues_dir: Path, issue_id: str, overrides: dict = None) -> dict:
    """Write a minimal report.json for an issue."""
    raw_u = make_raw_updates()
    raw_m = make_raw_metadata()
    issue = build_issue(issue_id, raw_u, raw_m)
    data = issue.model_dump()
    if overrides:
        data.update(overrides)
    idir = issues_dir / issue_id
    idir.mkdir(parents=True, exist_ok=True)
    save_json(idir / "report.json", data)
    return data


class TestRebuildIndex:
    def test_empty_dir_returns_zero(self, tmp_path):
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        with patch("vrp.index_builder.ISSUES_DIR", issues_dir), \
             patch("vrp.index_builder.INDEX_FILE", tmp_path / "index.json"), \
             patch("vrp.index_builder.STATS_FILE", tmp_path / "stats.json"):
            from vrp.index_builder import rebuild_index
            count = rebuild_index()
        assert count == 0

    def test_counts_reports(self, tmp_path):
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        for i in range(3):
            _write_report(issues_dir, f"10000000{i}")

        with patch("vrp.index_builder.ISSUES_DIR", issues_dir), \
             patch("vrp.index_builder.INDEX_FILE", tmp_path / "index.json"), \
             patch("vrp.index_builder.STATS_FILE", tmp_path / "stats.json"):
            from vrp.index_builder import rebuild_index
            count = rebuild_index()

        assert count == 3

    def test_index_json_written(self, tmp_path):
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        _write_report(issues_dir, "200000001")
        index_file = tmp_path / "index.json"

        with patch("vrp.index_builder.ISSUES_DIR", issues_dir), \
             patch("vrp.index_builder.INDEX_FILE", index_file), \
             patch("vrp.index_builder.STATS_FILE", tmp_path / "stats.json"):
            from vrp.index_builder import rebuild_index
            rebuild_index()

        entries = json.loads(index_file.read_text())
        assert len(entries) == 1
        entry = entries[0]
        assert entry["id"] == "200000001"
        assert "title" in entry
        assert "bounty_amount" in entry
        assert "severity" in entry
        assert "created_date" in entry
        assert "local_path" in entry

    def test_index_sorted_newest_first(self, tmp_path):
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        _write_report(issues_dir, "100", {"created_date": "2022-01-01T00:00:00+00:00"})
        _write_report(issues_dir, "200", {"created_date": "2024-01-01T00:00:00+00:00"})
        index_file = tmp_path / "index.json"

        with patch("vrp.index_builder.ISSUES_DIR", issues_dir), \
             patch("vrp.index_builder.INDEX_FILE", index_file), \
             patch("vrp.index_builder.STATS_FILE", tmp_path / "stats.json"):
            from vrp.index_builder import rebuild_index
            rebuild_index()

        entries = json.loads(index_file.read_text())
        assert entries[0]["id"] == "200"
        assert entries[1]["id"] == "100"

    def test_dirs_without_report_json_skipped(self, tmp_path):
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        # Dir with only raw data, no report.json
        (issues_dir / "999").mkdir()
        (issues_dir / "999" / "raw_updates.json").write_text("{}")
        _write_report(issues_dir, "888")
        index_file = tmp_path / "index.json"

        with patch("vrp.index_builder.ISSUES_DIR", issues_dir), \
             patch("vrp.index_builder.INDEX_FILE", index_file), \
             patch("vrp.index_builder.STATS_FILE", tmp_path / "stats.json"):
            from vrp.index_builder import rebuild_index
            count = rebuild_index()

        assert count == 1

    def test_malformed_created_date_does_not_crash(self, tmp_path):
        """Year extraction must not crash on bad created_date values."""
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        _write_report(issues_dir, "bad_date", {"created_date": "not-a-date"})
        index_file = tmp_path / "index.json"

        with patch("vrp.index_builder.ISSUES_DIR", issues_dir), \
             patch("vrp.index_builder.INDEX_FILE", index_file), \
             patch("vrp.index_builder.STATS_FILE", tmp_path / "stats.json"):
            from vrp.index_builder import rebuild_index
            count = rebuild_index()  # Must not raise

        assert count == 1
        import json
        entries = json.loads(index_file.read_text())
        assert entries[0]["year"] is None

    def test_none_created_date_handled(self, tmp_path):
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        _write_report(issues_dir, "no_date", {"created_date": None})
        index_file = tmp_path / "index.json"

        with patch("vrp.index_builder.ISSUES_DIR", issues_dir), \
             patch("vrp.index_builder.INDEX_FILE", index_file), \
             patch("vrp.index_builder.STATS_FILE", tmp_path / "stats.json"):
            from vrp.index_builder import rebuild_index
            rebuild_index()

        import json
        entries = json.loads(index_file.read_text())
        assert entries[0]["year"] is None


class TestBuildStats:
    def test_totals(self, tmp_path):
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        _write_report(issues_dir, "1", {"bounty_amount": 3000.0, "created_date": "2024-01-01T00:00:00+00:00"})
        _write_report(issues_dir, "2", {"bounty_amount": 7000.0, "created_date": "2024-06-01T00:00:00+00:00"})

        with patch("vrp.index_builder.ISSUES_DIR", issues_dir), \
             patch("vrp.index_builder.INDEX_FILE", tmp_path / "index.json"), \
             patch("vrp.index_builder.STATS_FILE", tmp_path / "stats.json"):
            from vrp.index_builder import build_stats, rebuild_index
            rebuild_index()
            stats = build_stats()

        assert stats["total_reports"] == 2
        assert stats["total_bounty"] == 10000.0
        assert stats["avg_bounty"] == 5000.0

    def test_by_year_breakdown(self, tmp_path):
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        _write_report(issues_dir, "1", {"created_date": "2024-03-01T00:00:00+00:00", "bounty_amount": 1000.0})
        _write_report(issues_dir, "2", {"created_date": "2025-03-01T00:00:00+00:00", "bounty_amount": 2000.0})

        with patch("vrp.index_builder.ISSUES_DIR", issues_dir), \
             patch("vrp.index_builder.INDEX_FILE", tmp_path / "index.json"), \
             patch("vrp.index_builder.STATS_FILE", tmp_path / "stats.json"):
            from vrp.index_builder import build_stats, rebuild_index
            rebuild_index()
            stats = build_stats()

        # by_year is keyed by string year
        assert stats["by_year"]["2024"]["count"] == 1
        assert stats["by_year"]["2025"]["count"] == 1

    def test_zero_bounty_amount_counted_in_avg_and_histogram(self, tmp_path):
        """bounty_amount=0.0 is falsy; confirm it's not excluded from stats."""
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        # One issue with $0 bounty (confirmed), one with $5000
        _write_report(issues_dir, "1", {"bounty_amount": 0.0, "created_date": "2024-01-01T00:00:00+00:00"})
        _write_report(issues_dir, "2", {"bounty_amount": 5000.0, "created_date": "2024-01-01T00:00:00+00:00"})

        with patch("vrp.index_builder.ISSUES_DIR", issues_dir), \
             patch("vrp.index_builder.INDEX_FILE", tmp_path / "index.json"), \
             patch("vrp.index_builder.STATS_FILE", tmp_path / "stats.json"):
            from vrp.index_builder import build_stats, rebuild_index
            rebuild_index()
            stats = build_stats()

        assert stats["total_bounty"] == 5000.0
        # avg should be (0.0 + 5000.0) / 2 = 2500.0, not 5000.0 / 1 = 5000.0
        assert stats["avg_bounty"] == 2500.0
        # $0 should appear in the $0-500 histogram bucket
        zero_bucket = next(b for b in stats["bounty_histogram"] if b["range"] == "$0-500")
        assert zero_bucket["count"] == 1
