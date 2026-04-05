"""Tests for vrp/parser.py — core parsing logic."""

import pytest
from tests.fixtures import (
    ISSUE_ID, TS_EPOCH, TS_ISO, BOUNTY_TEXT,
    make_raw_updates, make_raw_metadata,
)
from vrp.parser import (
    safe_get, parse_updates, parse_metadata,
    extract_bounty_info, extract_cve_ids,
    collect_all_attachments, build_issue,
)


# ---------------------------------------------------------------------------
# safe_get
# ---------------------------------------------------------------------------

class TestSafeGet:
    def test_list_index(self):
        assert safe_get([10, 20, 30], 1) == 20

    def test_nested(self):
        assert safe_get([[1, [2, 3]]], 0, 1, 0) == 2

    def test_out_of_bounds_returns_default(self):
        assert safe_get([1, 2], 5) is None
        assert safe_get([1, 2], 5, default="x") == "x"

    def test_none_at_any_level(self):
        assert safe_get([None, [1, 2]], 0, 1) is None

    def test_dict_key(self):
        assert safe_get({"a": {"b": 42}}, "a", "b") == 42

    def test_wrong_type_returns_default(self):
        # int index on dict → default
        assert safe_get({"a": 1}, 0) is None


# ---------------------------------------------------------------------------
# parse_updates
# ---------------------------------------------------------------------------

class TestParseUpdates:
    def test_empty_raw_returns_empty_list(self):
        assert parse_updates([], ISSUE_ID) == []
        assert parse_updates(None, ISSUE_ID) == []
        assert parse_updates([[]], ISSUE_ID) == []

    def test_basic_update_parsed(self):
        raw = make_raw_updates()
        updates = parse_updates(raw, ISSUE_ID)
        assert len(updates) == 2

    def test_author_extracted(self):
        raw = make_raw_updates()
        updates = parse_updates(raw, ISSUE_ID)
        assert updates[0].author == "reporter@example.com"
        assert updates[1].author == "vrp-panel@google.com"

    def test_timestamp_converted(self):
        raw = make_raw_updates()
        updates = parse_updates(raw, ISSUE_ID)
        assert updates[0].timestamp == TS_ISO

    def test_plaintext_extracted(self):
        raw = make_raw_updates(description="Hello world")
        updates = parse_updates(raw, ISSUE_ID)
        assert updates[0].text_plain == "Hello world"

    def test_html_extracted(self):
        raw = make_raw_updates(html="<p>rich text</p>")
        updates = parse_updates(raw, ISSUE_ID)
        assert updates[0].text_html == "<p>rich text</p>"

    def test_html_none_when_absent(self):
        raw = make_raw_updates()
        updates = parse_updates(raw, ISSUE_ID)
        assert updates[0].text_html is None

    def test_is_description_set_on_first_update(self):
        raw = make_raw_updates()
        updates = parse_updates(raw, ISSUE_ID)
        assert updates[0].is_description is True
        assert updates[1].is_description is False

    def test_bounty_award_flag(self):
        raw = make_raw_updates()
        updates = parse_updates(raw, ISSUE_ID)
        assert updates[0].is_bounty_award is False
        assert updates[1].is_bounty_award is True  # bounty_text triggers flag

    def test_attachment_parsed(self):
        atts = [[61000001, "text/html", 1234, "poc.html"]]
        raw = make_raw_updates(attachments=atts)
        updates = parse_updates(raw, ISSUE_ID)
        assert len(updates[0].attachments) == 1
        att = updates[0].attachments[0]
        assert att.id == 61000001
        assert att.filename == "poc.html"
        assert att.mime_type == "text/html"
        assert att.size_bytes == 1234
        assert ISSUE_ID in att.url

    def test_attachment_url_uses_issue_id(self):
        atts = [[99, "application/octet-stream", 0, "asan"]]
        raw = make_raw_updates(attachments=atts)
        updates = parse_updates(raw, ISSUE_ID)
        assert f"issues/{ISSUE_ID}/attachments/99" in updates[0].attachments[0].url

    def test_malformed_attachment_skipped(self):
        # Entry too short
        raw = make_raw_updates(attachments=[[1, "text/plain"]])
        updates = parse_updates(raw, ISSUE_ID)
        assert updates[0].attachments == []

    def test_non_int_attachment_id_skipped(self):
        raw = make_raw_updates(attachments=[["not-an-id", "text/plain", 0, "f.txt"]])
        updates = parse_updates(raw, ISSUE_ID)
        assert updates[0].attachments == []

    def test_index_assigned_sequentially(self):
        raw = make_raw_updates()
        updates = parse_updates(raw, ISSUE_ID)
        for i, u in enumerate(updates):
            assert u.index == i


