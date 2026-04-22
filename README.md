# Chromium VRP Reports

Scrapes and archives Chromium Vulnerability Reward Program (VRP) bug bounty reports from the [Chromium Issue Tracker](https://issues.chromium.org). Collects all bounty-awarded reports back to 2015, downloads all artifacts (PoC files, diffs, videos, screenshots), generates structured markdown, and provides a local dashboard for browsing everything offline.

**Live site:** https://vrp-reports.pages.dev/ — editorial archive, agent-accessible via [`/skill.md`](https://vrp-reports.pages.dev/skill.md), [`/schema.json`](https://vrp-reports.pages.dev/schema.json), [`/llms.txt`](https://vrp-reports.pages.dev/llms.txt).

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
playwright install chromium   # download browser binary (required)

# Start the dashboard (if data/ is already populated)
vrp serve
# Open http://localhost:8080
```

## CLI Commands

```
vrp run [--no-headless]  Full pipeline: discover → scrape → reprocess → markdown → index.
vrp serve [--port N]     Start the dashboard (default port: 8080).
vrp status               Show current counts and per-year discovery progress.
```

## Workflow

### First-time full collection (2015–present)

```bash
vrp run             # full pipeline (checkpointed — safe to re-run)
vrp serve           # browse the results at http://localhost:8080
```

### Adding new reports

```bash
vrp run             # discovers and scrapes new issues, skips already-done ones
vrp serve           # updated dashboard
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
├── index.html       SPA shell (Fraunces + JetBrains Mono from Google Fonts)
├── css/app.css      Editorial design system — tokens, dark/light themes
├── skill.md         Agent usage guide (exposed at /skill.md)
├── schema.json      JSON Schema for report.json (exposed at /schema.json)
├── llms.txt         Site manifest for LLM discoverability (exposed at /llms.txt)
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

## Testing

Install dev dependencies, then run the test suite:

```bash
pip install -e ".[dev]"
pytest tests/ -v
# or: make test
```

All tests run offline — no Playwright install or scraped data required.

## Contributing

1. Fork and create a branch
2. `make lint` and `make test` must pass
3. Open a PR against `main`

## Deployment

Deploys to Cloudflare Pages via `.github/workflows/deploy.yml` (manual dispatch or push to `main` touching `ui/**` or `build.sh`). Two-branch layout:

- `main` — source code + UI
- `data` — scraped output (`index.json`, `stats.json`, per-issue `report.json`/`report.md`)

`build.sh` checks out both branches, assembles `dist/`, and `wrangler pages deploy` publishes it. Scraping runs locally (CI scraping is blocked by bot detection on Azure IPs) — push the lightweight files to the `data` branch, then trigger the deploy workflow.

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the full flow, secrets setup, and token rotation.
