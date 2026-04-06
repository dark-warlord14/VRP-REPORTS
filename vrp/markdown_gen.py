"""Generate Markdown reports from parsed issue data."""


from markdownify import markdownify as md

from vrp.config import ISSUES_DIR
from vrp.parser import parse_updates
from vrp.utils import create_progress, load_json, logger


def _html_to_md(html: str) -> str:
    """Convert HTML to clean markdown."""
    try:
        result = md(html, heading_style="ATX", bullets="-", strip=["img"])
        return result.strip()
    except Exception:
        return html


def _format_size(size_bytes: int) -> str:
    """Format file size for display."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def generate_report_markdown(issue_id: str) -> bool:
    """Generate report.md for a single issue.

    Reads report.json and raw_updates.json, produces a clean markdown file.
    Returns True on success.
    """
    idir = ISSUES_DIR / issue_id
    report = load_json(idir / "report.json")
    raw_updates = load_json(idir / "raw_updates.json")

    if not report:
        return False

    lines = []

    # Title
    title = report.get("title", "Untitled")
    lines.append(f"# {title}")
    lines.append("")

    # Metadata table
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| **Issue ID** | [{issue_id}]({report.get('url', '')}) |")
    lines.append(f"| **Status** | {report.get('status', 'Unknown')} |")
    lines.append(f"| **Severity** | {report.get('severity', 'Unknown')} |")
    lines.append(f"| **Priority** | {report.get('priority', 'Unknown')} |")
    lines.append(f"| **Component** | {report.get('component', 'Unknown')} |")

    if report.get("os_platforms"):
        lines.append(f"| **Platforms** | {', '.join(report['os_platforms'])} |")
    if report.get("chrome_version"):
        lines.append(f"| **Chrome Version** | {report['chrome_version']} |")
    if report.get("cve_ids"):
        lines.append(f"| **CVE IDs** | {', '.join(report['cve_ids'])} |")

    lines.append(f"| **Reporter** | {report.get('reporter', 'Unknown')} |")
    if report.get("assignee"):
        lines.append(f"| **Assignee** | {report['assignee']} |")
    if report.get("created_date"):
        lines.append(f"| **Created** | {report['created_date'][:10]} |")

    bounty_amount = report.get("bounty_amount")
    if bounty_amount:
        lines.append(f"| **Bounty** | ${bounty_amount:,.2f} |")
    else:
        lines.append("| **Bounty** | Confirmed (amount unknown) |")

    lines.append("")

    # Parse updates once and reuse for both description and timeline
    updates = parse_updates(raw_updates, issue_id) if raw_updates else []

    # Description
    lines.append("## Description")
    lines.append("")

    if updates and updates[0].text_plain:
        # Prefer HTML conversion if available
        if updates[0].text_html:
            desc_md = _html_to_md(updates[0].text_html)
        else:
            desc_md = updates[0].text_plain
        lines.append(desc_md)
    else:
        snippet = report.get("description_snippet", "")
        lines.append(snippet or "*No description available.*")

    lines.append("")

    # Attachments
    attachments = report.get("attachments", [])
    if attachments:
        lines.append("## Attachments")
        lines.append("")
        for att in attachments:
            fname = att.get("filename", "unknown")
            mime = att.get("mime_type", "")
            size = _format_size(att.get("size_bytes", 0))
            local = att.get("local_path", "")
            if local:
                lines.append(f"- [{fname}]({local}) ({mime}, {size})")
            else:
                lines.append(f"- {fname} ({mime}, {size})")
        lines.append("")

    # Timeline / Comments
    if updates:
        comments = [u for u in updates[1:] if u.text_plain.strip()]
        if comments:
            lines.append("## Timeline")
            lines.append("")
            for u in comments:
                ts = u.timestamp[:10] if u.timestamp else "Unknown date"
                lines.append(f"### {u.author} ({ts})")
                lines.append("")
                if u.text_html:
                    lines.append(_html_to_md(u.text_html))
                else:
                    lines.append(u.text_plain)
                lines.append("")

    # Bounty Award
    rationale = report.get("bounty_rationale")
    if rationale:
        lines.append("## Bounty Award")
        lines.append("")
        for line in rationale.split("\n"):
            lines.append(f"> {line}")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Data from [Chromium Issue Tracker]({report.get('url', '')})*")
    lines.append("")

    # Write
    md_path = idir / "report.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return True


def generate_all_markdown(force: bool = False) -> int:
    """Generate report.md for all issues that have report.json.

    Skips issues where report.md already exists and is newer than report.json,
    unless force=True.

    Returns count of generated (or regenerated) files.
    """
    if not ISSUES_DIR.exists():
        logger.error("No issues directory found.")
        return 0

    issue_dirs = sorted([d for d in ISSUES_DIR.iterdir() if d.is_dir()])
    logger.info(f"Generating markdown for {len(issue_dirs)} issues...")

    count = 0
    with create_progress() as progress:
        task = progress.add_task("Generating markdown", total=len(issue_dirs))

        for idir in issue_dirs:
            json_path = idir / "report.json"
            md_path = idir / "report.md"

            if not json_path.exists():
                progress.update(task, advance=1)
                continue

            if not force and md_path.exists():
                if md_path.stat().st_mtime >= json_path.stat().st_mtime:
                    progress.update(task, advance=1)
                    continue

            if generate_report_markdown(idir.name):
                count += 1
            progress.update(task, advance=1)

    logger.info(f"Generated {count} markdown files")
    return count
