"""Phase 2: Extract data from individual issues.

Handles both live scraping (via Playwright) and offline reprocessing
of existing raw JSON files.
"""

import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright, BrowserContext

from vrp.config import (
    ISSUES_DIR, INDEX_FILE, QUEUE_FILE, HEADLESS, TIMEOUT,
    CONCURRENCY_LIMIT, DELAY_BETWEEN_ISSUES, USER_AGENT,
    BROWSER_RESTART_INTERVAL, BOUNTY_INDICATORS,
)
from vrp.parser import build_issue, parse_updates, collect_all_attachments
from vrp.utils import logger, save_json, load_json, download_file, sanitize_filename, create_progress


def _issue_dir(issue_id: str) -> Path:
    return ISSUES_DIR / issue_id


def _has_raw_data(issue_id: str) -> bool:
    d = _issue_dir(issue_id)
    return (d / "raw_updates.json").exists()


def _has_report(issue_id: str) -> bool:
    return (_issue_dir(issue_id) / "report.json").exists()


async def _extract_cookies(context: BrowserContext) -> dict:
    """Extract cookies from browser context for authenticated downloads."""
    cookies = await context.cookies()
    return {c["name"]: c["value"] for c in cookies}


async def scrape_issue(
    issue_id: str,
    context: BrowserContext,
    force: bool = False,
) -> bool:
    """Scrape a single issue from the Chromium Issue Tracker.

    Returns True if bounty report was found and saved.
    """
    idir = _issue_dir(issue_id)

    # Skip if already processed (unless force)
    if not force and _has_report(issue_id):
        return True

    url = f"https://issues.chromium.org/issues/{issue_id}"
    captured = {"updates": None, "metadata": None}

    async def on_response(response):
        try:
            ct = response.headers.get("content-type", "")
            if "json" not in ct:
                return
            if "updates" in response.url or "getIssue" in response.url:
                body = await response.text()
                if body.startswith(")]}'"):
                    body = body[4:].strip()
                data = json.loads(body)
                if "updates" in response.url:
                    captured["updates"] = data
                else:
                    captured["metadata"] = data
        except Exception as e:
            logger.debug(f"Response handler error for {issue_id}: {e}")

    page = await context.new_page()
    page.on("response", on_response)

    try:
        await page.goto(url, wait_until="networkidle", timeout=TIMEOUT)
        await asyncio.sleep(5)

        # Extract cookies after navigation so auth cookies are populated
        cookies = await _extract_cookies(context)

        # Quick bounty check on raw text before full parsing
        if captured["updates"]:
            all_text = json.dumps(captured["updates"]).lower()
            has_bounty_hint = any(
                ind.lower() in all_text for ind in BOUNTY_INDICATORS
            )
            if not has_bounty_hint:
                return False

        if not captured["updates"]:
            logger.warning(f"No updates captured for {issue_id}")
            return False

        # Save raw data first (for reprocessing later)
        idir.mkdir(parents=True, exist_ok=True)
        save_json(idir / "raw_updates.json", captured["updates"])
        if captured["metadata"]:
            save_json(idir / "raw_metadata.json", captured["metadata"])

        # Parse and build structured report
        issue = build_issue(issue_id, captured["updates"], captured["metadata"])
        if not issue:
            # Clean up raw files for non-bounty issues
            for f in idir.iterdir():
                f.unlink()
            idir.rmdir()
            return False

        logger.info(f"BOUNTY: {issue_id} - ${issue.bounty_amount or '?'} - {issue.title[:60]}")

        # Download attachments
        att_dir = idir / "attachments"
        for att in issue.attachments:
            fname = sanitize_filename(att.filename)
            local_path = att_dir / fname
            if not local_path.exists():
                ok = await download_file(
                    att.url, str(local_path), cookies=cookies,
                    expected_mime=att.mime_type,
                )
                if not ok:
                    att.local_path = None
                    continue
            att.local_path = f"attachments/{fname}"

        # Save enriched report
        save_json(idir / "report.json", issue.model_dump())

        return True

    except Exception as e:
        logger.error(f"Error scraping {issue_id}: {e}")
        return False
    finally:
        await page.close()


