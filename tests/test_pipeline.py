"""End-to-end pipeline integration test.

Runs reprocess → markdown → index on fixture data in a temp directory,
verifying that the full offline pipeline produces correct output from
raw JSON through to a browsable index.
"""

import json
from unittest.mock import patch

import pytest
from vrp.utils import save_json

from tests.fixtures import make_raw_metadata, make_raw_updates


@pytest.fixture()
def populated_data_dir(tmp_path):
    """A data dir with 5 issues: 4 bounty, 1 non-bounty."""
    data = tmp_path / "data"
    issues = data / "issues"
    issues.mkdir(parents=True)

    bounty_ids = ["100", "200", "300", "400"]
    for iid in bounty_ids:
        idir = issues / iid
        idir.mkdir()
        raw_u = make_raw_updates(description=f"Vuln in component {iid}")
        raw_m = make_raw_metadata(title=f"Bug {iid}", severity=2, status=4)
        save_json(idir / "raw_updates.json", raw_u)
        save_json(idir / "raw_metadata.json", raw_m)

    # Non-bounty issue: no bounty text, no bounty metadata
    nb_dir = issues / "500"
    nb_dir.mkdir()
    save_json(nb_dir / "raw_updates.json", make_raw_updates(bounty_text="Just a comment."))
    save_json(nb_dir / "raw_metadata.json", make_raw_metadata())

    return data


def _all_patches(data_dir):
    issues_dir = data_dir / "issues"
    return [
        patch("vrp.config.DATA_DIR", data_dir),
        patch("vrp.config.ISSUES_DIR", issues_dir),
        patch("vrp.config.INDEX_FILE", data_dir / "index.json"),
        patch("vrp.config.STATS_FILE", data_dir / "stats.json"),
        patch("vrp.config.QUEUE_FILE", data_dir / "discovery_queue.json"),
        patch("vrp.extractor.ISSUES_DIR", issues_dir),
        patch("vrp.extractor.QUEUE_FILE", data_dir / "discovery_queue.json"),
        patch("vrp.markdown_gen.ISSUES_DIR", issues_dir),
        patch("vrp.index_builder.ISSUES_DIR", issues_dir),
        patch("vrp.index_builder.INDEX_FILE", data_dir / "index.json"),
        patch("vrp.index_builder.STATS_FILE", data_dir / "stats.json"),
    ]


class TestFullOfflinePipeline:
    def test_reprocess_creates_report_json(self, populated_data_dir):
        patches = _all_patches(populated_data_dir)
        for p in patches:
            p.start()
        try:
            from vrp.extractor import reprocess_existing
            count = reprocess_existing()
        finally:
            for p in patches:
                p.stop()

        assert count == 4  # 4 bounty issues, 1 skipped

        issues = populated_data_dir / "issues"
        for iid in ["100", "200", "300", "400"]:
            assert (issues / iid / "report.json").exists(), f"Missing report.json for {iid}"
        # Non-bounty should NOT have report.json
        assert not (issues / "500" / "report.json").exists()

    def test_markdown_generates_md(self, populated_data_dir):
        patches = _all_patches(populated_data_dir)
        for p in patches:
            p.start()
        try:
            from vrp.extractor import reprocess_existing
            from vrp.markdown_gen import generate_all_markdown
            reprocess_existing()
            count = generate_all_markdown()
        finally:
            for p in patches:
                p.stop()

        assert count == 4
        issues = populated_data_dir / "issues"
        for iid in ["100", "200", "300", "400"]:
            md_path = issues / iid / "report.md"
            assert md_path.exists()
            content = md_path.read_text()
            assert f"Bug {iid}" in content
            assert "## Bounty Award" in content

    def test_index_reflects_bounty_reports(self, populated_data_dir):
        patches = _all_patches(populated_data_dir)
        for p in patches:
            p.start()
        try:
            from vrp.extractor import reprocess_existing
            from vrp.index_builder import build_stats, rebuild_index
            reprocess_existing()
            count = rebuild_index()
            stats = build_stats()
        finally:
            for p in patches:
                p.stop()

        assert count == 4

        index = json.loads((populated_data_dir / "index.json").read_text())
        assert len(index) == 4
        ids = {e["id"] for e in index}
        assert ids == {"100", "200", "300", "400"}

        # Stats correctness
        assert stats["total_reports"] == 4
        assert stats["total_bounty"] == 4 * 5000.0
        assert stats["avg_bounty"] == 5000.0

    def test_index_entry_schema(self, populated_data_dir):
        patches = _all_patches(populated_data_dir)
        for p in patches:
            p.start()
        try:
            from vrp.extractor import reprocess_existing
            from vrp.index_builder import rebuild_index
            reprocess_existing()
            rebuild_index()
        finally:
            for p in patches:
                p.stop()

        entries = json.loads((populated_data_dir / "index.json").read_text())
        required_fields = {
            "id", "title", "url", "status", "severity",
            "bounty_amount", "created_date", "local_path",
        }
        for entry in entries:
            missing = required_fields - entry.keys()
            assert not missing, f"Index entry missing fields: {missing}"

    def test_stats_by_year(self, populated_data_dir):
        patches = _all_patches(populated_data_dir)
        for p in patches:
            p.start()
        try:
            from vrp.extractor import reprocess_existing
            from vrp.index_builder import build_stats, rebuild_index
            reprocess_existing()
            rebuild_index()
            stats = build_stats()
        finally:
            for p in patches:
                p.stop()

        # All fixture issues have TS_EPOCH = 2024; by_year keyed by string year
        assert stats["by_year"]["2024"]["count"] == 4

    def test_pipeline_idempotent(self, populated_data_dir):
        """Running reprocess + index twice produces the same result."""
        patches = _all_patches(populated_data_dir)
        for p in patches:
            p.start()
        try:
            from vrp.extractor import reprocess_existing
            from vrp.index_builder import rebuild_index
            reprocess_existing()
            count1 = rebuild_index()
            reprocess_existing()
            count2 = rebuild_index()
        finally:
            for p in patches:
                p.stop()

        assert count1 == count2 == 4
