import os

# --- CONFIGURATION ---
# Target: Reports created on or after 2025-01-01
BASE_SEARCH_URL = "https://issues.chromium.org/issues?q=Type:Vulnerability%20-status:infeasible%20-status:not_reproducible%20-status:intended_behavior%20-status:obsolete%20-status:duplicate%20created%3E2024-12-31"
SEARCH_SORT = "&s=modified_time:desc"

# Directory Structure
DATA_DIR = "data"
ISSUES_DIR = "data/issues"
INDEX_FILE = "data/index.json"
QUEUE_FILE = "data/discovery_queue.json"

# Heuristic keywords for bounty/rewards
BOUNTY_KEYWORDS = [
    "reward", "bounty", "$$$", "rewarded", "VRP", 
    "reward-top-panel", "Reward-", "assigned", "award you", "decided to award"
]

# Scraper Settings
CONCURRENCY_LIMIT = 5 # Number of simultaneous pages/tabs
HEADLESS = True 
TIMEOUT = 60000 # 60 seconds
DELAY_BETWEEN_ISSUES = 2 # Seconds to wait between batches
MAX_SEARCH_PAGES = 100

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ISSUES_DIR, exist_ok=True)
