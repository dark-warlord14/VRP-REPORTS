---
name: chromium-vrp-reports
description: Query the Chromium VRP bug bounty archive — find vulnerability reports by year, severity, component, or bounty amount, and fetch full writeups. Use for security research, learning from real Chromium vulns, or trend analysis of browser bug bounties.
---

# Chromium VRP Reports

Static JSON archive of Chromium Vulnerability Reward Program reports. Served from Cloudflare CDN, no auth, CORS-enabled.

Base URL: `https://vrp-reports.pages.dev`

## When to use

- User asks about a specific Chromium CVE, bug ID, or bounty writeup.
- User wants to learn about real browser vulnerabilities (renderer bugs, sandbox escapes, UAFs, etc.).
- User wants stats/trends on Chromium bounties (biggest payouts, severity distribution, component hotspots).

## Endpoints

| URL | Purpose |
|-----|---------|
| `/data/index.json` | Array of all reports with summary fields. Fetch once, filter client-side. |
| `/data/stats.json` | Pre-computed aggregates (totals, histograms, top bounties). |
| `/data/issues/<id>/report.json` | Full structured report for one issue. |
| `/data/issues/<id>/report.md` | Markdown writeup (best for LLM context). |
| `/schema.json` | JSON Schema for `report.json`. |

## Index entry shape

```json
{
  "id": "324930013",
  "title": "monorail: issue chart page leaks unredacted emails",
  "url": "https://issues.chromium.org/issues/324930013",
  "status": "Assigned",
  "severity": "S3-Low",
  "component": "Issue Tracker, Platform>DevTools",
  "bounty_amount": 500.0,
  "created_date": "2024-02-13T04:02:41+00:00",
  "year": 2024,
  "attachment_count": 3,
  "local_path": "issues/324930013",
  "has_markdown": true
}
```

Severity values: `S0-Critical`, `S1-High`, `S2-Medium`, `S3-Low`, `Unknown`.

## Recipe: find matching reports

```python
import httpx

index = httpx.get("https://vrp-reports.pages.dev/data/index.json").json()

# Example: all critical 2024 bounties ≥ $20K
matches = [
    e for e in index
    if e["year"] == 2024
    and e["severity"] == "S0-Critical"
    and (e["bounty_amount"] or 0) >= 20000
]

# Fetch full markdown for top 3
for e in matches[:3]:
    md = httpx.get(f"https://vrp-reports.pages.dev/data/issues/{e['id']}/report.md").text
    print(md)
```

## Recipe: component hotspots

```python
stats = httpx.get("https://vrp-reports.pages.dev/data/stats.json").json()
top_components = stats["by_component"]   # already sorted, top 20
top_payouts = stats["top_bounties"]      # top 20 bounty amounts
```

## Notes for agents

- `index.json` is ~900KB; fetch once per session and cache.
- Fields may be `null` for older reports (e.g. `chrome_version`, `bounty_rationale`).
- Full `report.json` includes `attachments[]` (metadata only — attachment files aren't on the CDN, only linked back to the original Chromium issue tracker).
- No search endpoint exists. All filtering is client-side against `index.json`.
