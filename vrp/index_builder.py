"""Build index.json and stats.json from all report data."""

from collections import Counter, defaultdict
from pathlib import Path

from vrp.config import ISSUES_DIR, INDEX_FILE, STATS_FILE
from vrp.utils import logger, load_json, save_json, create_progress


def rebuild_index() -> int:
    """Scan all issue directories and build index.json.

    Returns count of indexed reports.
    """
    if not ISSUES_DIR.exists():
        logger.error("No issues directory found.")
        return 0

    issue_dirs = sorted([d for d in ISSUES_DIR.iterdir() if d.is_dir()])
    index = []

    with create_progress() as progress:
        task = progress.add_task("Building index", total=len(issue_dirs))

        for idir in issue_dirs:
            report = load_json(idir / "report.json")
            if report and report.get("bounty_confirmed"):
                # Extract year from created_date
                year = None
                created = report.get("created_date")
                if created and len(created) >= 4:
                    try:
                        year = int(created[:4])
                    except ValueError:
                        pass

                entry = {
                    "id": report["id"],
                    "title": report.get("title", "Untitled"),
                    "url": report.get("url", ""),
                    "status": report.get("status", "Unknown"),
                    "severity": report.get("severity", "Unknown"),
                    "component": report.get("component", "Unknown"),
                    "bounty_amount": report.get("bounty_amount"),
                    "created_date": created,
                    "year": year,
                    "attachment_count": len(report.get("attachments", [])),
                    "local_path": f"issues/{report['id']}",
                    "has_markdown": (idir / "report.md").exists(),
                }
                index.append(entry)

            progress.update(task, advance=1)

    # Sort by created_date descending (newest first)
    index.sort(key=lambda x: x.get("created_date") or "", reverse=True)

    save_json(INDEX_FILE, index)
    logger.info(f"Index built: {len(index)} reports")
    return len(index)


def build_stats() -> dict:
    """Compute analytics from index.json and save to stats.json."""
    index = load_json(INDEX_FILE)
    if not index:
        logger.error("No index.json found. Run 'vrp index' first.")
        return {}

    stats = {
        "total_reports": len(index),
        "total_bounty": 0.0,
        "avg_bounty": 0.0,
        "by_year": {},
        "by_severity": {},
        "by_status": {},
        "by_component": {},
        "bounty_histogram": [],
        "top_bounties": [],
    }

    # Aggregate
    year_counts = defaultdict(lambda: {"count": 0, "total_bounty": 0.0})
    severity_counts = Counter()
    status_counts = Counter()
    component_counts = Counter()
    bounty_amounts = []

    for entry in index:
        raw_amount = entry.get("bounty_amount")
        amount = raw_amount if raw_amount is not None else 0.0
        stats["total_bounty"] += amount
        if raw_amount is not None:
            bounty_amounts.append(raw_amount)

        year = entry.get("year")
        if year:
            year_counts[year]["count"] += 1
            year_counts[year]["total_bounty"] += amount

        severity_counts[entry.get("severity", "Unknown")] += 1
        status_counts[entry.get("status", "Unknown")] += 1

        comp = entry.get("component", "Unknown")
        # Use top-level component only
        top_comp = comp.split(">")[0].strip() if ">" in comp else comp
        component_counts[top_comp] += 1

    if bounty_amounts:
        stats["avg_bounty"] = round(stats["total_bounty"] / len(bounty_amounts), 2)

    # By year (sorted)
    stats["by_year"] = {
        str(y): year_counts[y]
        for y in sorted(year_counts.keys())
    }

    # By severity
    stats["by_severity"] = dict(severity_counts.most_common())

    # By status
    stats["by_status"] = dict(status_counts.most_common())

    # By component (top 20)
    stats["by_component"] = dict(component_counts.most_common(20))

    # Bounty histogram
    buckets = [
        ("$0-500", 0, 500),
        ("$500-1K", 500, 1000),
        ("$1K-3K", 1000, 3000),
        ("$3K-5K", 3000, 5000),
        ("$5K-10K", 5000, 10000),
        ("$10K-20K", 10000, 20000),
        ("$20K+", 20000, float("inf")),
    ]
    histogram = []
    for label, lo, hi in buckets:
        count = sum(1 for a in bounty_amounts if lo <= a < hi)
        histogram.append({"range": label, "count": count})
    stats["bounty_histogram"] = histogram

    # Top bounties
    top = sorted(index, key=lambda x: x.get("bounty_amount") if x.get("bounty_amount") is not None else -1, reverse=True)[:20]
    stats["top_bounties"] = [
        {
            "id": e["id"],
            "title": e["title"],
            "bounty_amount": e.get("bounty_amount"),
            "severity": e.get("severity"),
            "year": e.get("year"),
        }
        for e in top
    ]

    stats["total_bounty"] = round(stats["total_bounty"], 2)

    save_json(STATS_FILE, stats)
    logger.info(
        f"Stats built: {stats['total_reports']} reports, "
        f"${stats['total_bounty']:,.2f} total bounty"
    )
    return stats