# ---------------------------------------------------------------------------
# parse_metadata
# ---------------------------------------------------------------------------

class TestParseMetadata:
    def test_empty_returns_empty_dict(self):
        assert parse_metadata([]) == {}
        assert parse_metadata(None) == {}

    def test_title_extracted(self):
        raw = make_raw_metadata(title="Remote code execution")
        meta = parse_metadata(raw)
        assert meta["title"] == "Remote code execution"

    def test_status_mapped(self):
        raw = make_raw_metadata(status=4)
        assert parse_metadata(raw)["status"] == "Fixed"

    def test_severity_mapped(self):
        raw = make_raw_metadata(severity=2)
        assert parse_metadata(raw)["severity"] == "S1-High"

    def test_priority_mapped(self):
        raw = make_raw_metadata(priority=2)
        assert parse_metadata(raw)["priority"] == "P1"

    def test_reporter_extracted(self):
        raw = make_raw_metadata(reporter="user@example.com")
        assert parse_metadata(raw)["reporter"] == "user@example.com"

    def test_assignee_extracted(self):
        raw = make_raw_metadata(assignee="dev@google.com")
        assert parse_metadata(raw)["assignee"] == "dev@google.com"

    def test_component_custom_field(self):
        raw = make_raw_metadata(component="Blink>Layout")
        assert parse_metadata(raw)["component"] == "Blink>Layout"

    def test_os_platforms_split(self):
        raw = make_raw_metadata(os_platforms="Linux, Windows, Mac")
        platforms = parse_metadata(raw)["os_platforms"]
        assert platforms == ["Linux", "Windows", "Mac"]

    def test_chrome_version_extracted(self):
        raw = make_raw_metadata(chrome_version="120.0.6099.62")
        assert parse_metadata(raw)["chrome_version"] == "120.0.6099.62"

    def test_bounty_amount_from_metadata(self):
        raw = make_raw_metadata(bounty_amount=7500)
        assert parse_metadata(raw)["bounty_amount_meta"] == 7500.0

    def test_unknown_status_int(self):
        raw = make_raw_metadata(status=999)
        assert parse_metadata(raw)["status"] == "Unknown"

    def test_unrecognized_field_emits_debug_log(self, caplog):
        """Unknown custom field IDs should be logged at DEBUG level."""
        import logging
        raw = make_raw_metadata()
        # Inject an unknown field into the custom_fields list
        # Structure: raw[0][1][22][2][14] is the custom_fields list
        unknown_field_id = 999999
        raw[0][1][22][2][14].append([unknown_field_id, "somevalue"] + [None] * 8)

        with caplog.at_level(logging.DEBUG, logger="vrp.parser"):
            from vrp.parser import parse_metadata
            parse_metadata(raw)

        assert any(str(unknown_field_id) in r.message
                   for r in caplog.records if r.levelno == logging.DEBUG)


# ---------------------------------------------------------------------------
# extract_bounty_info
# ---------------------------------------------------------------------------

