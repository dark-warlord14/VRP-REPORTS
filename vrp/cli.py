"""CLI interface for VRP Reports."""

import asyncio

import click
from rich.console import Console
from rich.table import Table

from vrp.config import DATA_DIR, INDEX_FILE, ISSUES_DIR, QUEUE_FILE
from vrp.utils import load_json

console = Console()


@click.group()
@click.version_option(package_name="vrp-reports")
def cli():
    """Chromium VRP Bug Bounty Reports - Scraper & Dashboard."""
    # Create data directories on first use (deferred from config import)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ISSUES_DIR.mkdir(parents=True, exist_ok=True)


@cli.command()
@click.option("--year", type=int, help="Discover for a specific year only")
@click.option("--no-resume", is_flag=True, help="Re-run discovery even for cached years")
@click.option("--no-headless", is_flag=True, help="Show browser window")
def discover(year, no_resume, no_headless):
    """Phase 1: Discover issue IDs from search results."""
    from vrp.discovery import discover_all

    years = [year] if year else None
    result = asyncio.run(
        discover_all(years=years, resume=not no_resume, headless=not no_headless)
    )
    console.print(f"[green]Discovery complete: {len(result)} total IDs in queue[/green]")


@cli.command()
@click.option("--id", "issue_id", help="Scrape a single issue by ID")
@click.option("--force", is_flag=True, help="Re-scrape even if already processed")
@click.option("--no-headless", is_flag=True, help="Show browser window")
def scrape(issue_id, force, no_headless):
    """Phase 2: Extract data from discovered issues."""
    from vrp.extractor import scrape_all

    ids = [issue_id] if issue_id else None
    count = asyncio.run(scrape_all(issue_ids=ids, force=force, headless=not no_headless))
    console.print(f"[green]Scraping complete: {count} bounty reports found[/green]")


@cli.command()
def reprocess():
    """Re-parse existing raw JSON into enriched report.json (no re-scraping)."""
    from vrp.extractor import reprocess_existing

    count = reprocess_existing()
    console.print(f"[green]Reprocessed {count} reports[/green]")


@cli.command()
@click.option("--force", is_flag=True, help="Regenerate all markdown even if already up-to-date")
def markdown(force):
    """Generate/regenerate markdown for all reports."""
    from vrp.markdown_gen import generate_all_markdown

    count = generate_all_markdown(force=force)
    console.print(f"[green]Generated {count} markdown files[/green]")


@cli.command()
def index():
    """Rebuild index.json and stats.json."""
    from vrp.index_builder import build_stats, rebuild_index

    count = rebuild_index()
    stats = build_stats()
    console.print(f"[green]Index: {count} reports | Total bounty: ${stats.get('total_bounty', 0):,.2f}[/green]")


@cli.command()
@click.option("--port", default=8080, help="Port to serve on")
def serve(port):
    """Start the dashboard HTTP server."""
    from vrp.server import run_server

    run_server(port=port)


@cli.command()
@click.option("--no-headless", is_flag=True, help="Show browser window")
def run(no_headless):
    """Full pipeline: discover -> scrape -> reprocess -> markdown -> index."""
    from vrp.discovery import discover_all
    from vrp.extractor import reprocess_existing, scrape_all
    from vrp.index_builder import build_stats, rebuild_index
    from vrp.markdown_gen import generate_all_markdown

    headless = not no_headless

    try:
        console.print("[bold]Step 1/5: Discovery[/bold]")
        ids = asyncio.run(discover_all(headless=headless))
        console.print(f"  -> {len(ids)} issue IDs")
    except Exception as e:
        console.print(f"[red]Discovery failed: {e}[/red]")
        raise SystemExit(1)

    try:
        console.print("[bold]Step 2/5: Scraping[/bold]")
        bounty_count = asyncio.run(scrape_all(headless=headless))
        console.print(f"  -> {bounty_count} new bounty reports")
    except Exception as e:
        console.print(f"[red]Scraping failed: {e}[/red]")
        raise SystemExit(1)

    console.print("[bold]Step 3/5: Reprocessing[/bold]")
    reprocess_existing()

    console.print("[bold]Step 4/5: Markdown generation[/bold]")
    generate_all_markdown()

    console.print("[bold]Step 5/5: Building index & stats[/bold]")
    count = rebuild_index()
    stats = build_stats()

    console.print("\n[bold green]Pipeline complete![/bold green]")
    console.print(f"  Reports: {count}")
    console.print(f"  Total bounty: ${stats.get('total_bounty', 0):,.2f}")


@cli.command()
def status():
    """Show current project status."""
    # Count issues with report.json
    report_count = 0
    md_count = 0
    raw_count = 0

    if ISSUES_DIR.exists():
        for d in ISSUES_DIR.iterdir():
            if d.is_dir():
                if (d / "report.json").exists():
                    report_count += 1
                if (d / "report.md").exists():
                    md_count += 1
                if (d / "raw_updates.json").exists():
                    raw_count += 1

    # Queue info
    queue = load_json(QUEUE_FILE) or []

    # Index info
    index = load_json(INDEX_FILE) or []

    # Discovery checkpoints
    checkpoints = list(DATA_DIR.glob("discovery_*.json"))
    years_discovered = []
    for cp in checkpoints:
        year = cp.stem.replace("discovery_", "")
        data = load_json(cp) or []
        years_discovered.append((year, len(data)))

    table = Table(title="VRP Reports Status")
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="green")

    table.add_row("Discovery queue", str(len(queue)))
    table.add_row("Raw data (scraped)", str(raw_count))
    table.add_row("Enriched reports", str(report_count))
    table.add_row("Markdown files", str(md_count))
    table.add_row("Index entries", str(len(index)))

    if years_discovered:
        years_str = ", ".join(f"{y}({c})" for y, c in sorted(years_discovered))
        table.add_row("Discovery checkpoints", years_str)

    console.print(table)


if __name__ == "__main__":
    cli()
