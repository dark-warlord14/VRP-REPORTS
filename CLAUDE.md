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
make serve         # start dashboard at http://localhost:8080
make build         # build static dist/ for Cloudflare Pages
```

## Pipeline stages
1. `vrp discover` — finds issue IDs from Chromium Issue Tracker (year-by-year, checkpointed)
2. `vrp scrape` — scrapes each issue with Playwright, downloads attachments
3. `vrp reprocess` — re-parses raw JSON without re-scraping (offline)
4. `vrp markdown` — generates report.md for each issue
5. `vrp index` — builds index.json + stats.json
6. `vrp serve` — serves the SPA dashboard
7. `vrp run` — runs all stages end-to-end

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
