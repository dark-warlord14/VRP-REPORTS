"""Shared test fixtures matching the real Chromium Issue Tracker API response shapes."""

ISSUE_ID = "999000001"

# Epoch timestamp for 2024-01-15 12:00:00 UTC
TS_EPOCH = 1705320000  # 2024-01-15T12:00:00+00:00
TS_ISO = "2024-01-15T12:00:00+00:00"

BOUNTY_TEXT = (
    "Congratulations! Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5,000.00 "
    "for this report.\n\n"
    "Rationale for this decision:\nHigh severity use-after-free in renderer allowing sandbox escape.\n\n"
    "Important: Please confirm receipt of this award."
)


def make_raw_updates(
    description="Use-after-free in Blink renderer.",
    bounty_text=BOUNTY_TEXT,
    attachments=None,
    html=None,
):
    """Build a minimal raw_updates.json structure.

    Shape mirrors the real Chromium Issue Tracker API:
      raw[0][1][0] = list of update entries
      entry[0][1] = author email
      entry[1][0] = epoch timestamp
      entry[2][0] = plaintext
      entry[2][1] = attachments list (or None)
      entry[2][15][1][0][1] = HTML text
    """
    def _content(text, atts=None, html_text=None):
        # 16-element content array so index 15 is valid
        c = [text, atts] + [None] * 13
        if html_text:
            c.append([None, [[None, html_text]]])
        else:
            c.append(None)
        return c

    desc_entry = [
        [None, "reporter@example.com"],
        [TS_EPOCH],
        _content(description, attachments, html),
    ]
    bounty_entry = [
        [None, "vrp-panel@google.com"],
        [TS_EPOCH + 86400],
        _content(bounty_text),
    ]

    return [["b.ListIssueUpdatesResponse", [[desc_entry, bounty_entry]]]]


def make_raw_metadata(
    title="Use-after-free in Blink renderer",
    status=4,       # Fixed
    severity=2,     # S1-High
    priority=2,     # P1
    reporter="reporter@example.com",
    assignee="engineer@google.com",
    component="Blink",
    os_platforms="Linux, Windows",
    chrome_version="120.0.6099.62",
    bounty_amount=None,
):
    """Build a minimal raw_metadata.json structure.

    Shape mirrors real API:
      raw[0][1][22][2] = fields_array
      fields[2]=severity, [3]=status, [4]=priority, [5]=title
      fields[6][1]=reporter, [7][1]=assignee
      fields[14] = custom_fields list
    """
    from vrp.config import (
        FIELD_BOUNTY,
        FIELD_CHROME_VERSION,
        FIELD_COMPONENT,
        FIELD_OS,
    )

    custom_fields = [
        # [field_id, str_val, None, None, int_val, None, None, None, None, display_val]
        [FIELD_COMPONENT] + [None] * 8 + [component],
        [FIELD_CHROME_VERSION, chrome_version] + [None] * 8,
        [FIELD_OS] + [None] * 8 + [os_platforms],
    ]
    if bounty_amount is not None:
        row = [FIELD_BOUNTY, None, None, None, float(bounty_amount)] + [None] * 5
        custom_fields.append(row)

    fields = [
        None,           # [0]
        None,           # [1]
        severity,       # [2]
        status,         # [3]
        priority,       # [4]
        title,          # [5]
        [None, reporter],   # [6]
        [None, assignee],   # [7]
        None, None, None, None, None, None,  # [8]-[13]
        custom_fields,  # [14]
    ]

    # Pad raw[0][1] to index 22
    data = [None] * 22 + [[None, None, fields]]
    return [["b.IssueFetchResponse", data]]