async def scrape_all(
    issue_ids: list[str] | None = None,
    force: bool = False,
    headless: bool = HEADLESS,
) -> int:
    """Scrape all queued issues.

    Args:
        issue_ids: Specific IDs to scrape. Defaults to discovery queue.
        force: Re-scrape even if report already exists.
        headless: Run browser in headless mode.

    Returns:
        Number of bounty reports found.
    """
    if issue_ids is None:
        queue = load_json(QUEUE_FILE)
        if not queue:
            logger.error("No discovery queue found. Run 'vrp discover' first.")
            return 0
        issue_ids = queue

    # Filter out already-processed unless force
    if not force:
        pending = [iid for iid in issue_ids if not _has_report(iid)]
        logger.info(f"Queue: {len(issue_ids)} total, {len(pending)} pending")
        issue_ids = pending
    else:
        logger.info(f"Queue: {len(issue_ids)} total (force mode)")

    if not issue_ids:
        logger.info("Nothing to scrape.")
        return 0

    bounty_count = 0
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(user_agent=USER_AGENT)

        processed = 0
        with create_progress() as progress:
            task = progress.add_task("Scraping issues", total=len(issue_ids))

            async def process_one(iid: str):
                nonlocal bounty_count, processed
                async with semaphore:
                    result = await scrape_issue(iid, context, force=force)
                    if result:
                        bounty_count += 1
                    processed += 1
                    progress.update(task, advance=1)
                    await asyncio.sleep(DELAY_BETWEEN_ISSUES)

            # Process in batches to allow periodic browser restart.
            # asyncio.gather(*tasks) fully awaits ALL tasks in the batch
            # (including their DELAY_BETWEEN_ISSUES sleeps) before we proceed,
            # so context.close() is only called after every task has released
            # its semaphore and completed. This prevents use-after-close races.
            batch_size = BROWSER_RESTART_INTERVAL
            for i in range(0, len(issue_ids), batch_size):
                batch = issue_ids[i : i + batch_size]
                tasks = [process_one(iid) for iid in batch]
                await asyncio.gather(*tasks)  # all batch tasks finish here

                # Safe to restart context — no in-flight tasks remain
                if i + batch_size < len(issue_ids):
                    logger.info("Restarting browser context...")
                    await context.close()
                    context = await browser.new_context(user_agent=USER_AGENT)

        await browser.close()

    logger.info(f"Scraping complete: {bounty_count} bounty reports found out of {len(issue_ids)} processed")
    return bounty_count


def reprocess_existing() -> int:
    """Re-parse all existing raw JSON files to generate enriched reports.

    This does NOT re-scrape -- it only processes already-downloaded data.
    Returns count of successfully reprocessed reports.
    """
    if not ISSUES_DIR.exists():
        logger.error("No issues directory found.")
        return 0

    issue_dirs = sorted([d for d in ISSUES_DIR.iterdir() if d.is_dir()])
    logger.info(f"Reprocessing {len(issue_dirs)} existing issues...")

    count = 0
    with create_progress() as progress:
        task = progress.add_task("Reprocessing", total=len(issue_dirs))

        for idir in issue_dirs:
            issue_id = idir.name

            raw_updates = load_json(idir / "raw_updates.json")
            raw_metadata = load_json(idir / "raw_metadata.json")

            if not raw_updates:
                progress.update(task, advance=1)
                continue

            issue = build_issue(issue_id, raw_updates, raw_metadata)
            if issue:
                # Update local_path for any existing attachment files
                att_dir = idir / "attachments"
                if att_dir.exists():
                    existing_files = {f.name for f in att_dir.iterdir() if f.is_file()}
                    for att in issue.attachments:
                        fname = sanitize_filename(att.filename)
                        if fname in existing_files:
                            att.local_path = f"attachments/{fname}"
                        else:
                            # If file isn't downloaded, clear local_path to avoid broken links
                            att.local_path = None

                save_json(idir / "report.json", issue.model_dump())
                count += 1

            progress.update(task, advance=1)

    logger.info(f"Reprocessed: {count} bounty reports updated")
    return count
