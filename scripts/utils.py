import os
import json
import logging
import aiohttp
import asyncio
from typing import Dict, Any, List

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VRP_Scraper")

def save_json(filepath: str, data: Any):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_json(filepath: str) -> Any:
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

async def download_file(url: str, filepath: str):
    """Downloads a file from a URL to a local path."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(filepath, 'wb') as f:
                        f.write(await response.read())
                    return True
                else:
                    logger.error(f"Failed to download {url}: {response.status}")
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
    return False

def update_index(index_file: str, issue_data: Dict[str, Any]):
    """Appends an issue's summary to the index file."""
    index = load_json(index_file) or []
    # Avoid duplicates
    index = [item for item in index if item["id"] != issue_data["id"]]
    index.append(issue_data)
    save_json(index_file, index)
