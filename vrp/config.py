"""Configuration for VRP Reports scraper."""

import os
import re
from datetime import datetime
from pathlib import Path

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ISSUES_DIR = DATA_DIR / "issues"
INDEX_FILE = DATA_DIR / "index.json"
STATS_FILE = DATA_DIR / "stats.json"
QUEUE_FILE = DATA_DIR / "discovery_queue.json"
UI_DIR = PROJECT_ROOT / "ui"

# --- Search ---
BASE_SEARCH_TEMPLATE = (
    "https://issues.chromium.org/issues?q="
    "Type:Vulnerability"
    "%20-status:infeasible"
    "%20-status:not_reproducible"
    "%20-status:intended_behavior"
    "%20-status:obsolete"
    "%20-status:duplicate"
    "%20created%3E{start_date}"
    "%20created%3C{end_date}"
)
SEARCH_SORT = "&s=modified_time:desc"
MAX_SEARCH_PAGES = 200


def build_search_url(year: int) -> str:
    """Build search URL for a specific year."""
    start = f"{year}-01-01"
    end = f"{year + 1}-01-01"
    return BASE_SEARCH_TEMPLATE.format(start_date=start, end_date=end) + SEARCH_SORT


def get_all_years() -> list[int]:
    """Get list of years from 2015 to current year."""
    return list(range(2015, datetime.now().year + 1))


# --- Bounty Detection ---
BOUNTY_AWARD_PATTERN = re.compile(
    r'award you \$([\d,]+(?:\.\d+)?)', re.IGNORECASE
)
BOUNTY_INDICATORS = [
    "decided to award you",
    "Chrome Vulnerability Rewards Program (VRP) Panel",
    "Congratulations!",
    "VRP Panel has decided",
    "award you $",
]

# --- Enum Mappings ---
STATUS_MAP = {
    1: "New",
    2: "Assigned",
    3: "Accepted",
    4: "Fixed",
    5: "Verified",
    6: "Not Reproducible",
    7: "Infeasible",
    8: "Intended Behavior",
    9: "Obsolete",
    10: "Duplicate",
}

SEVERITY_MAP = {
    0: "Unspecified",
    1: "S0-Critical",
    2: "S1-High",
    3: "S2-Medium",
    4: "S3-Low",
    5: "S4-Minimal",
}

PRIORITY_MAP = {
    0: "Unspecified",
    1: "P0",
    2: "P1",
    3: "P2",
    4: "P3",
    5: "P4",
}

# --- Custom Field IDs (from Chromium Issue Tracker) ---
FIELD_COMPONENT = 1222907
FIELD_CHROME_VERSION = 1223033
FIELD_OS = 1223084
FIELD_BOUNTY = 1223135

# --- Scraper Settings (env var overrides) ---
CONCURRENCY_LIMIT = int(os.environ.get("VRP_CONCURRENCY", "5"))
HEADLESS = os.environ.get("VRP_HEADLESS", "true").lower() == "true"
TIMEOUT = int(os.environ.get("VRP_TIMEOUT", "60000"))
DELAY_BETWEEN_ISSUES = float(os.environ.get("VRP_DELAY", "2"))
BROWSER_RESTART_INTERVAL = int(os.environ.get("VRP_BROWSER_RESTART", "100"))

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