class TestExtractBountyInfo:
    def test_no_bounty(self):
        raw = make_raw_updates(bounty_text="Just a comment with no bounty.")
        updates = parse_updates(raw, ISSUE_ID)
        confirmed, amount, rationale = extract_bounty_info(updates)
        assert confirmed is False
        assert amount is None
        assert rationale is None

    def test_bounty_detected(self):
        raw = make_raw_updates()
        updates = parse_updates(raw, ISSUE_ID)
        confirmed, amount, rationale = extract_bounty_info(updates)
        assert confirmed is True
        assert amount == 5000.0

    def test_rationale_extracted(self):
        raw = make_raw_updates()
        updates = parse_updates(raw, ISSUE_ID)
        _, _, rationale = extract_bounty_info(updates)
        assert rationale is not None
        assert "use-after-free" in rationale.lower()

    def test_bounty_amount_with_comma(self):
        text = "We have decided to award you $15,000 for this report."
        raw = make_raw_updates(bounty_text=text)
        updates = parse_updates(raw, ISSUE_ID)
        _, amount, _ = extract_bounty_info(updates)
        assert amount == 15000.0

    def test_rationale_extracted_case_insensitive(self):
        """Rationale markers should match regardless of casing."""
        bounty_text = (
            "Chrome VRP Panel has decided to award you $1,000.\n\n"
            "RATIONALE FOR THIS DECISION: sandbox escape via type confusion.\n\n"
            "IMPORTANT: Please confirm receipt."
        )
        raw = make_raw_updates(bounty_text=bounty_text)
        updates = parse_updates(raw, ISSUE_ID)
        _, _, rationale = extract_bounty_info(updates)
        assert rationale is not None
        assert "sandbox escape" in rationale

    def test_rationale_extracted_when_important_absent(self):
        """Rationale extraction works when 'Important:' is not present."""
        bounty_text = (
            "Chrome VRP Panel has decided to award you $2,000.\n\n"
            "Rationale for this decision: buffer overflow in audio decoder."
        )
        raw = make_raw_updates(bounty_text=bounty_text)
        updates = parse_updates(raw, ISSUE_ID)
        _, _, rationale = extract_bounty_info(updates)
        assert rationale is not None
        assert "buffer overflow" in rationale


# ---------------------------------------------------------------------------
# extract_cve_ids
# ---------------------------------------------------------------------------

class TestExtractCveIds:
    def test_no_cves(self):
        raw = make_raw_updates(description="No CVE here")
        updates = parse_updates(raw, ISSUE_ID)
        assert extract_cve_ids(updates) == []

    def test_single_cve(self):
        raw = make_raw_updates(description="Fixed CVE-2024-12345 in renderer.")
        updates = parse_updates(raw, ISSUE_ID)
        cves = extract_cve_ids(updates)
        assert cves == ["CVE-2024-12345"]

    def test_multiple_cves_deduped_sorted(self):
        raw = make_raw_updates(description="CVE-2024-99999 and CVE-2023-11111 and CVE-2024-99999")
        updates = parse_updates(raw, ISSUE_ID)
        cves = extract_cve_ids(updates)
        assert cves == ["CVE-2023-11111", "CVE-2024-99999"]


# ---------------------------------------------------------------------------
# collect_all_attachments
# ---------------------------------------------------------------------------

class TestCollectAllAttachments:
    def test_deduplication_by_id(self):
        atts = [[1, "text/html", 100, "poc.html"], [1, "text/html", 100, "poc.html"]]
        raw = make_raw_updates(attachments=atts)
        updates = parse_updates(raw, ISSUE_ID)
        result = collect_all_attachments(updates)
        assert len(result) == 1
        assert result[0].id == 1

    def test_multiple_attachments(self):
        atts = [
            [1, "text/html", 100, "poc.html"],
            [2, "text/x-diff", 500, "patch.diff"],
        ]
        raw = make_raw_updates(attachments=atts)
        updates = parse_updates(raw, ISSUE_ID)
        result = collect_all_attachments(updates)
        assert len(result) == 2

    def test_empty_updates(self):
        assert collect_all_attachments([]) == []


