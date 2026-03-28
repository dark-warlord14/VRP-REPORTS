"""Structured parser for Google Issue Tracker API responses.

Parses the protobuf-like JSON from raw_updates.json and raw_metadata.json
into clean Python objects.
"""

import re
from datetime import datetime, timezone
from typing import Any, Optional

from vrp.config import (
    BOUNTY_AWARD_PATTERN, BOUNTY_INDICATORS, STATUS_MAP, SEVERITY_MAP,
    PRIORITY_MAP, FIELD_COMPONENT, FIELD_CHROME_VERSION, FIELD_OS, FIELD_BOUNTY,
)
from vrp.models import Attachment, Update, Issue


def safe_get(data: Any, *indices, default=None) -> Any:
    """Safely traverse nested arrays/dicts."""
    current = data
    for idx in indices:
        try:
            if current is None:
                return default
            if isinstance(idx, int) and isinstance(current, list):
                if idx < len(current):
                    current = current[idx]
                else:
                    return default
            elif isinstance(idx, str) and isinstance(current, dict):
                current = current.get(idx, default)
            else:
                return default
        except (IndexError, KeyError, TypeError):
            return default
    return current


def _epoch_to_iso(epoch_seconds: int) -> str:
    """Convert epoch seconds to ISO datetime string."""
    try:
        return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()
    except (ValueError, OSError, OverflowError):
        return ""


def _parse_attachment_entry(entry: list, issue_id: str) -> Optional[Attachment]:
    """Parse a single attachment array from the updates response."""
    if not isinstance(entry, list) or len(entry) < 4:
        return None
    att_id = entry[0]
    if not isinstance(att_id, int):
        return None
    return Attachment(
        id=att_id,
        filename=entry[3] if isinstance(entry[3], str) else f"file_{att_id}",
        mime_type=entry[1] if isinstance(entry[1], str) else "application/octet-stream",
        size_bytes=entry[2] if isinstance(entry[2], int) else 0,
        url=f"https://issues.chromium.org/action/issues/{issue_id}/attachments/{att_id}?download=true",
        local_path=None,
    )


def parse_updates(raw: Any, issue_id: str = "") -> list[Update]:
    """Parse raw_updates.json into structured Update objects.

    Structure: [["b.ListIssueUpdatesResponse", [updates_list]]]
    Each update: [author_arr, timestamp_arr, content_arr, ...]
      - author_arr[1] = email
      - timestamp_arr[0] = epoch seconds
      - content_arr[0] = plaintext
      - content_arr[1] = list of attachment arrays (or None)
      - content_arr[15][1][0][1] = HTML text (when available)
    """
    updates_list = safe_get(raw, 0, 1, 0, default=[])
    if not isinstance(updates_list, list):
        return []

    results = []
    for idx, entry in enumerate(updates_list):
        if not isinstance(entry, list):
            continue

        # Author
        author = safe_get(entry, 0, 1, default="Unknown")
        if not isinstance(author, str):
            author = "Unknown"

        # Timestamp
        epoch = safe_get(entry, 1, 0, default=None)
        ts_iso = _epoch_to_iso(epoch) if isinstance(epoch, (int, float)) else None

        # Content
        content = safe_get(entry, 2, default=None)
        text_plain = ""
        text_html = None
        attachments = []

        if isinstance(content, list) and len(content) > 0:
            # Plaintext
            text_plain = content[0] if isinstance(content[0], str) else ""

            # Attachments at content[1]
            att_list = safe_get(content, 1, default=None)
            if isinstance(att_list, list):
                for att_entry in att_list:
                    att = _parse_attachment_entry(att_entry, issue_id)
                    if att:
                        attachments.append(att)

            # HTML at content[15][1][0][1]
            html = safe_get(content, 15, 1, 0, 1, default=None)
            if isinstance(html, str) and html.strip():
                text_html = html

        # Detect bounty award
        is_bounty = any(
            indicator.lower() in text_plain.lower()
            for indicator in BOUNTY_INDICATORS
        ) if text_plain else False

        results.append(Update(
            index=idx,
            author=author,
            timestamp=ts_iso,
            text_plain=text_plain,
            text_html=text_html,
            attachments=attachments,
            is_description=(idx == 0 and bool(text_plain)),
            is_bounty_award=is_bounty,
        ))

    return results


