# Chromium VRP Reports

Scrapes and archives Chromium Vulnerability Reward Program (VRP) bug bounty reports from the [Chromium Issue Tracker](https://issues.chromium.org). Collects all bounty-awarded reports back to 2015, downloads all artifacts (PoC files, diffs, videos, screenshots), generates structured markdown, and provides a local dashboard for browsing everything offline.

## Features

- **Full history** — discovers all bounty-awarded reports from 2015 to present, year by year
- **Complete artifacts** — downloads real attachment filenames (`poc.html`, `browser.diff`, `demo.mp4`, ASAN logs, etc.)
- **Enriched metadata** — extracts bounty amount, severity, status, component, OS platforms, Chrome version, CVE IDs, reporter/assignee
- **Markdown export** — each report rendered as a standalone `report.md`
- **Local dashboard** — SPA with filtering, sorting, inline previews, and statistics charts
- **Offline-first** — all JS/CSS vendored; dashboard works without internet
- **CLI** — simple commands for every operation

## Quickstart

```bash
# Setup (one-time)
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Start the dashboard (230 reports already collected)
vrp serve
# Open http://localhost:8080
```

## CLI Commands

```
vrp discover [--year YEAR]   Phase 1: find issue IDs from search
vrp scrape [--id ID]         Phase 2: scrape issues and download artifacts
vrp reprocess                Re-parse existing raw JSON (no re-scraping)
vrp markdown                 Generate/regenerate all report.md files
vrp index                    Rebuild index.json + stats.json
vrp serve [--port 8080]      Start the dashboard
vrp run                      Full pipeline end to end
vrp status                   Show counts and progress
```

## Workflow

### First-time full collection (2015–present)

```bash
vrp run --no-headless   # or split into steps:
vrp discover            # finds all issue IDs by year (checkpointed)
vrp scrape              # extracts data + downloads attachments
vrp reprocess           # enrich from existing raw JSON (fast, offline)
vrp markdown            # generate report.md for all issues
vrp index               # rebuild index + stats
vrp serve               # browse the results
```

### Adding new reports

```bash
vrp discover --year 2026   # discover this year's new issues
vrp scrape                 # scrape only pending (skips already done)
vrp markdown               # generate new markdown files
vrp index                  # update index and stats
```

## Data Structure

```
data/
├── index.json               # Enriched index of all reports (sorted by date)
├── stats.json               # Precomputed analytics
├── discovery_queue.json     # All discovered issue IDs
├── discovery_{year}.json    # Per-year discovery checkpoints
└── issues/{id}/
    ├── report.json          # Enriched structured metadata
    ├── report.md            # Human-readable markdown
    ├── raw_updates.json     # Full API response (comments + history)
    ├── raw_metadata.json    # Issue metadata from API
    └── attachments/
        ├── poc.html
        ├── browser.diff
        ├── demo.mp4
        └── asan
```

### report.json schema

```json
{
  "id": "385355879",
  "url": "https://issues.chromium.org/issues/385355879",
  "title": "Use after free in AddressSignInPromoView.",
  "status": "Verified",
  "severity": "S3-Low",
  "priority": "P1",
  "component": "UI>Browser>Autofill>AddressesAndMore",
  "os_platforms": ["Linux", "Mac", "Windows"],
  "chrome_version": "133.0.6907.0",
  "cve_ids": [],
  "reporter": "ch...@gmail.com",
  "assignee": "am...@google.com",
  "created_date": "2025-01-01T18:58:01+00:00",
  "bounty_confirmed": true,
  "bounty_amount": 2000.0,
  "bounty_rationale": "$1,000 for highly mitigated memory corruption...",
  "attachments": [
    {"id": 61721871, "filename": "asan", "mime_type": "application/octet-stream", "size_bytes": 18394, "local_path": "attachments/asan"},
    {"id": 61721872, "filename": "browser.diff", "mime_type": "text/x-diff", "size_bytes": 805, "local_path": "attachments/browser.diff"}
  ],
  "update_count": 40,
  "description_snippet": "Use after free in AddressSignInPromoView..."
}
```

## Dashboard

```
http://localhost:8080/#/            Reports list (filter, sort, search)
http://localhost:8080/#/report/ID  Individual report (markdown, attachments, timeline)
http://localhost:8080/#/stats       Statistics (charts by year, severity, bounty distribution)
```

## Architecture

```
vrp/
├── config.py        Configuration, enums, year-based URL builder
├── models.py        Pydantic models: Issue, Update, Attachment, IndexEntry
├── parser.py        Structured parsing of Chromium Issue Tracker API responses
├── discovery.py     Year-by-year issue ID discovery via Playwright
├── extractor.py     Per-issue data extraction + artifact downloads
├── markdown_gen.py  Markdown report generation
├── index_builder.py Build index.json and stats.json
├── cli.py           Click CLI entry point
├── server.py        HTTP server for dashboard
└── utils.py         Logging, file I/O, download helpers

ui/
├── index.html       SPA shell
├── css/             PicoCSS (vendored) + custom styles
└── js/
    ├── app.js       Router, list/report/stats views
    ├── components.js Reusable UI components
    └── vendor/      markdown-it, Chart.js (vendored)
```

## Configuration

All defaults can be overridden with environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `VRP_CONCURRENCY` | `5` | Parallel browser tabs |
| `VRP_HEADLESS` | `true` | Run browser headless |
| `VRP_TIMEOUT` | `60000` | Page load timeout (ms) |
| `VRP_DELAY` | `2` | Delay between issues (seconds) |
| `VRP_BROWSER_RESTART` | `100` | Restart browser every N issues |
