"""Shared utilities for VRP Reports."""

import os
import json
import re
import asyncio
import logging
from typing import Any, Optional

import aiohttp
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("vrp")


# --- File I/O ---
def save_json(filepath: str | os.PathLike, data: Any) -> None:
    """Save data as JSON."""
    filepath = str(filepath)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def load_json(filepath: str | os.PathLike) -> Any:
    """Load JSON from file, returns None if not found."""
    filepath = str(filepath)
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def sanitize_filename(name: str) -> str:
    """Sanitize a filename, keeping it usable."""
    name = name.strip()
    # Replace problematic characters
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)
    return name or "unnamed"


# --- Network ---
async def download_file(
    url: str,
    filepath: str | os.PathLike,
    cookies: Optional[dict] = None,
    max_retries: int = 3,
) -> bool:
    """Download a file with retry and optional cookie auth."""
    filepath = str(filepath)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    for attempt in range(max_retries):
        try:
            jar = aiohttp.CookieJar()
            async with aiohttp.ClientSession(cookie_jar=jar) as session:
                if cookies:
                    for name, value in cookies.items():
                        jar.update_cookies({name: value})
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        with open(filepath, "wb") as f:
                            f.write(await resp.read())
                        return True
                    elif resp.status == 429:
                        wait = 2 ** (attempt + 1)
                        logger.warning(f"Rate limited on {url}, waiting {wait}s")
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"Download failed {url}: HTTP {resp.status}")
                        return False
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.warning(f"Download error {url}: {e}, retrying in {wait}s")
                await asyncio.sleep(wait)
            else:
                logger.error(f"Download failed after {max_retries} attempts: {url}: {e}")
    return False


# --- Progress ---
def create_progress() -> Progress:
    """Create a Rich progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[green]{task.completed}/{task.total}"),
    )
