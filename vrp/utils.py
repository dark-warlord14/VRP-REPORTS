"""Shared utilities for VRP Reports."""

import asyncio
import json
import logging
import os
import re
from typing import Any, Optional

import aiohttp
from rich.logging import RichHandler
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

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
    """Load JSON from file, returns None if not found or corrupt."""
    filepath = str(filepath)
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Corrupt JSON at {filepath}: {e}")
        return None


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
    expected_mime: Optional[str] = None,
    session: Optional[aiohttp.ClientSession] = None,
) -> bool:
    """Download a file with retry and optional cookie auth.

    If expected_mime is provided and the server returns text/html instead
    (e.g. an auth redirect page), the download is rejected as failed.

    If session is provided, it is reused directly (caller owns its lifecycle).
    Otherwise a new session is created per attempt.
    """
    filepath = str(filepath)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    for attempt in range(max_retries):
        try:
            if session is not None:
                _sess = session
                _ctx = None
            else:
                jar = aiohttp.CookieJar()
                _ctx = aiohttp.ClientSession(cookie_jar=jar)
                _sess = await _ctx.__aenter__()

            try:
                if cookies and session is None:
                    for name, value in cookies.items():
                        _sess.cookie_jar.update_cookies({name: value})
                async with _sess.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        resp_ct = resp.headers.get("content-type", "")
                        # Reject HTML responses when we expect non-HTML content
                        # (indicates an auth redirect page was served instead of the file)
                        if (
                            expected_mime
                            and "html" not in expected_mime
                            and "text/html" in resp_ct
                        ):
                            logger.warning(
                                f"Download returned HTML for {url} (auth required?), skipping"
                            )
                            return False
                        tmp_path = filepath + ".partial"
                        try:
                            with open(tmp_path, "wb") as f:
                                async for chunk in resp.content.iter_chunked(1024 * 64):
                                    f.write(chunk)
                            os.replace(tmp_path, filepath)
                        except Exception:
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)
                            raise
                        return True
                    elif resp.status == 429:
                        wait = 2 ** (attempt + 1)
                        logger.warning(f"Rate limited on {url}, waiting {wait}s")
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"Download failed {url}: HTTP {resp.status}")
                        return False
            finally:
                if _ctx is not None:
                    await _ctx.__aexit__(None, None, None)
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
