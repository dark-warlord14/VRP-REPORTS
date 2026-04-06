"""Phase 1: Discover issue IDs from Chromium Issue Tracker search results.

Supports year-by-year discovery with per-year checkpointing.
"""

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

from vrp.config import (
    DATA_DIR,
    HEADLESS,
    MAX_SEARCH_PAGES,
    QUEUE_FILE,
    TIMEOUT,
    USER_AGENT,
    build_search_url,
    get_all_years,
)
from vrp.utils import load_json, logger, save_json


def _checkpoint_path(year: int) -> Path:
    return DATA_DIR / f"discovery_{year}.json"


async def discover_ids_for_year(year: int, headless: bool = HEADLESS, resume: bool = True) -> set[str]:
    """Discover all issue IDs for a specific year."""
    checkpoint = _checkpoint_path(year)

    # Load existing checkpoint (unless caller explicitly disables resume)
    if resume:
        existing = load_json(checkpoint)
        if existing:
            logger.info(f"[{year}] Loaded {len(existing)} IDs from checkpoint")
            return set(existing)

    search_url = build_search_url(year)
    logger.info(f"[{year}] Discovering issues: {search_url[:100]}...")

    issue_ids: set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        try:
            await page.goto(search_url, wait_until="networkidle", timeout=TIMEOUT)
            page_count = 0

            while page_count < MAX_SEARCH_PAGES:
                await asyncio.sleep(3)

                # Extract issue IDs from all links
                links = await page.locator("a").evaluate_all(
                    "elements => elements.map(e => e.href)"
                )
                found_new = 0
                for link in links:
                    match = re.search(r"/issues/(\d+)", link)
                    if match:
                        iid = match.group(1)
                        if iid != "0" and iid not in issue_ids:
                            issue_ids.add(iid)
                            found_new += 1

                logger.info(
                    f"[{year}] Page {page_count + 1}: +{found_new} new, "
                    f"{len(issue_ids)} total"
                )

                # Paginate
                next_btn = page.locator("button[aria-label='Go to next page']")
                if await next_btn.is_visible() and await next_btn.is_enabled():
                    await next_btn.click()
                    await page.wait_for_load_state("networkidle")
                    page_count += 1
                else:
                    logger.info(f"[{year}] Reached end of results at page {page_count + 1}")
                    break

        except Exception as e:
            logger.error(f"[{year}] Discovery error: {e}")
        finally:
            await page.close()
            await browser.close()

    # Save checkpoint
    if issue_ids:
        save_json(checkpoint, sorted(issue_ids))
        logger.info(f"[{year}] Saved checkpoint: {len(issue_ids)} IDs")

    return issue_ids


async def discover_all(
    years: list[int] | None = None,
    resume: bool = True,
    headless: bool = HEADLESS,
) -> list[str]:
    """Run discovery for all years and merge into master queue.

    Args:
        years: Specific years to discover. Defaults to all years (2015-current).
        resume: Skip years that already have checkpoints.
        headless: Run browser in headless mode.

    Returns:
        Sorted list of all discovered issue IDs.
    """
    if years is None:
        years = get_all_years()

    all_ids: set[str] = set()

    # Load existing master queue
    existing_queue = load_json(QUEUE_FILE)
    if existing_queue:
        all_ids.update(existing_queue)
        logger.info(f"Loaded {len(existing_queue)} IDs from existing queue")

    for year in sorted(years):
        checkpoint = _checkpoint_path(year)
        if resume and checkpoint.exists():
            cached = load_json(checkpoint) or []
            all_ids.update(cached)
            logger.info(f"[{year}] Skipped (checkpoint exists: {len(cached)} IDs)")
            continue

        year_ids = await discover_ids_for_year(year, headless=headless, resume=resume)
        all_ids.update(year_ids)

    # Save master queue
    sorted_ids = sorted(all_ids)
    save_json(QUEUE_FILE, sorted_ids)
    logger.info(f"Master queue updated: {len(sorted_ids)} total IDs")

    return sorted_ids
