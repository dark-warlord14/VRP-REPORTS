# VRP Reports — Claude Code Guide

## What this project does
Scrapes Chromium Vulnerability Reward Program (VRP) bug bounty reports from the Chromium Issue Tracker, processes them into structured JSON/Markdown, and serves a local SPA dashboard.

## Setup
```bash
pip install -e ".[dev]" && playwright install chromium
```

## Common commands
```bash
make test          # run all tests
make lint          # ruff linter
make format        # ruff formatter
vrp run            # run full pipeline (discover → scrape → reprocess → markdown → index)
vrp serve          # start dashboard at http://localhost:8080
vrp status         # show current project state
```

## Pipeline stages (internal, all run via `vrp run`)
1. discover — finds issue IDs from Chromium Issue Tracker (year-by-year, checkpointed)
2. scrape — scrapes each issue with Playwright, downloads attachments
3. reprocess — re-parses raw JSON without re-scraping (offline)
4. markdown — generates report.md for each issue
5. index — builds index.json + stats.json

## Key directories
- `vrp/` — Python package (source)
- `tests/` — pytest test suite (all browser interactions are mocked)
- `ui/` — frontend SPA (HTML/CSS/JS, vendored Chart.js + markdown-it)
- `data/` — gitignored runtime data; lives on separate `data` branch in CI

## Configuration
All scraper settings are in `vrp/config.py` and overridable via env vars. See `.env.example`.

## Test patterns
- Tests use `unittest.mock.patch` to redirect `vrp.config.*` paths to temp directories
- No Playwright install needed to run tests — browser interactions are mocked
- `tests/fixtures.py` has helpers for building fake API response structures