def parse_metadata(raw: Any) -> dict:
    """Parse raw_metadata.json into a flat dict of fields.

    Structure: [["b.IssueFetchResponse", [nulls..., data_at_index_22]]]
      data_at_index_22 = [null, issue_id, fields_array]
      fields_array[2] = severity (int), [3] = status (int), [4] = priority (int)
      fields_array[5] = title, [6][1] = reporter, [7][1] = assignee
      fields_array[14] = custom fields list
    """
    fields = safe_get(raw, 0, 1, 22, 2, default=None)
    if not isinstance(fields, list):
        return {}

    result = {
        "title": safe_get(fields, 5, default="Untitled"),
        "status": STATUS_MAP.get(safe_get(fields, 3, default=0), "Unknown"),
        "severity": SEVERITY_MAP.get(safe_get(fields, 2, default=0), "Unknown"),
        "priority": PRIORITY_MAP.get(safe_get(fields, 4, default=0), "Unknown"),
        "reporter": safe_get(fields, 6, 1, default="Unknown"),
        "assignee": safe_get(fields, 7, 1, default=None),
    }

    # Parse custom fields
    custom_fields = safe_get(fields, 14, default=[])
    if isinstance(custom_fields, list):
        for cf in custom_fields:
            if not isinstance(cf, list) or len(cf) < 2:
                continue
            field_id = cf[0]
            display_val = safe_get(cf, 9, default=None)
            int_val = safe_get(cf, 4, default=None)
            str_val = safe_get(cf, 1, default=None)

            if field_id == FIELD_COMPONENT:
                result["component"] = display_val or "Unknown"
            elif field_id == FIELD_CHROME_VERSION:
                result["chrome_version"] = str_val or display_val
            elif field_id == FIELD_OS:
                os_str = display_val or ""
                result["os_platforms"] = [
                    s.strip() for s in os_str.split(",") if s.strip()
                ]
            elif field_id == FIELD_BOUNTY:
                if isinstance(int_val, (int, float)):
                    result["bounty_amount_meta"] = float(int_val)

    return result


def extract_bounty_info(updates: list[Update]) -> tuple[bool, Optional[float], Optional[str]]:
    """Extract bounty confirmation, amount, and rationale from updates."""
    for update in updates:
        if not update.is_bounty_award:
            continue

        # Extract dollar amount
        match = BOUNTY_AWARD_PATTERN.search(update.text_plain)
        amount = None
        if match:
            amount = float(match.group(1).replace(",", ""))

        # Extract rationale (text between "Rationale for this decision:" and "Important:")
        rationale = None
        text = update.text_plain
        rat_start = text.find("Rationale for this decision:")
        if rat_start != -1:
            rat_text = text[rat_start + len("Rationale for this decision:"):]
            rat_end = rat_text.find("Important:")
            if rat_end == -1:
                rat_end = rat_text.find("\n\n\n")
            if rat_end != -1:
                rationale = rat_text[:rat_end].strip()
            else:
                rationale = rat_text[:500].strip()

        return True, amount, rationale

    return False, None, None


def extract_cve_ids(updates: list[Update]) -> list[str]:
    """Extract CVE IDs from all update text."""
    cve_pattern = re.compile(r'CVE-\d{4}-\d{4,}')
    cves = set()
    for update in updates:
        if update.text_plain:
            cves.update(cve_pattern.findall(update.text_plain))
    return sorted(cves)


def collect_all_attachments(updates: list[Update]) -> list[Attachment]:
    """Collect all unique attachments across all updates."""
    seen_ids = set()
    attachments = []
    for update in updates:
        for att in update.attachments:
            if att.id not in seen_ids:
                seen_ids.add(att.id)
                attachments.append(att)
    return attachments


def build_issue(issue_id: str, raw_updates: Any, raw_metadata: Any) -> Optional[Issue]:
    """Build a complete Issue from raw API responses.

    Returns None if no bounty was detected.
    """
    updates = parse_updates(raw_updates, issue_id)
    metadata = parse_metadata(raw_metadata)

    bounty_confirmed, bounty_amount, bounty_rationale = extract_bounty_info(updates)

    # Also check metadata for bounty amount
    meta_amount = metadata.get("bounty_amount_meta")
    if meta_amount and not bounty_amount:
        bounty_amount = meta_amount
        bounty_confirmed = True

    if not bounty_confirmed and not meta_amount:
        return None

    # Collect attachments
    attachments = collect_all_attachments(updates)

    # Created date from first update timestamp
    created_date = None
    if updates:
        created_date = updates[0].timestamp

    # Modified date from last update
    modified_date = None
    if updates:
        for u in reversed(updates):
            if u.timestamp:
                modified_date = u.timestamp
                break

    # Description snippet
    description = ""
    if updates and updates[0].text_plain:
        description = updates[0].text_plain[:300].strip()

    cve_ids = extract_cve_ids(updates)

    title = metadata.get("title", "Untitled")
    if not title or title == "Untitled":
        # Fallback: try to find title from description
        if description:
            first_line = description.split("\n")[0].strip("# ").strip()
            if first_line:
                title = first_line[:120]

    return Issue(
        id=issue_id,
        url=f"https://issues.chromium.org/issues/{issue_id}",
        title=title,
        status=metadata.get("status", "Unknown"),
        severity=metadata.get("severity", "Unknown"),
        priority=metadata.get("priority", "Unknown"),
        component=metadata.get("component", "Unknown"),
        os_platforms=metadata.get("os_platforms", []),
        chrome_version=metadata.get("chrome_version"),
        cve_ids=cve_ids,
        reporter=metadata.get("reporter", "Unknown"),
        assignee=metadata.get("assignee"),
        created_date=created_date,
        modified_date=modified_date,
        bounty_confirmed=True,
        bounty_amount=bounty_amount or meta_amount,
        bounty_rationale=bounty_rationale,
        attachments=attachments,
        update_count=len(updates),
        description_snippet=description,
    )