# ---------------------------------------------------------------------------
# build_issue
# ---------------------------------------------------------------------------

class TestBuildIssue:
    def test_returns_none_when_no_bounty(self):
        raw_u = make_raw_updates(bounty_text="Just a regular comment.")
        raw_m = make_raw_metadata()
        result = build_issue(ISSUE_ID, raw_u, raw_m)
        assert result is None

    def test_returns_issue_when_bounty_detected(self):
        raw_u = make_raw_updates()
        raw_m = make_raw_metadata()
        issue = build_issue(ISSUE_ID, raw_u, raw_m)
        assert issue is not None
        assert issue.id == ISSUE_ID

    def test_url_constructed(self):
        raw_u = make_raw_updates()
        raw_m = make_raw_metadata()
        issue = build_issue(ISSUE_ID, raw_u, raw_m)
        assert issue.url == f"https://issues.chromium.org/issues/{ISSUE_ID}"

    def test_bounty_amount(self):
        raw_u = make_raw_updates()
        raw_m = make_raw_metadata()
        issue = build_issue(ISSUE_ID, raw_u, raw_m)
        assert issue.bounty_amount == 5000.0
        assert issue.bounty_confirmed is True

    def test_metadata_merged(self):
        raw_u = make_raw_updates()
        raw_m = make_raw_metadata(title="XSS in V8", severity=1, status=4)
        issue = build_issue(ISSUE_ID, raw_u, raw_m)
        assert issue.title == "XSS in V8"
        assert issue.severity == "S0-Critical"
        assert issue.status == "Fixed"

    def test_description_snippet_truncated(self):
        long_desc = "A" * 500
        raw_u = make_raw_updates(description=long_desc)
        raw_m = make_raw_metadata()
        issue = build_issue(ISSUE_ID, raw_u, raw_m)
        assert len(issue.description_snippet) <= 300

    def test_created_date_from_first_update(self):
        raw_u = make_raw_updates()
        raw_m = make_raw_metadata()
        issue = build_issue(ISSUE_ID, raw_u, raw_m)
        assert issue.created_date == TS_ISO

    def test_cve_ids_extracted(self):
        raw_u = make_raw_updates(description="Tracked as CVE-2024-99999.")
        raw_m = make_raw_metadata()
        issue = build_issue(ISSUE_ID, raw_u, raw_m)
        assert "CVE-2024-99999" in issue.cve_ids

    def test_bounty_from_metadata_field(self):
        """bounty_amount_meta in metadata triggers detection even without bounty text."""
        raw_u = make_raw_updates(bounty_text="No award phrase here.")
        raw_m = make_raw_metadata(bounty_amount=3000)
        issue = build_issue(ISSUE_ID, raw_u, raw_m)
        assert issue is not None
        assert issue.bounty_amount == 3000.0

    def test_title_fallback_to_description(self):
        raw_u = make_raw_updates(description="Memory corruption in audio decoder")
        raw_m = make_raw_metadata(title="Untitled")
        issue = build_issue(ISSUE_ID, raw_u, raw_m)
        assert issue.title == "Memory corruption in audio decoder"

    def test_build_issue_returns_none_when_parse_updates_raises(self):
        """build_issue must not propagate exceptions from parse_updates."""
        from unittest.mock import patch
        with patch("vrp.parser.parse_updates", side_effect=RuntimeError("API structure changed")):
            result = build_issue(ISSUE_ID, [], {})
        assert result is None

    def test_build_issue_returns_none_when_parse_metadata_raises(self):
        """build_issue must not propagate exceptions from parse_metadata."""
        from unittest.mock import patch
        with patch("vrp.parser.parse_metadata", side_effect=RuntimeError("Unexpected metadata shape")):
            result = build_issue(ISSUE_ID, make_raw_updates(), make_raw_metadata())
        assert result is None
